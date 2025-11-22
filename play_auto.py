import random
import json
import time
import os
from dataclasses import asdict
from typing import List
from config.game_config import GameConfig, PLAYER_NAMES
from src.player import Player
from src.game import Game
from src.agents.base_agent import BaseAgent
from src.agents.random_agent import RandomAgent
from src.agents.smart_agent import SmartAgent
from src.utils import generate_wires
from src.statistics import GameStatistics


USE_GLOBAL_BELIEF = True

def run_simulation():
    config = GameConfig(playing_irl=False, auto_filter=False, use_global_belief=USE_GLOBAL_BELIEF)
    wires = generate_wires(config)
    players = []
    agents = []
    
    # Timing data
    filter_times = []
    K = 10 
    
    # Identify VOID player if present
    void_player_id = None
    if "VOID" in PLAYER_NAMES:
        void_player_id = PLAYER_NAMES.index("VOID")
        print(f"VOID player identified at index {void_player_id}")
    
    for i in range(config.n_players):
        player = Player(i, wires[i], config)
        players.append(player)
        agents.append(SmartAgent(player))
        

    game = Game(players, config)
    print(f"Starting Game with {config.n_players} players...")
    for p in players:
        print(f"Player {p.player_id} wire: {p.wire}")
        
    # 5. Game Loop
    max_turns = 500
    while not game.is_game_over() and game.current_turn < max_turns:
        current_player_id = game.current_turn % config.n_players
        
        # Skip VOID player
        if current_player_id == void_player_id:
            print(f"\n--- Turn {game.current_turn} (VOID Player) ---")
            print("Skipping VOID player turn.")
            game.current_turn += 1
            continue
        game.current_turn += 1
        agent = agents[current_player_id]
        
        print(f"\n--- Turn {game.current_turn} (Player {current_player_id}) ---")
        action = agent.choose_action(game)
        
        if action:
            target_id, position, value = action
            
            print(f"Agent {current_player_id} calls Player {target_id} pos {position} value {value}")
            
            try:
                result = game.auto_make_call(current_player_id, target_id, position, value)
                print(f"Result: {'SUCCESS' if result.success else 'FAILURE'}")
                
                # If call failed, target reveals the actual value at that position
                if not result.success:
                    # Get the actual value from the target player
                    target_player = players[target_id]
                    actual_value = target_player.wire[position]
                    print(f"Call failed! Player {target_id} signals pos {position} is {actual_value}")
                    game.signal_value(target_id, actual_value, position)
                
                # Apply filters manually and measure time
                if game.current_turn % K == 0:
                    p = players[current_player_id]
                    print(f"Measuring filter time for Player {current_player_id} (Turn {game.current_turn})...")
                    start_time = time.time()
                    p.belief_system.apply_filters()
                    end_time = time.time()
                    duration = end_time - start_time
                    print(f"Filter time: {duration:.4f}s")
                    
                    # Calculate entropy
                    stats = GameStatistics(p.belief_system, config, p.wire)
                    entropy = stats.calculate_system_entropy()
                    if entropy == 0:
                        print("Entropy is zero, all beliefs resolved.")
                        break
                    
                    filter_times.append({
                        "turn": game.current_turn,
                        "time": duration,
                        "entropy": entropy
                    })
                    
                    # Save immediately
                    filename = "global_filter_time.json" if config.use_global_belief else "human_filter_time.json"
                    with open(filename, "w") as f:
                        json.dump(filter_times, f, indent=2)
                    
                    if entropy == 0:
                        break

            except ValueError as e:
                print(f"Invalid call attempted: {e}")
        else:
            print(f"Agent {current_player_id} could not make a valid move.")
            continue
            
    # 6. Results
    print("\n=== Game Over ===")
    if game.has_team_won():
        print("Team WON! All wires revealed.")
    else:
        print(f"Team LOST. Wrong calls: {game.wrong_calls_count}/{config.max_wrong_calls}")
        
    print(f"Total turns: {game.current_turn}")
    
    # Save belief state for all players
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_folder = f"logs/game_{timestamp}"
    
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
        
    # Save action history
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

if __name__ == "__main__":
    run_simulation()
