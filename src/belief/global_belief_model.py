from typing import Dict, Set, List, Optional, Union, Tuple
from src.belief.belief_model import BeliefModel
from src.data_structures import GameObservation, SignalCopyCountRecord, SignalAdjacentRecord
from config.game_config import GameConfig
import collections
from concurrent.futures import ProcessPoolExecutor
from src.belief.global_belief_utils import generate_signatures_worker, filter_signatures_worker

# Global executor to avoid overhead of creating processes repeatedly
_executor = None

def get_executor():
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor()
    return _executor

class GlobalBeliefModel(BeliefModel):
    """
    A BeliefModel that uses a global consistency algorithm (Propagated Dynamic Programming)
    to compute the minimal domain for every card slot.
    
    This replaces the iterative local filters with a single global solver that enforces:
    1. Sorted hands (Local)
    2. Known values and negative constraints (Local)
    3. "Called" value existence constraints (Local)
    4. Global resource limits (Global)
    """
    
    def __init__(self, observation: GameObservation, config: GameConfig):
        # Initialize mappings before super().__init__ because it might call filters
        self.sorted_values = sorted(config.wire_values)
        self.val_to_idx = {v: i for i, v in enumerate(self.sorted_values)}
        self.idx_to_val = {i: v for i, v in enumerate(self.sorted_values)}
        self.K = len(self.sorted_values)
        
        # Precompute total deck vector
        total_deck = [0] * self.K
        for v in self.sorted_values:
            total_deck[self.val_to_idx[v]] = config.get_copies(v)
        self.total_deck = tuple(total_deck)
        
        # Constraint tracking for copy count signals
        # Key: (player_id, position), Value: required copy count (1, 2, or 3)
        self.copy_count_constraints: Dict[Tuple[int, int], int] = {}
        
        # Constraint tracking for adjacent signals
        # Key: (player_id, pos1, pos2), Value: is_equal (True if same, False if different)
        self.adjacent_constraints: Dict[Tuple[int, int, int], bool] = {}
        
        # Cache for signatures
        # Key: (player_id, belief_hash, constraint_hash) -> Set[Tuple[int, ...]]
        self._signature_cache = {}
        
        super().__init__(observation, config)

    def apply_filters(self):
        """
        Override the iterative filter application with the Global Consistency Algorithm.
        """
        # Run the global solver
        self._solve_global_consistency()
        
        # Update value trackers based on new certainties
        self._update_value_trackers()

    def _solve_global_consistency(self):
        """
        Executes the 3-phase algorithm:
        1. Local Candidate Generation (Signatures)
        2. Forward-Backward Global Filtering
        3. Projection to Minimal Domains
        """
        N = self.config.n_players
        
        # --- Phase 1: Local Generation ---
        # V[i] stores set of valid signatures (tuples) for player i
        V: List[Set[Tuple[int, ...]]] = []
        
        futures = []
        cache_keys = []
        
        for i in range(N):
            min_counts = self._get_min_counts(i)
            cache_key = self._get_cache_key(i, min_counts)
            cache_keys.append(cache_key)
            
            if cache_key in self._signature_cache:
                # Use cached result (dummy future)
                V.append(self._signature_cache[cache_key])
                futures.append(None)
            else:
                # Submit task
                args = (
                    i, 
                    self.config.wires_per_player, 
                    self.sorted_values, 
                    self.val_to_idx, 
                    self.config.wire_distribution, 
                    self.beliefs[i], 
                    self.copy_count_constraints, 
                    self.adjacent_constraints, 
                    min_counts, 
                    self.K
                )
                futures.append(get_executor().submit(generate_signatures_worker, *args))
                V.append(None) # Placeholder

        # Collect results
        for i, f in enumerate(futures):
            if f is not None:
                sigs = f.result()
                if not sigs:
                    print(f"CRITICAL: No valid hands found for player {i}")
                    return
                V[i] = sigs
                # Update cache
                self._signature_cache[cache_keys[i]] = sigs

        # --- Phase 2: Forward Pass (Alpha) ---
        # Alpha[i] = set of consumed resource vectors after player i (0 to i-1)
        # Alpha[0] is {0-vector}
        # Alpha[N] should contain Total_Deck
        
        zero_vector = tuple([0] * self.K)
        Alpha: List[Set[Tuple[int, ...]]] = [set() for _ in range(N + 1)]
        Alpha[0].add(zero_vector)

        for i in range(N):
            # Pruning: If Alpha[i] is empty, we can't proceed
            if not Alpha[i]:
                print(f"CRITICAL: Alpha[{i}] is empty. Impossible state.")
                return

            for prev_res in Alpha[i]:
                for sig in V[i]:
                    # Vector addition
                    new_res = tuple(a + b for a, b in zip(prev_res, sig))
                    
                    # Check if valid (<= total_deck)
                    if all(x <= y for x, y in zip(new_res, self.total_deck)):
                        Alpha[i+1].add(new_res)
        
        # Check global consistency
        if self.total_deck not in Alpha[N]:
            print("CRITICAL: Global resource constraint not met (Total Deck not reachable).")
            # This implies the current beliefs/constraints are contradictory
            return

        # --- Phase 2: Backward Pass (Beta) ---
        # Beta[i] = set of resource vectors NEEDED by players i...N-1
        # Beta[N] is {0-vector} (needed by no one)
        # Note: Indexing aligns such that Beta[i] is what is needed FROM i onwards
        
        Beta: List[Set[Tuple[int, ...]]] = [set() for _ in range(N + 1)]
        Beta[N].add(zero_vector)

        for i in range(N - 1, -1, -1): # N-1 down to 0
            for needed_res in Beta[i+1]:
                for sig in V[i]:
                    # Vector addition: needed_res + sig
                    total_needed = tuple(a + b for a, b in zip(needed_res, sig))
                    
                    if all(x <= y for x, y in zip(total_needed, self.total_deck)):
                        Beta[i].add(total_needed)

        # --- Phase 3: Projection ---
        # For each player, find globally valid signatures and project to domains
        
        futures = []
        for p in range(N):
            args = (
                V[p], 
                Alpha[p], 
                Beta[p+1], 
                self.total_deck, 
                self.sorted_values, 
                self.config.wires_per_player
            )
            futures.append(get_executor().submit(filter_signatures_worker, *args))
            
        results = [f.result() for f in futures]
        
        for p, new_domains in enumerate(results):
            for pos in range(self.config.wires_per_player):
                # Intersect with existing beliefs
                self.beliefs[p][pos] &= new_domains[pos]
                
                if not self.beliefs[p][pos]:
                    print(f"CRITICAL: Belief for P{p} Pos{pos} became empty during projection!")

    def _get_min_counts(self, player_id: int) -> Dict[Union[int, float], int]:
        min_counts = collections.defaultdict(int)
        hand_size = self.config.wires_per_player
        player_beliefs = self.beliefs[player_id]
        
        for pos in range(hand_size):
            if len(player_beliefs[pos]) == 1:
                val = list(player_beliefs[pos])[0]
                min_counts[val] += 1
                
        for val, tracker in self.value_trackers.items():
            if player_id in tracker.called:
                min_counts[val] += 1
        return dict(min_counts)

    def _get_cache_key(self, player_id: int, min_counts: Dict):
        # Hash beliefs
        beliefs_tuple = tuple(frozenset(self.beliefs[player_id][pos]) for pos in range(self.config.wires_per_player))
        
        # Hash constraints
        # Copy count constraints for this player
        cc_constraints = tuple(sorted((pos, count) for (pid, pos), count in self.copy_count_constraints.items() if pid == player_id))
        
        # Adjacent constraints for this player
        adj_constraints = tuple(sorted(((p1, p2), eq) for (pid, p1, p2), eq in self.adjacent_constraints.items() if pid == player_id))
        
        # Min counts
        mc_tuple = tuple(sorted(min_counts.items()))
        
        return (player_id, beliefs_tuple, cc_constraints, adj_constraints, mc_tuple)

    
    def process_copy_count_signal(self, signal_record: SignalCopyCountRecord):
        """
        Override to handle copy count signals with GlobalBeliefModel.
        
        Stores the constraint and enforces it during signature generation.
        The global consistency algorithm will natively respect this constraint.
        
        Args:
            signal_record: The copy count signal to process
        """
        player_id = signal_record.player_id
        position = signal_record.position
        copy_count = signal_record.copy_count
        
        # Store the constraint for use in signature generation
        self.copy_count_constraints[(player_id, position)] = copy_count
        
        # Also apply immediate filtering to beliefs
        current_beliefs = self.beliefs[player_id][position]
        filtered_beliefs = {v for v in current_beliefs if self.config.wire_distribution[v] == copy_count}
        
        if filtered_beliefs:
            self.beliefs[player_id][position] = filtered_beliefs
        
        # Run global solver to propagate constraints
        if self.config.auto_filter:
            self.apply_filters()
    
    def process_adjacent_signal(self, signal_record: SignalAdjacentRecord):
        """
        Override to handle adjacent position signals with GlobalBeliefModel.
        
        Stores the constraint and enforces it during signature generation.
        The global consistency algorithm will natively respect this constraint.
        
        Args:
            signal_record: The adjacent signal to process
        """
        player_id = signal_record.player_id
        pos1 = signal_record.position1
        pos2 = signal_record.position2
        is_equal = signal_record.is_equal
        
        # Store the constraint for use in signature generation
        # Normalize to always store (smaller_pos, larger_pos)
        min_pos, max_pos = min(pos1, pos2), max(pos1, pos2)
        self.adjacent_constraints[(player_id, min_pos, max_pos)] = is_equal
        
        # Also apply immediate filtering to beliefs
        beliefs1 = self.beliefs[player_id][pos1]
        beliefs2 = self.beliefs[player_id][pos2]
        
        if is_equal:
            # Both positions must have the same value
            common_values = beliefs1 & beliefs2
            if common_values:
                self.beliefs[player_id][pos1] = common_values
                self.beliefs[player_id][pos2] = common_values
        else:
            # Positions have different values - filter if either is certain
            if len(beliefs2) == 1:
                certain_value = next(iter(beliefs2))
                self.beliefs[player_id][pos1] = beliefs1 - {certain_value}
            if len(beliefs1) == 1:
                certain_value = next(iter(beliefs1))
                self.beliefs[player_id][pos2] = beliefs2 - {certain_value}
        
        # Run global solver to propagate constraints
        if self.config.auto_filter:
            self.apply_filters()

