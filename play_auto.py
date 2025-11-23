import random
import json
import time
import os
from dataclasses import asdict
from typing import List, Tuple, Optional
from config.game_config import GameConfig, PLAYER_NAMES
from src.player import Player
from src.game import Game
from src.agents.base_agent import BaseAgent
from src.agents.random_agent import RandomAgent
from src.agents.smart_agent import SmartAgent
from src.agents.smartest_agent import SmartestAgent
from src.utils import generate_wires, find_first_unrevealed_position
from src.statistics import GameStatistics


USE_GLOBAL_BELIEF = True


def setup_game(config: GameConfig) -> Tuple[Game, List[Player], List[BaseAgent], Optional[int]]:
    wires = generate_wires(config)
    players = []
    agents = []
    
    void_player_id = None
    if "VOID" in PLAYER_NAMES:
        void_player_id = PLAYER_NAMES.index("VOID")
        print(f"VOID player identified at index {void_player_id}")
    
    for i in range(config.n_players):
        player = Player(i, wires[i], config)
        players.append(player)
        agents.append(SmartestAgent(player))
    
    game = Game(players, config)
    
    print(f"Starting Game with {config.n_players} players...")
    for p in players:
        print(f"Player {p.player_id} wire: {p.wire}")
    
    return game, players, agents, void_player_id


def send_initial_signals(game: Game, players: List[Player], void_player_id: Optional[int]):
    print("\n--- Initial Signals ---")
    for p in players:
        if p.player_id == void_player_id:
            continue
        
        pos_to_signal = random.randint(0, len(p.wire) - 1)
        value_to_signal = p.wire[pos_to_signal]
        
        print(f"Player {p.player_id} signals pos {pos_to_signal} is {value_to_signal}")
        game.signal_value(p.player_id, value_to_signal, pos_to_signal)


def handle_quad_double_reveal(game: Game, current_player_id: int, action: Tuple):
    _, pos1, pos2, pos3, pos4, value = action
    print(f"Agent {current_player_id} does QUAD DOUBLE REVEAL on positions [{pos1}, {pos2}] and [{pos3}, {pos4}] value {value}")
    
    try:
        game.double_reveal(current_player_id, value, pos1, pos2)
        print(f"First double reveal successful!")
        game.double_reveal(current_player_id, value, pos3, pos4)
        print(f"Second double reveal successful!")
    except ValueError as e:
        print(f"Invalid double reveal attempted: {e}")


def handle_double_reveal(game: Game, current_player_id: int, action: Tuple):
    _, pos1, pos2, value = action
    print(f"Agent {current_player_id} does DOUBLE REVEAL on positions [{pos1}, {pos2}] value {value}")
    
    try:
        game.double_reveal(current_player_id, value, pos1, pos2)
        print(f"Double reveal successful!")
    except ValueError as e:
        print(f"Invalid double reveal attempted: {e}")


def handle_double_chance(game: Game, players: List[Player], current_player_id: int, action: Tuple) -> bool:
    _, target_id, pos1, pos2, value = action
    print(f"Agent {current_player_id} calls DOUBLE CHANCE on Player {target_id} positions [{pos1}, {pos2}] value {value}")
    
    target_player = players[target_id]
    actual_val1 = target_player.wire[pos1]
    actual_val2 = target_player.wire[pos2]
    success = (actual_val1 == value or actual_val2 == value)
    
    print(f"Result: {'SUCCESS' if success else 'FAILURE'}")
    print(f"  Position {pos1} has {actual_val1}, Position {pos2} has {actual_val2}")

    caller_player = players[current_player_id]
    caller_pos_ = find_first_unrevealed_position(caller_player, value)
    
    if success:
        if actual_val1 == value:
            print(f"  Signaling Player {target_id} pos {pos1} = {value}")
            game.make_call(current_player_id, target_id, pos1, value, True, caller_pos_)
        elif actual_val2 == value:
            print(f"  Signaling Player {target_id} pos {pos2} = {value}")
            game.make_call(current_player_id, target_id, pos2, value, True, caller_pos_)
    else:
        print(f"  Double chance failed! Player {target_id} signals pos {pos1} = {actual_val1}")
        game.signal_value(target_id, actual_val1, pos1)
        
        for player in players:
            if player.belief_system:
                if value in player.belief_system.beliefs[target_id][pos1]:
                    player.belief_system.beliefs[target_id][pos1].discard(value)
                if value in player.belief_system.beliefs[target_id][pos2]:
                    player.belief_system.beliefs[target_id][pos2].discard(value)
                    print(f"  Removing {value} from Player {target_id} positions [{pos1},{pos2}] beliefs (double chance logic)")
        
        game.wrong_calls_count += 1
        if game.wrong_calls_count >= game.config.max_wrong_calls:
            print(f"Team lost! Too many wrong calls ({game.wrong_calls_count}/{game.config.max_wrong_calls})")
            game.game_over = True
            game.team_won = False
            return True
    
    return False


def handle_normal_call(game: Game, players: List[Player], current_player_id: int, action: Tuple, 
                      config: GameConfig, filter_times: List, K: int):
    target_id, position, value = action
    print(f"Agent {current_player_id} calls Player {target_id} pos {position} value {value}")
    
    try:
        result = game.auto_make_call(current_player_id, target_id, position, value)
        print(f"Result: {'SUCCESS' if result.success else 'FAILURE'}")
        
        if not result.success:
            target_player = players[target_id]
            actual_value = target_player.wire[position]
            print(f"Call failed! Player {target_id} signals pos {position} is {actual_value}")
            game.signal_value(target_id, actual_value, position)
            game.wrong_calls_count += 1
        
        if game.current_turn % K == 0 and K != 1:
            measure_filter_time(players[current_player_id], game.current_turn, config, filter_times)
    except ValueError as e:
        print(f"Invalid call attempted: {e}")


def measure_filter_time(player: Player, turn: int, config: GameConfig, filter_times: List):
    print(f"Measuring filter time for Player {player.player_id} (Turn {turn})...")
    start_time = time.time()
    player.belief_system.apply_filters()
    end_time = time.time()
    duration = end_time - start_time
    print(f"Filter time: {duration:.4f}s")
    
    stats = GameStatistics(player.belief_system, config, player.wire)
    entropy = stats.calculate_system_entropy()
    
    filter_times.append({
        "turn": turn,
        "time": duration,
        "entropy": entropy
    })
    
    filename = "global_filter_time.json" if config.use_global_belief else "human_filter_time.json"
    with open(filename, "w") as f:
        json.dump(filter_times, f, indent=2)


def process_action(game: Game, players: List[Player], agents: List[BaseAgent], 
                   current_player_id: int, config: GameConfig, filter_times: List, K: int) -> bool:
    agent = agents[current_player_id]
    print(f"\n--- Turn {game.current_turn} (Player {current_player_id}) ---")
    action = agent.choose_action(game)
    
    if not action:
        print(f"Agent {current_player_id} could not make a valid move.")
        return False
    
    if isinstance(action, tuple) and len(action) == 6 and action[0] == 'double_reveal_quad':
        handle_quad_double_reveal(game, current_player_id, action)
    elif isinstance(action, tuple) and len(action) == 4 and action[0] == 'double_reveal':
        handle_double_reveal(game, current_player_id, action)
    elif isinstance(action, tuple) and len(action) == 5 and action[0] == 'double_chance':
        game_over = handle_double_chance(game, players, current_player_id, action)
        if game_over:
            return None
    else:
        handle_normal_call(game, players, current_player_id, action, config, filter_times, K)
    
    return True


def process_turn(game: Game, players: List[Player], agents: List[BaseAgent], 
                void_player_id: Optional[int], config: GameConfig, filter_times: List, K: int) -> Tuple[bool, int]:
    current_player_id = game.current_turn % config.n_players
    
    if current_player_id == void_player_id:
        print(f"\n--- Turn {game.current_turn} (VOID Player) ---")
        print("Skipping VOID player turn.")
        game.current_turn += 1
        return False, 1
    
    if K == 1:
        players[current_player_id].belief_system.apply_filters()
    game.current_turn += 1
    action_result = process_action(game, players, agents, current_player_id, config, filter_times, K)
    
    if action_result is None:
        return None, 0
    elif action_result:
        return True, 0
    else:
        return False, 1


def run_game_loop(game: Game, players: List[Player], agents: List[BaseAgent], 
                  void_player_id: Optional[int], config: GameConfig, K: int = 1, max_turns: int = 100):
    filter_times = []
    consecutive_skips = 0
    
    while not game.is_game_over() and game.current_turn < max_turns:
        result = process_turn(game, players, agents, void_player_id, config, filter_times, K)
        
        if result is None:
            break
        
        action_taken, skip_count = result
        
        if action_taken:
            consecutive_skips = 0
        else:
            consecutive_skips += skip_count
            if consecutive_skips >= config.n_players:
                print("All players skipped. Ending game.")
                break


def print_game_results(game: Game, config: GameConfig):
    print("\n=== Game Over ===")
    if game.has_team_won():
        print("Team WON! All wires revealed.")
        print(f"Wrong calls: {game.wrong_calls_count}/{config.max_wrong_calls}")
    else:
        print(f"Team LOST. Wrong calls: {game.wrong_calls_count}/{config.max_wrong_calls}")
    print(f"Total turns: {game.current_turn}")


def save_game_logs(game: Game, players: List[Player]):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_folder = f"logs/game_{timestamp}"
    
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    
    action_history = {
        "calls": [asdict(r) for r in game.call_history],
        "double_reveals": [asdict(r) for r in game.double_reveal_history],
        "swaps": [asdict(r) for r in game.swap_history],
        "signals": [asdict(r) for r in game.signal_history],
        "reveals": [asdict(r) for r in game.reveal_history],
        "not_present": [asdict(r) for r in game.not_present_history],
        "has_values": game.has_values_history,
        "copy_count_signals": [asdict(r) for r in game.copy_count_signal_history],
        "adjacent_signals": [asdict(r) for r in game.adjacent_signal_history]
    }
    
    with open(f"{log_folder}/action_history.json", "w") as f:
        json.dump(action_history, f, indent=2)
    
    print(f"\nSaving belief states to {log_folder}...")
    for player in players:
        if player.belief_system:
            player.belief_system.save_to_folder(log_folder)
    print("Done.")


def run_simulation():
    config = GameConfig(playing_irl=False, auto_filter=False, use_global_belief=USE_GLOBAL_BELIEF)
    game, players, agents, void_player_id = setup_game(config)
    send_initial_signals(game, players, void_player_id)
    run_game_loop(game, players, agents, void_player_id, config)
    print_game_results(game, config)
    save_game_logs(game, players)


if __name__ == "__main__":
    run_simulation()
