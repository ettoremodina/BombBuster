"""
Random agent that makes random valid calls.
Useful for testing and as a baseline strategy.
"""

import random
from typing import Optional, Tuple, List
from src.agents.base_agent import BaseAgent
from src.player import Player
from src.game import Game


class RandomAgent(BaseAgent):
    """
    Agent that makes random valid calls.
    
    Strategy:
    1. Find all values this player has
    2. Pick a random target player
    3. Pick a random position
    4. Pick a random value from what this player has
    """
    
    def __init__(self, player: Player):
        """
        Initialize a random agent.
        
        Args:
            player: The Player object to control
        """
        super().__init__(player, name="RandomAgent")
    
    def choose_action(self, game: Game) -> Optional[Tuple[int, int, int]]:
        """
        Choose a random valid call.
        
        Args:
            game: Current game state
        
        Returns:
            Tuple of (target_id, position, value) or None if no valid calls
        """
        pass
    
    def _get_valid_targets(self, game: Game) -> List[int]:
        """
        Get list of valid target players (not self).
        
        Args:
            game: Current game state
        
        Returns:
            List of player IDs
        """
        pass
    
    def _get_valid_positions(self, game: Game) -> List[int]:
        """
        Get list of valid positions to call.
        
        Args:
            game: Current game state
        
        Returns:
            List of position indices
        """
        pass
    
    def _get_available_values(self) -> List[int]:
        """
        Get list of values this player has.
        
        Returns:
            List of wire values
        """
        pass
