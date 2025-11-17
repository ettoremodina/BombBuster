"""
Real-life gameplay script for BombBuster.
Used when playing with physical cards/wires with friends.

HOW TO USE:
1. Set your wire in MY_WIRE (your actual cards)
2. Set player names in PLAYER_NAMES (optional, for clarity)
3. Add calls to CALLS list as the game progresses
4. Add double reveals to DOUBLE_REVEALS list (optional, when revealing last 2 copies)
5. Run the script to see updated game state and suggestions

FEATURES:
- Automatic belief system updates
- Call suggestions (certain and uncertain)
- Double reveal support (reveal last 2 copies of a value at once)
- State persistence (saves to JSON, reloads on next run)
- User-friendly format: 1-indexed positions, player names
"""

from config.game_config import GameConfig
from src.utils import (
    run_irl_game_session,
    print_game_header,
    print_player_setup,
    print_call_history,
    print_game_state,
    print_player_info,
    print_belief_state,
    print_session_complete
)

# ============================================================================
# GAME CONFIGURATION - Edit these values
# ============================================================================

# Your wire (the cards you're holding)
MY_WIRE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Your player ID (0, 1, 2, 3, ...)
MY_PLAYER_ID = 0

# Player names (optional - makes output more readable)
# If you don't want to use names, set to None or {}
PLAYER_NAMES = {
    0: "Alice",
    1: "Bob", 
    2: "Charlie",
    3: "Diana",
    4: "Eve"
}

# Folder to save/load belief state
BELIEF_FOLDER = "real_game_beliefs"

# Control saving and loading of beliefs and value tracker
SAVE_TO_JSON = False   # Set to False to disable saving beliefs to JSON files
LOAD_FROM_JSON = True  # Set to False to start fresh (ignore existing JSON files)

# ============================================================================
# CALL HISTORY - Add calls here as they happen
# ============================================================================
# Format: (caller, target, position, value, success, [caller_position])
# 
# EASY FORMAT (recommended):
#   - Use player names from PLAYER_NAMES (or IDs as integers)
#   - Positions are 1-indexed (1, 2, 3, ...) - easier to count!
#   - caller_position is OPTIONAL - only for successful calls to reveal caller's wire position
#   - Example: ("Alice", "Bob", 3, 5, True, 2) = Alice calls Bob[3] = 5, SUCCESS, Alice has 5 at position 2
#   - Example: ("Alice", "Bob", 3, 5, True) = Alice calls Bob[3] = 5, SUCCESS (caller position not revealed)
#   - Example: (0, 1, 3, 5, False) = Player 0 calls Player 1[3] = 5, FAIL
#
# The script automatically converts to internal format (0-indexed)

CALLS = [
    # Add your calls here
    # ("Alice", "Bob", 5, 3, True, 3),      # Alice calls Bob position 5 = 3, SUCCESS
    # ("Bob", "Charlie", 5, 4, True, 6),    # Bob calls Charlie position 5 = 4, SUCCESS
    # ("Alice", "Bob", 2, 1, True, 1),   # Bob calls Charlie position 5 = 6, FAIL
    ("Alice", "Bob", 5, 7, True, 7),   # Alice calls Bob[3] = 7, SUCCESS, Alice has 7 at position 4

]

# ============================================================================
# DOUBLE REVEALS - Add double reveals here (optional)
# ============================================================================
# Format: (player, value, position1, position2)
#
# Use this when a player reveals the last 2 copies of a value at once
# 
# EASY FORMAT (recommended):
#   - Use player names from PLAYER_NAMES (or IDs as integers)
#   - Positions are 1-indexed (1, 2, 3, ...) - easier to count!
#   - Example: ("Alice", 5, 3, 7) = Alice reveals positions 3 and 7 both have value 5
#   - Example: (0, 5, 3, 7) = Player 0 reveals positions 3 and 7 both have value 5
#
# The script automatically converts to internal format (0-indexed)

DOUBLE_REVEALS = [
    # Add your double reveals here (optional)
    ("Bob", 12, 9, 10),  # Bob reveals last 2 copies of value 12
]

# ============================================================================
# WIRE SWAPS - Add swaps here (optional)
# ============================================================================
# Format: (player1, player2, init_pos1, init_pos2, final_pos1, final_pos2)
#
# Use this when two players exchange wires
# 
# EASY FORMAT (recommended):
#   - Use player names from PLAYER_NAMES (or IDs as integers)
#   - Positions are 1-indexed (1, 2, 3, ...) - easier to count!
#   - init_pos: position of wire being given away
#   - final_pos: position where received wire is inserted (after sorting)
#   - Example: ("Alice", "Bob", 5, 3, 4, 6)
#     Alice gives position 5, receives wire inserted at position 4
#     Bob gives position 3, receives wire inserted at position 6
#
# The script automatically converts to internal format (0-indexed)

SWAPS = [
    # Add your swaps here (optional)
    # ("Alice", "Bob", 5, 3, 4, 6),
]

# ============================================================================
# SCRIPT - Run the game session
# ============================================================================

def main():
    """Run the real-life game tracker."""
    
    # Create game configuration with IRL flag enabled
    # This disables validation that caller possesses the called value
    config = GameConfig(playing_irl=True)
    
    # Print header
    print_game_header(config)
    
    # Run game session
    try:
        result = run_irl_game_session(
            my_wire=MY_WIRE,
            my_player_id=MY_PLAYER_ID,
            calls=CALLS,
            config=config,
            belief_folder=BELIEF_FOLDER,
            player_names=PLAYER_NAMES,
            double_reveals=DOUBLE_REVEALS,
            swaps=SWAPS,
            save_to_json=SAVE_TO_JSON,
            load_from_json=LOAD_FROM_JSON
        )
    except ValueError as e:
        print(f"\n❌ ERROR: {e}\n")
        return
    
    # Extract results
    players = result['players']
    my_player = result['my_player']
    state = result['state']
    call_records = result['call_records']
    loaded_from_file = result['loaded_from_file']
    player_names = result['player_names']
    
    # Print player setup
    print_player_setup(players, MY_PLAYER_ID, player_names)
    
    # Show if loaded from previous session
    if loaded_from_file:
        print(f"\n📂 Loaded existing belief state from {BELIEF_FOLDER}/")
        print(f"   💡 You can manually edit JSON files in that folder")
    else:
        print(f"\n📝 Starting fresh belief state")
        print(f"   Will be saved to {BELIEF_FOLDER}/ folder")
    
    # Print call history
    print_call_history(call_records, player_names)
    
    # Print game state
    print_game_state(state, config)
    
    # Print your information and suggestions
    # print_player_info(my_player, MY_PLAYER_ID, state, player_names, config)
    
    # Print belief state
    print_belief_state(my_player, BELIEF_FOLDER, MY_PLAYER_ID, player_names, config)
    
    # Print session complete
    # print_session_complete(BELIEF_FOLDER)


if __name__ == "__main__":
    main()
