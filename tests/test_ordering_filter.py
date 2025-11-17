"""
Test script for the ordering filter.
Demonstrates how monotonic constraints deduce certain positions.
"""
import sys
from pathlib import Path

# Add parent directory to path so imports work from tests folder
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.player import Player
from src.game import Game
from config.game_config import GameConfig


def test_ordering_filter():
    """Test ordering filter with carefully crafted scenarios."""
    
    print("\n" + "="*80)
    print("TEST: Ordering Filter (Monotonic Constraint)")
    print("="*80)
    
    # Create configuration with small wire length for clarity
    config = GameConfig(n_players=3, max_wrong_calls=5)
    
    # Create specific wires to test ordering constraint
    # Player 0: [1, 1, 2, 3, 4, 5, 5, 6]
    # Player 1: [1, 2, 2, 3, 4, 5, 6, 6]
    # Player 2: [1, 1, 3, 3, 4, 5, 6, 6]
    wires = [
        [1, 1, 2, 3, 4, 5, 5, 6],
        [1, 2, 2, 3, 4, 5, 6, 6],
        [1, 1, 3, 3, 4, 5, 6, 6]
    ]
    
    print("\nActual wires:")
    for i, wire in enumerate(wires):
        print(f"  Player {i}: {wire}")
    
    # Create players
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    
    # Create game
    game = Game(players, config)
    
    print("\n" + "="*80)
    print("SCENARIO: Using ordering to deduce values")
    print("="*80)
    
    # Player 0's perspective: they know Player 1 has value 6 at position 7 (last position)
    print("\n1. Player 0 calls Player 1, position 7, value 6 (correct)")
    print(f"   Actual: Player 1[7] = {wires[1][7]}")
    game.make_call(0, 1, 7, 6, True)
    
    # Now Player 0 knows Player 1[7] = 6
    # Ordering filter should deduce: all positions 0-6 must have values <= 6
    # This should eliminate nothing (all values are <= 6)
    
    print("\n2. Player 0 calls Player 1, position 0, value 1 (correct)")
    print(f"   Actual: Player 1[0] = {wires[1][0]}")
    game.make_call(0, 1, 0, 1, True)
    
    # Now Player 0 knows Player 1[0] = 1
    # Ordering filter should deduce: all positions 1-7 must have values >= 1
    # This eliminates nothing (all values are >= 1)
    
    print("\n3. Player 0 calls Player 1, position 4, value 4 (correct)")
    print(f"   Actual: Player 1[4] = {wires[1][4]}")
    game.make_call(0, 1, 4, 4, True)
    
    # Now Player 0 knows Player 1[4] = 4
    # Ordering constraints:
    # - Positions 0-3 must have values <= 4
    # - Positions 5-7 must have values >= 4
    
    print("\n" + "="*80)
    print("BELIEF STATE (Player 0's perspective on Player 1)")
    print("="*80)
    
    player0_belief = players[0].belief_system
    print("\nPlayer 1 beliefs after ordering filter:")
    for pos in range(config.wires_per_player):
        possible = player0_belief.beliefs[1][pos]
        actual = wires[1][pos]
        
        if len(possible) == 1:
            val = list(possible)[0]
            status = "✓ REVEALED" if pos in [0, 4, 7] else "✓ CERTAIN"
            marker = " 🎯" if val == actual else " ❌ WRONG"
        else:
            status = f"{len(possible)} possibilities"
            marker = ""
        
        print(f"  Position {pos}: {sorted(possible)} [{status}] (actual: {actual}){marker}")
    
    # Show ValueTracker state
    print("\n" + "="*80)
    print("VALUE TRACKER STATE (Player 0's perspective)")
    print("="*80)
    
    print("\nTracking state for each value:")
    for value in sorted(player0_belief.value_trackers.keys()):
        tracker = player0_belief.value_trackers[value]
        print(f"\nValue {value}:")
        print(f"  Total copies: {tracker.total}")
        print(f"  Revealed (players): {tracker.revealed}")
        print(f"  Certain (players): {tracker.certain}")
        print(f"  Called (players): {tracker.called}")
        print(f"  Uncertain copies: {tracker.get_uncertain_count()}")
        if tracker.is_fully_accounted():
            print(f"  Status: ✓ Fully accounted for")
        else:
            print(f"  Status: ⏳ {tracker.get_uncertain_count()} still uncertain")
    
    # Now test a more complex scenario
    print("\n" + "="*80)
    print("ADVANCED SCENARIO: Position 3 deduction")
    print("="*80)
    
    # We know: pos[0]=1, pos[4]=4, pos[7]=6
    # Let's reveal position 2
    print("\n4. Player 2 calls Player 1, position 2, value 2 (correct)")
    print(f"   Actual: Player 1[2] = {wires[1][2]}")
    game.make_call(2, 1, 2, 2, True)
    
    # Now we know: pos[0]=1, pos[2]=2, pos[4]=4, pos[7]=6
    # Position 3 constraints:
    # - Must be >= 2 (from pos[2]=2)
    # - Must be <= 4 (from pos[4]=4)
    # So pos[3] ∈ {2, 3, 4}
    
    # Position 1 constraints:
    # - Must be >= 1 (from pos[0]=1)
    # - Must be <= 2 (from pos[2]=2)
    # So pos[1] ∈ {1, 2}
    
    print("\n" + "="*80)
    print("UPDATED BELIEF STATE (After position 2 revealed)")
    print("="*80)
    
    print("\nPlayer 1 beliefs:")
    revealed_positions = [0, 2, 4, 7]  # Positions that were successfully called
    for pos in range(config.wires_per_player):
        possible = player0_belief.beliefs[1][pos]
        actual = wires[1][pos]
        
        if len(possible) == 1:
            val = list(possible)[0]
            status = "✓ REVEALED" if pos in revealed_positions else "✓ CERTAIN (deduced)"
            marker = " 🎯" if val == actual else " ❌ WRONG"
        else:
            status = f"{len(possible)} possibilities"
            marker = ""
        
        print(f"  Position {pos}: {sorted(possible)} [{status}] (actual: {actual}){marker}")
    
    # Show updated ValueTracker state
    print("\n" + "="*80)
    print("UPDATED VALUE TRACKER STATE")
    print("="*80)
    
    print("\nTracking state for each value:")
    for value in sorted(player0_belief.value_trackers.keys()):
        tracker = player0_belief.value_trackers[value]
        print(f"\nValue {value}:")
        print(f"  Total copies: {tracker.total}")
        print(f"  Revealed (players): {tracker.revealed}")
        print(f"  Certain (players): {tracker.certain}")
        print(f"  Called (players): {tracker.called}")
        print(f"  Uncertain copies: {tracker.get_uncertain_count()}")
        if tracker.is_fully_accounted():
            print(f"  Status: ✓ Fully accounted for")
        else:
            print(f"  Status: ⏳ {tracker.get_uncertain_count()} still uncertain")
    
    # Check constraint propagation
    print("\n" + "="*80)
    print("CONSTRAINT ANALYSIS")
    print("="*80)
    
    print("\nKnown positions:")
    certain = player0_belief.get_certain_positions(1)
    for pos, val in sorted(certain.items()):
        print(f"  Position {pos}: {val}")
    
    print("\nUncertain positions with constraints:")
    for pos in range(config.wires_per_player):
        possible = player0_belief.beliefs[1][pos]
        if len(possible) > 1:
            actual = wires[1][pos]
            in_possible = "✓" if actual in possible else "❌ ELIMINATED"
            print(f"  Position {pos}: {sorted(possible)} (actual={actual} {in_possible})")
    
    # Consistency check
    print("\n" + "="*80)
    print("CONSISTENCY CHECK")
    print("="*80)
    
    consistent = player0_belief.is_consistent()
    print(f"Belief system: {'✓ Consistent' if consistent else '✗ INCONSISTENT'}")
    
    # Check if actual values are still possible
    all_valid = True
    for pos in range(config.wires_per_player):
        possible = player0_belief.beliefs[1][pos]
        actual = wires[1][pos]
        if actual not in possible:
            print(f"⚠️  ERROR: Actual value {actual} eliminated from position {pos}!")
            all_valid = False
    
    if all_valid:
        print("✓ All actual values still in possibility sets")
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)


if __name__ == "__main__":
    test_ordering_filter()
