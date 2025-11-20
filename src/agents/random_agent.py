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
        targets = self._get_valid_targets(game)
        if not targets:
            return None
            
        target_id = random.choice(targets)
        
        positions = self._get_valid_positions(game)
        if not positions:
            return None
            
        position = random.choice(positions)
        
        values = self._get_available_values()
        if not values:
            return None
            
        value = random.choice(values)
        
        return (target_id, position, value)
    
    def _get_valid_targets(self, game: Game) -> List[int]:
        """
        Get list of valid target players (not self).
        
        Args:
            game: Current game state
        
        Returns:
            List of player IDs
        """
        return [p.player_id for p in game.players if p.player_id != self.player.player_id]
    
    def _get_valid_positions(self, game: Game) -> List[int]:
        """
        Get list of valid positions to call.
        
        Args:
            game: Current game state
        
        Returns:
            List of position indices
        """
        return list(range(game.config.wires_per_player))
    
    def _get_available_values(self) -> List[int]:
        """
        Get list of values this player has.
        
        Returns:
            List of wire values
        """
        if self.player.wire is None:
            return []
        return list(set(self.player.wire))
