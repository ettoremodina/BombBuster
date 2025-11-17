"""
Debug script to trace the exact scenario with called value tracking.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.player import Player
from src.game import Game
from config.game_config import GameConfig


def print_value_tracker_detailed(player, value, label=""):
    """Print detailed ValueTracker state."""
    tracker = player.belief_system.value_trackers[value]
    print(f"\n{label}ValueTracker for value {value} (from Player {player.player_id}'s perspective):")
    print(f"  Total: {tracker.total}")
    print(f"  Revealed: {tracker.revealed}")
    print(f"  Certain: {tracker.certain}")
    print(f"  Called: {tracker.called}")
    print(f"  Uncertain: {tracker.uncertain}")
    

def main():
    """Reproduce the exact scenario from play_irl.py"""
    
    print("\n" + "="*80)
    print("DEBUG: Called Value Tracking Issue")
    print("="*80)
    
    config = GameConfig(n_players=4, max_wrong_calls=20)
    
    # Create dummy wires (Player 0's wire is what matters)
    wires = [
        [1, 2, 3, 3, 4, 5, 6, 7, 8, 9],  # Player 0 (you) - has value 3
        [1, 2, 2, 3, 4, 5, 6, 7, 8, 9],  # Player 1 - has value 3 at position 3
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], # Player 2 - has value 3
        [1, 2, 4, 5, 6, 7, 8, 9, 10, 11], # Player 3 - does NOT have value 3
    ]
    
    print("\nActual wires:")
    for i, wire in enumerate(wires):
        has_3 = 3 in wire
        label = "(YOU)" if i == 0 else ""
        print(f"  Player {i} {label}: {wire} - has 3: {has_3}")
    
    # Create players
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    game = Game(players, config)
    
    # From Player 0's perspective
    my_player = players[0]
    
    print("\n" + "="*80)
    print("Initial State (Player 0's perspective)")
    print("="*80)
    print_value_tracker_detailed(my_player, 3, "Initial: ")
    
    # Call 1: Player 0 -> Player 1[5] = 3 (SUCCESS)
    print("\n" + "="*80)
    print("Call 1: Player 0 → Player 1[5] = 3 (SUCCESS)")
    print("="*80)
    game.make_call(0, 1, 5, 3, True)
    print_value_tracker_detailed(my_player, 3, "After call 1: ")
    
    # Call 2: Player 1 -> Player 0[8] = 3 (FAIL)
    print("\n" + "="*80)
    print("Call 2: Player 1 → Player 0[8] = 3 (FAIL)")
    print("="*80)
    print("  (Player 1 makes a wrong call, so they have value 3 somewhere)")
    game.make_call(1, 0, 8, 3, False)
    print_value_tracker_detailed(my_player, 3, "After call 2: ")
    
    # Call 3: Player 2 -> Player 3[4] = 3 (FAIL)
    print("\n" + "="*80)
    print("Call 3: Player 2 → Player 3[4] = 3 (FAIL)")
    print("="*80)
    print("  (Player 2 makes a wrong call, so they have value 3 somewhere)")
    game.make_call(2, 3, 4, 3, False)
    print_value_tracker_detailed(my_player, 3, "After call 3: ")
    
    # Check if Player 2 is in any of the belief sets as certain
    print("\n" + "="*80)
    print("Check: Is Player 2 marked as certain for value 3?")
    print("="*80)
    
    player2_positions_with_3 = []
    for pos in range(config.wires_per_player):
        belief = my_player.belief_system.beliefs[2][pos]
        if len(belief) == 1 and 3 in belief:
            player2_positions_with_3.append(pos)
    
    print(f"  Positions where Player 2 is certain to have value 3: {player2_positions_with_3}")
    
    # Show all of Player 2's belief sets
    print("\n  Player 2's belief sets (from Player 0's perspective):")
    for pos in range(config.wires_per_player):
        belief = my_player.belief_system.beliefs[2][pos]
        print(f"    Position {pos}: {sorted(belief)}")
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    
    tracker = my_player.belief_system.value_trackers[3]
    
    expected_revealed = [1]  # Player 1 from call 1
    expected_certain = [0]   # Player 0 (you know your own wire)
    expected_called = [2]    # Player 1 should NOT be here (already revealed), Player 2 should be here
    
    print(f"\nExpected state:")
    print(f"  Revealed: {expected_revealed}")
    print(f"  Certain: {expected_certain}")
    print(f"  Called: {expected_called}")
    
    print(f"\nActual state:")
    print(f"  Revealed: {tracker.revealed}")
    print(f"  Certain: {tracker.certain}")
    print(f"  Called: {tracker.called}")
    
    # Check if correct
    revealed_ok = set(tracker.revealed) == set(expected_revealed)
    certain_ok = set(tracker.certain) == set(expected_certain)
    called_ok = set(tracker.called) == set(expected_called)
    
    print(f"\nValidation:")
    print(f"  Revealed: {'✓' if revealed_ok else '✗ WRONG'}")
    print(f"  Certain: {'✓' if certain_ok else '✗ WRONG'}")
    print(f"  Called: {'✓' if called_ok else '✗ WRONG - Player 2 should be in called list!'}")
    
    if not called_ok:
        print("\n" + "="*80)
        print("DEBUGGING: Why is Player 2 not in called list?")
        print("="*80)
        
        # Check if Player 2 is in certain or revealed
        if 2 in tracker.certain:
            print("  ❌ Player 2 is in CERTAIN list (shouldn't be before call)")
        if 2 in tracker.revealed:
            print("  ❌ Player 2 is in REVEALED list (shouldn't be)")
        
        # Manually check what _process_failed_call should have done
        print("\n  Call 3 details:")
        print(f"    Caller: Player 2")
        print(f"    Target: Player 3")
        print(f"    Value: 3")
        print(f"    Success: False")
        print(f"    my_player_id: {my_player.player_id}")
        print(f"    Condition (caller != my_player_id): {2 != my_player.player_id}")
        print(f"    Should call add_called(2): {2 != my_player.player_id}")


if __name__ == "__main__":
    main()
