"""
Example of play_irl.py with user-friendly format.
Shows how to use player names and 1-indexed positions.
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
# CONFIGURATION
# ============================================================================

MY_WIRE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
MY_PLAYER_ID = 0

# Optional: Give players names for easier reading
PLAYER_NAMES = {
    0: "Alice",
    1: "Bob",
    2: "Charlie",
    3: "Diana"
}

BELIEF_FOLDER = "real_game_beliefs"

# ============================================================================
# CALLS - Using user-friendly format
# ============================================================================

CALLS = [
    # Using names and 1-indexed positions (recommended!)
    ("Charlie", "Diana", 5, 3, False),    # Charlie calls Diana position 5 = 3, FAIL
    ("Alice", "Charlie", 6, 3, True),     # Alice calls Charlie position 6 = 3, SUCCESS
    ("Bob", "Alice", 9, 3, False),        # Bob calls Alice position 9 = 3, FAIL
    
    # You can also mix IDs and names:
    (0, "Bob", 1, 1, True),               # Alice calls Bob position 1 = 1, SUCCESS
    
    # Or use IDs only (if you prefer):
    # (0, 1, 1, 1, True),                 # Alice calls Bob position 1 = 1, SUCCESS
]

# ============================================================================
# MAIN
# ============================================================================

def main():
    config = GameConfig()
    print_game_header(config)
    
    try:
        result = run_irl_game_session(
            my_wire=MY_WIRE,
            my_player_id=MY_PLAYER_ID,
            calls=CALLS,
            config=config,
            belief_folder=BELIEF_FOLDER,
            player_names=PLAYER_NAMES
        )
    except ValueError as e:
        print(f"\n❌ ERROR: {e}\n")
        return
    
    players = result['players']
    my_player = result['my_player']
    state = result['state']
    call_records = result['call_records']
    loaded_from_file = result['loaded_from_file']
    player_names = result['player_names']
    
    print_player_setup(players, MY_PLAYER_ID, player_names)
    
    if loaded_from_file:
        print(f"\n📂 Loaded existing belief state from {BELIEF_FOLDER}/")
    else:
        print(f"\n📝 Starting fresh belief state")
    
    print_call_history(call_records, player_names)
    print_game_state(state, config)
    print_player_info(my_player, MY_PLAYER_ID, state, player_names)
    print_belief_state(my_player, BELIEF_FOLDER, MY_PLAYER_ID)
    print_session_complete(BELIEF_FOLDER)


if __name__ == "__main__":
    main()
