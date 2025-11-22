"""
Base Agent class for AI strategies.
Agents make decisions about what calls to make based on game state.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List
from src.player import Player
from src.game import Game
from src.statistics import GameStatistics
from config.game_config import PLAYER_NAMES


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
    
    def get_playable_values(self, game: Game) -> List[int]:
        """
        Get list of values this player can play (has and not revealed).
        """
        stats = GameStatistics(self.player.belief_system, game.config, self.player.wire)
        return list(stats.get_playable_values())

    def get_valid_targets(self, game: Game) -> List[Tuple[int, int]]:
        """
        Get list of valid (target_id, position) pairs to call.
        Excludes self, VOID player, and already revealed positions.
        """
        stats = GameStatistics(self.player.belief_system, game.config, self.player.wire)
        valid_targets = []
        
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
                if not stats.is_position_revealed(target_id, position):
                    valid_targets.append((target_id, position))
                    
        return valid_targets

    def get_player_id(self) -> int:
        """
        Get the ID of the player this agent controls.
        
        Returns:
            Player ID
        """
        return self.player.player_id
    
    def __repr__(self):
        return f"{self.name}(Player {self.player.player_id})"
