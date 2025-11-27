from typing import Dict, Set, List, Optional, Union, Tuple
from src.belief.belief_model import BeliefModel
from src.data_structures import GameObservation, SignalCopyCountRecord, SignalAdjacentRecord
from config.game_config import GameConfig
import collections
from concurrent.futures import ProcessPoolExecutor
from src.belief.global_belief_utils import generate_signatures_worker
import multiprocessing as mp

COMPLEXITY_THRESHOLD = 10000

_executor = None
_n_workers = max(1, mp.cpu_count() - 1)

def get_executor():
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(max_workers=_n_workers)
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
        
        # Storage for valid hands (actual value tuples, not signatures)
        # Populated after successful global filtering
        self.valid_hands: Dict[int, List[Tuple]] = {}
        
        super().__init__(observation, config)

    def apply_filters(self):
        """
        Override the iterative filter application with the Global Consistency Algorithm.
        Uses complexity heuristic to decide whether to run global solver or fall back.
        """
        # Phase 1: Generate local signatures (fast)
        V = self._generate_local_signatures()
        if V is None:
            super().apply_filters()
            return
        
        # Complexity heuristic: check total signatures before expensive global filtering
        total_signatures = sum(len(s) for s in V)
        if total_signatures > COMPLEXITY_THRESHOLD:
            print(f"⚠️  Complexity too high ({total_signatures} signatures), falling back to iterative filters")
            super().apply_filters()
            return
        
        # Phase 2 & 3: Global filtering and projection
        success = self._solve_global_consistency(V)
        
        if success:
            self._update_value_trackers()
            if self.config.playing_irl:
                try:
                    from config.game_config import BELIEF_FOLDER, PLAYER_NAMES
                    player_names_dict = {i: name for i, name in enumerate(PLAYER_NAMES)}
                    self.save_to_folder(BELIEF_FOLDER, player_names_dict)
                except Exception as e:
                    print(f"Warning: Failed to auto-save belief state: {e}")
        else:
            super().apply_filters()

    def _generate_local_signatures(self) -> Optional[List[Set[Tuple[int, ...]]]]:
        """
        Phase 1: Generate local candidate signatures for each player.
        Returns None if generation fails.
        """
        N = self.config.n_players
        
        V: List[Set[Tuple[int, ...]]] = []
        futures = []
        cache_keys = []
        
        for i in range(N):
            min_counts = self._get_min_counts(i) 
            cache_key = self._get_cache_key(i, min_counts)
            cache_keys.append(cache_key)
            
            if cache_key in self._signature_cache:
                V.append(self._signature_cache[cache_key])
                futures.append(None)
            else:
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
                V.append(None)

        for i, f in enumerate(futures):
            if f is not None:
                sigs = f.result()
                if not sigs:
                    print(f"CRITICAL: No valid hands found for player {i}")
                    return None
                V[i] = sigs
                self._signature_cache[cache_keys[i]] = sigs

        return V

    def _solve_global_consistency(self, V: List[Set[Tuple[int, ...]]]) -> bool:
        """
        Phase 2 & 3: Forward-backward global filtering and projection.
        Also stores valid hands for external use.
        Returns True on success, False on failure.
        """
        N = self.config.n_players
        K = self.K
        total_deck = self.total_deck

        # --- Phase 2: Forward Pass (Alpha) - Parallelized ---
        zero_vector = tuple([0] * K)
        Alpha: List[Set[Tuple[int, ...]]] = [set() for _ in range(N + 1)]
        Alpha[0].add(zero_vector)

        for i in range(N):
            if not Alpha[i]:
                print(f"CRITICAL: Alpha[{i}] is empty. Impossible state.")
                return False
            
            # Parallelize: split Alpha[i] across workers
            alpha_list = list(Alpha[i])
            V_i = V[i]
            
            if len(alpha_list) * len(V_i) > 1000:
                # Worth parallelizing
                chunk_size = max(1, len(alpha_list) // _n_workers)
                chunks = [alpha_list[j:j+chunk_size] for j in range(0, len(alpha_list), chunk_size)]
                
                from src.belief.global_belief_utils import forward_pass_worker
                futures = [
                    get_executor().submit(forward_pass_worker, chunk, V_i, total_deck)
                    for chunk in chunks
                ]
                
                new_alpha = set()
                for f in futures:
                    new_alpha.update(f.result())
                Alpha[i+1] = new_alpha
            else:
                # Sequential for small sets
                for prev_res in Alpha[i]:
                    for sig in V_i:
                        new_res = tuple(a + b for a, b in zip(prev_res, sig))
                        if all(x <= y for x, y in zip(new_res, total_deck)):
                            Alpha[i+1].add(new_res)
        
        if total_deck not in Alpha[N]:
            print("CRITICAL: Global resource constraint not met (Total Deck not reachable).")
            return False

        # --- Backward Pass (Beta) - Parallelized ---
        Beta: List[Set[Tuple[int, ...]]] = [set() for _ in range(N + 1)]
        Beta[N].add(zero_vector)

        for i in range(N - 1, -1, -1):
            beta_list = list(Beta[i+1])
            V_i = V[i]
            
            if len(beta_list) * len(V_i) > 1000:
                chunk_size = max(1, len(beta_list) // _n_workers)
                chunks = [beta_list[j:j+chunk_size] for j in range(0, len(beta_list), chunk_size)]
                
                from src.belief.global_belief_utils import backward_pass_worker
                futures = [
                    get_executor().submit(backward_pass_worker, chunk, V_i, total_deck)
                    for chunk in chunks
                ]
                
                new_beta = set()
                for f in futures:
                    new_beta.update(f.result())
                Beta[i] = new_beta
            else:
                for needed_res in Beta[i+1]:
                    for sig in V_i:
                        total_needed = tuple(a + b for a, b in zip(needed_res, sig))
                        if all(x <= y for x, y in zip(total_needed, total_deck)):
                            Beta[i].add(total_needed)

        # --- Phase 3: Projection - Parallelized ---
        from src.belief.global_belief_utils import filter_signatures_and_get_hands_worker
        
        futures = []
        for p in range(N):
            args = (
                V[p], 
                Alpha[p], 
                Beta[p+1], 
                total_deck, 
                self.sorted_values, 
                self.config.wires_per_player
            )
            futures.append(get_executor().submit(filter_signatures_and_get_hands_worker, *args))
        
        results = [f.result() for f in futures]
        
        for p, (new_domains, valid_hands) in enumerate(results):
            self.valid_hands[p] = valid_hands
            
            for pos in range(self.config.wires_per_player):
                self.beliefs[p][pos] &= new_domains[pos]
                
                if not self.beliefs[p][pos]:
                    print(f"CRITICAL: Belief for P{p} Pos{pos} became empty during projection!")
        
        return True

    def _get_min_counts(self, player_id: int) -> Dict[Union[int, float], int]:
        """
        Compute the minimum counts for each value for the given player,
        based on known cards and called values.
        """
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
        
        # Deep copy valid_hands
        new_model.valid_hands = {p: list(hands) for p, hands in self.valid_hands.items()}
        
        return new_model

    def get_valid_hands(self, player_id: int) -> List[Tuple]:
        """
        Get the list of valid hands for a player.
        If global filtering was used, returns the cached valid hands.
        Otherwise, generates them using local constraints only.
        """
        if player_id in self.valid_hands and self.valid_hands[player_id]:
            return self.valid_hands[player_id]
        
        # Fallback: generate hands locally (without global constraint)
        return self._generate_hands_local(player_id)
    
    def _generate_hands_local(self, player_id: int) -> List[Tuple]:
        """
        Generate valid hands for a player using only local constraints.
        Used as fallback when global filtering was not performed.
        """
        beliefs = self.beliefs[player_id]
        hand_size = self.config.wires_per_player
        valid_hands = []
        
        def backtrack(pos: int, current_hand: List, current_counts: Dict):
            if pos == hand_size:
                valid_hands.append(tuple(current_hand))
                return

            possible_values = sorted(list(beliefs[pos]))
            min_val = current_hand[-1] if pos > 0 else -float('inf')
            
            for val in possible_values:
                if val < min_val:
                    continue
                
                count = current_counts.get(val, 0) + 1
                if count > self.config.get_copies(val):
                    continue
                
                current_counts[val] = count
                current_hand.append(val)
                backtrack(pos + 1, current_hand, current_counts)
                current_hand.pop()
                current_counts[val] -= 1
                if current_counts[val] == 0:
                    del current_counts[val]

        backtrack(0, [], {})
        return valid_hands

