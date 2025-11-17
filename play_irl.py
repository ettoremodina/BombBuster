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
SAVE_TO_JSON = True   # Set to False to disable saving beliefs to JSON files
LOAD_FROM_JSON = False  # Set to False to start fresh (ignore existing JSON files)

# ============================================================================
# CALL HISTORY - Add calls here as they happen
# ============================================================================
# Format: (caller, target, position, value, success, [caller_position])

CALLS = [
    # ("Charlie", "Bob", 5, 8, True, ),     
    # ("Alice", "Bob", 7, 8, True, 8),     
]

# ============================================================================
# DOUBLE REVEALS - Add double reveals here 
# ============================================================================
# If I want to drop 4, just call the function twice
# Format: (player, value, position1, position2)

DOUBLE_REVEALS = [
    ("Charlie", 10, 9, 10),  # Charlie reveals last 2 copies of value 12
]

# ============================================================================
# WIRE SWAPS - Add swaps here (optional)
# ============================================================================
# Format: (player1, player2, init_pos1, init_pos2, final_pos1, final_pos2, received_value)
#
# Use this when two players exchange wires
# 
# IMPORTANT: received_value is REQUIRED if you (MY_PLAYER_ID) are one of the players!
#            This is the value YOU received from the swap (you can see it)
#
# EASY FORMAT (recommended):
#   - Use player names from PLAYER_NAMES (or IDs as integers)
#   - Positions are 1-indexed (1, 2, 3, ...) - easier to count!
#   - init_pos: position of wire being given away
#   - final_pos: position where received wire is inserted (after sorting)
#   - received_value: the value YOU received (required if you're involved)
#   
#   Example: ("Alice", "Bob", 5, 3, 4, 6, 7)
#     If YOU are Alice: You give position 5, receive value 7 inserted at position 4
#     If YOU are Bob: Bob gives position 3, receives wire inserted at position 6
#   
#   Example: ("Charlie", "Diana", 2, 8, 3, 7)
#     Neither player is you, so received_value is optional (can be omitted)
#
# The script automatically converts to internal format (0-indexed)

SWAPS = [
    # ("Alice", "Bob", 5, 4, 5, 7, 6),  # You (Alice) receive value 8
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
