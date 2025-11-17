"""
Demo script showing the call suggester in action.
Demonstrates how the suggester helps identify the best calls to make.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.player import Player
from src.game import Game
from config.game_config import GameConfig


def main():
    """Run a demo game showing call suggestions."""
    
    print("\n" + "="*80)
    print("CALL SUGGESTER DEMONSTRATION")
    print("="*80)
    print("\nThis demo shows how the call suggester helps you make optimal calls")
    print("based on your belief system and the values you have in your wire.\n")
    
    config = GameConfig(n_players=4, max_wrong_calls=20)
    
    # Create a game scenario
    wires = [
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Player 0 (YOU)
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Player 1
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Player 2
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # Player 3
    ]
    
    print("Game Setup:")
    print(f"  Players: {config.n_players}")
    print(f"  Wires per player: {config.wires_per_player}")
    print(f"  Your wire (Player 0): {wires[0]}")
    
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    game = Game(players, config)
    
    player0 = players[0]
    
    # Scenario 1: Initial state
    print("\n" + "="*80)
    print("SCENARIO 1: No information yet")
    print("="*80)
    print("\nAt the start of the game, you have no information about other players.")
    print("The suggester will pick from all possible calls with equal uncertainty.")
    
    suggestion = player0.suggest_call()
    if suggestion:
        target, pos, val = suggestion
        print(f"\n💡 Suggested call: Player 0 → Player {target}[{pos}] = {val}")
        print(f"   (This is a random guess - all positions equally uncertain)")
    
    # Scenario 2: After some reveals
    print("\n" + "="*80)
    print("SCENARIO 2: After revealing some positions")
    print("="*80)
    
    print("\nMaking some calls to gather information...")
    print("\n1. Player 1 → Player 0[0] = 1 (CORRECT)")
    game.make_call(1, 0, 0, 1, True)
    
    print("2. Player 1 → Player 0[2] = 3 (CORRECT)")
    game.make_call(1, 0, 2, 3, True)
    
    print("3. Player 2 → Player 3[5] = 6 (CORRECT)")
    game.make_call(2, 3, 5, 6, True)
    
    print("\nNow you have some information! Let's see what the suggester recommends...")
    player0.print_call_suggestions()
    
    # Scenario 3: Creating certain calls
    print("\n" + "="*80)
    print("SCENARIO 3: Creating CERTAIN calls through filtering")
    print("="*80)
    
    print("\nMaking more strategic calls to constrain beliefs...")
    print("\n4. Player 0 → Player 1[1] = 2 (CORRECT)")
    game.make_call(0, 1, 1, 2, True)
    
    print("5. Player 0 → Player 1[3] = 4 (CORRECT)")
    game.make_call(0, 1, 3, 4, True)
    
    print("\nNow Player 1[2] is highly constrained (must be between 2 and 4)")
    print("The ordering filter has reduced the possibilities...")
    
    player0.print_call_suggestions()
    
    # Make the suggested call
    suggestion = player0.suggest_call()
    if suggestion:
        target, pos, val = suggestion
        print(f"\n" + "="*80)
        print(f"Following the suggestion...")
        print(f"Making call: Player 0 → Player {target}[{pos}] = {val}")
        
        # Check if it's correct
        actual_value = players[target].get_value_at_position(pos)
        is_correct = (val == actual_value)
        
        game.make_call(0, target, pos, val, is_correct)
        
        if is_correct:
            print(f"✓ SUCCESS! The call was correct.")
        else:
            print(f"✗ FAILED. The actual value was {actual_value}.")
        
        print(f"{'='*80}")
    
    # Final state
    print("\n" + "="*80)
    print("FINAL STATE")
    print("="*80)
    
    state = game.get_game_state()
    print(f"\nTotal calls made: {state['total_calls']}")
    print(f"Wrong calls: {state['wrong_calls_count']} / {config.max_wrong_calls}")
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nKey takeaways:")
    print("  1. Call suggester prioritizes CERTAIN calls (belief set size = 1)")
    print("  2. If no certain calls, it picks the call with minimum uncertainty")
    print("  3. Only suggests calls for values YOU have in your wire")
    print("  4. As you gather more information, suggestions become more certain")
    print("\nUse player.print_call_suggestions() to see all available options!")
    print("Or use player.suggest_call() to get the single best recommendation.\n")


if __name__ == "__main__":
    main()
