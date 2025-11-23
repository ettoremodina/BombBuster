"""
Game configuration parameters for BombBuster.
Defines the wire distribution, number of players, and game constraints.
"""
USE_GLOBAL_BELIEF = True # Use the new global belief model (True) or the old one (False)

# Format: {value: number_of_copies}
WIRE_DISTRIBUTION = {
    **{i: 4 for i in range(1, 13)},  # Values 1-12 have 4 copies each
    2.5: 1,                       
    7.5: 1,                       
    8.5: 1,                       
    
}
EXTRA_UNCERTAIN_WIRES = {
    # 7.5: 1,
    # 8.5: 1,
    # 6.5: 1,
}
# Your player configuration
# MY_WIRE = list(range(1,13))+list(range(1,6))
MY_WIRE = [1,2,3,5,7,8,8,8.5,9,10,10,11,12]

# Player names (in order by player ID)
PLAYER_NAMES = [
    "Ettore",
    "Brini",
    "Frodo",
    # "Gorgo",
    # "Andre"
]


MY_PLAYER_NAME = "Ettore"
# Belief folder for saving/loading game state
BELIEF_FOLDER = "real_game_beliefs"

# Options
AUTO_SAVE = True       # Automatically save after each action
LOAD_EXISTING = True   # Load existing beliefs on startup

MAX_UNCERTAINTY = 4  # Max uncertainty level for entropy analysis





# enable USE_VOID_PLAYER when EXTRA_UNCERTAIN_WIRES is non-empty
USE_VOID_PLAYER = bool(EXTRA_UNCERTAIN_WIRES)
N = len(PLAYER_NAMES)  # Number of players


# Calculate if we need filler wires to make distribution divisible by number of players
if not USE_VOID_PLAYER:
    _initial_total = sum(WIRE_DISTRIBUTION.values())
    _filler_needed = (N - (_initial_total % N)) % N
    
    if _filler_needed > 0:
        # Add filler wires (value 99) that will be manually revealed at game start
        WIRE_DISTRIBUTION[99] = _filler_needed

if USE_VOID_PLAYER:
    # 1. Calculate expected hand size from the base configuration
    # Total real wires = base wires + all uncertain wires - 1 discarded
    # We need to round UP since some players may have one extra card
    _base_total_wires = sum(WIRE_DISTRIBUTION.values()) + sum(EXTRA_UNCERTAIN_WIRES.values()) - 1
    _hand_size = (_base_total_wires + N - 1) // N  # Ceiling division: round up
    
    # 1b. Add filler wires (99) for real players if needed
    # These are needed if the real wires don't divide evenly among real players
    _filler_needed = (N * _hand_size) - _base_total_wires
    if _filler_needed > 0:
        WIRE_DISTRIBUTION[99] = _filler_needed

    # 2. Add ALL extra wires (certain and uncertain) to the universe
    WIRE_DISTRIBUTION.update(EXTRA_UNCERTAIN_WIRES)
    
    # 3. Add the VOID player
    PLAYER_NAMES.append("VOID")
    N = len(PLAYER_NAMES)
    
    # 4. Add padding (0-value wires) to ensure VOID has the same hand size
    # The VOID player holds: [1 Discarded Wire from EXTRA_UNCERTAIN_WIRES] + [Padding Wires]
    # VOID's hand size = _hand_size
    # VOID has 1 uncertain wire from EXTRA_UNCERTAIN_WIRES
    # So padding needed = _hand_size - 1
    _current_total = sum(WIRE_DISTRIBUTION.values())
    _needed_total = N * _hand_size
    _padding_amount = _needed_total - _current_total
    
    if _padding_amount > 0:
        WIRE_DISTRIBUTION[0] = _padding_amount

# Derived parameters
WIRE_VALUES = sorted(WIRE_DISTRIBUTION.keys())  # All unique values
K = len(WIRE_VALUES)                             # Number of distinct wire values
TOTAL_WIRES = sum(WIRE_DISTRIBUTION.values())   # Total number of wires
NUM_PLAYERS = N
WIRES_PER_PLAYER = TOTAL_WIRES // N

# Game rules
MAX_WRONG_CALLS = 1000      # Team loses if they make this many wrong calls


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
        playing_irl: bool = False,
        use_global_belief: bool = False,
        auto_filter: bool = False
    ):
        """
        Initialize game configuration.
        
        Args:
            wire_distribution: Dict mapping wire values to their copy counts {value: count}
            n_players: Number of players
            max_wrong_calls: Maximum wrong calls before team loses
            playing_irl: If True, disables validation that caller possesses the called value
                        (useful when playing with physical cards where wires may not match simulation)
            use_global_belief: Whether to use the GlobalBeliefModel (True) or standard BeliefModel (False)
            auto_filter: Whether to automatically apply filters after every action (True) or wait for manual trigger (False)
        """
        self.wire_distribution = wire_distribution if wire_distribution is not None else WIRE_DISTRIBUTION
        self.n_players = n_players
        self.max_wrong_calls = max_wrong_calls
        self.playing_irl = playing_irl
        self.use_global_belief = use_global_belief
        self.auto_filter = auto_filter
        
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
