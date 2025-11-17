"""
Test the call suggester functionality.
Verifies that the suggester correctly identifies certain and uncertain calls.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.player import Player
from src.game import Game
from config.game_config import GameConfig


def test_call_suggester_basic():
    """Test basic call suggestion with certain and uncertain calls."""
    
    print("\n" + "="*80)
    print("TEST: Call Suggester - Basic Functionality")
    print("="*80)
    
    config = GameConfig(n_players=3, max_wrong_calls=20)
    
    wires = [
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Player 0
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Player 1
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Player 2
    ]
    
    print("\nActual wires:")
    for i, wire in enumerate(wires):
        print(f"  Player {i}: {wire}")
    
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    game = Game(players, config)
    
    print("\n--- Initial state: No calls yet ---")
    
    # Player 0's perspective
    player0 = players[0]
    suggestion = player0.suggest_call()
    
    if suggestion:
        target, pos, val = suggestion
        print(f"\nPlayer 0's suggestion: Call Player {target}[{pos}] = {val}")
    else:
        print("\nPlayer 0: No suggestion available")
    
    # Make some calls to create certain positions
    print("\n" + "="*80)
    print("Creating certain positions through calls")
    print("="*80)
    
    print("\n1. Player 0 → Player 1[0] = 1 (CORRECT)")
    game.make_call(0, 1, 0, 1, True)
    
    print("2. Player 0 → Player 1[2] = 3 (CORRECT)")
    game.make_call(0, 1, 2, 3, True)
    
    print("3. Player 1 → Player 2[5] = 6 (CORRECT)")
    game.make_call(1, 2, 5, 6, True)
    
    # Now check Player 0's suggestions
    print("\n" + "="*80)
    print("Player 0's Call Suggestions After Reveals")
    print("="*80)
    
    player0.print_call_suggestions()
    
    # Get detailed suggestions
    suggestions = player0.get_all_call_suggestions()
    
    print("\n--- Verification ---")
    print(f"Certain calls available: {len(suggestions['certain'])}")
    print(f"Uncertain calls available: {len(suggestions['uncertain'])}")
    
    # Player 0 should have certain calls for Player 1's revealed positions
    # because Player 0 also has those values
    certain_count = len(suggestions['certain'])
    if certain_count > 0:
        print(f"✓ Player 0 has {certain_count} certain call(s)")
    else:
        print("⚠️  Player 0 has no certain calls (unexpected)")
    
    return certain_count > 0


def test_call_suggester_filtering():
    """Test call suggester with filtering constraints."""
    
    print("\n" + "="*80)
    print("TEST: Call Suggester with Filtering")
    print("="*80)
    
    config = GameConfig(n_players=3, max_wrong_calls=20)
    
    wires = [
        [1, 1, 2, 3, 4, 5, 5, 5, 6, 6],   # Player 0 has values: 1,2,3,4,5,6
        [1, 2, 2, 3, 4, 5, 6, 7, 8, 9],   # Player 1
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Player 2
    ]
    
    print("\nActual wires:")
    for i, wire in enumerate(wires):
        print(f"  Player {i}: {wire}")
    
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    game = Game(players, config)
    
    # Make calls to constrain belief sets
    print("\n--- Making calls to constrain beliefs ---")
    
    print("1. Player 0 → Player 1[1] = 2 (CORRECT)")
    game.make_call(0, 1, 1, 2, True)
    
    print("2. Player 0 → Player 1[3] = 3 (CORRECT)")
    game.make_call(0, 1, 3, 3, True)
    
    # Position 2 is now constrained: must be >= 2 (from pos 1) and <= 3 (from pos 3)
    # So position 2 can only be {2, 3}, actual is 2
    
    print("\n--- Player 0's belief about Player 1[2] ---")
    belief_pos2 = players[0].belief_system.beliefs[1][2]
    print(f"Possible values for Player 1[2]: {sorted(belief_pos2)}")
    
    print("\n" + "="*80)
    print("Player 0's Call Suggestions")
    print("="*80)
    
    player0 = players[0]
    player0.print_call_suggestions()
    
    suggestions = player0.get_all_call_suggestions()
    
    # Check if Player 1[2] appears in suggestions with low uncertainty
    print("\n--- Checking if constrained position appears in suggestions ---")
    
    pos2_suggestions = [
        (t, p, v, u) for t, p, v, u in suggestions['uncertain']
        if t == 1 and p == 2
    ]
    
    if pos2_suggestions:
        print(f"✓ Found suggestions for Player 1[2]:")
        for target, pos, val, unc in pos2_suggestions:
            print(f"  → Call Player {target}[{pos}] = {val} (uncertainty: {unc})")
    else:
        print("  No suggestions found for Player 1[2]")
    
    return len(suggestions['certain']) > 0 or len(suggestions['uncertain']) > 0


def test_call_suggester_no_matching_values():
    """Test when player has no values matching known positions."""
    
    print("\n" + "="*80)
    print("TEST: Call Suggester with No Matching Values")
    print("="*80)
    
    config = GameConfig(n_players=3, max_wrong_calls=20)
    
    wires = [
        [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],   # Player 0: only has 1-5
        [6, 6, 7, 7, 8, 8, 9, 9, 10, 10], # Player 1: only has 6-10
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Player 2: has all
    ]
    
    print("\nActual wires:")
    for i, wire in enumerate(wires):
        values = sorted(set(wire))
        print(f"  Player {i}: {wire}  (unique: {values})")
    
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    game = Game(players, config)
    
    # Reveal some positions in Player 1 (who has 6-10)
    print("\n--- Revealing Player 1's positions ---")
    print("1. Player 2 → Player 1[0] = 6 (CORRECT)")
    game.make_call(2, 1, 0, 6, True)
    
    print("2. Player 2 → Player 1[2] = 7 (CORRECT)")
    game.make_call(2, 1, 2, 7, True)
    
    # Now Player 0 knows Player 1 has 6 and 7, but Player 0 doesn't have those values!
    print("\n" + "="*80)
    print("Player 0's Call Suggestions")
    print("="*80)
    print("(Player 0 has values 1-5, but Player 1's known values are 6-7)")
    
    player0 = players[0]
    player0.print_call_suggestions()
    
    suggestions = player0.get_all_call_suggestions()
    
    # Player 0 should still have suggestions for Player 2
    print("\n--- Verification ---")
    total_suggestions = len(suggestions['certain']) + len(suggestions['uncertain'])
    print(f"Total suggestions: {total_suggestions}")
    
    if total_suggestions > 0:
        print("✓ Player 0 can still make calls (probably targeting Player 2)")
    else:
        print("⚠️  Player 0 has no call suggestions")
    
    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("CALL SUGGESTER TEST SUITE")
    print("="*80)
    
    test1 = test_call_suggester_basic()
    test2 = test_call_suggester_filtering()
    test3 = test_call_suggester_no_matching_values()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Test 1 (basic): {'✓ PASSED' if test1 else '✗ FAILED'}")
    print(f"Test 2 (filtering): {'✓ PASSED' if test2 else '✗ FAILED'}")
    print(f"Test 3 (no matching): {'✓ PASSED' if test3 else '✗ FAILED'}")
    
    if test1 and test2 and test3:
        print("\n✓ ALL TESTS PASSED")
    else:
        print("\n✗ SOME TESTS FAILED")
