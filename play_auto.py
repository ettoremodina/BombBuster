import random
from typing import List
from config.game_config import GameConfig
from src.player import Player
from src.game import Game
from src.agents.smart_agent import SmartAgent
from src.utils import generate_wires

def run_simulation():
    # 1. Setup Configuration
    # Use default distribution but ensure it works for 3 players (default is 5)
    # Or just use default N=5
    config = GameConfig(playing_irl=False)
    
    # 2. Generate Wires
    wires = generate_wires(config)
    
    # 3. Create Players and Agents
    players = []
    agents = []
    for i in range(config.n_players):
        player = Player(i, wires[i], config)
        players.append(player)
        agents.append(SmartAgent(player))
        
    # 4. Initialize Game
    game = Game(players, config)
    
    print(f"Starting Game with {config.n_players} players...")
    for p in players:
        print(f"Player {p.player_id} wire: {p.wire}")
        
    # 5. Game Loop
    max_turns = 100
    while not game.is_game_over() and game.current_turn < max_turns:
        current_player_id = game.current_turn % config.n_players
        agent = agents[current_player_id]
        
        print(f"\n--- Turn {game.current_turn} (Player {current_player_id}) ---")
        
        # Agent chooses action
        action = agent.choose_action(game)
        
        if action:
            target_id, position, value = action
            print(f"Agent {current_player_id} calls Player {target_id} pos {position} value {value}")
            
            try:
                result = game.auto_make_call(current_player_id, target_id, position, value)
                print(f"Result: {'SUCCESS' if result.success else 'FAILURE'}")
            except ValueError as e:
                print(f"Invalid call attempted: {e}")
                # If random agent makes invalid call (e.g. calling value it doesn't have), 
                # we should probably just skip turn or break.
                # RandomAgent logic should prevent this, but good to handle.
                break
        else:
            print(f"Agent {current_player_id} could not make a valid move.")
            break
            
    # 6. Results
    print("\n=== Game Over ===")
    if game.has_team_won():
        print("Team WON! All wires revealed.")
    else:
        print(f"Team LOST. Wrong calls: {game.wrong_calls_count}/{config.max_wrong_calls}")
        
    print(f"Total turns: {game.current_turn}")
    
    # Save belief state for all players
    import time
    import os
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_folder = f"logs/game_{timestamp}"
    
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
        
    print(f"\nSaving belief states to {log_folder}...")
    for player in players:
        if player.belief_system:
            player.belief_system.save_to_folder(log_folder)
            
    print("Done.")

if __name__ == "__main__":
    run_simulation()
