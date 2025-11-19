"""
Test for anchor-based position-value filtering.
Verifies that the improved _apply_uncertain_position_value_filter correctly
handles ordering constraints when a player has copies of a value.
"""

from src.belief.belief_model import BeliefModel
from src.data_structures import GameObservation, CallRecord
from config.game_config import GameConfig


def test_value_10_ordering_constraint():
    """
    Test case from user example:
    - Ettore (player 0) has a copy of value 10
    - Positions 4-9 have revealed values: [11, 11, 11, 11, 12, 12]
    - Value 10 has max 4 copies total, if Ettore has 1, max 3 remaining
    - For other player, value 10 can only be in positions 1, 2, 3
    - It CANNOT be in position 0 due to ordering (would need 4 positions before the 11s)
    
    Expected behavior:
    - Position 0 should NOT contain value 10 after filtering
    - Positions 1, 2, 3 should still allow value 10
    """
    config = GameConfig(n_players=2)  # 2 players for simplicity
    
    # Player 0 (Ettore) wire: [?, ?, ?, ?, 11, 11, 11, 11, 12, 12]
    # where one of the ?s is value 10
    my_wire = [10, 9, 8, 7, 11, 11, 11, 11, 12, 12]
    
    observation = GameObservation(
        player_id=0,
        my_wire=my_wire,
        call_history=[],
        double_reveal_history=[],
        swap_history=[]
    )
    
    belief = BeliefModel(observation, config)
    
    # Simulate revealing positions 4-9 for player 0
    for pos in range(4, 10):
        value = my_wire[pos]
        belief.beliefs[0][pos] = {value}
        belief.value_trackers[value].add_revealed(0, pos)
    
    # Apply the filter
    belief._apply_uncertain_position_value_filter()
    
    # Check player 1's beliefs (the other player from Ettore's perspective)
    player1_beliefs = belief.beliefs[1]
    
    print("\nPlayer 1 beliefs after filtering:")
    for pos in range(10):
        values = sorted(list(player1_beliefs[pos]))
        print(f"  Position {pos}: {values} ({len(values)} possibilities)")
    
    # Value 10 should NOT be in position 0
    assert 10 not in player1_beliefs[0], \
        f"Value 10 should not be in position 0, but found: {player1_beliefs[0]}"
    
    # Value 10 SHOULD still be possible in positions 1, 2, 3
    for pos in [1, 2, 3]:
        assert 10 in player1_beliefs[pos], \
            f"Value 10 should be possible in position {pos}, but found: {player1_beliefs[pos]}"
    
    print("\n✓ Test passed! Value 10 correctly eliminated from position 0")


def test_anchor_based_filtering_comprehensive():
    """
    More comprehensive test of anchor-based filtering.
    """
    config = GameConfig(n_players=2)
    
    # Player 0 wire: [1, 2, 3, 4, 11, 11, 11, 11, 12, 12]
    my_wire = [1, 2, 3, 4, 11, 11, 11, 11, 12, 12]
    
    observation = GameObservation(
        player_id=0,
        my_wire=my_wire,
        call_history=[],
        double_reveal_history=[],
        swap_history=[]
    )
    
    belief = BeliefModel(observation, config)
    
    # Reveal all of player 0's wire
    for pos in range(10):
        value = my_wire[pos]
        belief.beliefs[0][pos] = {value}
        if pos < 4:  # Don't double-add for positions already marked in initialization
            belief.value_trackers[value].add_revealed(0, pos)
    
    # Apply the filter
    belief._apply_uncertain_position_value_filter()
    
    # Check player 1's beliefs
    player1_beliefs = belief.beliefs[1]
    
    print("\nPlayer 1 beliefs after comprehensive filtering:")
    for pos in range(10):
        values = sorted(list(player1_beliefs[pos]))
        print(f"  Position {pos}: {values} ({len(values)} possibilities)")
    
    # Low values (1-4) are all used by player 0, so player 1 cannot have them
    for value in [1, 2, 3, 4]:
        for pos in range(10):
            assert value not in player1_beliefs[pos], \
                f"Value {value} should not be possible for player 1 at any position"
    
    # Player 1 must have values from the remaining pool
    # Since player 0 has all 11s and 12s, player 1 cannot have them
    for value in [11, 12]:
        for pos in range(10):
            assert value not in player1_beliefs[pos], \
                f"Value {value} should not be possible for player 1 (all copies with player 0)"
    
    print("\n✓ Comprehensive test passed!")


if __name__ == "__main__":
    test_value_10_ordering_constraint()
    test_anchor_based_filtering_comprehensive()
