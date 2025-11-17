"""
Simple test script for BombBuster game.
Tests Player and Game classes without belief system.
"""

from src.player import Player
from src.game import Game
from src.utils import generate_wires, print_all_wires
from config.game_config import GameConfig


def test_basic_game():
    """Test basic game setup and calls without belief system."""
    print("\n" + "="*70)
    print("TEST: Basic Game Setup and Calls")
    print("="*70)
    
    # Create configuration
    config = GameConfig(n_players=3, max_wrong_calls=3)
    print(f"\nGame Config:")
    print(f"  Values: {config.wire_values}")
    print(f"  Wire distribution: {config.wire_distribution}")
    print(f"  Players: {config.n_players}")
    print(f"  Wires per player: {config.wires_per_player}")
    print(f"  Max wrong calls: {config.max_wrong_calls}")
    
    # Generate wires
    wires = generate_wires(config, seed=42)
    print_all_wires(wires)
    
    # Create players
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    print(f"Created {len(players)} players")
    
    # Test player methods
    print("\n" + "="*70)
    print("TEST: Player Methods")
    print("="*70)
    
    player0 = players[0]
    print(f"\nPlayer 0 wire: {player0.get_wire()}")
    print(f"Player 0 certain values: {player0.get_certain_values()}")
    print(f"Player 0 has value 3? {player0.has_value(3)}")
    print(f"Player 0 value at position 0: {player0.get_value_at_position(0)}")
    
    # Create game
    game = Game(players, config)
    print(f"\n" + "="*70)
    print("TEST: Game Creation and State")
    print("="*70)
    print(f"Game created successfully")
    print(f"Initial state: {game.get_game_state()}")
    
    # Test some calls
    print(f"\n" + "="*70)
    print("TEST: Making Calls")
    print("="*70)
    
    # Correct call: Player 0 calls Player 1, position 0
    target_value = wires[1][0]
    print(f"\nPlayer 0 calls Player 1, position 0, value {target_value}")
    success = (target_value == wires[1][0])
    call1 = game.make_call(caller_id=0, target_id=1, position=0, value=target_value, success=success)
    print(f"Result: {call1}")
    print(f"Game state: {game.get_game_state()}")
    
    # Wrong call: Player 1 calls Player 2, position 1 with wrong value
    wrong_value = 999 if 999 not in wires[2] else 1
    # Pick a value player 1 has that player 2 doesn't have at position 1
    actual_value = wires[2][1]
    wrong_value = [v for v in wires[1] if v != actual_value][0]
    print(f"\nPlayer 1 calls Player 2, position 1, value {wrong_value} (actual: {actual_value})")
    call2 = game.make_call(caller_id=1, target_id=2, position=1, value=wrong_value, success=False)
    print(f"Result: {call2}")
    print(f"Game state: {game.get_game_state()}")
    
    # Another correct call
    target_value2 = wires[0][2]
    print(f"\nPlayer 2 calls Player 0, position 2, value {target_value2}")
    success2 = (target_value2 == wires[0][2])
    call3 = game.make_call(caller_id=2, target_id=0, position=2, value=target_value2, success=success2)
    print(f"Result: {call3}")
    print(f"Game state: {game.get_game_state()}")
    
    # Test validation errors
    print(f"\n" + "="*70)
    print("TEST: Call Validation")
    print("="*70)
    
    try:
        game.make_call(caller_id=0, target_id=0, position=0, value=1, success=True)
        print("ERROR: Should have raised ValueError for calling self")
    except ValueError as e:
        print(f"✓ Correctly rejected self-call: {e}")
    
    try:
        game.make_call(caller_id=0, target_id=1, position=999, value=1, success=True)
        print("ERROR: Should have raised ValueError for invalid position")
    except ValueError as e:
        print(f"✓ Correctly rejected invalid position: {e}")
    
    # Test game over (max wrong calls)
    print(f"\n" + "="*70)
    print("TEST: Game Over Conditions")
    print("="*70)
    
    remaining = game.get_wrong_calls_remaining()
    print(f"\nWrong calls remaining: {remaining}")
    print(f"Making {remaining} more wrong calls to trigger loss...")
    
    for i in range(remaining):
        game.make_call(caller_id=0, target_id=1, position=0, value=1, success=False)
        print(f"  Wrong call {i+1}: {game.get_game_state()}")
    
    print(f"\nGame over? {game.is_game_over()}")
    print(f"Team won? {game.has_team_won()}")
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETED")
    print("="*70)


if __name__ == "__main__":
    test_basic_game()

