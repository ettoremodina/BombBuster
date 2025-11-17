"""
Test script for BeliefModel.
Tests belief initialization, call processing, and visualization.
"""
import sys
from pathlib import Path

# Add parent directory to path so imports work from tests folder
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.player import Player
from src.game import Game
from src.utils import generate_wires, print_all_wires
from config.game_config import GameConfig


def test_belief_system():
    """Test the belief system with a simple game scenario."""
    
    print("\n" + "="*80)
    print("TEST: Belief System")
    print("="*80)
    
    # Create configuration
    config = GameConfig(n_players=3, max_wrong_calls=5)
    
    # Generate wires
    wires = generate_wires(config, seed=42)
    print_all_wires(wires)
    
    # Create players
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    
    # Create game (this initializes belief systems)
    game = Game(players, config)
    
    print("\n" + "="*80)
    print("INITIAL BELIEF STATE (Player 0)")
    print("="*80)
    players[0].belief_system.print_beliefs()
    
    # Test some calls
    print("\n" + "="*80)
    print("TEST SCENARIO: Making Calls")
    print("="*80)
    
    # Call 1: Player 0 calls Player 1, position 0
    target_value = wires[1][0]
    print(f"\n1. Player 0 calls Player 1, position 0, value {target_value}")
    print(f"   Actual value at Player 1[0]: {wires[1][0]}")
    success = (target_value == wires[1][0])
    call1 = game.make_call(0, 1, 0, target_value, success)
    print(f"   Result: {'SUCCESS' if success else 'FAIL'}")
    
    # Call 2: Player 1 calls Player 2, position 1 (wrong)
    wrong_value = [v for v in wires[1] if v != wires[2][1]][0]
    print(f"\n2. Player 1 calls Player 2, position 1, value {wrong_value}")
    print(f"   Actual value at Player 2[1]: {wires[2][1]}")
    call2 = game.make_call(1, 2, 1, wrong_value, False)
    print(f"   Result: FAIL (intentional)")
    
    # Call 3: Player 2 calls Player 0, position 2 (correct)
    correct_value = wires[0][2]
    print(f"\n3. Player 2 calls Player 0, position 2, value {correct_value}")
    print(f"   Actual value at Player 0[2]: {wires[0][2]}")
    call3 = game.make_call(2, 0, 2, correct_value, True)
    print(f"   Result: SUCCESS")
    
    # Show updated beliefs
    print("\n" + "="*80)
    print("UPDATED BELIEF STATE (Player 0)")
    print("="*80)
    players[0].belief_system.print_beliefs()
    
    # Show ValueTracker view for Player 1
    print("\n" + "="*80)
    print("VALUE TRACKER VIEW (Player 1's Belief System)")
    print("="*80)
    
    player1_belief = players[1].belief_system
    print(f"\nTracking state for each value from Player 1's perspective:")
    print("-" * 80)
    
    for value in sorted(player1_belief.value_trackers.keys()):
        tracker = player1_belief.value_trackers[value]
        print(f"\nValue {value}:")
        print(f"  Total copies: {tracker.total}")
        print(f"  Revealed (players): {tracker.revealed}")
        print(f"  Certain (players): {tracker.certain}")
        print(f"  Called (players): {tracker.called}")
        print(f"  Uncertain copies: {tracker.get_uncertain_count()}")
        if tracker.is_fully_accounted():
            print(f"  Status: ✓ Fully accounted for")
        else:
            print(f"  Status: ⏳ Still uncertain")
    
    # Check consistency
    print("\n" + "="*80)
    print("CONSISTENCY CHECK")
    print("="*80)
    
    for player in players:
        consistent = player.belief_system.is_consistent()
        print(f"Player {player.player_id} belief system: {'✓ Consistent' if consistent else '✗ INCONSISTENT'}")
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)


if __name__ == "__main__":
    test_belief_system()
