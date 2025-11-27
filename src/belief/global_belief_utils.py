from typing import Dict, Set, List, Tuple, Optional, Union
import collections


def forward_pass_worker(
    alpha_chunk: List[Tuple[int, ...]],
    V_i: Set[Tuple[int, ...]],
    total_deck: Tuple[int, ...]
) -> Set[Tuple[int, ...]]:
    """Worker for parallelized forward pass."""
    result = set()
    for prev_res in alpha_chunk:
        for sig in V_i:
            new_res = tuple(a + b for a, b in zip(prev_res, sig))
            if all(x <= y for x, y in zip(new_res, total_deck)):
                result.add(new_res)
    return result


def backward_pass_worker(
    beta_chunk: List[Tuple[int, ...]],
    V_i: Set[Tuple[int, ...]],
    total_deck: Tuple[int, ...]
) -> Set[Tuple[int, ...]]:
    """Worker for parallelized backward pass."""
    result = set()
    for needed_res in beta_chunk:
        for sig in V_i:
            total_needed = tuple(a + b for a, b in zip(needed_res, sig))
            if all(x <= y for x, y in zip(total_needed, total_deck)):
                result.add(total_needed)
    return result


def generate_signatures_worker(
    player_id: int,
    hand_size: int,
    sorted_values: List,
    val_to_idx: Dict,
    wire_distribution: Dict,
    player_beliefs: List[Set],
    copy_count_constraints: Dict[Tuple[int, int], int],
    adjacent_constraints: Dict[Tuple[int, int, int], bool],
    min_counts: Dict,
    K: int
) -> Set[Tuple[int, ...]]:
    """
    Worker function to generate valid signatures for a player.
    """
    valid_sigs = set()
    
    # Pre-process min_counts to use indices for faster lookup
    min_counts_indices = {val_to_idx[v]: c for v, c in min_counts.items()}
    
    # Prepare for recursion
    current_hand = [None] * hand_size
    
    def backtrack(pos: int, min_val_idx: int, current_counts: Dict[int, int]):
        # Pruning: Check if we can still satisfy min_counts
        remaining_slots = hand_size - pos
        needed_sum = 0
        for v_idx, min_c in min_counts_indices.items():
            curr = current_counts.get(v_idx, 0)
            if min_c > curr:
                needed = min_c - curr
                needed_sum += needed
        
        if needed_sum > remaining_slots:
            return

        if pos == hand_size:
            # Hand complete - validate all constraints before adding
            
            # Check adjacent constraints
            for (pid, p1, p2), is_equal in adjacent_constraints.items():
                if pid == player_id:
                    # Ensure positions are within the hand we're building
                    if p1 < hand_size and p2 < hand_size:
                        val1 = current_hand[p1]
                        val2 = current_hand[p2]
                        if is_equal and val1 != val2:
                            return  # Constraint violated
                        if not is_equal and val1 == val2:
                            return  # Constraint violated
            
            # Check copy count constraints
            for (pid, p), req_count in copy_count_constraints.items():
                if pid == player_id:
                    val = current_hand[p]
                    v_idx = val_to_idx[val]
                    if current_counts.get(v_idx, 0) != req_count:
                        return

            # Convert counts to signature vector
            sig = [0] * K
            for v_idx, count in current_counts.items():
                sig[v_idx] = count
            valid_sigs.add(tuple(sig))
            return

        # Possible values for this position
        # Must be >= min_val_idx (sorted)
        # Must be in beliefs[pos]
        # Count must not exceed global total
        
        possible_values = player_beliefs[pos]
        
        # Iterate through sorted values starting from min_val_idx
        for v_idx in range(min_val_idx, K):
            val = sorted_values[v_idx]
            
            # Check if value is allowed at this position
            if val not in possible_values:
                continue
            
            # Check global count constraint
            # Use wire_distribution directly or passed config
            # Assuming wire_distribution maps value -> total copies
            if current_counts.get(v_idx, 0) >= wire_distribution[val]:
                continue
            
            # Check adjacent equality constraint (early pruning)
            # If previous position exists and we have an adjacent constraint
            if pos > 0:
                # Check if there's a constraint between pos-1 and pos
                if (player_id, pos-1, pos) in adjacent_constraints:
                    is_equal = adjacent_constraints[(player_id, pos-1, pos)]
                    prev_val = current_hand[pos-1]
                    if is_equal and val != prev_val:
                        continue  # Must be equal but isn't
                    if not is_equal and val == prev_val:
                        continue  # Must be different but isn't
                # Also check reverse ordering (pos, pos-1)
                if (player_id, pos, pos-1) in adjacent_constraints:
                    is_equal = adjacent_constraints[(player_id, pos, pos-1)]
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
    final_sigs = set()
    for sig in valid_sigs:
        valid = True
        for val, min_c in min_counts.items():
            v_idx = val_to_idx[val]
            if sig[v_idx] < min_c:
                valid = False
                break
        if valid:
            final_sigs.add(sig)
            
    return final_sigs

def filter_signatures_worker(
    V_p: Set[Tuple[int, ...]],
    Alpha_p: Set[Tuple[int, ...]],
    Beta_next: Set[Tuple[int, ...]],
    total_deck: Tuple[int, ...],
    sorted_values: List,
    hand_size: int
) -> List[Set]:
    """
    Worker function to filter signatures and project to domains.
    Returns a list of sets (new domains for each position).
    """
    new_domains, _ = filter_signatures_and_get_hands_worker(
        V_p, Alpha_p, Beta_next, total_deck, sorted_values, hand_size
    )
    return new_domains


def filter_signatures_and_get_hands_worker(
    V_p: Set[Tuple[int, ...]],
    Alpha_p: Set[Tuple[int, ...]],
    Beta_next: Set[Tuple[int, ...]],
    total_deck: Tuple[int, ...],
    sorted_values: List,
    hand_size: int
) -> Tuple[List[Set], List[Tuple]]:
    """
    Worker function to filter signatures, project to domains, and return valid hands.
    Returns (new_domains, valid_hands) where valid_hands is a list of value tuples.
    """
    valid_signatures = set()
    
    for sig in V_p:
        remainder = tuple(t - s for t, s in zip(total_deck, sig))
        
        is_valid = False
        
        if len(Alpha_p) < len(Beta_next):
            for prev in Alpha_p:
                needed_next = tuple(r - a for r, a in zip(remainder, prev))
                if needed_next in Beta_next:
                    is_valid = True
                    break
        else:
            for next_vec in Beta_next:
                needed_prev = tuple(r - n for r, n in zip(remainder, next_vec))
                if needed_prev in Alpha_p:
                    is_valid = True
                    break
        
        if is_valid:
            valid_signatures.add(sig)
    
    new_domains = [set() for _ in range(hand_size)]
    valid_hands = []
    
    for sig in valid_signatures:
        hand = []
        for v_idx, count in enumerate(sig):
            val = sorted_values[v_idx]
            hand.extend([val] * count)
        
        hand_tuple = tuple(hand)
        valid_hands.append(hand_tuple)
        
        for pos in range(hand_size):
            new_domains[pos].add(hand[pos])
            
    return new_domains, valid_hands
