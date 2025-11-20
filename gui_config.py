"""
GUI Configuration for BombBuster IRL
Edit this file to configure your game settings
"""

# Your player configuration
MY_PLAYER_NAME = "Ettore"
MY_WIRE = [1,3.1,4,6,6,6.5,8,9,9,10,12]

# Player names (in order by player ID)
PLAYER_NAMES = [
    "Ettore",
    "Brini",
    "Frodo",
    "Gorgo",
    "Andre"
]

# Belief folder for saving/loading game state
BELIEF_FOLDER = "real_game_beliefs"

# Options
AUTO_SAVE = True       # Automatically save after each action
LOAD_EXISTING = True   # Load existing beliefs on startup
USE_GLOBAL_BELIEF = True # Use the new global belief model (True) or the old one (False)
