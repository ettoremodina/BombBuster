"""
Utility functions for BombBuster game setup.
Handles wire distribution, game utilities, and IRL gameplay helpers.
"""

import random
import json
from typing import List, Union, Dict, Tuple, Optional
from pathlib import Path
from config.game_config import GameConfig, USE_VOID_PLAYER, EXTRA_UNCERTAIN_WIRES, PLAYER_NAMES
from src.statistics import GameStatistics


def find_first_unrevealed_position(player, value: Union[int, float]) -> Optional[int]:
    """
    Find the first position in the player's wire that contains the given value
    and has not been revealed yet.
    
    Args:
        player: The Player object
        value: The value to search for
        
    Returns:
        The index of the first unrevealed position with the value, or None if not found.
    """
    if player.wire is None:
        return None
        
    value_tracker = None
    if hasattr(player, 'belief_system') and player.belief_system is not None:
        value_tracker = player.belief_system.value_trackers.get(value)
    
    for pos, val in enumerate(player.wire):
        if val == value:
            # Check if this position is revealed
            is_revealed = False
            if value_tracker:
                for revealed_pid, revealed_pos in value_tracker.revealed:
                    if revealed_pid == player.player_id and revealed_pos == pos:
                        is_revealed = True
                        break
            
            if not is_revealed:
                return pos
                
    return None


def generate_wires(config: GameConfig, seed: int = None) -> List[List[Union[int, float]]]:
    """
    Generate wires for all players.
    
    Args:
        config: Game configuration
        seed: Random seed for reproducibility
        
    Returns:
        List of sorted wires, one per player (values can be int or float)
    """
    if seed is not None:
        random.seed(seed)
    
    if USE_VOID_PLAYER:
        # 1. Identify VOID player
        try:
            void_idx = PLAYER_NAMES.index("VOID")
        except ValueError:
            # Fallback if VOID not found in names but flag is set
            void_idx = config.n_players - 1 
            print("WARNING: VOID player not found in PLAYER_NAMES, assigning last index as VOID.")
        
        # 2. Select one uncertain wire for VOID
        uncertain_candidates = []
        for val, count in EXTRA_UNCERTAIN_WIRES.items():
            uncertain_candidates.extend([val] * count)
        
        if not uncertain_candidates:
             void_wire_val = None
        else:
            void_wire_val = random.choice(uncertain_candidates)
            
        # 3. Build decks
        real_deck = []
        void_deck = []
        
        # Collect all 0s for VOID
        zeros_count = config.get_copies(0)
        if zeros_count > 0:
            void_deck.extend([0] * zeros_count)
        
        # Add the chosen uncertain wire to VOID
        if void_wire_val is not None:
            void_deck.append(void_wire_val)
            
        # Now build real_deck with everything else
        for value in config.wire_values:
            if value == 0:
                continue # Already handled
            
            count = config.get_copies(value)
            
            if value == void_wire_val:
                # We gave one to VOID
                count -= 1
            
            if count > 0:
                real_deck.extend([value] * count)
                
        # Shuffle real deck
        random.shuffle(real_deck)
        
        # Distribute
        wires = [None] * config.n_players
        
        # Assign VOID wire
        wires[void_idx] = sorted(void_deck)
        
        # Assign Real wires
        current_idx = 0
        for i in range(config.n_players):
            if i == void_idx:
                continue
                
            hand_size = config.wires_per_player
            wires[i] = sorted(real_deck[current_idx : current_idx + hand_size])
            current_idx += hand_size
            
        return wires

    # Standard generation (No VOID player)
    # Create full deck
    deck = []
    for value in config.wire_values:
        copies = config.get_copies(value)
        deck.extend([value] * copies)
    
    # Shuffle and deal
    random.shuffle(deck)
    
    wires = []
    for i in range(config.n_players):
        start_idx = i * config.wires_per_player
        end_idx = start_idx + config.wires_per_player
        wire = sorted(deck[start_idx:end_idx])
        wires.append(wire)
    
    return wires


def print_all_wires(wires: List[List[Union[int, float]]]):
    """Print all wires in a formatted way (for debugging)."""
    print("\n" + "=" * 70)
    print("GROUND TRUTH - All Player Wires")
    print("=" * 70)
    for player_id, wire in enumerate(wires):
        print(f"Player {player_id}: {wire}")
    print("=" * 70 + "\n")


# ============================================================================
# IRL Gameplay Utilities - Helper Functions
# ============================================================================

def _parse_player_id(player_identifier: Union[str, int], player_names: Dict[int, str] = None) -> int:
    """
    Convert player name or ID to integer ID.
    
    Args:
        player_identifier: Player name (str) or ID (int)
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Integer player ID
    """
    if isinstance(player_identifier, int):
        return player_identifier
    
    # Create reverse mapping (name -> ID) if needed
    if player_names:
        name_to_id = {name: pid for pid, name in player_names.items()}
        if player_identifier in name_to_id:
            return name_to_id[player_identifier]
    
    # Try to parse as integer
    try:
        return int(player_identifier)
    except ValueError:
        raise ValueError(f"Invalid player identifier: {player_identifier}. Must be player name or ID.")


def _get_player_name(player_id: int, player_names: Dict[int, str] = None) -> str:
    """
    Get player name from ID, or fallback to 'Player X' format.
    
    Args:
        player_id: Player ID
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Player name string
    """
    if player_names:
        return player_names.get(player_id, f"Player {player_id}")
    return f"Player {player_id}"


# ============================================================================
# IRL Gameplay Utilities - Conversion Functions
# ============================================================================

def convert_call_to_internal(call: Tuple, player_names: Dict[int, str] = None) -> Tuple:
    """
    Convert a user-friendly call format (1-indexed positions, optional names) 
    to internal format (0-indexed positions, player IDs).
    
    Args:
        call: Tuple of (caller, target, position, value, success) 
              OR (caller, target, position, value, success, caller_position)
              - caller/target can be player names (str) or IDs (int)
              - position is 1-indexed (user-friendly)
              - caller_position is 1-indexed (optional, only for successful calls)
        player_names: Optional dict mapping IDs to names {0: "Alice", 1: "Bob", ...}
        
    Returns:
        Tuple of (caller_id, target_id, position_0indexed, value, success, caller_position_0indexed)
        caller_position_0indexed will be None if not provided
    """
    # Handle both 5-element and 6-element tuples
    if len(call) == 5:
        caller, target, position, value, success = call
        caller_position = None
    elif len(call) == 6:
        caller, target, position, value, success, caller_position = call
    else:
        raise ValueError(f"Call tuple must have 5 or 6 elements, got {len(call)}")
    
    # Convert names to IDs
    caller_id = _parse_player_id(caller, player_names)
    target_id = _parse_player_id(target, player_names)
    
    # Convert position from 1-indexed to 0-indexed
    position_internal = position - 1
    
    # Convert caller_position from 1-indexed to 0-indexed if provided
    caller_position_internal = None
    if caller_position is not None:
        caller_position_internal = caller_position - 1
    
    return (caller_id, target_id, position_internal, value, success, caller_position_internal)


def convert_double_reveal_to_internal(reveal: Tuple, player_names: Dict[int, str] = None) -> Tuple:
    """
    Convert a user-friendly double reveal format (1-indexed positions, optional names)
    to internal format (0-indexed positions, player IDs).
    
    Args:
        reveal: Tuple of (player, value, position1, position2)
                - player can be name (str) or ID (int)
                - positions are 1-indexed (user-friendly)
        player_names: Optional dict mapping IDs to names {0: "Alice", 1: "Bob", ...}
        
    Returns:
        Tuple of (player_id, value, position1_0indexed, position2_0indexed)
    """
    player, value, position1, position2 = reveal
    
    # Convert name to ID
    player_id = _parse_player_id(player, player_names)
    
    # Convert positions from 1-indexed to 0-indexed
    return (player_id, value, position1 - 1, position2 - 1)


def format_double_reveal_for_user(reveal_record, player_names: Dict[int, str] = None) -> str:
    """
    Format a double reveal record in a user-friendly way with names and 1-indexed positions.
    
    Args:
        reveal_record: DoubleRevealRecord object
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    player_name = _get_player_name(reveal_record.player_id, player_names)
    pos1_display = reveal_record.position1 + 1
    pos2_display = reveal_record.position2 + 1
    return f"{player_name} DOUBLE REVEAL positions {pos1_display} and {pos2_display} = {reveal_record.value}"


def convert_signal_to_internal(signal: Tuple, player_names: Dict[int, str] = None) -> Tuple:
    """
    Convert a user-friendly signal format (1-indexed position, optional names)
    to internal format (0-indexed position, player ID).
    
    Args:
        signal: Tuple of (player, value, position)
                - player can be name (str) or ID (int)
                - position is 1-indexed (user-friendly)
        player_names: Optional dict mapping IDs to names {0: "Alice", 1: "Bob", ...}
        
    Returns:
        Tuple of (player_id, value, position_0indexed)
    """
    player, value, position = signal
    player_id = _parse_player_id(player, player_names)
    return (player_id, value, position - 1)


def format_signal_for_user(signal_record, player_names: Dict[int, str] = None) -> str:
    """
    Format a signal record in a user-friendly way with names and 1-indexed position.
    
    Args:
        signal_record: SignalRecord object
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    player_name = _get_player_name(signal_record.player_id, player_names)
    pos_display = signal_record.position + 1
    return f"{player_name} SIGNALS position {pos_display} = {signal_record.value}"


def convert_not_present_to_internal(not_present: Tuple, player_names: Dict[int, str] = None) -> Tuple:
    """
    Convert a user-friendly not-present format to internal format.
    
    Args:
        not_present: Tuple of (player, value) or (player, value, position)
                     - player can be name (str) or ID (int)
                     - position is 1-indexed if present
        player_names: Optional dict mapping IDs to names {0: "Alice", 1: "Bob", ...}
        
    Returns:
        Tuple of (player_id, value, position_0indexed)
    """
    if len(not_present) == 3:
        player, value, pos_1based = not_present
        position = pos_1based - 1
    else:
        player, value = not_present
        position = None
    
    player_id = _parse_player_id(player, player_names)
    return (player_id, value, position)


def format_not_present_for_user(not_present_record, player_names: Dict[int, str] = None) -> str:
    """
    Format a not-present record in a user-friendly way with names.
    
    Args:
        not_present_record: NotPresentRecord object
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    player_name = _get_player_name(not_present_record.player_id, player_names)
    
    if not_present_record.position is not None:
        return f"{player_name} DOES NOT HAVE value {not_present_record.value} at pos {not_present_record.position + 1}"
    return f"{player_name} DOES NOT HAVE value {not_present_record.value}"


def convert_has_value_to_internal(has_value: Tuple, player_names: Dict[int, str] = None) -> Tuple:
    """
    Convert a user-friendly has-value format to internal format.
    
    Args:
        has_value: Tuple of (player, value)
                   - player can be name (str) or ID (int)
        player_names: Optional dict mapping IDs to names {0: "Alice", 1: "Bob", ...}
        
    Returns:
        Tuple of (player_id, value)
    """
    player, value = has_value
    player_id = _parse_player_id(player, player_names)
    return (player_id, value)


def format_has_value_for_user(player_id: int, value: Union[int, float], player_names: Dict[int, str] = None) -> str:
    """
    Format a has-value record in a user-friendly way with names.
    
    Args:
        player_id: Player ID
        value: The value the player has
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    player_name = _get_player_name(player_id, player_names)
    return f"{player_name} HAS value {value}"


def convert_swap_to_internal(swap: Tuple, player_names: Dict[int, str] = None, my_player_id: int = None) -> Tuple:
    """
    Convert a user-friendly swap format (1-indexed positions, optional names)
    to internal format (0-indexed positions, player IDs).
    
    Args:
        swap: Tuple of (player1, player2, init_pos1, init_pos2, final_pos1, final_pos2, [received_value])
              - players can be names (str) or IDs (int)
              - positions are 1-indexed (user-friendly)
              - received_value is OPTIONAL: the value received by the IRL player (my_player_id)
                If provided and one of the players is my_player_id, this value will be used
        player_names: Optional dict mapping IDs to names {0: "Alice", 1: "Bob", ...}
        my_player_id: Optional ID of the IRL player (needed to determine which player receives the value)
        
    Returns:
        Tuple of (player1_id, player2_id, init_pos1_0idx, init_pos2_0idx, 
                  final_pos1_0idx, final_pos2_0idx, received_value_or_none)
    """
    # Handle both 6-element and 7-element tuples
    if len(swap) == 7:
        player1, player2, init_pos1, init_pos2, final_pos1, final_pos2, received_value = swap
    elif len(swap) == 6:
        player1, player2, init_pos1, init_pos2, final_pos1, final_pos2 = swap
        received_value = None
    else:
        raise ValueError(f"Swap tuple must have 6 or 7 elements, got {len(swap)}")
    
    # Convert names to IDs
    player1_id = _parse_player_id(player1, player_names)
    player2_id = _parse_player_id(player2, player_names)
    
    # Validate received_value is provided when IRL player is involved
    if my_player_id is not None and received_value is None:
        if player1_id == my_player_id or player2_id == my_player_id:
            raise ValueError(
                f"received_value is required when you (Player {my_player_id}) are involved in a swap. "
                f"Format: (player1, player2, init_pos1, init_pos2, final_pos1, final_pos2, received_value)"
            )
    
    # Convert positions from 1-indexed to 0-indexed
    return (player1_id, player2_id, init_pos1 - 1, init_pos2 - 1,
            final_pos1 - 1, final_pos2 - 1, received_value)


def format_swap_for_user(swap_record, player_names: Dict[int, str] = None) -> str:
    """
    Format a swap record in a user-friendly way with names and 1-indexed positions.
    
    Args:
        swap_record: SwapRecord object
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    p1_name = _get_player_name(swap_record.player1_id, player_names)
    p2_name = _get_player_name(swap_record.player2_id, player_names)
    
    # Convert positions to 1-indexed
    p1_init = swap_record.player1_init_pos + 1
    p2_init = swap_record.player2_init_pos + 1
    p1_final = swap_record.player1_final_pos + 1
    p2_final = swap_record.player2_final_pos + 1
    
    return f"{p1_name}[{p1_init}→{p1_final}] ↔ {p2_name}[{p2_init}→{p2_final}]"


def format_call_for_user(call_record, player_names: Dict[int, str] = None) -> str:
    """
    Format a call record in a user-friendly way with names and 1-indexed positions.
    
    Args:
        call_record: CallRecord object
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    caller_name = _get_player_name(call_record.caller_id, player_names)
    target_name = _get_player_name(call_record.target_id, player_names)
    position_user = call_record.position + 1
    result = "SUCCESS" if call_record.success else "FAIL"
    return f"{caller_name} → {target_name}[{position_user}] = {call_record.value} [{result}]"


def save_action_history(belief_folder: str, player_id: int, 
                       calls: List[Tuple], double_reveals: List[Tuple],
                       swaps: List[Tuple], signals: List[Tuple],
                       reveals: List[Tuple], not_present: List[Tuple],
                       has_values: List[Tuple] = None,
                       copy_count_signals: List[Tuple] = None,
                       adjacent_signals: List[Tuple] = None):
    """
    Save the action history to track what has been processed.
    
    Args:
        belief_folder: Folder to save history
        player_id: Player ID
        calls: List of call tuples
        double_reveals: List of double reveal tuples
        swaps: List of swap tuples
        signals: List of signal tuples
        reveals: List of reveal tuples
        not_present: List of not-present tuples
        has_values: List of has-value tuples
        copy_count_signals: List of copy count signal tuples
        adjacent_signals: List of adjacent signal tuples
    """
    from pathlib import Path
    
    if has_values is None:
        has_values = []
    if copy_count_signals is None:
        copy_count_signals = []
    if adjacent_signals is None:
        adjacent_signals = []
    
    belief_path = Path(belief_folder)
    player_dir = belief_path / f"player_{player_id}"
    player_dir.mkdir(parents=True, exist_ok=True)
    
    history_file = player_dir / "action_history.json"
    
    history_data = {
        "calls": calls,
        "double_reveals": double_reveals,
        "swaps": swaps,
        "signals": signals,
        "reveals": reveals,
        "not_present": not_present,
        "has_values": has_values,
        "copy_count_signals": copy_count_signals,
        "adjacent_signals": adjacent_signals
    }
    
    with history_file.open("w", encoding="utf-8") as fh:
        json.dump(history_data, fh, indent=2)


def load_action_history(belief_folder: str, player_id: int) -> Optional[Dict]:
    """
    Load the action history if it exists.
    
    Args:
        belief_folder: Folder where history is saved
        player_id: Player ID
        
    Returns:
        Dict with action lists or None if file doesn't exist
    """
    from pathlib import Path
    
    belief_path = Path(belief_folder)
    history_file = belief_path / f"player_{player_id}" / "action_history.json"
    
    if not history_file.exists():
        return None
    
    with history_file.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def get_new_actions(old_actions: List, new_actions: List) -> List:
    """
    Get only the new actions that weren't in the old list.
    
    Args:
        old_actions: Previously processed actions
        new_actions: All actions including old and new
        
    Returns:
        List of only new actions
    """
    old_count = len(old_actions)
    return new_actions[old_count:]


def run_irl_game_session(
    my_wire: List[Union[int, float]],
    my_player_id: int,
    calls: List[Tuple],
    config: GameConfig,
    belief_folder: str = "real_game_beliefs",
    player_names: Dict[int, str] = None,
    double_reveals: List[Tuple] = None,
    swaps: List[Tuple] = None,
    signals: List[Tuple] = None,
    reveals: List[Tuple] = None,
    not_present: List[Tuple] = None,
    has_values: List[Tuple] = None,
    copy_count_signals: List[Tuple] = None,
    adjacent_signals: List[Tuple] = None,
    save_to_json: bool = True,
    load_from_json: bool = True
) -> Dict:
    """
    Run a complete IRL game session with all processing.
    
    Args:
        my_wire: Your wire (actual cards you're holding)
        my_player_id: Your player ID
        calls: List of call tuples (can use 1-indexed positions and names)
        config: Game configuration
        belief_folder: Folder to save/load belief state
        player_names: Optional dict mapping player IDs to names
        double_reveals: Optional list of double reveal tuples (player, value, pos1, pos2)
        swaps: Optional list of swap tuples (player1, player2, init_pos1, init_pos2, final_pos1, final_pos2)
        signals: Optional list of signal tuples (player, value, position)
        reveals: Optional list of reveal tuples (player, value, position)
        not_present: Optional list of not-present tuples (player, value)
        has_values: Optional list of has-value tuples (player, value)
        save_to_json: If True, save beliefs and value tracker to JSON files
        load_from_json: If True, attempt to load existing beliefs from JSON files
        
    Returns:
        Dict with game state, player object, and other info
    """
    from src.player import Player
    from src.game import Game
    from src.belief.belief_model import BeliefModel
    from src.data_structures import GameObservation
    
    if double_reveals is None:
        double_reveals = []
    if swaps is None:
        swaps = []
    if signals is None:
        signals = []
    if reveals is None:
        reveals = []
    if not_present is None:
        not_present = []
    if has_values is None:
        has_values = []
    if copy_count_signals is None:
        copy_count_signals = []
    if adjacent_signals is None:
        adjacent_signals = []
    
    # Validate wire length
    if len(my_wire) != config.wires_per_player:
        raise ValueError(
            f"MY_WIRE has {len(my_wire)} values, but config expects {config.wires_per_player}. "
            f"Please update MY_WIRE or modify WIRE_DISTRIBUTION in config/game_config.py"
        )
    
    # Generate dummy wires for other players
    all_wires = generate_wires(config, seed=42)
    all_wires[my_player_id] = sorted(my_wire)
    
    # Create players
    players = []
    for player_id in range(config.n_players):
        if player_id == my_player_id:
            player = Player(player_id, my_wire, config)
        else:
            player = Player(player_id, all_wires[player_id], config)
        players.append(player)
    
    # Create game
    game = Game(players, config)
    
    # Try to load existing belief state (only if load_from_json is True)
    belief_path = Path(belief_folder)
    belief_file = belief_path / f"player_{my_player_id}" / "belief.json"
    
    loaded_from_file = False
    if load_from_json and belief_file.exists():
        my_player = players[my_player_id]
        # Create observation for loading
        observation = GameObservation(
            player_id=my_player_id,
            my_wire=my_player.wire,
            my_revealed_positions=my_player.revealed_positions.copy(),
            call_history=[],
            n_players=config.n_players,
            wire_length=config.wires_per_player
        )
        
        loaded_belief = BeliefModel.load_from_folder(
            str(belief_path),
            my_player_id,
            observation,
            config
        )
        my_player.belief_system = loaded_belief
        loaded_from_file = True

    
    # Determine which actions to process (incremental if both save and load are enabled)
    calls_to_process = calls
    double_reveals_to_process = double_reveals
    swaps_to_process = swaps
    signals_to_process = signals
    reveals_to_process = reveals
    not_present_to_process = not_present
    has_values_to_process = has_values
    copy_count_signals_to_process = copy_count_signals
    adjacent_signals_to_process = adjacent_signals
    processed_incrementally = False
    
    # If both save and load are enabled, only process new actions
    if save_to_json and load_from_json and loaded_from_file:
        old_history = load_action_history(belief_folder, my_player_id)
        if old_history is not None:
            # Only process actions that are new since last save
            calls_to_process = get_new_actions(old_history.get("calls", []), calls)
            double_reveals_to_process = get_new_actions(old_history.get("double_reveals", []), double_reveals)
            swaps_to_process = get_new_actions(old_history.get("swaps", []), swaps)
            signals_to_process = get_new_actions(old_history.get("signals", []), signals)
            reveals_to_process = get_new_actions(old_history.get("reveals", []), reveals)
            not_present_to_process = get_new_actions(old_history.get("not_present", []), not_present)
            has_values_to_process = get_new_actions(old_history.get("has_values", []), has_values)
            copy_count_signals_to_process = get_new_actions(old_history.get("copy_count_signals", []), copy_count_signals)
            adjacent_signals_to_process = get_new_actions(old_history.get("adjacent_signals", []), adjacent_signals)
            
            if any([calls_to_process, double_reveals_to_process, swaps_to_process, 
                   signals_to_process, reveals_to_process, not_present_to_process, has_values_to_process,
                   copy_count_signals_to_process, adjacent_signals_to_process]):
                processed_incrementally = True
                print(f"\n⚡ Incremental update: Processing {len(calls_to_process)} new calls, "
                      f"{len(double_reveals_to_process)} double reveals, {len(swaps_to_process)} swaps, "
                      f"{len(signals_to_process)} signals, {len(reveals_to_process)} reveals, "
                      f"{len(not_present_to_process)} not-present, {len(has_values_to_process)} has-values, "
                      f"{len(copy_count_signals_to_process)} copy-count, {len(adjacent_signals_to_process)} adjacent")
            else:
                print(f"\n✓ No new actions to process")

            # CRITICAL: Replay old swaps to ensure player's wire is up to date
            # When loading beliefs, we skip processing old actions, so the player's wire 
            # (which is re-initialized from config) would be stale without this replay.
            old_swaps = old_history.get("swaps", [])
            if old_swaps:
                # print(f"Replaying {len(old_swaps)} old swaps to update wire state...")
                for swap in old_swaps:
                    try:
                        internal_swap = convert_swap_to_internal(swap, player_names, my_player_id)
                        p1, p2, init1, init2, final1, final2, received_value = internal_swap
                        
                        # Normalize: In IRL mode, always put the IRL player (my_player_id) as player1
                        if received_value is not None:
                            if p2 == my_player_id:
                                p1, p2 = p2, p1
                                init1, init2 = init2, init1
                                final1, final2 = final2, final1
                        
                        # Only update if it affects us (my_player_id)
                        if p1 == my_player_id:
                            # Calculate final position logic (same as Game.swap_wires)
                            final1 = final1 + 1 if final1 >= init1 else final1
                            
                            player1 = game.players[p1]
                            
                            # We know what we received
                            value_p1_receives = received_value
                            
                            if value_p1_receives is not None:
                                # Update wire
                                player1.wire[init1] = None
                                player1.wire.insert(final1, value_p1_receives)
                                player1.wire = [v for v in player1.wire if v is not None]
                    except Exception as e:
                        print(f"Error replaying old swap: {e}")
    
    # Process all calls, double reveals, swaps, signals, reveals, and not-present announcements
    call_records = []
    double_reveal_records = []
    swap_records = []
    signal_records = []
    reveal_records = []
    not_present_records = []
    has_value_records = []
    copy_count_signal_records = []
    adjacent_signal_records = []
    
    for call in calls_to_process:
        try:
            # Convert call to internal format
            internal_call = convert_call_to_internal(call, player_names)
            caller, target, pos, val, success, caller_pos = internal_call
            
            call_record = game.make_call(caller, target, pos, val, success, caller_pos)
            call_records.append(call_record)
        except ValueError as e:
            call_records.append(f"ERROR: {e}")
    
    # Process double reveals
    for reveal in double_reveals_to_process:
        try:
            # Convert reveal to internal format
            internal_reveal = convert_double_reveal_to_internal(reveal, player_names)
            player, val, pos1, pos2 = internal_reveal
            
            reveal_record = game.double_reveal(player, val, pos1, pos2)
            double_reveal_records.append(reveal_record)
        except ValueError as e:
            double_reveal_records.append(f"ERROR: {e}")
    
    # Process swaps
    for swap in swaps_to_process:
        try:
            # Convert swap to internal format
            internal_swap = convert_swap_to_internal(swap, player_names, my_player_id)
            p1, p2, init1, init2, final1, final2, received_value = internal_swap
            
            # Normalize: In IRL mode, always put the IRL player (my_player_id) as player1
            # This simplifies the logic in belief_model.py
            if received_value is not None:
                if p2 == my_player_id:
                    # Swap players and positions so IRL player is always player1
                    p1, p2 = p2, p1
                    init1, init2 = init2, init1
                    final1, final2 = final2, final1
                    # received_value stays the same - it's what the IRL player receives
                
                # Now IRL player is always player1
                swap_record = game.swap_wires(p1, p2, init1, init2, final1, final2, 
                                             player1_received_value=received_value)
            else:
                # Simulation mode - no normalization needed
                swap_record = game.swap_wires(p1, p2, init1, init2, final1, final2)
            
            swap_records.append(swap_record)
        except ValueError as e:
            swap_records.append(f"ERROR: {e}")
    
    # Process signals
    for signal in signals_to_process:
        try:
            # Convert signal to internal format
            internal_signal = convert_signal_to_internal(signal, player_names)
            player, val, pos = internal_signal
            
            signal_record = game.signal_value(player, val, pos)
            signal_records.append(signal_record)
        except ValueError as e:
            signal_records.append(f"ERROR: {e}")
    
    # Process reveals
    for reveal in reveals_to_process:
        try:
            # Convert reveal to internal format (same format as signal)
            internal_reveal = convert_signal_to_internal(reveal, player_names)
            player, val, pos = internal_reveal
            
            reveal_record = game.reveal_value(player, val, pos)
            reveal_records.append(reveal_record)
        except ValueError as e:
            reveal_records.append(f"ERROR: {e}")
    
    # Process not-present announcements
    for np in not_present_to_process:
        try:
            # Convert not-present to internal format
            internal_np = convert_not_present_to_internal(np, player_names)
            player, val, pos = internal_np
            
            np_record = game.announce_not_present(player, val, pos)
            not_present_records.append(np_record)
        except ValueError as e:
            not_present_records.append(f"ERROR: {e}")
            
    # Process has-value announcements
    for hv in has_values_to_process:
        try:
            # Convert has-value to internal format
            internal_hv = convert_has_value_to_internal(hv, player_names)
            player, val = internal_hv
            
            # Note: announce_has_value doesn't return a record, but we track it anyway
            game.announce_has_value(player, val)
            has_value_records.append(f"Player {player} has value {val}")
        except ValueError as e:
            has_value_records.append(f"ERROR: {e}")
    
    # Process copy count signals
    for ccs in copy_count_signals_to_process:
        try:
            # Format: (player_name/id, position_0indexed, copy_count)
            if isinstance(ccs, tuple) and len(ccs) >= 3:
                # Create reverse mapping (name -> ID) if needed
                player_id = ccs[0]
                if isinstance(player_id, str) and player_names:
                    name_to_id = {name: pid for pid, name in player_names.items()}
                    player_id = name_to_id.get(player_id, int(player_id))
                
                position = ccs[1]
                copy_count = ccs[2]
                
                record = game.signal_copy_count(int(player_id), position, copy_count)
                copy_count_signal_records.append(record)
        except ValueError as e:
            copy_count_signal_records.append(f"ERROR: {e}")
    
    # Process adjacent signals
    for adj in adjacent_signals_to_process:
        try:
            # Format: (player_name/id, pos1_0indexed, pos2_0indexed, is_equal)
            if isinstance(adj, tuple) and len(adj) >= 4:
                # Create reverse mapping (name -> ID) if needed
                player_id = adj[0]
                if isinstance(player_id, str) and player_names:
                    name_to_id = {name: pid for pid, name in player_names.items()}
                    player_id = name_to_id.get(player_id, int(player_id))
                
                pos1 = adj[1]
                pos2 = adj[2]
                is_equal = adj[3]
                
                record = game.signal_adjacent(int(player_id), pos1, pos2, is_equal)
                adjacent_signal_records.append(record)
        except ValueError as e:
            adjacent_signal_records.append(f"ERROR: {e}")
    
    # Get game state
    state = game.get_game_state()
    
    # Save belief state and action history (only if save_to_json is True)
    my_player = players[my_player_id]
    if save_to_json and my_player.belief_system is not None:
        try:
            my_player.belief_system.save_to_folder(belief_folder, player_names)
            # Also save action history to enable incremental processing
            save_action_history(belief_folder, my_player_id, 
                              calls, double_reveals, swaps, signals, reveals, not_present, has_values,
                              copy_count_signals, adjacent_signals)
        except Exception as e:
            print(f"⚠️  Warning: Could not save belief state: {e}")
    
    return {
        'players': players,
        'game': game,
        'my_player': my_player,
        'state': state,
        'call_records': call_records,
        'double_reveal_records': double_reveal_records,
        'swap_records': swap_records,
        'signal_records': signal_records,
        'reveal_records': reveal_records,
        'not_present_records': not_present_records,
        'has_value_records': has_value_records,
        'copy_count_signal_records': copy_count_signal_records,
        'adjacent_signal_records': adjacent_signal_records,
        'loaded_from_file': loaded_from_file,
        'processed_incrementally': processed_incrementally,
        'belief_folder': belief_folder,
        'player_names': player_names or {}
    }


def print_game_header(config: GameConfig):
    """Print game configuration header."""
    print("\n" + "="*80)
    print("BOMBBUSTER - Real-Life Game Tracker")
    print("="*80)
    print(f"\nGame Configuration:")
    print(f"  Values: {config.wire_values}")
    print(f"  Wire distribution: {config.wire_distribution}")
    print(f"  Players: {config.n_players}")
    print(f"  Wires per player: {config.wires_per_player}")
    print(f"  Max wrong calls: {config.max_wrong_calls}")


def print_player_setup(players, my_player_id: int, player_names: Dict[int, str] = None):
    """Print player setup information."""
    for player in players:
        pid = player.player_id
        name = player_names.get(pid, f"Player {pid}") if player_names else f"Player {pid}"
        
        if pid == my_player_id:
            print(f"\n  {name} (YOU): Wire = {player.get_wire()}")
        else:
            print(f"  {name}: Wire = [Unknown - physical cards]")


def print_call_history(call_records, player_names: Dict[int, str] = None, only_recent: bool = False):
    """Print formatted call history."""
    print(f"\n" + "="*80)
    if only_recent and call_records:
        print("RECENTLY PROCESSED ACTIONS")
    else:
        print("CALL HISTORY")
    print("="*80)
    
    if not call_records:
        print("\nNo new actions processed.")
    else:
        for i, record in enumerate(call_records):
            if isinstance(record, str):  # Error message
                print(f"\n{i+1}. {record}")
            else:
                formatted = format_call_for_user(record, player_names)
                print(f"\n{i+1}. {formatted}")


def print_game_state(state, config: GameConfig):
    """Print current game state."""
    print(f"\n" + "="*80)
    print("GAME STATE")
    print("="*80)
    
    print(f"\nTurn: {state['turn']}")
    print(f"Total calls: {state['total_calls']}")
    print(f"Wrong calls: {state['wrong_calls_count']} / {config.max_wrong_calls}")
    print(f"Wrong calls remaining: {state['wrong_calls_remaining']}")
    
    if state['game_over']:
        print(f"\n{'='*80}")
        if state['team_won']:
            print("🎉 TEAM WINS! All wires deduced!")
        else:
            print("💥 TEAM LOSES! Too many wrong calls.")
        print(f"{'='*80}")
    else:
        print(f"\nGame status: ONGOING")


def print_player_info(my_player, my_player_id: int, state, player_names: Dict[int, str] = None, config: GameConfig = None):
    """Print your information and call suggestions."""
    player_name = player_names.get(my_player_id, f"Player {my_player_id}") if player_names else f"Player {my_player_id}"
    
    print(f"\n" + "="*80)
    print(f"YOUR INFORMATION ({player_name})")
    print("="*80)
    
    # Show call suggestions using Statistics class
    if my_player.belief_system is not None and not state['game_over']:
        # Create statistics analyzer
        stats = GameStatistics(my_player.belief_system, config or my_player.config, my_player.get_wire())
        
        # Use the statistics class to print suggestions
        stats.print_call_suggestions(player_names)


def print_belief_state(my_player, belief_folder: str, my_player_id: int, player_names: Dict[int, str] = None, config: GameConfig = None):
    """Print belief state, statistics, and save to JSON."""
    if my_player.belief_system is None:
        return
    
    print(f"\n" + "="*80)
    print("BELIEF STATE")
    print("="*80)
    my_player.belief_system.print_beliefs(player_names)
    # Check consistency
    if not my_player.belief_system.is_consistent():
        print("\n⚠️  WARNING: Belief state is INCONSISTENT! Some position has no possible values.")
    
    # Info about saved files
    print(f"\n💾 Belief state saved to {belief_folder}/")
    print(f"   📁 Files: {belief_folder}/player_{my_player_id}/belief.json")
    print(f"   📁 Files: {belief_folder}/player_{my_player_id}/value_tracker.json")
    
def print_statistics(my_player, player_names: Dict[int, str] = None, config: GameConfig = None):
    # Print statistics
    stats = GameStatistics(my_player.belief_system, config or my_player.config, my_player.get_wire())
    stats.print_statistics(player_names)
    
  


def print_session_complete(belief_folder: str):
    """Print session complete message."""
    print(f"\n" + "="*80)
    print("SESSION COMPLETE")
    print("="*80)
    print("\nTo continue playing:")
    print("1. Add call tuples to the CALLS list")
    print("2. Format: (caller, target, position, value, success)")
    print("   - Use player names (strings) or IDs (integers)")
    print("   - Positions are 1-indexed (1, 2, 3, ...)")
    print("3. Re-run this script")
    print(f"\n💡 Tip: Your belief state is saved in {belief_folder}/")
    print("   You can manually edit the JSON files to adjust beliefs")
    print("   The script will load from saved state on next run\n")


