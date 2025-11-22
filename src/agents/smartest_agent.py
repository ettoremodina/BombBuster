"""
Smartest agent that uses entropy analysis to choose the best action.
"""

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
    1. Use GameStatistics.get_entropy_suggestion() to find the call that maximizes information gain.
    2. If a suggestion is found, execute it.
    3. If no suggestion (e.g. no playable values), pass.
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
        
        # Get entropy-based suggestion
        # We use a small max_uncertainty to keep simulation fast, 
        # but high enough to be useful. 3 is a good balance.
        # We disable parallel processing here to avoid potential issues with 
        # multiprocessing within the game loop if not handled carefully,
        # though it can be enabled if performance is critical.
        suggestion = stats.get_entropy_suggestion(max_uncertainty=3, use_parallel=False)
        
        best_call = suggestion.get('best_call')
        
        if best_call:
            target_id, position, value = best_call
            
            # Double check validity (should be valid from suggester, but safety first)
            # Skip VOID player check just in case suggester didn't filter it
            if target_id < len(PLAYER_NAMES) and PLAYER_NAMES[target_id] == "VOID":
                return None
                
            return (target_id, position, value)
            
        return None
