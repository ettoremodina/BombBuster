"""
Random agent that makes random valid calls.
Useful for testing and as a baseline strategy.
"""

import random
from typing import Optional, Tuple
from src.agents.base_agent import BaseAgent
from src.player import Player
from src.game import Game


class RandomAgent(BaseAgent):
    """
    Agent that makes random valid calls.
    
    Strategy:
    1. Find all values this player has that are NOT revealed (playable values)
    2. Find all valid target positions (not self, not VOID, not revealed)
    3. Pick a random target/position and a random playable value
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
        # 1. Get playable values (values I have that are not revealed)
        playable_values = self.get_playable_values(game)
        if not playable_values:
            return None
            
        # 2. Find all valid (target, position) pairs
        valid_targets = self.get_valid_targets(game)
        if not valid_targets:
            return None
            
        # 3. Choose random move and value
        target_id, position = random.choice(valid_targets)
        value = random.choice(playable_values)
        
        return (target_id, position, value)

