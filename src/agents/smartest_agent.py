"""
Smartest agent that uses entropy analysis to choose the best action.
"""

import random
from typing import Optional, Tuple
from src.agents.base_agent import BaseAgent
from src.player import Player
from src.game import Game
from src.statistics import GameStatistics
from config.game_config import PLAYER_NAMES
from src.utils import find_first_unrevealed_position


class SmartestAgent(BaseAgent):
    """
    Agent that uses entropy minimization to choose the best call.
    
    Strategy:
    1. Check for any CERTAIN calls (where a target position has only 1 possible value, and I have that value).
    2. If certain calls exist, make one.
    3. If no certain calls, use GameStatistics.get_entropy_suggestion() to find the call that maximizes information gain.
    4. If no suggestion (e.g. no playable values), pass.
    """
    
    def __init__(self, player: Player):
        """
        Initialize the smartest agent.
        
        Args:
            player: The Player object to control
        """
        super().__init__(player, name="SmartestAgent")
        self.used_double_chance = False  # Track if double chance has been used
    
    def choose_action(self, game: Game) -> Optional[Tuple]:
        """
        Choose the best action based on entropy analysis.
        
        Args:
            game: Current game state
        
        Returns:
            Tuple of (target_id, position, value) for normal calls
            Tuple of ('double_chance', target_id, position1, position2, value) for double chance
            Tuple of ('double_reveal', position1, position2, value) for double reveal
            or None if no valid calls
        """
        # Initialize statistics helper
        stats = GameStatistics(self.player.belief_system, game.config, self.player.wire)

        # 0. Check for last remaining wires (can do double reveal)
        value_trackers = self.player.belief_system.value_trackers
        for value in game.config.wire_values:
            if value not in value_trackers:
                continue
            
            tracker = value_trackers[value]
            total_copies = game.config.get_copies(value)
            revealed_count = len(tracker.revealed)
            
            # Count how many of this value I have
            my_count = 0
            my_positions = []
            for pos, val in enumerate(self.player.wire):
                if val == value:
                    # Check if this position is not already revealed
                    is_revealed = False
                    for revealed_pid, revealed_pos in tracker.revealed:
                        if revealed_pid == self.player.player_id and revealed_pos == pos:
                            is_revealed = True
                            break
                    
                    if not is_revealed:
                        my_count += 1
                        my_positions.append(pos)
            
            # Check if I have the last remaining wires for this value
            if my_count + revealed_count == total_copies and my_count >= 2:
                print(f"Agent {self.player.player_id} has last {my_count} copies of value {value}!")
                
                if my_count == 2:
                    # Do a single double reveal
                    return ('double_reveal', my_positions[0], my_positions[1], value)
                elif my_count == 4:
                    # Do both double reveals in the same turn
                    return ('double_reveal_quad', my_positions[0], my_positions[1], my_positions[2], my_positions[3], value)
                # Note: my_count == 3 shouldn't happen (can only reveal pairs)
        
        # 1. Get playable values (values I have that are not revealed)
        playable_values = list(stats.get_playable_values())
        if not playable_values:
            return None
            
        playable_set = set(playable_values)
        
        # 2. Look for CERTAIN calls
        certain_calls = []
        
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
                if stats.is_position_revealed(target_id, position):
                    continue
                
                # Get beliefs for this position
                beliefs = self.player.belief_system.beliefs[target_id][position]
                
                # If belief size is 1, it's a certain call (if I have the value)
                if len(beliefs) == 1:
                    val = list(beliefs)[0]
                    if val in playable_set:
                        certain_calls.append((target_id, position, val))
        
        # 3. Execute strategy
        if certain_calls:
            # Prioritize certain calls
            return random.choice(certain_calls)
        
        # 3b. Check for double chance if not used yet
        if not self.used_double_chance:
            print(f"Agent {self.player.player_id} checking for DOUBLE CHANCE opportunity...")
            double_chance_suggestions = stats.get_double_chance_suggestions()
            if double_chance_suggestions:
                # Get best double chance (first one, already sorted by probability)
                best_dc = double_chance_suggestions[0]
                self.used_double_chance = True
                target_id = best_dc['target_id']
                pos1, pos2 = best_dc['positions']
                value = best_dc['value']
                
                # Skip VOID player
                if target_id < len(PLAYER_NAMES) and PLAYER_NAMES[target_id] == "VOID":
                    pass  # Fall through to entropy suggestion
                else:
                    print(f"Agent {self.player.player_id} using DOUBLE CHANCE: P{target_id}[{pos1},{pos2}]={value} (prob: {best_dc['probability']:.1%})")
                    return ('double_chance', target_id, pos1, pos2, value)
                
        print(f"Agent {self.player.player_id} using ENTROPY analysis for best call...")
        suggestion = stats.get_entropy_suggestion(max_uncertainty=3, use_parallel=True)
        
        best_call = suggestion.get('best_call')
        
        if best_call:
            target_id, position, value = best_call
            
            # Double check validity (should be valid from suggester, but safety first)
            # Skip VOID player check just in case suggester didn't filter it
            if target_id < len(PLAYER_NAMES) and PLAYER_NAMES[target_id] == "VOID":
                return None
                
            return (target_id, position, value)
            
        return None
