"""
Comprehensive test for wire swap functionality.
Tests swap with 3 players, K=6, no 0.5 values, saves all beliefs to JSON.
"""

import sys
from pathlib import Path
import shutil

# Add parent directory to path so imports work from tests folder
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.player import Player
from src.game import Game
from config.game_config import GameConfig


def test_swap_comprehensive():
    """Test swap with 3 players, save all beliefs."""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE SWAP TEST")
    print("="*80)
    
    # Create simple config: 3 players, K=6, no 0.5 values
    config = GameConfig(
        wire_distribution={
            1: 4,
            2: 4, 
            3: 4,
            4: 4,
            5: 4,
            6: 4
        },
        n_players=3,
        # wires_per_player=8,
        playing_irl=False  # Simulation mode - everyone knows swapped values
    )
    
    # Create players with known wires (sorted)
    # every player gets two copies of each value from 1 to 6
    wires = [ 
        [1, 1, 2, 2, 3, 3, 4, 4],  # Player 0 (Alice)
        [1, 1, 2, 2, 5, 5, 6, 6],  # Player 1 (Bob)
        [3, 3, 4, 4, 5, 5, 6, 6]   # Player 2 (Charlie)
    ]
    

    player_names = {
        0: "Alice",
        1: "Bob", 
        2: "Charlie"
    }
    
    players = [Player(i, wires[i], config) for i in range(3)]
    game = Game(players, config)
    
    print("\nInitial wires:")
    for i, p in enumerate(players):
        print(f"  {player_names[i]} (Player {i}): {p.wire}")
    
    # Setup output folder
    project_root = Path(__file__).parent.parent
    output_folder = "swap_test_beliefs"
    output_path = project_root / output_folder
    
    # Clean up old snapshots if they exist
    if output_path.exists():
        shutil.rmtree(output_path)

    
    initial_path = output_path / "initial"
    for player in players:
        player.belief_system.save_to_folder(str(initial_path), player_names)

    
    swap_result = game.swap_wires(
        player1_id=0,
        player2_id=1,
        init_pos1=0,
        init_pos2=7,
        final_pos1=7,
        final_pos2=0
    )
    wires_after = [ 
        [1, 2, 2, 3, 3, 4, 4, 6],  # Player 0 (Alice)
        [1, 1, 1, 2, 2, 5, 5, 6],  # Player 1 (Bob)
        [3, 3, 4, 4, 5, 5, 6, 6]   # Player 2 (Charlie)
    ]

    # swap_result = game.swap_wires(
    #     player1_id=0,
    #     player2_id=1,
    #     init_pos1=7,
    #     init_pos2=0,
    #     final_pos1=0,
    #     final_pos2=3
    # )

    # wires_after = [ 
    #     [1, 1, 2, 2, 3, 3, 4, 4],  # Player 0 (Alice)
    #     [1, 1, 2, 2, 5, 5, 6, 6],  # Player 1 (Bob)
    #     [3, 3, 4, 4, 5, 5, 6, 6]   # Player 2 (Charlie)
    # ]
    

    
    print(f"\n{'='*80}")
    print("WIRES AFTER SWAP")
    print(f"{'='*80}")
    for i, p in enumerate(players):
        print(f"  {player_names[i]} (Player {i}): {p.wire}")
    
    # save post-swap beliefs
    post_swap_path = output_path / "after_swap"
    for player in players:
        player.belief_system.save_to_folder(str(post_swap_path), player_names)
        
  
if __name__ == "__main__":
    test_swap_comprehensive()
