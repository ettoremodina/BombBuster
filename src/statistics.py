"""
Statistics and analysis module for the BombBuster belief system.
Tracks uncertainty metrics and provides call suggestions.
"""

import math
from typing import Dict, List, Tuple, Set, Union, Optional
from src.belief.belief_model import BeliefModel
from config.game_config import GameConfig
# from tqdm import tqdm

class GameStatistics:
    """
    Analyzes the belief system to compute uncertainty metrics and suggest optimal calls.
    
    This class provides:
    - Entropy calculations (Shannon entropy) for measuring uncertainty
    - Per-player and system-wide statistics
    - Call suggestion algorithms
    - Progress tracking
    """
    
    def __init__(self, belief_model: BeliefModel, config: GameConfig, my_wire: List[Union[int, float]] = None):
        """
        Initialize statistics for a belief model.
        
        Args:
            belief_model: The belief model to analyze
            config: Game configuration
            my_wire: Optional - the player's actual wire (for call filtering)
        """
        self.belief_model = belief_model
        self.config = config
        self.my_wire = my_wire
        self.my_player_id = belief_model.my_player_id
    
    def calculate_position_entropy(self, player_id: int, position: int) -> float:
        """
        Calculate Shannon entropy for a single position.
        
        H = -Σ P(value) × log₂(P(value))
        
        For uniform belief: P(value) = 1 / |possible_values|
        
        Args:
            player_id: Player whose position to analyze
            position: Position index
            
        Returns:
            Entropy in bits (0 = certain, higher = more uncertain)
        """
        possible_values = self.belief_model.beliefs[player_id][position]
        n = len(possible_values)
        
        if n <= 1:
            return 0.0  # Certain or empty (no uncertainty)
        
        # Uniform distribution: P = 1/n for each value
        # H = -n × (1/n × log₂(1/n)) = -log₂(1/n) = log₂(n)
        return math.log2(n)
    
    def calculate_player_entropy(self, player_id: int) -> float:
        """
        Calculate total entropy for one player's wire.
        
        Args:
            player_id: Player to analyze
            
        Returns:
            Total entropy across all positions (in bits)
        """
        total_entropy = 0.0
        for position in range(self.config.wires_per_player):
            total_entropy += self.calculate_position_entropy(player_id, position)
        return total_entropy
    
    def calculate_system_entropy(self) -> float:
        """
        Calculate total entropy across all players.
        
        Returns:
            Total system entropy (in bits)
        """
        total_entropy = 0.0
        for player_id in range(self.config.n_players):
            total_entropy += self.calculate_player_entropy(player_id)
        return total_entropy
    
    def get_player_statistics(self, player_id: int) -> Dict:
        """
        Get comprehensive statistics for one player.
        
        Args:
            player_id: Player to analyze
            
        Returns:
            Dict with keys:
            - 'entropy': Total entropy (bits)
            - 'entropy_normalized': Normalized entropy (0-1)
            - 'certain_count': Number of certain positions
            - 'uncertain_count': Number of uncertain positions
            - 'avg_possibilities': Average number of possibilities per position
            - 'progress_percent': Percentage of positions that are certain
        """
        entropy = self.calculate_player_entropy(player_id)
        
        # Maximum possible entropy: all positions have all values possible
        max_entropy = self.config.wires_per_player * math.log2(len(self.config.wire_values))
        entropy_normalized = entropy / max_entropy if max_entropy > 0 else 0.0
        
        certain_count = 0
        uncertain_count = 0
        total_possibilities = 0
        
        for position in range(self.config.wires_per_player):
            possible = self.belief_model.beliefs[player_id][position]
            if len(possible) == 1:
                certain_count += 1
            else:
                uncertain_count += 1
            total_possibilities += len(possible)
        
        avg_possibilities = total_possibilities / self.config.wires_per_player if self.config.wires_per_player > 0 else 0
        progress_percent = 100.0 * certain_count / self.config.wires_per_player if self.config.wires_per_player > 0 else 0
        
        return {
            'entropy': entropy,
            'entropy_normalized': entropy_normalized,
            'certain_count': certain_count,
            'uncertain_count': uncertain_count,
            'avg_possibilities': avg_possibilities,
            'progress_percent': progress_percent
        }
    
    def get_system_statistics(self) -> Dict:
        """
        Get system-wide statistics.
        
        Returns:
            Dict with keys:
            - 'total_entropy': Total system entropy
            - 'avg_player_entropy': Average per-player entropy
            - 'completion_percent': Overall completion percentage
            - 'most_uncertain_player': Player ID with highest entropy
        """
        total_entropy = self.calculate_system_entropy()
        
        player_entropies = {pid: self.calculate_player_entropy(pid) 
                           for pid in range(self.config.n_players)}
        
        avg_player_entropy = total_entropy / self.config.n_players if self.config.n_players > 0 else 0
        
        # Calculate overall completion
        total_certain = sum(self.get_player_statistics(pid)['certain_count'] 
                           for pid in range(self.config.n_players))
        total_positions = self.config.n_players * self.config.wires_per_player
        completion_percent = 100.0 * total_certain / total_positions if total_positions > 0 else 0
        
        most_uncertain_player = max(player_entropies, key=player_entropies.get) if player_entropies else 0
        
        return {
            'total_entropy': total_entropy,
            'avg_player_entropy': avg_player_entropy,
            'completion_percent': completion_percent,
            'most_uncertain_player': most_uncertain_player,
            'player_entropies': player_entropies
        }
    
    def get_playable_values(self) -> Set[Union[int, float]]:
        """
        Get values that the player has and are NOT revealed.
        
        Returns:
            Set of playable values
        """
        playable_values = set()
        value_trackers = self.belief_model.value_trackers
        
        if self.my_wire is not None:
            # If we know the wire, check each position
            for pos, val in enumerate(self.my_wire):
                is_revealed = False
                if val in value_trackers:
                    for pid, r_pos in value_trackers[val].revealed:
                        if pid == self.my_player_id and r_pos == pos:
                            is_revealed = True
                            break
                if not is_revealed:
                    playable_values.add(val)
        else:
            # Fallback to beliefs (only certain values)
            for pos in range(self.config.wires_per_player):
                beliefs = self.belief_model.beliefs[self.my_player_id][pos]
                if len(beliefs) == 1:
                    val = list(beliefs)[0]
                    is_revealed = False
                    if val in value_trackers:
                        for pid, r_pos in value_trackers[val].revealed:
                            if pid == self.my_player_id and r_pos == pos:
                                is_revealed = True
                                break
                    if not is_revealed:
                        playable_values.add(val)
        
        return playable_values

    def is_position_revealed(self, player_id: int, position: int) -> bool:
        """
        Check if a specific position for a player is already revealed.
        
        Args:
            player_id: The player ID
            position: The position index
            
        Returns:
            True if revealed, False otherwise
        """
        # We need to check all value trackers to see if this position is revealed
        # This is a bit inefficient but safe. 
        # Alternatively, we could check if the belief is certain and then check that value's tracker.
        
        # Optimization: Check if belief is certain first
        beliefs = self.belief_model.beliefs[player_id][position]
        if len(beliefs) == 1:
            val = list(beliefs)[0]
            if val in self.belief_model.value_trackers:
                for pid, r_pos in self.belief_model.value_trackers[val].revealed:
                    if pid == player_id and r_pos == position:
                        return True
        
        # If belief is not certain, it can't be revealed (revealed implies certain)
        # Unless there's some inconsistency, but let's assume consistency.
        return False

    def get_all_call_suggestions(self) -> Dict[str, List[Tuple[int, int, Union[int, float], int]]]:
        """
        Get all possible call suggestions organized by certainty level.
        Filters out revealed values and revealed target positions.
        
        Returns:
            Dict with keys:
            - 'certain': List of (target_id, position, value, 1)
            - 'uncertain': List of (target_id, position, value, uncertainty) sorted by uncertainty
        """
        my_values = self.get_playable_values()
        if not my_values:
            return {'certain': [], 'uncertain': []}
        
        certain_calls = []
        uncertain_calls = []
        
        for target_id in range(self.config.n_players):
            if target_id == self.my_player_id:
                continue
            
            for position in range(self.config.wires_per_player):
                # Skip if target position is already revealed
                if self.is_position_revealed(target_id, position):
                    continue
                
                possible_values = self.belief_model.beliefs[target_id][position]
                
                for value in possible_values:
                    if value not in my_values:
                        continue
                    
                    if len(possible_values) == 1:
                        certain_calls.append((target_id, position, value, 1))
                    else:
                        uncertain_calls.append((target_id, position, value, len(possible_values)))
        
        uncertain_calls.sort(key=lambda x: x[3])
        
        return {
            'certain': certain_calls,
            'uncertain': uncertain_calls
        }
    
    def get_entropy_suggestion(self, max_uncertainty: int = 3, progress_callback=None, use_parallel: bool = True) -> Dict:
        """
        Get the best call suggestion based on entropy minimization.
        Uses simulation to calculate expected information gain.
        
        Args:
            max_uncertainty: Max number of possibilities to consider for simulation
            progress_callback: Optional callback for progress updates
            use_parallel: Whether to use parallel processing (default True)
            
        Returns:
            Result dict from EntropySuggester
        """
        # Local import to avoid circular dependency
        from src.belief.entropy_suggester import EntropySuggester
        
        suggester = EntropySuggester(self.belief_model, self.config)
        return suggester.suggest_best_call(max_uncertainty, progress_callback=progress_callback, use_parallel=use_parallel)

    def print_call_suggestions(self, player_names: Dict[int, str] = None):
        """
        Print all available call suggestions in a readable format.
        
        Args:
            player_names: Optional dict mapping player IDs to names
        """
        suggestions = self.get_all_call_suggestions()
        
        my_name = player_names.get(self.my_player_id, f"Player {self.my_player_id}") if player_names else f"Player {self.my_player_id}"
        
        print(f"\n{'='*80}")
        print(f"CALL SUGGESTIONS for {my_name}")
        print(f"{'='*80}")
        
        my_values = self.get_playable_values()
        print(f"\nYour values (can call): {sorted(my_values)}")
        
        # Print certain calls
        certain = suggestions['certain']
        if certain:
            print(f"\n✓ CERTAIN CALLS ({len(certain)}):")
            print("  These calls are GUARANTEED to be correct!")
            for target_id, position, value, _ in certain[:10]:
                target_name = player_names.get(target_id, f"Player {target_id}") if player_names else f"Player {target_id}"
                print(f"    → Call {target_name}[{position+1}] = {value}")
            if len(certain) > 10:
                print(f"    ... and {len(certain) - 10} more certain calls")
        else:
            print(f"\n✓ CERTAIN CALLS: None available")
        
        # Print uncertain calls
        uncertain = suggestions['uncertain']
        if uncertain:
            print(f"\n⚠️  UNCERTAIN CALLS ({len(uncertain)}):")
            print("  These calls have some chance of being wrong")
            
            by_uncertainty = {}
            for target_id, position, value, unc in uncertain:
                if unc not in by_uncertainty:
                    by_uncertainty[unc] = []
                by_uncertainty[unc].append((target_id, position, value))
            
            for unc in sorted(by_uncertainty.keys())[:3]:
                calls = by_uncertainty[unc]
                probability = 1.0 / unc
                print(f"\n  Uncertainty: {unc} possible values (probability: {probability:.1%})")
                for target_id, position, value in calls[:5]:
                    target_name = player_names.get(target_id, f"Player {target_id}") if player_names else f"Player {target_id}"
                    print(f"    → Call {target_name}[{position+1}] = {value}")
                if len(calls) > 5:
                    print(f"    ... and {len(calls) - 5} more at this level")
        else:
            print(f"\n⚠️  UNCERTAIN CALLS: None available")
        
        # Print best suggestion (Entropy Based)
        if not certain and uncertain:
            print(f"\n{'='*80}")
            print(f"🧠 ANALYZING BEST UNCERTAIN CALL (Entropy Simulation)...")
            entropy_result = self.get_entropy_suggestion(max_uncertainty=3)
            
            best_call = entropy_result['best_call']
            if best_call:
                target_id, position, value = best_call
                target_name = player_names.get(target_id, f"Player {target_id}") if player_names else f"Player {target_id}"
                
                print(f"💡 RECOMMENDED CALL (Max Info Gain):")
                print(f"   {my_name} → {target_name}[{position+1}] = {value}")
                print(f"   Expected Info Gain: {entropy_result['information_gain']:.4f} bits")
                print(f"   Time taken: {entropy_result['time_taken']:.2f}s ({entropy_result['candidates_analyzed']} simulations)")
            else:
                print(f"   No suitable candidates for simulation (too uncertain or no playable values).")
            print(f"{'='*80}")
        elif certain:
             print(f"\n{'='*80}")
             print(f"💡 RECOMMENDATION: Take any CERTAIN call.")
             print(f"{'='*80}")
        
        # Print Double Chance suggestions
        self.print_double_chance_suggestions(player_names)
    
    def print_statistics(self, player_names: Dict[int, str] = None):
        """
        Print comprehensive statistics for all players and the system.
        
        Args:
            player_names: Optional dict mapping player IDs to names
        """
        print(f"\n{'='*80}")
        print(f"GAME STATISTICS")
        print(f"{'='*80}")
        
        # System-wide stats
        sys_stats = self.get_system_statistics()
        print(f"\n📊 System Overview:")
        print(f"  Total Entropy: {sys_stats['total_entropy']:.2f} bits")
        print(f"  Average Player Entropy: {sys_stats['avg_player_entropy']:.2f} bits")
        print(f"  Overall Completion: {sys_stats['completion_percent']:.1f}%")
        
        most_uncertain = sys_stats['most_uncertain_player']
        most_uncertain_name = player_names.get(most_uncertain, f"Player {most_uncertain}") if player_names else f"Player {most_uncertain}"
        print(f"  Most Uncertain: {most_uncertain_name} ({sys_stats['player_entropies'][most_uncertain]:.2f} bits)")
        
        # Per-player stats
        print(f"\n📈 Per-Player Statistics:")
        for player_id in range(self.config.n_players):
            player_name = player_names.get(player_id, f"Player {player_id}") if player_names else f"Player {player_id}"
            stats = self.get_player_statistics(player_id)
            
            marker = "👤" if player_id == self.my_player_id else "  "
            print(f"\n{marker} {player_name}:")
            print(f"     Entropy: {stats['entropy']:.2f} bits (norm: {stats['entropy_normalized']:.2%})")
            print(f"     Certain: {stats['certain_count']}/{self.config.wires_per_player} positions ({stats['progress_percent']:.1f}%)")
            print(f"     Avg Possibilities: {stats['avg_possibilities']:.2f} per position")
        
        print(f"\n{'='*80}")
        
    def _generate_valid_hands(self, player_id: int) -> List[Tuple[Union[int, float], ...]]:
        """
        Generate all valid sorted hands for a player based on current beliefs.
        """
        beliefs = self.belief_model.beliefs[player_id]
        hand_size = self.config.wires_per_player
        valid_hands = []
        
        def backtrack(pos: int, current_hand: List[Union[int, float]], current_counts: Dict[Union[int, float], int]):
            if pos == hand_size:
                valid_hands.append(tuple(current_hand))
                return

            # Determine possible values for this position
            # Must be in beliefs[pos]
            # Must be >= previous value (sorted constraint)
            
            possible_values = sorted(list(beliefs[pos]))
            min_val = current_hand[-1] if pos > 0 else -float('inf')
            
            for val in possible_values:
                if val < min_val:
                    continue
                
                # Check count constraint
                count = current_counts.get(val, 0) + 1
                if count > self.config.get_copies(val):
                    continue
                
                # Recurse
                current_counts[val] = count
                current_hand.append(val)
                backtrack(pos + 1, current_hand, current_counts)
                current_hand.pop()
                current_counts[val] -= 1
                if current_counts[val] == 0:
                    del current_counts[val]

        backtrack(0, [], {})
        return valid_hands

    def get_double_chance_suggestions(self, max_hands: int = 1000000) -> List[Dict]:
        """
        Get suggestions for the 'Double Chance' mechanic.
        Select 2 wires of the same player and a value.
        Success if either wire has that value.
        
        Args:
            max_hands: Maximum number of hands to generate before using approximation
        
        Returns:
            List of dicts with keys: target_id, positions, value, probability, is_certain
        """
        suggestions = []
        my_values = self.get_playable_values()
        if not my_values:
            return []
        
        for target_id in range(self.config.n_players):
            if target_id == self.my_player_id:
                continue
            
            valid_hands = self._generate_valid_hands(target_id)
            print(f"Generated {len(valid_hands)} valid hands for player {target_id}")
            
            if len(valid_hands) > max_hands:
                self._add_approximate_double_chance_suggestions(
                    target_id, my_values, suggestions
                )
            else:
                if not valid_hands:
                    continue
                
                self._add_exact_double_chance_suggestions(
                    target_id, my_values, valid_hands, suggestions
                )
                            
        suggestions.sort(key=lambda x: x['probability'], reverse=True)
        return suggestions

    
    def _add_exact_double_chance_suggestions(
        self, 
        target_id: int, 
        my_values: Set[Union[int, float]], 
        valid_hands: List[Tuple[Union[int, float], ...]], 
        suggestions: List[Dict]
    ):
        """Add suggestions using exact hand enumeration (single-pass optimization)."""
        total_hands = len(valid_hands)
        
        # Single pass through all hands to collect all statistics
        # For each (pos_i, pos_j, value) combination, count successes
        success_counts = {}
        
        for hand in valid_hands:
            # For each pair of positions
            for i in range(self.config.wires_per_player):
                if self.is_position_revealed(target_id, i):
                    continue
                
                for j in range(i + 1, self.config.wires_per_player):
                    if self.is_position_revealed(target_id, j):
                        continue
                    
                    # Check which values from my_values appear at position i or j
                    val_i = hand[i]
                    val_j = hand[j]
                    
                    # If either position has a value we can play, count it
                    for value in my_values:
                        if val_i == value or val_j == value:
                            key = (i, j, value)
                            success_counts[key] = success_counts.get(key, 0) + 1
        
        # Convert counts to suggestions
        for (i, j, value), count in success_counts.items():
            prob = count / total_hands
            suggestions.append({
                'target_id': target_id,
                'positions': (i, j),
                'value': value,
                'probability': prob,
                'is_certain': prob >= 0.999999
            })
    
    def _add_approximate_double_chance_suggestions(
        self, 
        target_id: int, 
        my_values: Set[Union[int, float]], 
        suggestions: List[Dict]
    ):
        """Add suggestions using belief-based approximation for large search spaces."""
        beliefs = self.belief_model.beliefs[target_id]
        
        for i in range(self.config.wires_per_player):
            if self.is_position_revealed(target_id, i):
                continue
            
            for j in range(i + 1, self.config.wires_per_player):
                if self.is_position_revealed(target_id, j):
                    continue
                
                pos_i_beliefs = beliefs[i]
                pos_j_beliefs = beliefs[j]
                
                for value in my_values:
                    # Approximate probability assuming independence (upper bound)
                    # P(value at i OR value at j) ≈ P(value at i) + P(value at j) - P(value at i) * P(value at j)
                    
                    if value not in pos_i_beliefs and value not in pos_j_beliefs:
                        continue
                    
                    prob_i = 1.0 / len(pos_i_beliefs) if value in pos_i_beliefs else 0.0
                    prob_j = 1.0 / len(pos_j_beliefs) if value in pos_j_beliefs else 0.0
                    
                    # Independence assumption (may overestimate)
                    prob = prob_i + prob_j - (prob_i * prob_j)
                    
                    if prob > 0:
                        suggestions.append({
                            'target_id': target_id,
                            'positions': (i, j),
                            'value': value,
                            'probability': prob,
                            'is_certain': False  # Never certain with approximation
                        })

    def print_double_chance_suggestions(self, player_names: Dict[int, str] = None):
        """
        Print suggestions for the Double Chance mechanic.
        """
        suggestions = self.get_double_chance_suggestions()
        
        print(f"\n{'='*80}")
        print(f"DOUBLE CHANCE SUGGESTIONS")
        print(f"{'='*80}")
        
        if not suggestions:
            print("No suggestions available.")
            print(f"{'='*80}")
            return

        # Filter for high probability ones to avoid spam
        
        certain = [s for s in suggestions if s['is_certain']]
        uncertain = [s for s in suggestions if not s['is_certain']]
        
        if certain:
            print(f"\n✓ CERTAIN DOUBLE CHANCES ({len(certain)}):")
            for s in certain[:10]:
                target_name = player_names.get(s['target_id'], f"Player {s['target_id']}") if player_names else f"Player {s['target_id']}"
                p1, p2 = s['positions']
                print(f"    → Call {target_name}[{p1+1} or {p2+1}] = {s['value']}")
            if len(certain) > 10:
                print(f"    ... and {len(certain) - 10} more certain calls")
        
        if uncertain:
            print(f"\n⚠️  BEST UNCERTAIN DOUBLE CHANCES:")
            # Show top 5
            for s in uncertain[:5]:
                target_name = player_names.get(s['target_id'], f"Player {s['target_id']}") if player_names else f"Player {s['target_id']}"
                p1, p2 = s['positions']
                print(f"    → Call {target_name}[{p1+1} or {p2+1}] = {s['value']} (Prob: {s['probability']:.1%})")
        
        print(f"{'='*80}")
