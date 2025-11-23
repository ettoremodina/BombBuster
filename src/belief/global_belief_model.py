from typing import Dict, Set, List, Optional, Union, Tuple
from src.belief.belief_model import BeliefModel
from src.data_structures import GameObservation, SignalCopyCountRecord, SignalAdjacentRecord
from config.game_config import GameConfig
import collections
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from src.belief.global_belief_utils import generate_signatures_worker, filter_signatures_worker
import time

TIME_OUT = 5.0

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
        
        # Cache for signatures
        # Key: (player_id, belief_hash, constraint_hash) -> Set[Tuple[int, ...]]
        self._signature_cache = {}
        
        super().__init__(observation, config)

    def apply_filters(self):
        """
        Override the iterative filter application with the Global Consistency Algorithm.
        Falls back to parent's iterative filters if global solver takes too long (>10s).
        """
        start_time = time.time()
        timeout_seconds = TIME_OUT
        
        try:
            # Run the global solver with timeout monitoring
            self._solve_global_consistency_with_timeout(timeout_seconds, start_time)
            
            elapsed = time.time() - start_time
            if elapsed >= timeout_seconds:
                # Timeout occurred, fall back to parent method
                print(f"⚠️  Global solver timed out after {elapsed:.2f}s, falling back to iterative filters")
                super().apply_filters()
            else:
                # Success - update value trackers and save
                self._update_value_trackers()
                # Save state if playing IRL
                if self.config.playing_irl:
                    try:
                        # Import here to avoid circular imports
                        from config.game_config import BELIEF_FOLDER, PLAYER_NAMES
                        player_names_dict = {i: name for i, name in enumerate(PLAYER_NAMES)}
                        self.save_to_folder(BELIEF_FOLDER, player_names_dict)
                    except Exception as e:
                        print(f"Warning: Failed to auto-save belief state: {e}")
        except TimeoutError:
            # Explicit timeout from futures
            print(f"⚠️  Global solver timed out, falling back to iterative filters")
            super().apply_filters()
        except Exception as e:
            # Any other error, fall back to parent method
            print(f"⚠️  Global solver failed with error: {e}, falling back to iterative filters")
            super().apply_filters()

    def _solve_global_consistency_with_timeout(self, timeout_seconds: float, start_time: float):
        """
        Executes the 3-phase algorithm with timeout checking:
        1. Local Candidate Generation (Signatures)
        2. Forward-Backward Global Filtering
        3. Projection to Minimal Domains
        
        Raises TimeoutError if execution exceeds timeout_seconds.
        """
        N = self.config.n_players
        
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("Global solver exceeded timeout")
        
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

        # Collect results with timeout
        for i, f in enumerate(futures):
            if f is not None:
                # Check timeout before waiting
                remaining_time = timeout_seconds - (time.time() - start_time)
                if remaining_time <= 0:
                    raise TimeoutError("Global solver exceeded timeout during signature generation")
                
                try:
                    sigs = f.result(timeout=remaining_time)
                except TimeoutError:
                    raise TimeoutError("Global solver exceeded timeout during signature generation")
                
                if not sigs:
                    print(f"CRITICAL: No valid hands found for player {i}")
                    return
                V[i] = sigs
                # Update cache
                self._signature_cache[cache_keys[i]] = sigs

        # Check timeout
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("Global solver exceeded timeout")

        # --- Phase 2: Forward Pass (Alpha) ---
        # Alpha[i] = set of consumed resource vectors after player i (0 to i-1)
        # Alpha[0] is {0-vector}
        # Alpha[N] should contain Total_Deck
        
        zero_vector = tuple([0] * self.K)
        Alpha: List[Set[Tuple[int, ...]]] = [set() for _ in range(N + 1)]
        Alpha[0].add(zero_vector)

        for i in range(N):
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError("Global solver exceeded timeout during forward pass")
            
            # Pruning: If Alpha[i] is empty, we can't proceed
            if not Alpha[i]:
                print(f"CRITICAL: Alpha[{i}] is empty. Impossible state.")
                return

            for prev_res in Alpha[i]:
                for sig in V[i]:
                    if time.time() - start_time > timeout_seconds:
                        raise TimeoutError("Global solver exceeded timeout during forward pass")
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

        # Check timeout
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("Global solver exceeded timeout")

        # --- Phase 2: Backward Pass (Beta) ---
        # Beta[i] = set of resource vectors NEEDED by players i...N-1
        # Beta[N] is {0-vector} (needed by no one)
        # Note: Indexing aligns such that Beta[i] is what is needed FROM i onwards
        
        Beta: List[Set[Tuple[int, ...]]] = [set() for _ in range(N + 1)]
        Beta[N].add(zero_vector)

        for i in range(N - 1, -1, -1): # N-1 down to 0
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError("Global solver exceeded timeout during backward pass")
            
            for needed_res in Beta[i+1]:
                for sig in V[i]:
                    # Vector addition: needed_res + sig
                    total_needed = tuple(a + b for a, b in zip(needed_res, sig))
                    
                    if all(x <= y for x, y in zip(total_needed, self.total_deck)):
                        Beta[i].add(total_needed)

        # Check timeout
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("Global solver exceeded timeout")

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
        
        # Collect results with timeout
        results = []
        for f in futures:
            remaining_time = timeout_seconds - (time.time() - start_time)
            if remaining_time <= 0:
                raise TimeoutError("Global solver exceeded timeout during projection")
            
            try:
                results.append(f.result(timeout=remaining_time))
            except TimeoutError:
                raise TimeoutError("Global solver exceeded timeout during projection")
        
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


    def clone(self) -> 'GlobalBeliefModel':
        """
        Create a deep copy of the global belief model.
        """
        new_model = super().clone()
        
        # Copy GlobalBeliefModel specific attributes
        new_model.sorted_values = self.sorted_values
        new_model.val_to_idx = self.val_to_idx
        new_model.idx_to_val = self.idx_to_val
        new_model.K = self.K
        new_model.total_deck = self.total_deck
        
        # Deep copy constraints
        new_model.copy_count_constraints = self.copy_count_constraints.copy()
        new_model.adjacent_constraints = self.adjacent_constraints.copy()
        
        # Share the cache (it's safe as keys are hashes of state)
        new_model._signature_cache = self._signature_cache
        
        return new_model

