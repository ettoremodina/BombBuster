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
from src.agents.smartest_agent import SmartestAgent
from src.utils import generate_wires
from src.statistics import GameStatistics


USE_GLOBAL_BELIEF = False

def run_simulation():
    config = GameConfig(playing_irl=False, auto_filter=False, use_global_belief=USE_GLOBAL_BELIEF)
    wires = generate_wires(config)
    players = []
    agents = []
    
    # Timing data
    filter_times = []
    K = 1
    
    # Identify VOID player if present
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
        
    # Initial signals: Each player signals one of their own cards
    print("\n--- Initial Signals ---")
    for p in players:
        if p.player_id == void_player_id:
            continue
        
        # Pick a random position to signal
        pos_to_signal = random.randint(0, len(p.wire) - 1)
        value_to_signal = p.wire[pos_to_signal]
        
        print(f"Player {p.player_id} signals pos {pos_to_signal} is {value_to_signal}")
        game.signal_value(p.player_id, value_to_signal, pos_to_signal)

    # 5. Game Loop
    max_turns = 100
    consecutive_skips = 0
    while not game.is_game_over() and game.current_turn < max_turns:
        current_player_id = game.current_turn % config.n_players
        if K == 1:
            players[current_player_id].belief_system.apply_filters()
        
        # Skip VOID player
        if current_player_id == void_player_id:
            print(f"\n--- Turn {game.current_turn} (VOID Player) ---")
            print("Skipping VOID player turn.")
            game.current_turn += 1
            consecutive_skips += 1
            if consecutive_skips >= config.n_players:
                print("All players skipped. Ending game.")
                break
            continue
        game.current_turn += 1
        agent = agents[current_player_id]
        
        print(f"\n--- Turn {game.current_turn} (Player {current_player_id}) ---")
        action = agent.choose_action(game)
        
        if action:
            consecutive_skips = 0
            
            # Check if this is a quad double reveal action (4 positions)
            if isinstance(action, tuple) and len(action) == 6 and action[0] == 'double_reveal_quad':
                # Handle quad double reveal
                _, pos1, pos2, pos3, pos4, value = action
                
                print(f"Agent {current_player_id} does QUAD DOUBLE REVEAL on positions [{pos1}, {pos2}] and [{pos3}, {pos4}] value {value}")
                
                try:
                    # Do first double reveal
                    game.double_reveal(current_player_id, value, pos1, pos2)
                    print(f"First double reveal successful!")
                    # Do second double reveal
                    game.double_reveal(current_player_id, value, pos3, pos4)
                    print(f"Second double reveal successful!")
                except ValueError as e:
                    print(f"Invalid double reveal attempted: {e}")
            
            # Check if this is a double reveal action
            elif isinstance(action, tuple) and len(action) == 4 and action[0] == 'double_reveal':
                # Handle double reveal
                _, pos1, pos2, value = action
                
                print(f"Agent {current_player_id} does DOUBLE REVEAL on positions [{pos1}, {pos2}] value {value}")
                
                try:
                    game.double_reveal(current_player_id, value, pos1, pos2)
                    print(f"Double reveal successful!")
                except ValueError as e:
                    print(f"Invalid double reveal attempted: {e}")
            
            # Check if this is a double chance action
            elif isinstance(action, tuple) and len(action) == 5 and action[0] == 'double_chance':
                # Handle double chance
                _, target_id, pos1, pos2, value = action
                
                print(f"Agent {current_player_id} calls DOUBLE CHANCE on Player {target_id} positions [{pos1}, {pos2}] value {value}")
                
                # Check if either position has the value
                target_player = players[target_id]
                actual_val1 = target_player.wire[pos1]
                actual_val2 = target_player.wire[pos2]
                
                success = (actual_val1 == value or actual_val2 == value)
                
                print(f"Result: {'SUCCESS' if success else 'FAILURE'}")
                print(f"  Position {pos1} has {actual_val1}, Position {pos2} has {actual_val2}")

                # Find caller's first unrevealed position with this value
                caller_player = players[current_player_id]
                caller_pos_ = None
                value_tracker = caller_player.belief_system.value_trackers.get(value)
                for caller_pos, caller_val in enumerate(caller_player.wire):
                    if caller_val == value:
                        # Check if this position is not revealed
                        is_revealed = False
                        if value_tracker:
                            for revealed_pid, revealed_pos in value_tracker.revealed:
                                if revealed_pid == current_player_id and revealed_pos == caller_pos:
                                    is_revealed = True
                                    break
                        
                        if not is_revealed:
                            caller_pos_ = caller_pos
                            break
                
                # Process as signals to update beliefs
                if success:
                    # Signal only ONE successful position (choose the first matching one)
                    if actual_val1 == value:
                        print(f"  Signaling Player {target_id} pos {pos1} = {value}")
                        game.make_call(current_player_id, target_id, pos1, value, True,caller_pos_)
                    elif actual_val2 == value:
                        print(f"  Signaling Player {target_id} pos {pos2} = {value}")
                        game.make_call(current_player_id, target_id, pos2, value, True,caller_pos_)
                    
                else:
                    # Failed double chance - target signals only ONE position
                    # Choose the first position
                    print(f"  Double chance failed! Player {target_id} signals pos {pos1} = {actual_val1}")
                    game.signal_value(target_id, actual_val1, pos1)
                    
                    # Remove the value from BOTH positions' beliefs for all players
                    for player in players:
                        if player.belief_system:
                            if value in player.belief_system.beliefs[target_id][pos1]:
                                player.belief_system.beliefs[target_id][pos1].discard(value)
                            if value in player.belief_system.beliefs[target_id][pos2]:
                                player.belief_system.beliefs[target_id][pos2].discard(value)
                                print(f"  Removing {value} from Player {target_id} positions [{pos1},{pos2}] beliefs (double chance logic)")
                    
                    # Increment wrong calls
                    game.wrong_calls_count += 1
                    if game.wrong_calls_count >= game.config.max_wrong_calls:
                        print(f"Team lost! Too many wrong calls ({game.wrong_calls_count}/{game.config.max_wrong_calls})")
                        game.game_over = True
                        game.team_won = False
                        break
                
            else:
                # Normal call
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
                        game.wrong_calls_count += 1
                    
                    # Apply filters manually and measure time
                    if game.current_turn % K == 0 and K!=1:
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
                        
                        filter_times.append({
                            "turn": game.current_turn,
                            "time": duration,
                            "entropy": entropy
                        })
                        
                        # Save immediately
                        filename = "global_filter_time.json" if config.use_global_belief else "human_filter_time.json"
                        with open(filename, "w") as f:
                            json.dump(filter_times, f, indent=2)
                    
    
                except ValueError as e:
                    print(f"Invalid call attempted: {e}")
        else:
            print(f"Agent {current_player_id} could not make a valid move.")
            consecutive_skips += 1
            if consecutive_skips >= config.n_players:
                print("All players skipped. Ending game.")
                break
            continue
            
    # 6. Results
    print("\n=== Game Over ===")
    if game.has_team_won():
        print("Team WON! All wires revealed.")
        print(f"Wrong calls: {game.wrong_calls_count}/{config.max_wrong_calls}")
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
