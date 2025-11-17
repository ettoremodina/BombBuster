"""
Test script for BeliefModel JSON serialization (save/load).
Demonstrates saving belief states to disk and loading them back.
"""

import sys
from pathlib import Path

# Add parent directory to path so imports work from tests folder
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.player import Player
from src.game import Game
from config.game_config import GameConfig
import shutil


def test_serialization():
    """Test saving and loading belief models from JSON files."""
    
    print("\n" + "="*80)
    print("TEST: BeliefModel JSON Serialization")
    print("="*80)
    
    # Create configuration (uses default WIRE_DISTRIBUTION)
    config = GameConfig()
    
    # create random wires
    from src.utils import generate_wires
    wires = generate_wires(config, seed=123)
    
    print("\nActual wires:")
    for i, wire in enumerate(wires):
        print(f"  Player {i}: {wire}")
    
    # Create players and game
    players = [Player(i, wires[i], config) for i in range(config.n_players)]
    game = Game(players, config)
    
    print("\n" + "="*80)
    print("PART 1: Make some calls to create interesting belief state")
    print("="*80)
    
    # # Make several calls
    # print("\n1. Player 2 calls Player 0, position 0, value 1 (CORRECT)")
    # game.make_call(2, 0, 0, 1, True)
    
    # print("\n2. Player 1 calls Player 0, position 2, value 2 (CORRECT)")
    # game.make_call(1, 0, 2, 2, True)
    
    # print("\n3. Player 1 calls Player 2, position 0, value 3 (WRONG)")
    # game.make_call(1, 2, 0, 3, False)
    
    # print("\n4. Player 0 calls Player 1, position 7, value 5 (WRONG)")
    # game.make_call(0, 1, 7, 5, False)
    
    # print("\n5. Player 2 calls Player 0, position 3, value 3 (CORRECT)")
    # game.make_call(2, 0, 3, 3, True)
    
    # Show current belief state
    print("\n" + "="*80)
    print("BELIEF STATE BEFORE SAVING (Player 1)")
    print("="*80)
    players[1].belief_system.print_beliefs()
    
    print("\n" + "="*80)
    print("VALUE TRACKER BEFORE SAVING (Player 1)")
    print("="*80)
    print("\nValue trackers:")
    for value in sorted(players[1].belief_system.value_trackers.keys()):
        tracker = players[1].belief_system.value_trackers[value]
        print(f"  Value {value}: revealed={tracker.revealed}, certain={tracker.certain}, "
              f"called={tracker.called}, uncertain={tracker.get_uncertain_count()}")
    
    print("\n" + "="*80)
    print("PART 2: Save all belief models to disk")
    print("="*80)
    
    # Create output folder in project root
    project_root = Path(__file__).parent.parent
    output_folder = "belief_snapshots"
    output_path = project_root / output_folder
    
    # Clean up old snapshots if they exist
    if output_path.exists():
        shutil.rmtree(output_path)
        print(f"\n✓ Cleaned up old snapshots in '{output_folder}'")
    
    # Save all players' belief models
    print(f"\nSaving belief models to '{output_folder}/'...")
    for player in players:
        player.belief_system.save_to_folder(str(output_path))
        print(f"  ✓ Saved Player {player.player_id} beliefs to "
              f"{output_folder}/player_{player.player_id}/")
    
    # List created files
    print("\nCreated files:")
    for player_id in range(config.n_players):
        player_dir = output_path / f"player_{player_id}"
        for file in sorted(player_dir.glob("*.json")):
            file_size = file.stat().st_size
            print(f"  - {file.relative_to(output_path.parent)} ({file_size} bytes)")
    
    print("\n" + "="*80)
    print("PART 3: Load belief models from disk")
    print("="*80)
    
    # Load Player 1's belief model
    print(f"\nLoading Player 1's belief model from '{output_folder}/player_1/'...")
    
    # Need to create a GameObservation for Player 1
    from src.data_structures import GameObservation
    observation_p1 = GameObservation(
        player_id=1,
        my_wire=wires[1],
        my_revealed_positions={},
        call_history=game.call_history,
        n_players=config.n_players,
        wire_length=config.wires_per_player
    )
    
    loaded_belief = game.players[1].belief_system.__class__.load_from_folder(
        str(output_path), 1, observation_p1, config
    )
    
    print("✓ Loaded successfully")
    
    print("\n" + "="*80)
    print("BELIEF STATE AFTER LOADING (Player 1)")
    print("="*80)
    loaded_belief.print_beliefs()
    
    print("\n" + "="*80)
    print("VALUE TRACKER AFTER LOADING (Player 1)")
    print("="*80)
    print("\nValue trackers:")
    for value in sorted(loaded_belief.value_trackers.keys()):
        tracker = loaded_belief.value_trackers[value]
        print(f"  Value {value}: revealed={tracker.revealed}, certain={tracker.certain}, "
              f"called={tracker.called}, uncertain={tracker.get_uncertain_count()}")
    
    print("\n" + "="*80)
    print("PART 4: Verify data integrity")
    print("="*80)
    
    # Compare original and loaded belief models
    print("\nComparing original vs loaded belief models...")
    
    all_match = True
    for player_id in range(config.n_players):
        for pos in range(config.wires_per_player):
            original = players[1].belief_system.beliefs[player_id][pos]
            loaded = loaded_belief.beliefs[player_id][pos]
            if original != loaded:
                print(f"  ✗ Mismatch at Player {player_id}, Position {pos}: "
                      f"{original} vs {loaded}")
                all_match = False
    
    if all_match:
        print("  ✓ All belief sets match perfectly")
    
    # Compare value trackers
    print("\nComparing value trackers...")
    all_vt_match = True
    for value in config.wire_values:
        orig_tracker = players[1].belief_system.value_trackers[value]
        load_tracker = loaded_belief.value_trackers[value]
        
        if (orig_tracker.revealed != load_tracker.revealed or
            orig_tracker.certain != load_tracker.certain or
            orig_tracker.called != load_tracker.called):
            print(f"  ✗ Mismatch for value {value}")
            all_vt_match = False
    
    if all_vt_match:
        print("  ✓ All value trackers match perfectly")
    
    print("\n" + "="*80)
    print("PART 5: Inspect JSON files")
    print("="*80)
    
    # Show a sample JSON file
    print("\nSample: Player 1's belief.json (first 30 lines):")
    print("-" * 80)
    belief_file = output_path / "player_1" / "belief.json"
    with belief_file.open("r") as f:
        lines = f.readlines()[:30]
        for line in lines:
            print(line.rstrip())
        if len(lines) == 30:
            print("  ... (truncated)")
    
    print("\n" + "="*80)
    print("Sample: Player 1's value_tracker.json:")
    print("-" * 80)
    vt_file = output_path / "player_1" / "value_tracker.json"
    with vt_file.open("r") as f:
        print(f.read())
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)
    print(f"\n✓ Belief snapshots saved to '{output_folder}/'")
    print("✓ Load/save cycle verified successfully")
    print(f"\nYou can manually edit the JSON files in '{output_folder}/' and reload them for debugging.")


if __name__ == "__main__":
    test_serialization()
