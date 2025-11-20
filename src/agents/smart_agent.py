from typing import Optional, Tuple, List
import random
from src.agents.base_agent import BaseAgent
from src.game import Game

class SmartAgent(BaseAgent):
    """
    Agent that plays intelligently:
    1. Prioritizes calling values it is certain about (but not yet revealed).
    2. Falls back to making smart guesses (unrevealed positions) if no certainties.
    """
    
    def __init__(self, player):
        super().__init__(player, name="SmartAgent")
    
    def choose_action(self, game: Game) -> Optional[Tuple[int, int, int]]:
        # 1. Check for certain but unrevealed positions
        certain_calls = self._get_certain_unrevealed_calls(game)
        if certain_calls:
            # Found certain calls! Pick one.
            return random.choice(certain_calls)
            
        # 2. Fallback: Smart random guess
        # Only guess on positions that are NOT yet revealed
        return self._make_smart_guess(game)
    
    def _get_certain_unrevealed_calls(self, game: Game) -> List[Tuple[int, int, int]]:
        """Find all calls that are certain (deduced) but not yet revealed."""
        possible_calls = []
        if self.player.belief_system is None:
            return []
            
        for target_id in range(game.config.n_players):
            if target_id == self.player.player_id:
                continue
                
            # Get certain positions for this target
            certain_pos = self.player.belief_system.get_certain_positions(target_id)
            
            for pos, value in certain_pos.items():
                # Check if already revealed
                tracker = self.player.belief_system.value_trackers[value]
                is_revealed = any(p == target_id and p_pos == pos for p, p_pos in tracker.revealed)
                
                if not is_revealed:
                    # Check if we have this value to make the call (unless IRL mode)
                    if game.config.playing_irl or self.player.has_value(value):
                        possible_calls.append((target_id, pos, value))
                        
        return possible_calls
        
    def _make_smart_guess(self, game: Game) -> Optional[Tuple[int, int, int]]:
        """Make a random guess on an unrevealed position."""
        # Get available values (my hand)
        my_values = list(set(self.player.wire)) if self.player.wire else []
        if not my_values:
            return None
            
        # Find unrevealed positions for other players
        candidates = []
        for target_id in range(game.config.n_players):
            if target_id == self.player.player_id:
                continue
                
            # Check each position
            for pos in range(game.config.wires_per_player):
                # Check if this position is revealed (any value)
                is_pos_revealed = False
                if self.player.belief_system:
                    for val in game.config.wire_values:
                        tracker = self.player.belief_system.value_trackers[val]
                        if any(p == target_id and p_pos == pos for p, p_pos in tracker.revealed):
                            is_pos_revealed = True
                            break
                
                if not is_pos_revealed:
                    # Add candidate for each value I have
                    for val in my_values:
                        candidates.append((target_id, pos, val))
                            
        if candidates:
            return random.choice(candidates)
        return None
