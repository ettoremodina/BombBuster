"""
Test wire swap functionality.
"""

from config.game_config import GameConfig
from src.player import Player
from src.game import Game


def test_swap_basic():
    """Test basic swap functionality with IRL mode."""
    
    # Create simple config
    config = GameConfig(
        wire_distribution={1: 2, 2: 2, 3: 2},  # 2 copies each
        n_players=3,
        playing_irl=True  # Skip validation
    )
    
    # Create players with known wires
    wires = [
        [1, 2],  # Player 0
        [1, 3],  # Player 1
        [2, 3],  # Player 2
    ]
    
    players = [Player(i, wires[i], config) for i in range(3)]
    game = Game(players, config)
    
    print("Initial wires:")
    for i, p in enumerate(players):
        print(f"  Player {i}: {p.wire}")
    
    # Swap: Player 0[1]=2 with Player 1[1]=3
    # Player 0 gives away position 1 (value 2), receives value 3, should go to position 1
    # Player 1 gives away position 1 (value 3), receives value 2, should go to position 1
    result = game.swap_wires(
        player1_id=0, player2_id=1,
        init_pos1=1, init_pos2=1,
        final_pos1=1, final_pos2=1
    )
    
    print(f"\nSwap executed: {result}")
    print("\nFinal wires:")
    for i, p in enumerate(players):
        print(f"  Player {i}: {p.wire}")
    
    # Verify wires changed
    assert players[0].wire == [1, 3], f"Player 0 should have [1, 3], got {players[0].wire}"
    assert players[1].wire == [1, 2], f"Player 1 should have [1, 2], got {players[1].wire}"
    
    # Verify beliefs were updated
    p0_belief = players[0].belief_system
    p1_belief = players[1].belief_system
    
    # Player 0 now knows they have value 3 at position 1
    assert 3 in p0_belief.beliefs[0][1], "Player 0 should know they have 3 at position 1"
    
    # Player 1 now knows they have value 2 at position 1
    assert 2 in p1_belief.beliefs[1][1], "Player 1 should know they have 2 at position 1"
    
    print("\n✓ Basic swap test passed")


def test_swap_with_sorting():
    """Test swap where wires need to be inserted at different positions."""
    
    config = GameConfig(
        wire_distribution={1: 2, 2: 2, 3: 2, 4: 2, 5: 2},
        n_players=2,
        playing_irl=False  # Enable validation to check sorting
    )
    
    # Create wires
    wires = [
        [1, 2, 3, 4, 5],  # Player 0
        [1, 2, 3, 4, 5],  # Player 1
    ]
    
    players = [Player(i, wires[i], config) for i in range(2)]
    game = Game(players, config)
    
    print("\nInitial wires:")
    for i, p in enumerate(players):
        print(f"  Player {i}: {p.wire}")
    
    # Swap: Player 0[1]=2 with Player 1[3]=4
    # Player 0 gives 2, receives 4 -> should go after 3 (position 2 or 3)
    # Player 1 gives 4, receives 2 -> should go after 1 (position 1 or 2)
    
    # After removing 2 from [1,2,3,4,5], we have [1,3,4,5]
    # Inserting 4 at position 2 gives [1,3,4,4,5]
    # Wait, that's not right... let me reconsider
    
    # After Player 0 removes position 1 (value 2): [1, 3, 4, 5]
    # We want to insert value 4 -> it should go at position 2 to get [1, 3, 4, 4, 5]
    # But we have 4 already... this won't work with these values
    
    # Let me use different starting wires
    players[0].wire = [1, 3, 4, 5, 5]
    players[1].wire = [1, 2, 2, 4, 5]
    
    print("\nAdjusted wires:")
    for i, p in enumerate(players):
        print(f"  Player {i}: {p.wire}")
    
    # Swap: Player 0[1]=3 with Player 1[1]=2
    # Player 0: remove 3 from [1,3,4,5,5] -> [1,4,5,5], insert 2 at position 1 -> [1,2,4,5,5]
    # Player 1: remove 2 from [1,2,2,4,5] -> [1,2,4,5], insert 3 at position 2 -> [1,2,3,4,5]
    
    result = game.swap_wires(
        player1_id=0, player2_id=1,
        init_pos1=1, init_pos2=1,
        final_pos1=1, final_pos2=2
    )
    
    print(f"\nSwap executed: {result}")
    print("\nFinal wires:")
    for i, p in enumerate(players):
        print(f"  Player {i}: {p.wire}")
    
    # Verify sorting maintained
    assert players[0].wire == sorted(players[0].wire), f"Player 0 wire not sorted: {players[0].wire}"
    assert players[1].wire == sorted(players[1].wire), f"Player 1 wire not sorted: {players[1].wire}"
    
    assert players[0].wire == [1, 2, 4, 5, 5], f"Player 0 expected [1, 2, 4, 5, 5], got {players[0].wire}"
    assert players[1].wire == [1, 2, 3, 4, 5], f"Player 1 expected [1, 2, 3, 4, 5], got {players[1].wire}"
    
    print("\n✓ Swap with sorting test passed")


if __name__ == "__main__":
    print("=" * 70)
    print("Testing Wire Swap Functionality")
    print("=" * 70)
    
    print("\n1. Basic swap (IRL mode)")
    test_swap_basic()
    
    print("\n2. Swap with sorting validation")
    test_swap_with_sorting()
    
    print("\n" + "=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)
