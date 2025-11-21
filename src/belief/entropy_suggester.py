"""
Entropy-based call suggester for BombBuster.
Simulates potential calls to maximize information gain (minimize system entropy).
"""

import time
import math
from typing import Dict, List, Tuple, Optional, Union
from concurrent.futures import ProcessPoolExecutor, as_completed
from src.belief.belief_model import BeliefModel
from src.statistics import GameStatistics
from config.game_config import GameConfig


def _analyze_single_candidate(belief_model, config, target_id, position, value, num_possibilities, current_entropy):
    """
    Analyze a single candidate call (designed to be run in parallel).
    This function is at module level to support pickling for multiprocessing.
    
    Args:
        belief_model: The belief model to clone and simulate
        config: Game configuration
        target_id: Target player ID
        position: Position to call
        value: Value to call
        num_possibilities: Number of possible values at this position
        current_entropy: Current system entropy
        
    Returns:
        Dict with analysis results for this candidate
    """
    # Probability of success (assuming uniform distribution)
    p_success = 1.0 / num_possibilities
    p_failure = 1.0 - p_success
    
    # Simulate Success
    sim_model_success = belief_model.clone()
    sim_model_success.beliefs[target_id][position] = {value}
    sim_model_success.apply_filters()
    stats_success = GameStatistics(sim_model_success, config)
    h_success = stats_success.calculate_system_entropy()
    
    # Simulate Failure
    sim_model_failure = belief_model.clone()
    if value in sim_model_failure.beliefs[target_id][position]:
        sim_model_failure.beliefs[target_id][position].remove(value)
    sim_model_failure.apply_filters()
    stats_failure = GameStatistics(sim_model_failure, config)
    h_failure = stats_failure.calculate_system_entropy()
    
    # Expected Entropy
    expected_entropy = (p_success * h_success) + (p_failure * h_failure)
    info_gain = current_entropy - expected_entropy
    
    return {
        'call': (target_id, position, value),
        'expected_entropy': expected_entropy,
        'info_gain': info_gain,
        'h_success': h_success,
        'h_failure': h_failure,
        'p_success': p_success
    }


class EntropySuggester:
    """
    Suggests calls by simulating their outcome and calculating Expected Information Gain.
    
    Algorithm:
    1. Identify candidate calls (uncertain positions).
    2. For each candidate:
       a. Simulate SUCCESS (Value is correct):
          - Clone model, set value, propagate constraints.
          - Calculate resulting system entropy (H_success).
       b. Simulate FAILURE (Value is incorrect):
          - Clone model, remove value, propagate constraints.
          - Calculate resulting system entropy (H_failure).
       c. Calculate Expected Entropy:
          E[H] = P(success) * H_success + P(failure) * H_failure
    3. Return call with minimum Expected Entropy.
    """
    
    def __init__(self, belief_model: BeliefModel, config: GameConfig):
        self.belief_model = belief_model
        self.config = config
        # We use a temporary stats object just to access helper methods like get_playable_values
        # Ideally those should be in BeliefModel or a shared utils, but reusing GameStatistics is fine.
        self.stats = GameStatistics(belief_model, config)
        
    def suggest_best_call(self, max_uncertainty: int = 3, progress_callback=None, use_parallel: bool = True, max_workers: int = None) -> Dict:
        """
        Find the call that minimizes expected system entropy.
        
        Args:
            max_uncertainty: Only consider positions with <= this many possibilities.
                             Lower values are faster but might miss high-impact calls on very uncertain positions.
            progress_callback: Optional callable(current, total, message) for progress updates.
            use_parallel: Whether to use parallel processing (default True). Set to False for debugging.
            max_workers: Number of parallel workers. If None, uses CPU count.
                             
        Returns:
            Dict containing:
            - 'best_call': (target_id, position, value)
            - 'expected_entropy': The expected entropy after this call
            - 'information_gain': Current Entropy - Expected Entropy
            - 'candidates_analyzed': Number of calls simulated
            - 'time_taken': Execution time in seconds
            - 'details': List of all analyzed calls with their scores
        """
        start_time = time.time()
        
        # 1. Get candidate calls
        candidates = self._get_candidate_calls(max_uncertainty)
        
        if not candidates:
            return {
                'best_call': None,
                'expected_entropy': 0,
                'information_gain': 0,
                'time_taken': time.time() - start_time,
                'candidates_analyzed': 0,
                'details': []
            }
            
        current_entropy = self.stats.calculate_system_entropy()
        total_candidates = len(candidates)
        
        if use_parallel:
            results = self._analyze_candidates_parallel(candidates, current_entropy, total_candidates, progress_callback, max_workers)
        else:
            results = self._analyze_candidates_sequential(candidates, current_entropy, total_candidates, progress_callback)
        
        # Final progress update
        if progress_callback:
            progress_callback(total_candidates, total_candidates, "Analysis complete")
            
        # 3. Find best call (max information gain / min expected entropy)
        # Sort by info gain descending
        results.sort(key=lambda x: x['info_gain'], reverse=True)
        
        best_result = results[0] if results else None
        
        return {
            'best_call': best_result['call'] if best_result else None,
            'expected_entropy': best_result['expected_entropy'] if best_result else 0,
            'information_gain': best_result['info_gain'] if best_result else 0,
            'candidates_analyzed': len(results),
            'time_taken': time.time() - start_time,
            'details': results
        }
    
    def _get_candidate_calls(self, max_uncertainty: int) -> List[Tuple[int, int, Union[int, float], int]]:
        """
        Get list of valid calls to analyze.
        Filters by:
        - Not my own wire
        - Not already revealed
        - Uncertainty <= max_uncertainty
        - Value is in my playable values (I must have the value to call it)
        """
        candidates = []
        my_playable_values = self.stats.get_playable_values()
        
        for player_id in range(self.config.n_players):
            if player_id == self.belief_model.my_player_id:
                continue
                
            for position in range(self.config.wires_per_player):
                # Skip revealed positions
                if self.stats.is_position_revealed(player_id, position):
                    continue
                
                possible_values = self.belief_model.beliefs[player_id][position]
                n = len(possible_values & my_playable_values)
                num_possibilities = len(possible_values)
                
                # Skip if certain (entropy 0, no gain to analyze) or too uncertain
                if n > max_uncertainty:
                    continue
                
                for value in possible_values:
                    # I can only call values I have
                    if value in my_playable_values:
                        candidates.append((player_id, position, value, num_possibilities))
                        
        return candidates
    
    def _analyze_candidates_sequential(self, candidates, current_entropy, total_candidates, progress_callback):
        """Sequential analysis (original implementation)."""
        results = []
        
        for idx, (target_id, position, value, num_possibilities) in enumerate(candidates):
            # Update progress
            if progress_callback:
                progress_callback(idx, total_candidates, f"Analyzing call {idx+1}/{total_candidates}")
            
            # Probability of success (assuming uniform distribution)
            p_success = 1.0 / num_possibilities
            p_failure = 1.0 - p_success
            
            # Simulate Success
            h_success = self._simulate_outcome(target_id, position, value, is_success=True)
            
            # Simulate Failure
            h_failure = self._simulate_outcome(target_id, position, value, is_success=False)
            
            # Expected Entropy
            expected_entropy = (p_success * h_success) + (p_failure * h_failure)
            info_gain = current_entropy - expected_entropy
            
            results.append({
                'call': (target_id, position, value),
                'expected_entropy': expected_entropy,
                'info_gain': info_gain,
                'h_success': h_success,
                'h_failure': h_failure,
                'p_success': p_success
            })
        
        return results
    
    def _analyze_candidates_parallel(self, candidates, current_entropy, total_candidates, progress_callback, max_workers):
        """Parallel analysis using ProcessPoolExecutor."""
        results = []
        completed_count = 0
        
        # Prepare arguments for parallel processing
        # Each worker needs: belief_model, config, target_id, position, value, num_possibilities, current_entropy
        tasks = []
        for target_id, position, value, num_possibilities in candidates:
            tasks.append((self.belief_model, self.config, target_id, position, value, num_possibilities, current_entropy))
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_idx = {executor.submit(_analyze_single_candidate, *task): idx for idx, task in enumerate(tasks)}
            
            # Process completed tasks as they finish
            for future in as_completed(future_to_idx):
                result = future.result()
                results.append(result)
                
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count, total_candidates, f"Analyzed {completed_count}/{total_candidates} calls")
        
        return results

    def _simulate_outcome(self, target_id: int, position: int, value: Union[int, float], is_success: bool) -> float:
        """
        Run a simulation for a specific outcome and return the resulting system entropy.
        """
        # Clone the model
        sim_model = self.belief_model.clone()
        
        # Apply the hypothetical constraint
        if is_success:
            # Constraint: Position IS value
            sim_model.beliefs[target_id][position] = {value}
            # Also update value tracker to reflect this "virtual" revelation/certainty
            # Note: In a real game, a successful call reveals the card.
            # We should simulate the revelation effects if possible, but just setting belief is the core.
            # The GlobalBeliefModel will pick up the count constraint from the belief.
        else:
            # Constraint: Position IS NOT value
            if value in sim_model.beliefs[target_id][position]:
                sim_model.beliefs[target_id][position].remove(value)
        
        # Propagate constraints
        # This is where the heavy lifting happens (GlobalBeliefModel solver)
        sim_model.apply_filters()
        
        # Calculate entropy of the resulting state
        sim_stats = GameStatistics(sim_model, self.config)
        return sim_stats.calculate_system_entropy()
