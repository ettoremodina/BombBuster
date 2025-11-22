"""
Smartest agent that uses entropy analysis to choose the best action.
"""

import random
from typing import Optional, Tuple
from src.agents.base_agent import BaseAgent
from src.player import Player
from src.game import Game
from src.statistics import GameStatistics
from config.game_config import PLAYER_NAMES


class SmartestAgent(BaseAgent):
    """
    Agent that uses entropy minimization to choose the best call.
    
    Strategy:
    1. Check for any CERTAIN calls (where a target position has only 1 possible value, and I have that value).
    2. If certain calls exist, make one.
    3. If no certain calls, use GameStatistics.get_entropy_suggestion() to find the call that maximizes information gain.
    4. If no suggestion (e.g. no playable values), pass.
    """
    
    def __init__(self, player: Player):
        """
        Initialize the smartest agent.
        
        Args:
            player: The Player object to control
        """
        super().__init__(player, name="SmartestAgent")
    
    def choose_action(self, game: Game) -> Optional[Tuple[int, int, int]]:
        """
        Choose the best action based on entropy analysis.
        
        Args:
            game: Current game state
        
        Returns:
            Tuple of (target_id, position, value) or None if no valid calls
        """
        # Initialize statistics helper
        stats = GameStatistics(self.player.belief_system, game.config, self.player.wire)

        # 1. Get playable values (values I have that are not revealed)
        playable_values = list(stats.get_playable_values())
        if not playable_values:
            return None
            
        playable_set = set(playable_values)
        
        # 2. Look for CERTAIN calls
        certain_calls = []
        
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
                
                # If belief size is 1, it's a certain call (if I have the value)
                if len(beliefs) == 1:
                    val = list(beliefs)[0]
                    if val in playable_set:
                        certain_calls.append((target_id, position, val))
        
        # 3. Execute strategy
        if certain_calls:
            # Prioritize certain calls
            return random.choice(certain_calls)

        suggestion = stats.get_entropy_suggestion(max_uncertainty=3, use_parallel=True)
        
        best_call = suggestion.get('best_call')
        
        if best_call:
            target_id, position, value = best_call
            
            # Double check validity (should be valid from suggester, but safety first)
            # Skip VOID player check just in case suggester didn't filter it
            if target_id < len(PLAYER_NAMES) and PLAYER_NAMES[target_id] == "VOID":
                return None
                
            return (target_id, position, value)
            
        return None
