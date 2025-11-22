"""
Smart agent that prioritizes certain calls.
"""

import random
from typing import Optional, Tuple, List
from src.agents.base_agent import BaseAgent
from src.player import Player
from src.game import Game
from src.statistics import GameStatistics
from config.game_config import PLAYER_NAMES


class SmartAgent(BaseAgent):
    """
    Agent that prioritizes certain calls over random guesses.
    
    Strategy:
    1. Identify all playable values (values I have that are not revealed).
    2. Check for any CERTAIN calls (where a target position has only 1 possible value, and I have that value).
    3. If certain calls exist, make one.
    4. If no certain calls, fall back to random valid call.
    """
    
    def __init__(self, player: Player):
        """
        Initialize a smart agent.
        
        Args:
            player: The Player object to control
        """
        super().__init__(player, name="SmartAgent")
    
    def choose_action(self, game: Game) -> Optional[Tuple[int, int, int]]:
        """
        Choose the best available call.
        
        Args:
            game: Current game state
        
        Returns:
            Tuple of (target_id, position, value) or None if no valid calls
        """
        # Initialize statistics helper to access game state logic
        stats = GameStatistics(self.player.belief_system, game.config, self.player.wire)
        
        # 1. Get playable values (values I have that are not revealed)
        playable_values = list(stats.get_playable_values())
        if not playable_values:
            return None
            
        playable_set = set(playable_values)
        
        # 2. Look for CERTAIN calls
        certain_calls = []
        uncertain_calls = []
        
        for target_id in range(game.config.n_players):
            # Skip self
            if target_id == self.player.player_id:
                continue
                
            # Skip VOID player
            if target_id < len(PLAYER_NAMES) and PLAYER_NAMES[target_id] == "VOID":
                continue
                
            # Check positions
            for position in range(game.config.wires_per_player):
                # Skip if position is already revealed
                if stats.is_position_revealed(target_id, position):
                    continue
                
                # Get beliefs for this position
                beliefs = self.player.belief_system.beliefs[target_id][position]
                
                # Check intersection with my playable values
                common_values = beliefs.intersection(playable_set)
                
                if not common_values:
                    continue
                
                # If belief size is 1, it's a certain call (if I have the value)
                if len(beliefs) == 1:
                    val = list(beliefs)[0]
                    if val in playable_set:
                        certain_calls.append((target_id, position, val))
                else:
                    # Uncertain call - pick a random value from the intersection
                    for val in common_values:
                        uncertain_calls.append((target_id, position, val))
        
        # 3. Execute strategy
        if certain_calls:
            # Prioritize certain calls
            return random.choice(certain_calls)
        
        if uncertain_calls:
            # Fallback to random valid call
            return random.choice(uncertain_calls)
            
        return None
