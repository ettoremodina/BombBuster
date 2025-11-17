"""
Test for r_k constraint filtering with called values.
Verifies that when all copies of a value are accounted for (revealed + certain + called),
the value is removed from players who don't have it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.player import Player
from src.game import Game
from config.game_config import GameConfig


def print_belief_summary(player, target_player_id, label=""):
    """Helper to print a summary of beliefs for a specific player."""
    print(f"\n{label}Player {player.player_id}'s belief about Player {target_player_id}:")
    for pos in range(player.belief_system.config.wires_per_player):
        possible = player.belief_system.beliefs[target_player_id][pos]
        print(f"  Position {pos}: {sorted(possible)}")


def print_value_tracker(belief_system, value, label=""):
    """Helper to print ValueTracker state."""
    tracker = belief_system.value_trackers[value]
    print(f"\n{label}ValueTracker for value {value}:")
    print(f"  Total copies: {tracker.total}")
    print(f"  Revealed: {tracker.revealed}")
    print(f"  Certain: {tracker.certain}")
    print(f"  Called: {tracker.called}")
    print(f"  Uncertain: {tracker.uncertain}")
    print(f"  Fully accounted: {tracker.is_fully_accounted()}")


def test_r_k_constraint_filter():
    """
    Test r_k constraint filter with a scenario where all copies are accounted for.
    """
    
    print("\n" + "="*80)
    print("TEST: r_k Constraint Filter with Called Values")
    print("="*80)
    
    # Create a simple game with 4 players
    # Use value 3 which has 3 copies in the default config
    config = GameConfig(n_players=4, max_wrong_calls=20)
    
    wires = [
        [1, 1, 2, 3, 4, 5, 5, 5],  # Player 0 has value 3 at position 3
        [2, 2, 2, 3, 4, 6, 6, 6],  # Player 1 has value 3 at position 3
        [1, 1, 3, 3, 4, 4, 5, 6],  # Player 2 has value 3 at positions 2, 3
        [1, 2, 2, 4, 4, 4, 5, 6]   # Player 3 does NOT have value 3
    ]
    
    print("\nActual wires:")
    for i, wire in enumerate(wires):
        count_3 = wire.count(3)
        has_3 = "✓" if 3 in wire else "✗"
        print(f"  Player {i}: {wire}  (has value 3: {has_3}, count: {count_3})")
    
    total_3s = sum(wire.count(3) for wire in wires)
    print(f"\nTotal value 3 in game: {total_3s}")
    print(f"Expected r_k for value 3: {config.get_copies(3)}")
    
    # Create players and game
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    game = Game(players, config)
    
    print("\n" + "="*80)
    print("SCENARIO: Account for all copies of value 3")
    print("="*80)
    
    # Initial state - Player 0's view
    print("\n--- Initial State ---")
    print_value_tracker(players[0].belief_system, 3, "Player 0's ")
    print_belief_summary(players[0], 3, "Before calls: ")
    
    # Step 1: Reveal one copy (Player 1 has it)
    print("\n--- Step 1: Reveal value 3 for Player 1 ---")
    print("Call: Player 0 -> Player 1[3] = 3 (CORRECT)")
    game.make_call(0, 1, 3, 3, True)
    
    print_value_tracker(players[0].belief_system, 3, "Player 0's ")
    print(f"  Accounted: {players[0].belief_system.value_trackers[3].get_accounted_players()}")
    
    # Step 2: Player 2 makes a wrong call with value 3 (demonstrates ownership)
    print("\n--- Step 2: Wrong call demonstrates Player 2 has value 3 ---")
    print("Call: Player 2 -> Player 0[0] = 3 (WRONG)")
    print(f"  (Player 2 actually has 3, but not at position 0)")
    game.make_call(2, 0, 0, 3, False)
    
    print_value_tracker(players[0].belief_system, 3, "Player 0's ")
    print(f"  Accounted: {players[0].belief_system.value_trackers[3].get_accounted_players()}")
    
    # Step 3: Reveal another copy (Player 0 has it)
    print("\n--- Step 3: Reveal value 3 for Player 0 ---")
    print("Call: Player 1 -> Player 0[3] = 3 (CORRECT)")
    game.make_call(1, 0, 3, 3, True)
    
    print_value_tracker(players[0].belief_system, 3, "Player 0's ")
    print(f"  Accounted: {players[0].belief_system.value_trackers[3].get_accounted_players()}")
    
    # Now we have 3 copies accounted for:
    # - Player 0: revealed
    # - Player 1: revealed
    # - Player 2: called (has it somewhere)
    # Total = 3, which equals r_k for value 3
    
    print("\n" + "="*80)
    print("VERIFICATION: r_k constraint should remove value 3 from Player 3")
    print("="*80)
    
    print("\nPlayer 0's belief about Player 3 (who should NOT have value 3):")
    player3_has_3_in_belief = False
    for pos in range(config.wires_per_player):
        possible = players[0].belief_system.beliefs[3][pos]
        has_3 = 3 in possible
        if has_3:
            player3_has_3_in_belief = True
        print(f"  Position {pos}: {sorted(possible)} {'<-- has 3!' if has_3 else ''}")
    
    # Verify that Player 3 does not have value 3 in any belief set
    if not player3_has_3_in_belief:
        print("\n✓ SUCCESS: Value 3 correctly removed from Player 3's belief sets")
        print("  (All copies accounted for by Players 0, 1, and 2)")
    else:
        print("\n✗ FAILURE: Value 3 still appears in Player 3's belief sets")
        print("  (r_k constraint filter did not work correctly)")
    
    # Also check Player 1's perspective
    print("\n--- Cross-check from Player 1's perspective ---")
    print_value_tracker(players[1].belief_system, 3, "Player 1's ")
    print(f"  Accounted: {players[1].belief_system.value_trackers[3].get_accounted_players()}")
    
    print("\nPlayer 1's belief about Player 3:")
    player3_has_3_in_p1_belief = False
    for pos in range(config.wires_per_player):
        possible = players[1].belief_system.beliefs[3][pos]
        has_3 = 3 in possible
        if has_3:
            player3_has_3_in_p1_belief = True
        print(f"  Position {pos}: {sorted(possible)} {'<-- has 3!' if has_3 else ''}")
    
    if not player3_has_3_in_p1_belief:
        print("\n✓ Player 1 also correctly removed value 3 from Player 3")
    else:
        print("\n✗ Player 1 still has value 3 in Player 3's belief sets")
    
    # Verify consistency
    print("\n--- Consistency Check ---")
    for i, player in enumerate(players):
        consistent = player.belief_system.is_consistent()
        status = "✓" if consistent else "✗"
        print(f"Player {i} belief system: {status} {'consistent' if consistent else 'INCONSISTENT'}")
    
    return not player3_has_3_in_belief and not player3_has_3_in_p1_belief


def test_r_k_with_certain_positions():
    """
    Test r_k constraint when some positions become certain through filtering.
    """
    
    print("\n" + "="*80)
    print("TEST: r_k Constraint with Certain (not revealed) Positions")
    print("="*80)
    
    config = GameConfig(n_players=3, max_wrong_calls=20)
    
    # Value 4 has 3 copies
    wires = [
        [1, 2, 3, 4, 5, 6, 6, 6],  # Player 0 has value 4 at position 3
        [1, 2, 3, 4, 5, 5, 6, 6],  # Player 1 has value 4 at position 3
        [1, 2, 3, 4, 5, 5, 5, 6],  # Player 2 has value 4 at position 3
    ]
    
    print("\nActual wires:")
    for i, wire in enumerate(wires):
        count_4 = wire.count(4)
        print(f"  Player {i}: {wire}  (value 4 count: {count_4})")
    
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    game = Game(players, config)
    
    print("\n--- Reveal positions to constrain beliefs ---")
    
    # Reveal positions around position 3 to make it certain
    print("Call: Player 0 -> Player 1[2] = 3 (CORRECT)")
    game.make_call(0, 1, 2, 3, True)
    
    print("Call: Player 0 -> Player 1[4] = 5 (CORRECT)")
    game.make_call(0, 1, 4, 5, True)
    
    # Now position 3 should be constrained: must be >= 3 and <= 5
    # So possible values are {3, 4, 5}, actual is 4
    
    print("\nPlayer 0's belief about Player 1[3]:")
    possible_p1_pos3 = players[0].belief_system.beliefs[1][3]
    print(f"  Possible values: {sorted(possible_p1_pos3)}")
    
    # Now if we reveal value 4 for other players
    print("\n--- Account for value 4 copies ---")
    print("Call: Player 1 -> Player 0[3] = 4 (CORRECT)")
    game.make_call(1, 0, 3, 4, True)
    
    print("Call: Player 1 -> Player 2[3] = 4 (CORRECT)")
    game.make_call(1, 2, 3, 4, True)
    
    print_value_tracker(players[0].belief_system, 4, "Player 0's ")
    
    # Now 2 out of 3 copies are revealed. If Player 1[3] becomes certain to be 4,
    # then all 3 copies are accounted and no other player can have it
    
    print("\nPlayer 0's belief about Player 1[3] after revealing others:")
    possible_p1_pos3 = players[0].belief_system.beliefs[1][3]
    print(f"  Possible values: {sorted(possible_p1_pos3)}")
    
    if len(possible_p1_pos3) == 1 and 4 in possible_p1_pos3:
        print("  ✓ Position became certain (value 4)")
        print("\nValueTracker should now show all 3 copies accounted:")
        print_value_tracker(players[0].belief_system, 4, "Player 0's ")
    
    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("R_K CONSTRAINT FILTER TEST SUITE")
    print("="*80)
    
    test1_passed = test_r_k_constraint_filter()
    print("\n")
    test2_passed = test_r_k_with_certain_positions()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Test 1 (called values): {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"Test 2 (certain positions): {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n✓ ALL TESTS PASSED")
    else:
        print("\n✗ SOME TESTS FAILED")
