"""
Base Agent class for AI strategies.
Agents make decisions about what calls to make based on game state.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from src.player import Player
from src.game import Game


class BaseAgent(ABC):
    """
    Abstract base class for agents that control players.
    
    An agent observes the game state and decides what action to take.
    Separates decision-making (agent) from game mechanics (player/game).
    
    Attributes:
        player: The Player object this agent controls
        name: Human-readable name for this agent type
    """
    
    def __init__(self, player: Player, name: str = "BaseAgent"):
        """
        Initialize an agent to control a player.
        
        Args:
            player: The Player object to control
            name: Name of this agent type
        """
        self.player = player
        self.name = name
    
    @abstractmethod
    def choose_action(self, game: Game) -> Optional[Tuple[int, int, int]]:
        """
        Choose what call to make based on current game state.
        
        Args:
            game: Current game state
        
        Returns:
            Tuple of (target_id, position, value) or None to pass/end turn
        """
        pass
    
    def get_player_id(self) -> int:
        """
        Get the ID of the player this agent controls.
        
        Returns:
            Player ID
        """
        return self.player.player_id
    
    def __repr__(self):
        return f"{self.name}(Player {self.player.player_id})"
