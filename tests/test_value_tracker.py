"""
Test script for ValueTracker updates and certain (but not revealed) positions.
Demonstrates:
1. Wrong calls demonstrate ownership without revealing positions
2. Filtering deduces certain positions (not yet revealed)
3. Players can only call values they possess
4. ValueTracker updates correctly for all players
"""
import sys
from pathlib import Path

# Add parent directory to path so imports work from tests folder
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.player import Player
from src.game import Game
from config.game_config import GameConfig


def print_value_tracker(belief_system, value, label=""):
    """Helper to print ValueTracker state for a specific value."""
    tracker = belief_system.value_trackers[value]
    print(f"\n{label}Value {value} tracker:")
    print(f"  Total copies: {tracker.total}")
    print(f"  Revealed (players): {tracker.revealed}")
    print(f"  Certain (players): {tracker.certain}")
    print(f"  Called (players): {tracker.called}")
    print(f"  Uncertain copies: {tracker.get_uncertain_count()}")
    if tracker.is_fully_accounted():
        print(f"  Status: ✓ Fully accounted for")
    else:
        print(f"  Status: ⏳ {tracker.get_uncertain_count()} still uncertain")


def test_value_tracker():
    """Test ValueTracker updates and certain position deduction."""
    
    print("\n" + "="*80)
    print("TEST: ValueTracker Updates and Certain Positions")
    print("="*80)
    
    # Create configuration
    config = GameConfig(n_players=3, max_wrong_calls=10)
    
    wires = [
        [1, 1, 2, 3, 4, 5, 5, 5],
        [2, 2, 2, 3, 4, 6, 6, 6],
        [1, 1, 3, 3, 4, 4, 5, 6]
    ]
    
    print("\nActual wires:")
    for i, wire in enumerate(wires):
        print(f"  Player {i}: {wire}")
    
    # Create players and game
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    game = Game(players, config)
    
    print("\n" + "="*80)
    print("PART 1: Test calling constraint (can only call values you possess)")
    print("="*80)
    
    # Try to make Player 0 call a value they don't have (should fail)
    print("\n❌ Attempting illegal call: Player 0 calls value 6 (they don't have it at all)")
    print(f"   Player 0's wire: {wires[0]}")
    print(f"   Player 0 has value 6? {6 in wires[0]}")
    
    # Player 0 doesn't have value 6, so this should raise an error
    # Let's verify this would fail (but not actually call it)
    try:
        # This should fail validation
        game._validate_call(0, 1, 7, 6)
        print("   ERROR: Call should have been rejected!")
    except ValueError as e:
        print(f"   ✓ Call correctly rejected: {e}")
    
    print("\n✓ Attempting legal call: Player 1 calls value 6 (they have it)")
    print(f"   Player 1's wire: {wires[1]}")
    print(f"   Player 1 has value 6? {6 in wires[1]}")
    
    print("\n" + "="*80)
    print("PART 2: Wrong calls demonstrate ownership (add to 'called' list)")
    print("="*80)
    
    # Player 1 makes wrong calls with values they possess
    print("\n1. Player 1 calls Player 2, position 0, value 3 (WRONG)")
    print(f"   Player 1 has value 3? {3 in wires[1]} ✓")
    print(f"   Actual value at Player 2[0]: {wires[2][0]}")
    game.make_call(1, 2, 0, 3, False)  # Wrong call
    
    # Check ValueTracker update for value 2
    print("\n   ValueTracker update for value 2:")
    for player_idx in range(3):
        tracker = players[player_idx].belief_system.value_trackers[2]
        print(f"   Player {player_idx}'s tracker: revealed={tracker.revealed}, "
              f"certain={tracker.certain}, called={tracker.called}")
    
    print("\n2. Player 0 calls Player 1, position 7, value 5 (WRONG)")
    print(f"   Player 0 has value 5? {5 in wires[0]} ✓")
    print(f"   Actual value at Player 1[7]: {wires[1][7]}")
    game.make_call(0, 1, 7, 5, False)  # Wrong call
    
    print_value_tracker(players[0].belief_system, 5, "   Player 0's ")
    
    print("\n" + "="*80)
    print("PART 3: Create scenario for certain (but not revealed) position")
    print("="*80)
    
    # We'll create a scenario where filtering deduces a value is certain
    # Strategy: Reveal several positions to constrain via ordering filter
    # Player 0: [1, 1, 2, 3, 4, 5, 5, 5]
    # Player 1: [2, 2, 2, 3, 4, 6, 6, 6]
    # Player 2: [1, 1, 3, 3, 4, 4, 5, 6]
    
    print("\n3. Player 2 calls Player 0, position 0, value 1 (CORRECT)")
    print(f"   Player 2 has value 1? {1 in wires[2]} ✓")
    print(f"   Actual value at Player 0[0]: {wires[0][0]}")
    game.make_call(2, 0, 0, 1, True)
    
    print("\n4. Player 1 calls Player 0, position 2, value 2 (CORRECT)")
    print(f"   Player 1 has value 2? {2 in wires[1]} ✓")
    print(f"   Actual value at Player 0[2]: {wires[0][2]}")
    game.make_call(1, 0, 2, 2, True)
    
    print("\n5. Player 2 calls Player 0, position 3, value 3 (CORRECT)")
    print(f"   Player 2 has value 3? {3 in wires[2]} ✓")
    print(f"   Actual value at Player 0[3]: {wires[0][3]}")
    game.make_call(2, 0, 3, 3, True)
    
    # Now position 1 is constrained:
    # - Must be >= 1 (from position 0)
    # - Must be <= 2 (from position 2)
    # So position 1 can only be {1, 2}, actual is 1
    
    print("\n6. Player 2 calls Player 0, position 5, value 5 (CORRECT)")
    print(f"   Player 2 has value 5? {5 in wires[2]} ✓")
    print(f"   Actual value at Player 0[5]: {wires[0][5]}")
    game.make_call(2, 0, 5, 5, True)
    
    # Now position 4 is constrained:
    # - Must be >= 3 (from position 3)
    # - Must be <= 5 (from position 5)
    # So position 4 can be {3, 4, 5}, actual is 4
    
    print("\n" + "="*80)
    print("BELIEF STATE: Player 1's view of Player 0 after filtering")
    print("="*80)
    
    player1_belief = players[1].belief_system
    revealed_positions = [0, 2, 3, 5]  # Updated to match new calls
    
    print("\nPlayer 0 positions from Player 1's perspective:")
    certain_not_revealed = []
    for pos in range(config.wires_per_player):
        possible = player1_belief.beliefs[0][pos]
        actual = wires[0][pos]
        
        if len(possible) == 1:
            val = list(possible)[0]
            if pos in revealed_positions:
                status = "✓ REVEALED (successful call)"
            else:
                status = "✓ CERTAIN (deduced by filter)"
                certain_not_revealed.append((pos, val))
            marker = " 🎯" if val == actual else " ❌ WRONG"
        else:
            status = f"{len(possible)} possibilities"
            marker = ""
        
        print(f"  Position {pos}: {sorted(possible)} [{status}] (actual: {actual}){marker}")
    
    print("\n" + "="*80)
    print("VALUE TRACKER STATE (checking 'certain' list)")
    print("="*80)
    
    if certain_not_revealed:
        print(f"\n✓ Found {len(certain_not_revealed)} position(s) that are CERTAIN but NOT REVEALED:")
        for pos, val in certain_not_revealed:
            print(f"  Position {pos} = {val}")
            print(f"  This value should be in the 'certain' list of ValueTracker[{val}]")
            
            # Check all players' ValueTrackers for this value
            print(f"\n  ValueTracker updates for value {val} across all players:")
            for player_idx in range(3):
                tracker = players[player_idx].belief_system.value_trackers[val]
                print(f"    Player {player_idx}'s view: revealed={tracker.revealed}, "
                      f"certain={tracker.certain}, called={tracker.called}")
    else:
        print("\n⚠️  No positions became certain through filtering (unexpected)")
    
    print("\n" + "="*80)
    print("DETAILED VALUE TRACKER VIEW (Player 1's perspective)")
    print("="*80)
    
    print("\nAll value trackers from Player 1's belief system:")
    for value in sorted(player1_belief.value_trackers.keys()):
        print_value_tracker(player1_belief, value, f"\n")
    
    print("\n" + "="*80)
    print("PART 4: Verify ValueTracker consistency across all players")
    print("="*80)
    
    # Check that all players have consistent ValueTracker updates
    print("\nChecking ValueTracker for value 1 across all players:")
    for player_idx in range(3):
        tracker = players[player_idx].belief_system.value_trackers[1]
        print(f"  Player {player_idx}: revealed={tracker.revealed}, "
              f"certain={tracker.certain}, called={tracker.called}, "
              f"uncertain={tracker.get_uncertain_count()}")
    
    print("\nChecking ValueTracker for value 2 across all players:")
    for player_idx in range(3):
        tracker = players[player_idx].belief_system.value_trackers[2]
        print(f"  Player {player_idx}: revealed={tracker.revealed}, "
              f"certain={tracker.certain}, called={tracker.called}, "
              f"uncertain={tracker.get_uncertain_count()}")
    
    # Verify consistency
    print("\n" + "="*80)
    print("CONSISTENCY CHECKS")
    print("="*80)
    
    all_consistent = True
    for player in players:
        consistent = player.belief_system.is_consistent()
        status = "✓" if consistent else "✗"
        print(f"{status} Player {player.player_id} belief system: "
              f"{'Consistent' if consistent else 'INCONSISTENT'}")
        all_consistent = all_consistent and consistent
    
    if all_consistent:
        print("\n✓ All belief systems are consistent")
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)


if __name__ == "__main__":
    test_value_tracker()
