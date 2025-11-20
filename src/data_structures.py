"""
Core data structures for the BombBuster game.
These classes represent the fundamental information units in the game.
"""

from typing import Dict, List, Optional, Set, Union, Tuple
from dataclasses import dataclass


@dataclass
class CallRecord:
    """
    Public record of a single call made during the game.
    This is observable by all players and forms the basis of belief updates.
    
    Attributes:
        caller_id: ID of the player making the call
        target_id: ID of the player being called
        position: Wire position being called (0-indexed)
        value: The value being called (can be int or float)
        success: True if the call was correct, False otherwise
        caller_position: Position in caller's wire where they have this value (0-indexed, only for successful calls)
        turn_number: Game turn when this call was made
    """
    caller_id: int
    target_id: int
    position: int
    value: Union[int, float]
    success: bool
    caller_position: Optional[int] = None
    turn_number: Optional[int] = None
    
    def __repr__(self):
        result = "SUCCESS" if self.success else "FAIL"
        if self.success and self.caller_position is not None:
            return f"Turn {self.turn_number}: P{self.caller_id}[{self.caller_position}] -> P{self.target_id}[{self.position}]={self.value} [{result}]"
        return f"Turn {self.turn_number}: P{self.caller_id} -> P{self.target_id}[{self.position}]={self.value} [{result}]"


@dataclass
class DoubleRevealRecord:
    """
    Public record of a double reveal action.
    When a player has the last 2 copies of a value, they can reveal both at once.
    
    Attributes:
        player_id: ID of the player revealing the wires
        value: The value being revealed (can be int or float)
        position1: First wire position (0-indexed)
        position2: Second wire position (0-indexed)
        turn_number: Game turn when this reveal was made
    """
    player_id: int
    value: Union[int, float]
    position1: int
    position2: int
    turn_number: Optional[int] = None
    
    def __repr__(self):
        return f"Turn {self.turn_number}: P{self.player_id} DOUBLE REVEAL [{self.position1}, {self.position2}]={self.value}"


@dataclass
class SwapRecord:
    """
    Public record of a wire swap between two players.
    Players exchange wires which then get inserted into sorted positions.
    
    Attributes:
        player1_id: ID of first player
        player2_id: ID of second player
        player1_init_pos: Initial position in player1's wire (before swap)
        player2_init_pos: Initial position in player2's wire (before swap)
        player1_final_pos: Final position where player1 receives the wire (after sorting)
        player2_final_pos: Final position where player2 receives the wire (after sorting)
        player1_received_value: Value that player1 received (None if player doesn't know)
        player2_received_value: Value that player2 received (None if player doesn't know)
        turn_number: Game turn when this swap was made
    """
    player1_id: int
    player2_id: int
    player1_init_pos: int
    player2_init_pos: int
    player1_final_pos: int
    player2_final_pos: int
    player1_received_value: Optional[Union[int, float]] = None
    player2_received_value: Optional[Union[int, float]] = None
    turn_number: Optional[int] = None
    
    def __repr__(self):
        return (f"Turn {self.turn_number}: P{self.player1_id}[{self.player1_init_pos}]→{self.player1_final_pos} ↔ "
                f"P{self.player2_id}[{self.player2_init_pos}]→{self.player2_final_pos}")


@dataclass
class SignalRecord:
    """
    Public record of a player signaling they have a certain value at a specific position.
    This is a direct announcement of knowledge, useful for speeding up IRL gameplay.
    
    Attributes:
        player_id: ID of the player making the signal
        value: The value at the position (can be int or float)
        position: Wire position being signaled (0-indexed)
        turn_number: Game turn when this signal was made
    """
    player_id: int
    value: Union[int, float]
    position: int
    turn_number: Optional[int] = None
    
    def __repr__(self):
        return f"Turn {self.turn_number}: P{self.player_id} SIGNALS [{self.position}]={self.value}"


@dataclass
class NotPresentRecord:
    """
    Public record of a player announcing they don't have a specific value.
    This allows removing a value from all of a player's possible positions,
    or from a specific position if specified.
    
    Attributes:
        player_id: ID of the player making the announcement
        value: The value they don't have (can be int or float)
        position: Optional specific position (0-indexed) where the value is not present
        turn_number: Game turn when this announcement was made
    """
    player_id: int
    value: Union[int, float]
    position: Optional[int] = None
    turn_number: Optional[int] = None
    
    def __repr__(self):
        if self.position is not None:
            return f"Turn {self.turn_number}: P{self.player_id} DOES NOT HAVE {self.value} at pos {self.position}"
        return f"Turn {self.turn_number}: P{self.player_id} DOES NOT HAVE {self.value}"


@dataclass
class GameObservation:
    """
    All information available to a single player.
    This ensures independence: each player only sees their own wire and public call history.
    
    Attributes:
        player_id: ID of the player who owns this observation
        my_wire: The player's own wire (full knowledge, values can be int or float)
        my_revealed_positions: Positions visible to this player (dict: position -> value)
        call_history: List of all calls made in the game (public information)
        n_players: Total number of players
        wire_length: Number of wires per player
    """
    player_id: int
    my_wire: List[Union[int, float]]
    my_revealed_positions: Dict[int, Union[int, float]]
    call_history: List[CallRecord]
    n_players: int
    wire_length: int


class ValueTracker:
    """
    Tracks the state of a specific value across all players.
    Used for r_k filtering to determine when all copies of a value are accounted for.
    
    Data structure:
    {
        "total": r_k,                              # Total copies in game (constant)
        "revealed": [(player_id, position), ...],  # Positions revealed via correct calls
        "certain": [(player_id, position), ...],   # Positions deduced via filtering
        "called": [player_id, ...]                 # Players who called it (position unknown)
    }
    
    Key formula:
    uncertain_copies = total - len(revealed) - len(certain) - len(called)
    
    Rules:
    - A player can only be in ONE state at a time (mutually exclusive)
    - revealed: Position confirmed via correct call - tuple (player_id, position)
    - certain: Position deduced via filtering - tuple (player_id, position)
    - called: Wrong call demonstrated ownership - just player_id (position unknown)
    
    State transitions:
    - uncertain → called: Wrong call demonstrates ownership (no position info)
    - uncertain/called → certain: Filtering deduces position
    - uncertain/called/certain → revealed: Correct call confirms position
    """
    
    def __init__(self, value: float, total: int):
        """
        Initialize value tracking.
        
        Args:
            value: The wire value to track
            total: Total copies of this value in the game (r_k)
        """
        self.value = value
        self.total = total
        self.revealed: List[Tuple[int, int]] = []  # [(player_id, position), ...]
        self.certain: List[Tuple[int, int]] = []   # [(player_id, position), ...]
        self.called: List[int] = []                # [player_id, ...] - position unknown
    
    @property
    def uncertain(self) -> int:
        """
        Property for easy access to uncertain count.
        
        Returns:
            Number of uncertain copies
        """
        return self.total - len(self.revealed) - len(self.certain) - len(self.called)
    
    def get_uncertain_count(self) -> int:
        """
        Calculate how many copies are still uncertain.
        
        Returns:
            Number of uncertain copies
        """
        return self.total - len(self.revealed) - len(self.certain) - len(self.called)
    
    def get_revealed_count(self) -> int:
        """
        Get the number of revealed copies.
        
        Returns:
            Number of revealed copies
        """
        return len(self.revealed)
    
    def is_fully_accounted(self) -> bool:
        """
        Check if all copies are accounted for (no uncertain copies).
        
        Returns:
            True if uncertain_count == 0
        """
        return self.get_uncertain_count() == 0
    
    def add_revealed(self, player_id: int, position: int):
        """
        Mark a player's position as having revealed this value.
        Removes from certain if the same position is there.
        
        Args:
            player_id: The player who revealed the value
            position: The position where the value was revealed
        """
        # Remove from certain if this exact position was certain
        self.certain = [(p, pos) for p, pos in self.certain if not (p == player_id and pos == position)]
        
        # Remove player from called list (they had it, now we know where)
        if player_id in self.called:
            self.called.remove(player_id)
        
        # Add to revealed if not already there
        if (player_id, position) not in self.revealed:
            self.revealed.append((player_id, position))
        else:
            print(f"XX Warning: Player {player_id} position {position} already in revealed list for value {self.value}")
    
    def add_certain(self, player_id: int, position: int):
        """
        Mark a player's position as certain to have this value (deduced, not revealed).
        Removes from called if present. Does NOT remove from revealed.
        
        Args:
            player_id: The player who is certain to have the value
            position: The position that is certain
        """
        # Skip if this position is already revealed or certain
        if (player_id, position) in self.revealed or (player_id, position) in self.certain:
            return
        
        # Remove player from called if present (now we know the position)
        if player_id in self.called:
            self.called.remove(player_id)
        
        self.certain.append((player_id, position))
    
    def add_called(self, player_id: int):
        """
        Mark a player as having called this value (wrong call).
        Position is unknown, so we just store the player ID.
        
        Args:
            player_id: The player who called the value
        """

        # Skip if player already certain (with position info)
        if any(p == player_id for p, pos in self.certain):
            return
        
        # Add to called if not already there
        if player_id not in self.called:
            self.called.append(player_id)
    
    def get_accounted_players(self) -> List[int]:
        """
        Get all players who are accounted for (revealed, certain, or called).
        
        Returns:
            List of all unique player IDs in any tracking list
        """
        players = set()
        players.update(p for p, pos in self.revealed)
        players.update(p for p, pos in self.certain)
        players.update(self.called)
        return list(players)
    
    def __repr__(self):
        return (f"ValueTracker(value={self.value}, total={self.total}, "
                f"revealed={self.revealed}, certain={self.certain}, "
                f"called={self.called}, uncertain={self.get_uncertain_count()})")

    def to_dict(self, player_names: Dict[int, str] = None) -> Dict:
        """Serialize the ValueTracker to a JSON-serializable dict.
        
        Args:
            player_names: Optional dict mapping player IDs to names {0: "Alice", 1: "Bob", ...}
                         If provided, player IDs will be replaced with names in the output
        """
        def format_player(player_id: int) -> Union[str, int]:
            """Convert player ID to name if available, otherwise return ID."""
            if player_names and player_id in player_names:
                return player_names[player_id]
            return player_id
        
        def format_position_tuple(player_id: int, position: int) -> List:
            """Format a (player_id, position) tuple with name if available."""
            return [format_player(player_id), position]
        
        return {
            "revealed": [format_position_tuple(p, pos) for p, pos in self.revealed],
            "certain": [format_position_tuple(p, pos) for p, pos in self.certain],
            "called": [format_player(p) for p in self.called],
            "uncertain": f"{self.get_uncertain_count()}/{self.total}"
        }

    @classmethod
    def from_dict(cls, data: Dict, value: int, total: int, player_names: Dict[int, str] = None) -> "ValueTracker":
        """Create a ValueTracker from a dict produced by to_dict().
        
        Args:
            data: Dict with revealed, certain, called lists
            value: The value this tracker represents
            total: Total number of copies in the game
            player_names: Optional dict mapping player IDs to names, used to convert names back to IDs
        """
        vt = cls(value, total)
        
        # Create reverse mapping from names to IDs if player_names provided
        name_to_id = {}
        if player_names:
            name_to_id = {name: pid for pid, name in player_names.items()}
        
        def parse_player(player_identifier: Union[str, int]) -> int:
            """Convert player name or ID to integer ID."""
            if isinstance(player_identifier, int):
                return player_identifier
            elif isinstance(player_identifier, str):
                # Try to convert name to ID
                if player_identifier in name_to_id:
                    return name_to_id[player_identifier]
                # Fallback: try to parse as integer
                try:
                    return int(player_identifier)
                except ValueError:
                    raise ValueError(f"Unknown player name: {player_identifier}")
            else:
                raise TypeError(f"Invalid player identifier type: {type(player_identifier)}")
        
        # revealed: convert to list of tuples
        revealed_data = data.get("revealed", [])
        vt.revealed = []
        for item in revealed_data:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                # Format: [player_identifier, position]
                player_id = parse_player(item[0])
                position = int(item[1])
                vt.revealed.append((player_id, position))
            elif isinstance(item, int):
                # Old format: just player_id (position unknown, treat as invalid/skip)
                pass
        
        # certain: convert to list of tuples
        certain_data = data.get("certain", [])
        vt.certain = []
        for item in certain_data:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                # Format: [player_identifier, position]
                player_id = parse_player(item[0])
                position = int(item[1])
                vt.certain.append((player_id, position))
            elif isinstance(item, int):
                # Old format: just player_id (position unknown, treat as invalid/skip)
                pass
        
        # called: list of player identifiers (names or IDs)
        called_data = data.get("called", [])
        vt.called = []
        for player_identifier in called_data:
            player_id = parse_player(player_identifier)
            vt.called.append(player_id)
        
        return vt
