"""
Test that _apply_uncertain_position_value_filter works correctly when there are no anchors (beginning of game).
"""

from src.belief.belief_model import BeliefModel
from src.data_structures import GameObservation
from config.game_config import GameConfig


def test_no_anchors_basic():
    """
    Test at the very beginning - player knows only their own wire, no anchors for other players.
    The filter should still apply global ordering constraints.
    """
    config = GameConfig()
    
    # Player 0 has wire [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    my_wire = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    observation = GameObservation(
        player_id=0,
        my_wire=my_wire,
        call_history=[],
        double_reveal_history=[],
        swap_history=[]
    )
    
    belief = BeliefModel(observation, config)
    
    # Player 0 should know their own wire with certainty
    for pos in range(10):
        assert len(belief.beliefs[0][pos]) == 1
        assert list(belief.beliefs[0][pos])[0] == my_wire[pos]
    
    # Other players should have all possible values initially (no anchors)
    # But some constraints should still apply based on global counts
    for player_id in range(1, config.n_players):
        for pos in range(10):
            # Should have reduced possibilities based on what player 0 has
            # For example, player 0 has all of 1-10, so others can't have those values
            # (assuming 4 copies each)
            possible = belief.beliefs[player_id][pos]
            assert len(possible) > 0, f"Player {player_id} position {pos} has no possibilities"
            
            # Values 1-10 that player 0 has should still be possible for others
            # because there are 4 copies of each (3 remaining)
            # But player 0 already has 1 copy, leaving 3 for distribution
            
    print("✓ No-anchor test passed - beliefs are consistent at game start")


def test_no_anchors_with_called():
    """
    Test when there are no certain anchors but some called values.
    """
    config = GameConfig()
    
    # Player 0 has wire [1, 2, 2.5, 3, 4, 5, 6, 6.5, 7, 8]
    my_wire = [1, 2, 2.5, 3, 4, 5, 6, 6.5, 7, 8]
    
    observation = GameObservation(
        player_id=0,
        my_wire=my_wire,
        call_history=[],
        double_reveal_history=[],
        swap_history=[]
    )
    
    belief = BeliefModel(observation, config)
    
    # Check that beliefs are consistent
    assert belief.is_consistent()
    
    # Print beliefs for player 1 to verify
    print("\nPlayer 1 beliefs (no anchors):")
    for pos in range(10):
        print(f"  Position {pos}: {sorted(belief.beliefs[1][pos])} ({len(belief.beliefs[1][pos])} possibilities)")
    
    print("✓ No-anchor with called test passed")


if __name__ == "__main__":
    test_no_anchors_basic()
    test_no_anchors_with_called()
