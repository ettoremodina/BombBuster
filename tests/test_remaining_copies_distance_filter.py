"""
Test the remaining copies distance filter implementation.
This filter eliminates values from positions when placing that value would
leave no valid values for intermediate positions between anchors.
"""

from src.belief.belief_model import BeliefModel
from src.data_structures import GameObservation, CallRecord, SignalRecord
from config.game_config import GameConfig


def test_example_1_y4_cannot_be_10():
    """
    Test Example 1: ...11-11-11-11-y1-y2-y3-y4... and another player has a 10
    
    Setup:
    - Player 0 has: 11-11-11-11-?-?-?-? (4 known 11s, then 4 unknowns)
    - Player 1 has a 10 somewhere (signaled or certain)
    - Only 3 copies of 10 remain available for player 0
    
    Expected: y4 (position 7) cannot be 10
    Because if y4=10, y3=10, y2=10, then y1 would have no valid value
    """
    # Create a simple config with values 10, 11, 12 and multiple copies
    config = GameConfig(
        wire_distribution={10: 4, 11: 4, 12: 4},
        n_players=2,
        max_wrong_calls=5
    )
    
    # Player 0's wire: we know positions 0-3 are 11, positions 4-7 are unknown
    player_wire = [11, 11, 11, 11, 10, 10, 10, 12]  # True wire (player knows all)
    
    # Create observation for player 0
    observation = GameObservation(
        player_id=0,
        my_wire=player_wire,
        my_revealed_positions={},
        call_history=[],
        n_players=2,
        wire_length=8
    )
    
    # Create belief model
    belief = BeliefModel(observation, config)
    
    # Signal that player 1 has a 10 (reducing available copies to 3 for player 0)
    signal = SignalRecord(player_id=1, value=10, position=0, turn_number=1)
    belief.process_signal(signal)
    
    # After processing, check beliefs for player 0
    # Positions 4, 5, 6 should potentially have 10
    # Position 7 should NOT have 10 (y4 cannot be 10)
    
    print("Player 0 beliefs after signaling player 1 has a 10:")
    for pos in range(8):
        print(f"  Position {pos}: {belief.beliefs[0][pos]}")
    
    # The filter should remove 10 from position 7
    assert 10 not in belief.beliefs[0][7], f"Position 7 should not contain 10, but has: {belief.beliefs[0][7]}"
    
    print("✓ Test passed: y4 (position 7) correctly cannot be 10")


def test_example_2_y2_cannot_be_3():
    """
    Test Example 2: 3-y1-y2-1 and another player has two 3s
    
    Setup:
    - Player 0 has: 3-?-?-1 (positions 0 and 3 known, positions 1 and 2 unknown)
    - Two other players have 3s (leaving only 1 copy for player 0 - which is at position 0)
    - Actually, we need only 1 remaining 3 for the uncertain positions
    
    Expected: y2 (position 2) cannot be 3
    Because if y2=3, then y1 would need a value between 3 and 3 (impossible)
    """
    # Create a simple config with values 1, 2, 3 and multiple copies
    config = GameConfig(
        wire_distribution={1: 4, 2: 4, 3: 4},
        n_players=3,
        max_wrong_calls=5
    )
    
    # Player 0's wire: position 0 = 3, positions 1-2 unknown, position 3 = 1
    # Let's say the true wire is [3, 2, 2, 1] but we're testing belief constraints
    player_wire = [3, 2, 2, 1]
    
    # Create observation for player 0
    observation = GameObservation(
        player_id=0,
        my_wire=player_wire,
        my_revealed_positions={},
        call_history=[],
        n_players=3,
        wire_length=4
    )
    
    # Create belief model
    belief = BeliefModel(observation, config)
    
    # Signal that player 1 has a 3
    signal1 = SignalRecord(player_id=1, value=3, position=0, turn_number=1)
    belief.process_signal(signal1)
    
    # Signal that player 2 has a 3
    signal2 = SignalRecord(player_id=2, value=3, position=0, turn_number=2)
    belief.process_signal(signal2)
    
    # Now player 0 has 3 at position 0, and two other players have 3s
    # This means there's only 1 copy of 3 remaining uncertain (but player 0 already has it at pos 0)
    # So no more 3s should be possible for player 0's uncertain positions
    
    print("\nPlayer 0 beliefs after signaling two other players have 3:")
    for pos in range(4):
        print(f"  Position {pos}: {belief.beliefs[0][pos]}")
    
    # Position 2 should not have 3
    # Actually, since player 0 already has 3 at position 0 (certain), and two others have it,
    # there should be no more 3s available for positions 1 and 2
    
    # The filter should remove 3 from positions 1 and 2
    assert 3 not in belief.beliefs[0][1], f"Position 1 should not contain 3, but has: {belief.beliefs[0][1]}"
    assert 3 not in belief.beliefs[0][2], f"Position 2 should not contain 3, but has: {belief.beliefs[0][2]}"
    
    print("✓ Test passed: y1 and y2 correctly cannot be 3")


def test_no_removal_when_single_value():
    """
    Test that the filter never removes a value when it's the only one in the set.
    This is a safety check to ensure we don't create contradictions.
    """
    config = GameConfig(
        wire_distribution={1: 4, 2: 4, 3: 4},
        n_players=2,
        max_wrong_calls=5
    )
    
    player_wire = [1, 2, 3, 3]
    
    observation = GameObservation(
        player_id=0,
        my_wire=player_wire,
        my_revealed_positions={},
        call_history=[],
        n_players=2,
        wire_length=4
    )
    
    belief = BeliefModel(observation, config)
    
    # Manually set position 2 to have only one value
    belief.beliefs[0][2] = {3}
    
    # Apply filters
    belief.apply_filters()
    
    # Check that position 2 still has the value 3
    assert len(belief.beliefs[0][2]) == 1, f"Position 2 should still have exactly 1 value, but has: {belief.beliefs[0][2]}"
    assert 3 in belief.beliefs[0][2], f"Position 2 should still contain 3, but has: {belief.beliefs[0][2]}"
    
    print("\n✓ Test passed: Filter does not remove values when set size is 1")


if __name__ == "__main__":
    test_example_1_y4_cannot_be_10()
    test_example_2_y2_cannot_be_3()
    test_no_removal_when_single_value()
    print("\n✅ All tests passed!")
