from typing import Dict, Set, List, Optional, Union, Tuple
from src.belief.belief_model import BeliefModel
from src.data_structures import GameObservation, SignalCopyCountRecord, SignalAdjacentRecord
from config.game_config import GameConfig
import collections

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
        
        for i in range(N):
            sigs = self._generate_valid_signatures(i)
            if not sigs:
                # Contradiction detected for this player
                # In a real game, this shouldn't happen unless state is inconsistent
                print(f"CRITICAL: No valid hands found for player {i}")
                return
            V.append(sigs)

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
        
        for p in range(N):
            valid_signatures = set()
            
            # A signature 'sig' for player 'p' is valid if:
            # exists prev in Alpha[p], next in Beta[p+1] s.t. prev + sig + next == Total
            # => prev + next == Total - sig
            
            # Optimization: Iterate sigs, calculate remainder, check if split exists
            for sig in V[p]:
                remainder = tuple(t - s for t, s in zip(self.total_deck, sig))
                
                # Check if remainder can be formed by Alpha[p] + Beta[p+1]
                # This is still potentially O(|Alpha| * |Beta|), which can be large.
                # But usually Alpha and Beta are sparse.
                
                is_valid = False
                # We need to find if ANY pair sums to remainder
                # Iterate the smaller set for efficiency
                if len(Alpha[p]) < len(Beta[p+1]):
                    for prev in Alpha[p]:
                        needed_next = tuple(r - a for r, a in zip(remainder, prev))
                        if needed_next in Beta[p+1]:
                            is_valid = True
                            break
                else:
                    for next_vec in Beta[p+1]:
                        needed_prev = tuple(r - n for r, n in zip(remainder, next_vec))
                        if needed_prev in Alpha[p]:
                            is_valid = True
                            break
                
                if is_valid:
                    valid_signatures.add(sig)
            
            # Now project valid signatures back to domains
            self._project_signatures_to_beliefs(p, valid_signatures)

    def _generate_valid_signatures(self, player_id: int) -> Set[Tuple[int, ...]]:
        """
        Generates all valid signatures (resource vectors) for a player
        given their local constraints (beliefs, called values).
        """
        valid_sigs = set()
        
        # Constraints
        hand_size = self.config.wires_per_player
        player_beliefs = self.beliefs[player_id]
        
        # "Called" constraints: Minimum count for specific values
        min_counts = collections.defaultdict(int)
        
        # 1. Count from certain positions
        for pos in range(hand_size):
            if len(player_beliefs[pos]) == 1:
                val = list(player_beliefs[pos])[0]
                min_counts[val] += 1
        
        # 2. Add "called" but unlocated copies
        # If player is in 'called' list for a value, they must have an EXTRA copy
        # beyond what is already certain/revealed?
        # Based on ValueTracker logic: 'called' means "has value, position unknown".
        # 'certain' means "has value, position known".
        # 'add_certain' removes from 'called'.
        # So 'called' implies a copy that is NOT in 'certain'.
        # So we simply increment the requirement.
        for val, tracker in self.value_trackers.items():
            if player_id in tracker.called:
                min_counts[val] += 1
        
        # Prepare for recursion
        # We generate sorted hands, then convert to signature
        # We need to track the actual hand to check positional constraints
        
        current_hand = [None] * hand_size
        
        def backtrack(pos: int, min_val_idx: int, current_counts: Dict[int, int]):
            if pos == hand_size:
                # Hand complete - validate all constraints before adding
                
                # Check adjacent constraints
                for (pid, p1, p2), is_equal in self.adjacent_constraints.items():
                    if pid == player_id:
                        # Ensure positions are within the hand we're building
                        if p1 < hand_size and p2 < hand_size:
                            val1 = current_hand[p1]
                            val2 = current_hand[p2]
                            if is_equal and val1 != val2:
                                return  # Constraint violated
                            if not is_equal and val1 == val2:
                                return  # Constraint violated
                
                # Convert counts to signature vector
                sig = [0] * self.K
                for v_idx, count in current_counts.items():
                    sig[v_idx] = count
                valid_sigs.add(tuple(sig))
                return

            # Possible values for this position
            # Must be >= min_val_idx (sorted)
            # Must be in beliefs[pos]
            # Count must not exceed global total
            
            possible_values = player_beliefs[pos]
            
            # Check copy count constraint for this position
            if (player_id, pos) in self.copy_count_constraints:
                required_copies = self.copy_count_constraints[(player_id, pos)]
                # Filter possible values to only those with required copy count
                possible_values = {v for v in possible_values 
                                 if self.config.wire_distribution[v] == required_copies}
            
            # Iterate through sorted values starting from min_val_idx
            for v_idx in range(min_val_idx, self.K):
                val = self.sorted_values[v_idx]
                
                # Check if value is allowed at this position
                if val not in possible_values:
                    continue
                
                # Check global count constraint
                if current_counts.get(v_idx, 0) >= self.config.get_copies(val):
                    continue
                
                # Check adjacent equality constraint (early pruning)
                # If previous position exists and we have an adjacent constraint
                if pos > 0:
                    # Check if there's a constraint between pos-1 and pos
                    if (player_id, pos-1, pos) in self.adjacent_constraints:
                        is_equal = self.adjacent_constraints[(player_id, pos-1, pos)]
                        prev_val = current_hand[pos-1]
                        if is_equal and val != prev_val:
                            continue  # Must be equal but isn't
                        if not is_equal and val == prev_val:
                            continue  # Must be different but isn't
                    # Also check reverse ordering (pos, pos-1)
                    if (player_id, pos, pos-1) in self.adjacent_constraints:
                        is_equal = self.adjacent_constraints[(player_id, pos, pos-1)]
                        prev_val = current_hand[pos-1]
                        if is_equal and val != prev_val:
                            continue
                        if not is_equal and val == prev_val:
                            continue
                
                # Update state
                current_hand[pos] = val
                current_counts[v_idx] = current_counts.get(v_idx, 0) + 1
                
                # Recurse
                backtrack(pos + 1, v_idx, current_counts)
                
                # Backtrack
                current_hand[pos] = None
                current_counts[v_idx] -= 1
                if current_counts[v_idx] == 0:
                    del current_counts[v_idx]

        # Start backtracking
        backtrack(0, 0, {})
        
        # Filter signatures by min_counts
        # We could have done this inside backtracking, but it's easier here
        # unless the space is huge.
        # Actually, let's filter the RESULTING signatures.
        final_sigs = set()
        for sig in valid_sigs:
            valid = True
            for val, min_c in min_counts.items():
                v_idx = self.val_to_idx[val]
                if sig[v_idx] < min_c:
                    valid = False
                    break
            if valid:
                final_sigs.add(sig)
                
        return final_sigs

    def _project_signatures_to_beliefs(self, player_id: int, valid_signatures: Set[Tuple[int, ...]]):
        """
        Given a set of globally valid signatures for a player,
        reconstruct the possible values for each position.
        """
        hand_size = self.config.wires_per_player
        
        # Initialize new domains as empty
        new_domains = [set() for _ in range(hand_size)]
        
        # For each signature, reconstruct the UNIQUE sorted hand
        for sig in valid_signatures:
            # Reconstruct hand from signature
            hand = []
            for v_idx, count in enumerate(sig):
                val = self.sorted_values[v_idx]
                hand.extend([val] * count)
            
            # Hand is already sorted because we iterated v_idx in order
            
            # Verify this hand is locally valid (matches beliefs)
            # (It should be, because we generated signatures from valid hands,
            # but multiple hands could map to same signature?
            # WAIT. If hand is sorted, Signature -> Hand is 1-to-1.
            # So the hand MUST be valid if the signature was generated from a valid hand?
            # YES, provided we enforced positional constraints during generation.
            # BUT, did we?
            # In _generate_valid_signatures, we checked `val in possible_values` at each step.
            # So the hand generated IS valid.
            # AND since Signature->Hand is 1-to-1 for sorted hands,
            # the reconstructed hand is EXACTLY the one we generated.
            
            # Add values to domains
            for pos in range(hand_size):
                new_domains[pos].add(hand[pos])
        
        # Update beliefs
        for pos in range(hand_size):
            # Intersect with existing beliefs (should be subset anyway, but good for safety)
            self.beliefs[player_id][pos] &= new_domains[pos]
            
            # If domain becomes empty, that's an issue (shouldn't happen if logic is correct)
            if not self.beliefs[player_id][pos]:
                print(f"CRITICAL: Belief for P{player_id} Pos{pos} became empty during projection!")
    
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

