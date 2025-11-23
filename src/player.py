"""
Player class represents a participant in the BombBuster game.
Each player has a wire (sorted values) and maintains beliefs about all players' wires.
"""

from typing import List, Dict, Optional, Tuple, Set, Union
from src.belief.belief_model import BeliefModel
from src.data_structures import CallRecord
from config.game_config import GameConfig


class Player:
    """
    Represents a player in the game.
    
    Each player has:
    - A player ID
    - A wire (sorted list of values, can be int or float) - optional for real-life gameplay
    - Revealed positions (which positions are visible to them)
    - A belief model tracking possible values for all players' wires
    
    NOTE: For real-life gameplay, wire can be None since players track their own
    physical wires. For simulations/testing, wire should be provided.
    
    Attributes:
        player_id: Unique identifier for this player
        wire: Sorted list of wire values (private, optional for real-life play)
        revealed_positions: Dict mapping position to value for visible positions
        belief_system: BeliefModel tracking all players' possible values
        config: Game configuration
    """
    
    def __init__(self, player_id: int, wire: Optional[List[Union[int, float]]], config: GameConfig):
        """
        Initialize a player with their wire.
        
        Args:
            player_id: Unique identifier for this player
            wire: Sorted list of wire values (optional, None for real-life gameplay)
            config: Game configuration
            
        Raises:
            ValueError: If wire length doesn't match config.wires_per_player
        """
        self.player_id = player_id
        
        # Validate wire length if provided
        if wire is not None:
            if len(wire) != config.wires_per_player:
                raise ValueError(
                    f"Wire length mismatch: expected {config.wires_per_player} wires, "
                    f"got {len(wire)}. Check your MY_WIRE and config.WIRE_DISTRIBUTION."
                )
        
        self.wire = sorted(wire) if wire is not None else None
        self.config = config
        self.revealed_positions: Dict[int, Union[int, float]] = {}
        self.belief_system: Optional[BeliefModel] = None  # Initialized by Game
    
    
    def has_value(self, value: int) -> bool:
        """
        Check if this player has a specific value in their wire.
        
        NOTE: Only works if wire is provided (simulation mode).
        For real-life play, players know their own values without this method.
        
        Args:
            value: The wire value to check
        
        Returns:
            True if the player has this value
        """
        if self.wire is None:
            raise ValueError("Wire not available (real-life mode). Players track their own values.")
        return value in self.wire
    
    def has_won(self) -> bool:
        """
        Check if this player has deduced their entire wire.
        Note: In collaborative mode, this doesn't mean the game is won,
        just that this player's wire is fully revealed.
        
        Returns:
            True if all positions for this player are certain
        """
        if self.belief_system is None:
            return False
        
        # Check if all positions have only one possible value
        for position in range(self.config.wires_per_player):
            if len(self.belief_system.beliefs[self.player_id][position]) > 1:
                return False
        
        return True
    
    def get_certain_values(self) -> Set[Union[int, float]]:
        """
        Get the set of values this player is certain they have.
        Based on revealed positions and belief deductions.
        
        Returns:
            Set of values that are certain (can be int or float)
        """
        # If we have the actual wire, return all values from it
        if self.wire is not None:
            return set(self.wire)
        
        # Otherwise, use belief system
        if self.belief_system is None:
            return set()
        
        certain_values = set()
        for position in range(self.config.wires_per_player):
            possible_values = self.belief_system.beliefs[self.player_id][position]
            if len(possible_values) == 1:
                certain_values.add(list(possible_values)[0])
        
        return certain_values
    
    def get_uncertain_positions(self) -> List[int]:
        """
        Get list of positions where this player is still uncertain about the value.
        
        Returns:
            List of position indices
        """
        if self.belief_system is None:
            return list(range(self.config.wires_per_player))
        
        uncertain_positions = []
        for position in range(self.config.wires_per_player):
            if len(self.belief_system.beliefs[self.player_id][position]) > 1:
                uncertain_positions.append(position)
        
        return uncertain_positions
    
    def get_wire(self) -> Optional[List[Union[int, float]]]:
        """
        Get the player's wire.
        Each player knows their own wire (either physical cards or stored).
        
        Returns:
            Copy of the wire, or None if not available (shouldn't happen normally)
        """
        return self.wire.copy() if self.wire is not None else None
    
    def print_state(self):
        """
        Print the player's wire and current belief state.
        Useful for debugging and game visualization.
        """
        print(f"\n{'='*60}")
        print(f"Player {self.player_id}")
        
        if self.wire is not None:
            print(f"Private Wire: {self.wire}")
        else:
            print(f"Private Wire: [Real-life mode - not tracked]")
        
        print(f"Revealed Positions: {self.revealed_positions}")
        print(f"Certain Values: {self.get_certain_values()}")
        print(f"Uncertain Positions: {self.get_uncertain_positions()}")
        
        if self.belief_system is not None:
            self.belief_system.print_beliefs()
        
        print(f"{'='*60}")
