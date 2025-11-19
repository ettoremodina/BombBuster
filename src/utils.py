"""
Utility functions for BombBuster game setup.
Handles wire distribution, game utilities, and IRL gameplay helpers.
"""

import random
import json
from typing import List, Union, Dict, Tuple, Optional
from pathlib import Path
from config.game_config import GameConfig
from src.statistics import GameStatistics


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
# IRL Gameplay Utilities
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
    
    # Create reverse mapping (name -> ID) if needed
    name_to_id = {}
    if player_names:
        name_to_id = {name: pid for pid, name in player_names.items()}
    
    # Convert names to IDs if needed
    if isinstance(caller, str):
        if caller in name_to_id:
            caller = name_to_id[caller]
        else:
            try:
                caller = int(caller)
            except ValueError:
                raise ValueError(f"Invalid caller: {caller}. Must be player name or ID.")
    
    if isinstance(target, str):
        if target in name_to_id:
            target = name_to_id[target]
        else:
            try:
                target = int(target)
            except ValueError:
                raise ValueError(f"Invalid target: {target}. Must be player name or ID.")
    
    # Convert position from 1-indexed to 0-indexed
    position_internal = position - 1
    
    # Convert caller_position from 1-indexed to 0-indexed if provided
    caller_position_internal = None
    if caller_position is not None:
        caller_position_internal = caller_position - 1
    
    return (int(caller), int(target), position_internal, value, success, caller_position_internal)


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
    
    # Create reverse mapping (name -> ID) if needed
    name_to_id = {}
    if player_names:
        name_to_id = {name: pid for pid, name in player_names.items()}
    
    # Convert name to ID if needed
    if isinstance(player, str):
        if player in name_to_id:
            player = name_to_id[player]
        else:
            try:
                player = int(player)
            except ValueError:
                raise ValueError(f"Invalid player: {player}. Must be player name or ID.")
    
    # Convert positions from 1-indexed to 0-indexed
    pos1_internal = position1 - 1
    pos2_internal = position2 - 1
    
    return (int(player), value, pos1_internal, pos2_internal)


def format_double_reveal_for_user(reveal_record, player_names: Dict[int, str] = None) -> str:
    """
    Format a double reveal record in a user-friendly way with names and 1-indexed positions.
    
    Args:
        reveal_record: DoubleRevealRecord object
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    if player_names:
        player_name = player_names.get(reveal_record.player_id, f"Player {reveal_record.player_id}")
    else:
        player_name = f"Player {reveal_record.player_id}"
    
    # Convert positions to 1-indexed
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
    
    # Create reverse mapping (name -> ID) if needed
    name_to_id = {}
    if player_names:
        name_to_id = {name: pid for pid, name in player_names.items()}
    
    # Convert name to ID if needed
    if isinstance(player, str):
        if player in name_to_id:
            player = name_to_id[player]
        else:
            try:
                player = int(player)
            except ValueError:
                raise ValueError(f"Invalid player: {player}. Must be player name or ID.")
    
    # Convert position from 1-indexed to 0-indexed
    pos_internal = position - 1
    
    return (int(player), value, pos_internal)


def format_signal_for_user(signal_record, player_names: Dict[int, str] = None) -> str:
    """
    Format a signal record in a user-friendly way with names and 1-indexed position.
    
    Args:
        signal_record: SignalRecord object
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    if player_names:
        player_name = player_names.get(signal_record.player_id, f"Player {signal_record.player_id}")
    else:
        player_name = f"Player {signal_record.player_id}"
    
    # Convert position to 1-indexed
    pos_display = signal_record.position + 1
    
    return f"{player_name} SIGNALS position {pos_display} = {signal_record.value}"


def convert_not_present_to_internal(not_present: Tuple, player_names: Dict[int, str] = None) -> Tuple:
    """
    Convert a user-friendly not-present format to internal format.
    
    Args:
        not_present: Tuple of (player, value)
                     - player can be name (str) or ID (int)
        player_names: Optional dict mapping IDs to names {0: "Alice", 1: "Bob", ...}
        
    Returns:
        Tuple of (player_id, value)
    """
    player, value = not_present
    
    # Create reverse mapping (name -> ID) if needed
    name_to_id = {}
    if player_names:
        name_to_id = {name: pid for pid, name in player_names.items()}
    
    # Convert name to ID if needed
    if isinstance(player, str):
        if player in name_to_id:
            player = name_to_id[player]
        else:
            try:
                player = int(player)
            except ValueError:
                raise ValueError(f"Invalid player: {player}. Must be player name or ID.")
    
    return (int(player), value)


def format_not_present_for_user(not_present_record, player_names: Dict[int, str] = None) -> str:
    """
    Format a not-present record in a user-friendly way with names.
    
    Args:
        not_present_record: NotPresentRecord object
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    if player_names:
        player_name = player_names.get(not_present_record.player_id, f"Player {not_present_record.player_id}")
    else:
        player_name = f"Player {not_present_record.player_id}"
    
    return f"{player_name} DOES NOT HAVE value {not_present_record.value}"


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
    
    # Create reverse mapping (name -> ID) if needed
    name_to_id = {}
    if player_names:
        name_to_id = {name: pid for pid, name in player_names.items()}
    
    # Convert names to IDs if needed
    if isinstance(player1, str):
        if player1 in name_to_id:
            player1 = name_to_id[player1]
        else:
            try:
                player1 = int(player1)
            except ValueError:
                raise ValueError(f"Invalid player1: {player1}. Must be player name or ID.")
    
    if isinstance(player2, str):
        if player2 in name_to_id:
            player2 = name_to_id[player2]
        else:
            try:
                player2 = int(player2)
            except ValueError:
                raise ValueError(f"Invalid player2: {player2}. Must be player name or ID.")
    
    # Validate received_value is provided when IRL player is involved
    if my_player_id is not None and received_value is None:
        if int(player1) == my_player_id or int(player2) == my_player_id:
            raise ValueError(
                f"received_value is required when you (Player {my_player_id}) are involved in a swap. "
                f"Format: (player1, player2, init_pos1, init_pos2, final_pos1, final_pos2, received_value)"
            )
    
    # Convert positions from 1-indexed to 0-indexed
    init_pos1_internal = init_pos1 - 1
    init_pos2_internal = init_pos2 - 1
    final_pos1_internal = final_pos1 - 1
    final_pos2_internal = final_pos2 - 1
    
    return (int(player1), int(player2), init_pos1_internal, init_pos2_internal,
            final_pos1_internal, final_pos2_internal, received_value)


def format_swap_for_user(swap_record, player_names: Dict[int, str] = None) -> str:
    """
    Format a swap record in a user-friendly way with names and 1-indexed positions.
    
    Args:
        swap_record: SwapRecord object
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    if player_names:
        p1_name = player_names.get(swap_record.player1_id, f"Player {swap_record.player1_id}")
        p2_name = player_names.get(swap_record.player2_id, f"Player {swap_record.player2_id}")
    else:
        p1_name = f"Player {swap_record.player1_id}"
        p2_name = f"Player {swap_record.player2_id}"
    
    # Convert positions to 1-indexed
    p1_init_display = swap_record.player1_init_pos + 1
    p2_init_display = swap_record.player2_init_pos + 1
    p1_final_display = swap_record.player1_final_pos + 1
    p2_final_display = swap_record.player2_final_pos + 1
    
    return (f"{p1_name}[{p1_init_display}→{p1_final_display}] ↔ "
            f"{p2_name}[{p2_init_display}→{p2_final_display}]")


def format_call_for_user(call_record, player_names: Dict[int, str] = None) -> str:
    """
    Format a call record in a user-friendly way with names and 1-indexed positions.
    
    Args:
        call_record: CallRecord object
        player_names: Optional dict mapping IDs to names
        
    Returns:
        Formatted string
    """
    if player_names:
        caller_name = player_names.get(call_record.caller_id, f"Player {call_record.caller_id}")
        target_name = player_names.get(call_record.target_id, f"Player {call_record.target_id}")
    else:
        caller_name = f"Player {call_record.caller_id}"
        target_name = f"Player {call_record.target_id}"
    
    # Convert position to 1-indexed
    position_user = call_record.position + 1
    
    result = "SUCCESS" if call_record.success else "FAIL"
    return f"{caller_name} → {target_name}[{position_user}] = {call_record.value} [{result}]"


def save_action_history(belief_folder: str, player_id: int, 
                       calls: List[Tuple], double_reveals: List[Tuple],
                       swaps: List[Tuple], signals: List[Tuple],
                       not_present: List[Tuple]):
    """
    Save the action history to track what has been processed.
    
    Args:
        belief_folder: Folder to save history
        player_id: Player ID
        calls: List of call tuples
        double_reveals: List of double reveal tuples
        swaps: List of swap tuples
        signals: List of signal tuples
        not_present: List of not-present tuples
    """
    from pathlib import Path
    
    belief_path = Path(belief_folder)
    player_dir = belief_path / f"player_{player_id}"
    player_dir.mkdir(parents=True, exist_ok=True)
    
    history_file = player_dir / "action_history.json"
    
    history_data = {
        "calls": calls,
        "double_reveals": double_reveals,
        "swaps": swaps,
        "signals": signals,
        "not_present": not_present
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
    not_present: List[Tuple] = None,
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
        not_present: Optional list of not-present tuples (player, value)
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
    if not_present is None:
        not_present = []
    
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
    reveals_to_process = double_reveals
    swaps_to_process = swaps
    signals_to_process = signals
    not_present_to_process = not_present
    processed_incrementally = False
    
    # If both save and load are enabled, only process new actions
    if save_to_json and load_from_json and loaded_from_file:
        old_history = load_action_history(belief_folder, my_player_id)
        if old_history is not None:
            # Only process actions that are new since last save
            calls_to_process = get_new_actions(old_history.get("calls", []), calls)
            reveals_to_process = get_new_actions(old_history.get("double_reveals", []), double_reveals)
            swaps_to_process = get_new_actions(old_history.get("swaps", []), swaps)
            signals_to_process = get_new_actions(old_history.get("signals", []), signals)
            not_present_to_process = get_new_actions(old_history.get("not_present", []), not_present)
            
            if any([calls_to_process, reveals_to_process, swaps_to_process, 
                   signals_to_process, not_present_to_process]):
                processed_incrementally = True
                print(f"\n⚡ Incremental update: Processing {len(calls_to_process)} new calls, "
                      f"{len(reveals_to_process)} reveals, {len(swaps_to_process)} swaps, "
                      f"{len(signals_to_process)} signals, {len(not_present_to_process)} not-present")
            else:
                print(f"\n✓ No new actions to process")
    
    # Process all calls, double reveals, and swaps
    call_records = []
    reveal_records = []
    swap_records = []
    signal_records = []
    not_present_records = []
    
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
    for reveal in reveals_to_process:
        try:
            # Convert reveal to internal format
            internal_reveal = convert_double_reveal_to_internal(reveal, player_names)
            player, val, pos1, pos2 = internal_reveal
            
            reveal_record = game.double_reveal(player, val, pos1, pos2)
            reveal_records.append(reveal_record)
        except ValueError as e:
            reveal_records.append(f"ERROR: {e}")
    
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
    
    # Process not-present announcements
    for np in not_present_to_process:
        try:
            # Convert not-present to internal format
            internal_np = convert_not_present_to_internal(np, player_names)
            player, val = internal_np
            
            np_record = game.announce_not_present(player, val)
            not_present_records.append(np_record)
        except ValueError as e:
            not_present_records.append(f"ERROR: {e}")
    
    # Get game state
    state = game.get_game_state()
    
    # Save belief state and action history (only if save_to_json is True)
    my_player = players[my_player_id]
    if save_to_json and my_player.belief_system is not None:
        try:
            my_player.belief_system.save_to_folder(belief_folder, player_names)
            # Also save action history to enable incremental processing
            save_action_history(belief_folder, my_player_id, 
                              calls, double_reveals, swaps, signals, not_present)
        except Exception as e:
            print(f"⚠️  Warning: Could not save belief state: {e}")
    
    return {
        'players': players,
        'game': game,
        'my_player': my_player,
        'state': state,
        'call_records': call_records,
        'reveal_records': reveal_records,
        'swap_records': swap_records,
        'signal_records': signal_records,
        'not_present_records': not_present_records,
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

