"""
Test cases for the new signal features: copy count and adjacent signals.
"""

from src.game import Game
from src.player import Player
from config.game_config import GameConfig


def test_copy_count_signal():
    """Test that copy count signal correctly filters belief sets."""
    
    # Setup: Simple 2-player game with known distribution
    config = GameConfig(
        n_players=2,
        wires_per_player=3,
        wire_distribution={1: 2, 2: 2, 3: 2},
        max_wrong_calls=3,
        auto_filter=True,
        use_global_belief=False,
        playing_irl=False
    )
    
    # Player 0: [1, 2, 3]
    # Player 1: [1, 2, 3]
    player0 = Player(0, [1, 2, 3], config)
    player1 = Player(1, [1, 2, 3], config)
    
    game = Game([player0, player1], config)
    
    # Initial beliefs should include all values for all positions
    assert 1 in player0.belief_system.beliefs[1][0]
    assert 2 in player0.belief_system.beliefs[1][0]
    assert 3 in player0.belief_system.beliefs[1][0]
    
    # Player 1 signals that position 0 has a value with 2 copies
    # All values have 2 copies, so this shouldn't filter anything in this case
    game.signal_copy_count(player_id=1, position=0, copy_count=2)
    
    # All values should still be possible
    assert 1 in player0.belief_system.beliefs[1][0]
    assert 2 in player0.belief_system.beliefs[1][0]
    assert 3 in player0.belief_system.beliefs[1][0]
    
    print("✓ Copy count signal test passed")


def test_copy_count_signal_with_filtering():
    """Test copy count signal with mixed distribution."""
    
    # Setup with mixed distribution
    config = GameConfig(
        n_players=2,
        wires_per_player=4,
        wire_distribution={1: 1, 2: 2, 3: 3, 4: 2},
        max_wrong_calls=3,
        auto_filter=True,
        use_global_belief=False,
        playing_irl=False
    )
    
    # Player 0: [1, 2, 3, 4]
    # Player 1: [2, 3, 3, 4]
    player0 = Player(0, [1, 2, 3, 4], config)
    player1 = Player(1, [2, 3, 3, 4], config)
    
    game = Game([player0, player1], config)
    
    # Player 1 signals that position 2 has a value with 3 copies
    # Only value 3 has 3 copies
    game.signal_copy_count(player_id=1, position=2, copy_count=3)
    
    # Position 2 should now only have value 3 as possible
    beliefs = player0.belief_system.beliefs[1][2]
    assert 3 in beliefs
    assert len(beliefs) == 1, f"Expected only value 3, got {beliefs}"
    
    print("✓ Copy count filtering test passed")


def test_adjacent_signal_equal():
    """Test adjacent signal with equal values."""
    
    config = GameConfig(
        n_players=2,
        wires_per_player=3,
        wire_distribution={1: 2, 2: 2, 3: 2},
        max_wrong_calls=3,
        auto_filter=True,
        use_global_belief=False,
        playing_irl=False
    )
    
    # Player 0: [1, 2, 3]
    # Player 1: [1, 2, 3]
    player0 = Player(0, [1, 2, 3], config)
    player1 = Player(1, [1, 2, 3], config)
    
    game = Game([player0, player1], config)
    
    # Player 1 signals that positions 0 and 1 have the same value
    # Both should be constrained to their intersection
    game.signal_adjacent(player_id=1, position1=0, position2=1, is_equal=True)
    
    # Both positions should have the same belief set
    beliefs0 = player0.belief_system.beliefs[1][0]
    beliefs1 = player0.belief_system.beliefs[1][1]
    assert beliefs0 == beliefs1
    
    print("✓ Adjacent equal signal test passed")


def test_adjacent_signal_different():
    """Test adjacent signal with different values."""
    
    config = GameConfig(
        n_players=2,
        wires_per_player=3,
        wire_distribution={1: 2, 2: 2, 3: 2},
        max_wrong_calls=3,
        auto_filter=True,
        use_global_belief=False,
        playing_irl=False
    )
    
    # Player 0: [1, 2, 3]
    # Player 1: [1, 2, 3]
    player0 = Player(0, [1, 2, 3], config)
    player1 = Player(1, [1, 2, 3], config)
    
    game = Game([player0, player1], config)
    
    # First, make position 0 certain by revealing it
    game.reveal_value(player_id=1, value=1, position=0)
    
    # Now signal that positions 0 and 1 have different values
    game.signal_adjacent(player_id=1, position1=0, position2=1, is_equal=False)
    
    # Position 1 should not contain value 1
    beliefs1 = player0.belief_system.beliefs[1][1]
    assert 1 not in beliefs1, f"Position 1 should not contain value 1, got {beliefs1}"
    assert 2 in beliefs1 or 3 in beliefs1
    
    print("✓ Adjacent different signal test passed")


def test_signal_validation():
    """Test that validation works correctly for new signals."""
    
    config = GameConfig(
        n_players=2,
        wires_per_player=3,
        wire_distribution={1: 2, 2: 2, 3: 2},
        max_wrong_calls=3,
        auto_filter=True,
        use_global_belief=False,
        playing_irl=False
    )
    
    player0 = Player(0, [1, 2, 3], config)
    player1 = Player(1, [1, 2, 3], config)
    
    game = Game([player0, player1], config)
    
    # Test invalid copy count
    try:
        game.signal_copy_count(player_id=0, position=0, copy_count=4)
        assert False, "Should have raised ValueError for invalid copy count"
    except ValueError as e:
        assert "copy_count" in str(e).lower()
    
    # Test non-adjacent positions
    try:
        game.signal_adjacent(player_id=0, position1=0, position2=2, is_equal=True)
        assert False, "Should have raised ValueError for non-adjacent positions"
    except ValueError as e:
        assert "adjacent" in str(e).lower()
    
    print("✓ Signal validation test passed")


if __name__ == "__main__":
    test_copy_count_signal()
    test_copy_count_signal_with_filtering()
    test_adjacent_signal_equal()
    test_adjacent_signal_different()
    test_signal_validation()
    print("\n✓ All new signal tests passed!")
