"""
Game configuration parameters for BombBuster.
Defines the wire distribution, number of players, and game constraints.
"""

# Game parameters
# Define wire values and their copy counts
# Format: {value: number_of_copies}
WIRE_DISTRIBUTION = {
    **{i: 4 for i in range(1, 13)},  # Values 1-12 have 4 copies each
    6.5: 1,                           # Value 2.5 has 2 copies
    1.1:1,
    3.1:1,
    5.1:1,
    2.1:1,
    99:2,

}

N = 5  # Number of players (collaborative team)

# Derived parameters
WIRE_VALUES = sorted(WIRE_DISTRIBUTION.keys())  # All unique values
K = len(WIRE_VALUES)                             # Number of distinct wire values
TOTAL_WIRES = sum(WIRE_DISTRIBUTION.values())   # Total number of wires
NUM_PLAYERS = N
WIRES_PER_PLAYER = TOTAL_WIRES // N

# Game rules
MAX_WRONG_CALLS = 5      # Team loses if they make this many wrong calls


class GameConfig:
    """
    Configuration class for game parameters.
    Encapsulates all game rules and parameters.
    """
    
    def __init__(
        self,
        wire_distribution: dict = None,
        n_players: int = N,
        max_wrong_calls: int = MAX_WRONG_CALLS,
        playing_irl: bool = False
    ):
        """
        Initialize game configuration.
        
        Args:
            wire_distribution: Dict mapping wire values to their copy counts {value: count}
            n_players: Number of players
            max_wrong_calls: Maximum wrong calls before team loses
            playing_irl: If True, disables validation that caller possesses the called value
                        (useful when playing with physical cards where wires may not match simulation)
        """
        self.wire_distribution = wire_distribution if wire_distribution is not None else WIRE_DISTRIBUTION
        self.n_players = n_players
        self.max_wrong_calls = max_wrong_calls
        self.playing_irl = playing_irl
        
        # Derived values
        self.wire_values = sorted(self.wire_distribution.keys())
        self.K = len(self.wire_values)
        self.k = self.K  # Alias for backwards compatibility
        self.total_wires = sum(self.wire_distribution.values())
        self.wires_per_player = self.total_wires // n_players
        
        # For backwards compatibility (deprecated - use wire_distribution instead)
        self.r_k = None  # No longer a single value
        
        # Validate configuration
        self._validate()
    
    def get_copies(self, value) -> int:
        """
        Get the number of copies for a specific wire value.
        
        Args:
            value: The wire value to query
            
        Returns:
            Number of copies of this value in the game
        """
        return self.wire_distribution.get(value, 0)
    
    def _validate(self):
        """Validate that the configuration is internally consistent."""
        assert self.total_wires % self.n_players == 0, \
            "Total wires must be evenly divisible by number of players"
        assert self.max_wrong_calls > 0, \
            "Must allow at least one wrong call"
        assert len(self.wire_values) == self.K, \
            "Wire values list length must match K"
        assert len(set(self.wire_values)) == self.K, \
            "Wire values must be unique"
        assert all(count > 0 for count in self.wire_distribution.values()), \
            "All wire values must have at least one copy"


def validate_config():
    """Validate that the default configuration is internally consistent."""
    assert TOTAL_WIRES % N == 0, "Total wires must be evenly divisible by number of players"
    assert sum(WIRE_DISTRIBUTION.values()) == TOTAL_WIRES, "Total wires must equal sum of all copies"
    
validate_config()
