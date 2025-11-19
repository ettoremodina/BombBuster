"""
Implementation of the belief system for BombBuster.
Each player maintains candidate sets representing possible values
for every wire position across all players from their perspective.
"""

from typing import Dict, Set, List, Optional, Union
from itertools import combinations
from src.data_structures import CallRecord, DoubleRevealRecord, SwapRecord, SignalRecord, NotPresentRecord, GameObservation, ValueTracker
from config.game_config import GameConfig
import json
from pathlib import Path


class BeliefModel:
    """
    Manages the deduction logic and belief state for a single player.
    
    The core data structure is:
    beliefs[player_id][position] = {possible_values}
    
    This represents what values each player might have at each position,
    from the perspective of the player who owns this belief model.
    
    Attributes:
        my_player_id: ID of the player who owns this belief model
        observation: GameObservation with available information
        beliefs: Dict[player_id][position] -> Set of possible values
        value_trackers: Dict[value] -> ValueTracker (value can be int or float)
        player_has_value: Dict tracking which values each player has demonstrated
        config: Game configuration
    """
    
    def __init__(self, observation: GameObservation, config: GameConfig):
        """
        Initialize belief model from a player's observation.
        
        Args:
            observation: GameObservation containing all available information
            config: Game configuration with rules and parameters
        """
        self.my_player_id = observation.player_id
        self.observation = observation
        self.config = config
        self.beliefs: Dict[int, Dict[int, Set[Union[int, float]]]] = {}
        self.value_trackers: Dict[Union[int, float], ValueTracker] = {}  # value can be int or float

        # Initialize value trackers
        self._initialize_value_trackers()
        
        # Initialize beliefs and apply initial constraints
        self._initialize_beliefs()
        self._apply_uncertain_position_value_filter()
    
    def _initialize_value_trackers(self):
        """
        Initialize ValueTracker for each possible wire value.
        Each value may have a different number of copies.
        """
        for value in self.config.wire_values:
            copies = self.config.get_copies(value)
            self.value_trackers[value] = ValueTracker(value, copies)
    
    def _initialize_beliefs(self):
        """
        Initialize belief sets for all players and positions.
        Set own revealed positions as certain, others as all possible values.
        """
        # Initialize for all players
        for player_id in range(self.config.n_players):
            self.beliefs[player_id] = {}
            
            for position in range(self.config.wires_per_player):
                if player_id == self.my_player_id:
                    # I know my own wire - add to certain, not revealed
                    value = self.observation.my_wire[position]
                    self.beliefs[player_id][position] = {value}
                    # Update value tracker: own wire values are certain (with position)
                    self.value_trackers[value].add_certain(player_id, position)
                else:
                    # Other players - unknown, start with all possible values
                    self.beliefs[player_id][position] = set(self.config.wire_values)
 
    def process_call(self, call_record: CallRecord):
        """
        Update beliefs based on a public call.
        This is the ONLY way beliefs change during the game (maintains independence).
        
        Args:
            call_record: The call to process
        """
        if call_record.success:
            self._process_successful_call(call_record)
        else:
            self._process_failed_call(call_record)
        
        # Apply filters after processing the call to deduce new information
        self.apply_filters()
    
    def process_double_reveal(self, reveal_record: DoubleRevealRecord):
        """
        Update beliefs based on a double reveal action.
        When a player reveals the last 2 copies of a value at once.
        
        Args:
            reveal_record: The double reveal to process
        """
        player_id = reveal_record.player_id
        value = reveal_record.value
        pos1 = reveal_record.position1
        pos2 = reveal_record.position2
        
        # Both positions now have this value (revealed)
        self.beliefs[player_id][pos1] = {value}
        self.beliefs[player_id][pos2] = {value}
        
        # Add both positions to revealed in value tracker
        self.value_trackers[value].add_revealed(player_id, pos1)
        self.value_trackers[value].add_revealed(player_id, pos2)
        
        # Apply filters to deduce new information
        self.apply_filters()
    
    def process_signal(self, signal_record: SignalRecord):
        """
        Update beliefs based on a player's signal.
        When a player announces they have a certain value at a specific position.
        
        Args:
            signal_record: The signal to process
        """
        player_id = signal_record.player_id
        value = signal_record.value
        position = signal_record.position
        
        # Set the belief for this position to the signaled value (revealed)
        self.beliefs[player_id][position] = {value}
        
        # Add to certain     in value tracker
        self.value_trackers[value].add_certain(player_id, position)
        
        # Apply filters to deduce new information
        self.apply_filters()
    
    def process_not_present(self, not_present_record: NotPresentRecord):
        """
        Update beliefs based on a player announcing they don't have a specific value.
        Remove the value from all of the player's possible positions.
        
        Args:
            not_present_record: The not-present announcement to process
        """
        player_id = not_present_record.player_id
        value = not_present_record.value
        
        # Remove this value from all positions for this player
        for position in range(len(self.beliefs[player_id])):
            if value in self.beliefs[player_id][position]:
                self.beliefs[player_id][position].discard(value)
        
        # Apply filters to deduce new information
        self.apply_filters()
    
    def process_swap(self, swap_record: SwapRecord):
        """
        Update beliefs based on a wire swap between two players.
        
        The swap involves:
        1. Removing wires from initial positions
        2. Inserting swapped wires into final positions (in shortened list)
        3. If the observing player is one of the swappers, they learn the value they received
        4. Update value trackers to reflect position changes
        
        Note: In IRL mode, the IRL player (me) is always normalized to be player1 in utils.py
        
        Args:
            swap_record: The swap to process
        """
        p1_id = swap_record.player1_id
        p2_id = swap_record.player2_id
        p1_init = swap_record.player1_init_pos
        p2_init = swap_record.player2_init_pos
        p1_final = swap_record.player1_final_pos
        p2_final = swap_record.player2_final_pos
        
        # Store the belief sets that are being swapped (BEFORE any modifications)
        # These are needed for updating value trackers
        p1_init_beliefs_original = self.beliefs[p1_id][p1_init].copy()
        p2_init_beliefs_original = self.beliefs[p2_id][p2_init].copy()
        
        p1_init_beliefs = self.beliefs[p1_id][p1_init].copy()
        p2_init_beliefs = self.beliefs[p2_id][p2_init].copy()
        
        # If this player is involved in the swap, they know what they received
        # In IRL mode, I'm always player1 (normalized in utils.py)
        if self.my_player_id == p1_id and swap_record.player1_received_value is not None: 
            # This player is player1 and knows they received a specific value
            p2_init_beliefs = {swap_record.player1_received_value}
        
        if self.my_player_id == p2_id and swap_record.player2_received_value is not None:
            # This player is player2 and knows they received a specific value
            # (shouldn't happen in IRL mode due to normalization, but kept for completeness)
            p1_init_beliefs = {swap_record.player2_received_value}
        
        # Update value trackers BEFORE changing beliefs structure
        # We need to track which values are moving and update their positions
        # Pass the original belief sets to determine which called values to remove
        self._update_value_trackers_for_swap(swap_record, p1_init_beliefs_original, p2_init_beliefs_original)
        
        # Apply swap to player1: remove from init_pos1, insert at final_pos1
        p1_beliefs_list = [self.beliefs[p1_id][pos].copy() for pos in range(len(self.beliefs[p1_id]))]
        p1_beliefs_list[p1_init] = None
        p1_beliefs_list.insert(p1_final, p2_init_beliefs)
        k = 0
        for belief_set in p1_beliefs_list:
            if belief_set is not None:
                self.beliefs[p1_id][k] = belief_set
                k += 1

        
        # Apply swap to player2: remove from init_pos2, insert at final_pos2
        p2_beliefs_list = [self.beliefs[p2_id][pos].copy() for pos in range(len(self.beliefs[p2_id]))]
        p2_beliefs_list[p2_init] = None
        p2_beliefs_list.insert(p2_final, p1_init_beliefs)
        k = 0
        for belief_set in p2_beliefs_list:
            if belief_set is not None:
                self.beliefs[p2_id][k] = belief_set
                k += 1

        # Apply filters to deduce new information
        self.apply_filters()

    def calculate_new_position(self, player_id: int, old_pos: int, 
                                swap_player_id: int, init_pos: int, final_pos: int) -> int:
        """
        Calculate new position after a swap for a given player.
        
        Swap mechanics: remove from init_pos, then insert at final_pos
        """
        if player_id != swap_player_id:
            return old_pos  # No change for other players
        
        if old_pos < init_pos and old_pos< final_pos:
            return old_pos  # No change
        
        elif old_pos > init_pos and old_pos > final_pos:
            return old_pos  # No change
    
        elif old_pos < init_pos and old_pos >= final_pos:
            return old_pos + 1  # Shift right due to insertion
        
        elif old_pos > init_pos and old_pos <= final_pos:
            return old_pos - 1  # Shift left due to removal
        
        elif old_pos == init_pos:
            return final_pos  # This position is being exchanged
        
        elif old_pos == final_pos:
            return init_pos  # This position is being exchanged
        
        else:
            raise ValueError(f"Unhandled position case for old_pos={old_pos}, init_pos={init_pos}, final_pos={final_pos}")
        
    def _update_value_trackers_for_swap(self, swap_record: SwapRecord, 
                                         p1_swapped_beliefs: Set[Union[int, float]], 
                                         p2_swapped_beliefs: Set[Union[int, float]]):
        """
        Update value trackers when a swap occurs.
        
        Requirements:
        1. ALL players need to update value tracker (both involved and not involved)
        2. Revealed wires cannot be swapped, but they change relative position
           - Update positions for revealed values belonging to swapping players
        3. If a certain value got exchanged, update both player and position (swap them)
        4. Other certain values need position updates due to the swap (like revealed ones)
        5. In IRL mode: if I'm receiving a value, update the certain tracker with what I received
        6. Remove both swappers from 'called' lists - but only for values that could have been
           in the positions they swapped (check belief sets)
        
        Args:
            swap_record: The swap record containing all swap information
            p1_swapped_beliefs: The belief set for player1's swapped position (before swap)
            p2_swapped_beliefs: The belief set for player2's swapped position (before swap)
        """
        p1_id = swap_record.player1_id
        p2_id = swap_record.player2_id
        p1_init = swap_record.player1_init_pos
        p2_init = swap_record.player2_init_pos
        p1_final = swap_record.player1_final_pos
        p2_final = swap_record.player2_final_pos

        # Adjust final positions based on insertion point relative to initial position
        if p2_final - 1 >= p2_init:
            p2_final -= 1
        if p1_final - 1 >= p1_init:
            p1_final -= 1

        # For each value tracker, update all positions
        for value, tracker in self.value_trackers.items():
            # Update REVEALED positions
            new_revealed = []
            for pid, pos in tracker.revealed:
                # Revealed wires CANNOT be swapped (game rule)
                if pid == p1_id:
                    # Other positions for player 1 - calculate new position
                    new_pos = self.calculate_new_position(pid, pos, p1_id, p1_init, p1_final)
                    new_revealed.append((pid, new_pos))

                elif pid == p2_id:
                    # Other positions for player 2 - calculate new position
                    new_pos = self.calculate_new_position(pid, pos, p2_id, p2_init, p2_final)
                    new_revealed.append((pid, new_pos))

                else:
                    # Other players - no change
                    new_revealed.append((pid, pos))
            
            tracker.revealed = new_revealed
            
            # Update CERTAIN positions
            new_certain = []
            for pid, pos in tracker.certain:
                # Check if this certain value is being exchanged
                if pid == p1_id and pos == p1_init:
                    # This value is being swapped from p1 to p2
                    # In IRL mode: if I'm player 2 and received a different value, skip this
                    # (the correct value will be added after this loop)
                    if self.config.playing_irl and self.my_player_id == p2_id and swap_record.player2_received_value is not None:
                        # Skip - will be replaced with the actual received value
                        continue
                    else:
                        new_certain.append((p2_id, p2_final))
                        
                elif pid == p2_id and pos == p2_init:
                    # This value is being swapped from p2 to p1
                    # In IRL mode: if I'm player 1 and received a different value, skip this
                    # (the correct value will be added after this loop)
                    if self.config.playing_irl and self.my_player_id == p1_id and swap_record.player1_received_value is not None:
                        # Skip - will be replaced with the actual received value
                        continue
                    else:
                        new_certain.append((p1_id, p1_final))
                        
                elif pid == p1_id:
                    new_pos = self.calculate_new_position(pid, pos, p1_id, p1_init, p1_final)
                    new_certain.append((pid, new_pos))
    
                elif pid == p2_id:
                    # Other certain positions for player 2 - calculate new position
                    new_pos = self.calculate_new_position(pid, pos, p2_id, p2_init, p2_final)
                    new_certain.append((pid, new_pos))

                else:
                    # Other players - no change
                    new_certain.append((pid, pos))
            
            tracker.certain = new_certain
            
            # Update CALLED list - remove swappers only if this value could have been
            # in the position they swapped (check belief sets)
            new_called = set()
            for pid in tracker.called:
                should_keep = True
                
                # Check if player1 called this value and it was in their swapped position
                if pid == p1_id and value in p1_swapped_beliefs:
                    should_keep = False  # Remove from called - they might have swapped it away
                
                # Check if player2 called this value and it was in their swapped position
                elif pid == p2_id and value in p2_swapped_beliefs:
                    should_keep = False  # Remove from called - they might have swapped it away
                
                if should_keep:
                    new_called.add(pid)
            
            tracker.called = new_called
            
        # In IRL mode: if I received a value, mark it as certain for me
        # This replaces any value that was at the swap position
        if self.config.playing_irl:
            if self.my_player_id == p1_id and swap_record.player1_received_value is not None:
                # I'm player 1 and I know what I received
                self.value_trackers[swap_record.player1_received_value].add_certain(p1_id, p1_final)
            
            if self.my_player_id == p2_id and swap_record.player2_received_value is not None:
                # I'm player 2 and I know what I received
                self.value_trackers[swap_record.player2_received_value].add_certain(p2_id, p2_final)
    
    def _process_successful_call(self, call: CallRecord):
        """
        Handle a successful (correct) call.
        Both caller and target have this value at revealed positions.
        
        Args:
            call: The successful call record
        """
        # Target has this value at this position (now revealed)
        self.beliefs[call.target_id][call.position] = {call.value}
        self.value_trackers[call.value].add_revealed(call.target_id, call.position)
        
        # Caller also has this value at their revealed position (if specified)
        if call.caller_position is not None:
            self.beliefs[call.caller_id][call.caller_position] = {call.value}
            self.value_trackers[call.value].add_revealed(call.caller_id, call.caller_position)
    
    def _process_failed_call(self, call: CallRecord):
        """
        Handle a failed (incorrect) call.
        Target does NOT have this value at this position.
        Caller has this value somewhere (demonstrated ownership).
        
        Args:
            call: The failed call record
        """
        # Target does NOT have this value at this position
        self.beliefs[call.target_id][call.position].discard(call.value)
        
        # Caller has this value somewhere (they wouldn't call it otherwise)
        # But only OTHER players add the caller to their 'called' list
        # The caller themselves already know they have it (in their 'certain' list)
        if call.caller_id != self.my_player_id:
            self.value_trackers[call.value].add_called(call.caller_id)
    
    def apply_filters(self):
        """
        Apply all filtering methods to prune impossible values.
        This includes:
        - Ordering filter (monotonic constraint)
        - Subset cardinality matching (Sudoku-style)
        - r_k filtering (removed, redundant)
        
        Runs iteratively until no more changes occur.
        """
        max_iterations = 100  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            changed = False
            
            # Apply ordering filter
            if self._apply_ordering_filter():
                changed = True
            
            # Apply distance constraint filter (r_k based)
            if self._apply_distance_filter():
                changed = True
            
            # # Apply uncertain position-value constraint filter
            if self._apply_uncertain_position_value_filter():
                changed = True

            # Apply subset cardinality filter
            if self._apply_subset_cardinality_filter():
                changed = True
            
            # If no changes, we've reached a fixed point
            if not changed:
                break
            
            iteration += 1
        
        if iteration >= max_iterations:
            print(f"⚠️  Warning: apply_filters() reached max iterations ({max_iterations})")
            
        
        # After filtering, update ValueTracker for any newly certain positions
        # print(f"performed {iteration} loops of filters")
        self._update_value_trackers()
    
    def _update_value_trackers(self):
        """
        Update ValueTracker when belief sets become size 1 (certain).
        This moves players from 'called' or leaves them in 'certain' list.
        Only updates for OTHER players (not own wire, which is already in 'certain').
        """
        for player_id in range(self.config.n_players):
            # Skip own wire (already in 'certain' from initialization)
            if player_id == self.my_player_id:
                continue
            
            for position in range(self.config.wires_per_player):
                possible = self.beliefs[player_id][position]
                
                # If belief set has exactly one value, it's certain
                if len(possible) == 1:
                    value = list(possible)[0]
                    tracker = self.value_trackers[value]
                    
                    # Only add to certain if not already tracked for this position
                    if not any(p == player_id and pos == position for p, pos in tracker.revealed):
                        if not any(p == player_id and pos == position for p, pos in tracker.certain):
                            tracker.add_certain(player_id, position)
    
    def _apply_ordering_filter(self) -> bool:
        """
        Apply monotonic ordering constraint within each player's wire.
        If position i has max value M, all positions to the left must have values <= M.
        If position i has min value m, all positions to the right must have values >= m.
        
        Returns:
            True if any changes were made
        """
        changed = False
        
        for player_id in range(self.config.n_players):
            # Forward pass: propagate max constraints left
            for pos in range(self.config.wires_per_player):
                possible = self.beliefs[player_id][pos]
                if not possible:
                    continue
                
                # Max value at this position constrains all positions to the left
                max_val = max(possible)
                for left_pos in range(pos):
                    before_size = len(self.beliefs[player_id][left_pos])
                    # Remove values > max_val from left positions
                    self.beliefs[player_id][left_pos] = {
                        v for v in self.beliefs[player_id][left_pos] if v <= max_val
                    }
                    if len(self.beliefs[player_id][left_pos]) < before_size:
                        changed = True
            
            # Backward pass: propagate min constraints right
            for pos in range(self.config.wires_per_player):
                possible = self.beliefs[player_id][pos]
                if not possible:
                    continue
                
                # Min value at this position constrains all positions to the right
                min_val = min(possible)
                for right_pos in range(pos + 1, self.config.wires_per_player):
                    before_size = len(self.beliefs[player_id][right_pos])
                    # Remove values < min_val from right positions
                    self.beliefs[player_id][right_pos] = {
                        v for v in self.beliefs[player_id][right_pos] if v >= min_val
                    }
                    if len(self.beliefs[player_id][right_pos]) < before_size:
                        changed = True
        
        return changed
    
    def _apply_distance_filter(self) -> bool:
        """
        Apply distance constraint using sliding window approach.
        
        For each player and each value, determine a window size based on:
        - Number of certain positions for that value
        - Number of revealed positions for that value  
        - Number of uncertain copies
        - +1 if the player has called that value (they have it but position unknown)
        
        The sliding window represents all possible consecutive positions where this value
        could appear given the known certain/revealed positions. Any window that contains
        all certain/revealed positions is valid, and the value can only appear in positions
        covered by at least one valid window.
        
        Returns:
            True if any changes were made
        """
        changed = False
        W = self.config.wires_per_player
        
        # For each player and value
        for player_id in range(self.config.n_players):
            for value in self.config.wire_values:
                tracker = self.value_trackers[value]
                
                # Find certain and revealed positions for this player and value
                certain_positions = set()
                revealed_positions = set()
                
                for pos in range(W):
                    belief = self.beliefs[player_id][pos]
                    if len(belief) == 1 and value in belief:
                        certain_positions.add(pos)
                
                # Check revealed positions from tracker
                for pid, pos in tracker.revealed:
                    if pid == player_id:
                        revealed_positions.add(pos)
                
                # Combine certain and revealed positions (they must all be in the window)
                required_positions = certain_positions | revealed_positions
                
                # If no required positions, skip this filter (no constraint)
                if not required_positions:
                    continue
                
                # Calculate window size
                uncertain = tracker.uncertain
                
                # Add back 1 if this player called this value
                if player_id in tracker.called:
                    uncertain += 1
                
                # Window size = certain + revealed + uncertain
                window_size = len(certain_positions) + len(revealed_positions) + uncertain
                
                # If window_size >= W, no constraint (value can be anywhere)
                if window_size >= W:
                    continue
                
                # Find all valid window positions (windows that contain all required positions)
                valid_positions = set()
                
                # Slide the window across all possible starting positions
                for window_start in range(W - window_size + 1):
                    window_end = window_start + window_size - 1  # inclusive
                    
                    # Check if this window contains all required positions
                    window_contains_all = all(
                        window_start <= pos <= window_end 
                        for pos in required_positions
                    )
                    
                    if window_contains_all:
                        # All positions in this window are valid for this value
                        for pos in range(window_start, window_end + 1):
                            valid_positions.add(pos)
                
                # Remove this value from all positions NOT in valid_positions
                for pos in range(W):
                    if pos not in valid_positions:
                        before_size = len(self.beliefs[player_id][pos])
                        self.beliefs[player_id][pos].discard(value)
                        if len(self.beliefs[player_id][pos]) < before_size:
                            changed = True
        
        return changed
    
    def _apply_subset_cardinality_filter(self) -> bool:
        """
        Apply subset cardinality matching (hidden pairs/triples/etc).
        
        Algorithm:
        - Merge all position belief sets across ALL players (track origin)
        - Generate all value combinations of size H (where 2 <= H < total_values)
        - For each combination, count how many positions (across all players) contain 
          ANY of those values
        - If exactly H positions contain values from the combination,
          then those H positions can ONLY have those H values
        - Remove all OTHER values (not in the combination) from those H positions
        
        This is the "hidden subset" technique from Sudoku applied globally.
        
        Returns:
            True if any changes were made
        """
        changed = False
        
        # Collect all belief sets across all players with their origins
        all_positions = []  # List of (player_id, position, belief_set)
        all_values = set()
        
        for player_id in range(self.config.n_players):
            for pos in range(self.config.wires_per_player):
                belief = self.beliefs[player_id][pos]
                all_positions.append((player_id, pos, belief))
                all_values.update(belief)
        
        if len(all_values) <= 2:
            return False  # Not enough values to form meaningful combinations
        
        # Try combinations of size H (skip H=1 as instructed, also skip full set)
        for H in range(2, len(all_values)):
            # Generate all H-sized combinations of values
            for value_combo in combinations(sorted(all_values), H):
                value_set = set(value_combo)
                
                # Find positions (across ALL players) that contain ANY value from this combination
                matching_positions = []
                for player_id, pos, belief in all_positions:
                    # Check if this position's belief intersects with the combination
                    if belief & value_set:
                        matching_positions.append((player_id, pos))
                
                # If exactly H positions contain values from this combination
                if len(matching_positions) == H:                    
                    for player_id, pos in matching_positions:
                        before_size = len(self.beliefs[player_id][pos])
                        # Keep only values from the combination
                        self.beliefs[player_id][pos] &= value_set
                        if len(self.beliefs[player_id][pos]) < before_size:
                            changed = True
        
        return changed
  
    def _apply_uncertain_position_value_filter(self) -> bool:
        """
        Apply position-value constraints based on remaining UNCERTAIN values.
        
        This filter looks at which values are still uncertain (not revealed/called/certain)
        and constrains positions based on:
        - Wire ordering (non-decreasing)
        - Remaining uncertain copies of each value
        - Position in the wire
        
        Key insight: If we know that certain high values are already placed,
        we can eliminate them from early positions more aggressively.
        Similarly, if low values are already accounted for, they can't appear
        in late positions.
        
        Algorithm:
        1. For each value, count how many copies are still UNCERTAIN
           (uncertain = not in revealed, certain, or called lists)
        2. Build a threshold from high to low based on uncertain counts
        3. Eliminate values from positions where they cannot appear
        
        Example:
        - Value 12 has 4 copies, but 3 are already certain → only 1 uncertain copy
        - If there are 2+ positions before this could appear, eliminate it from position 0
        
        Returns:
            True if any changes were made
        """
        changed = False
        W = self.config.wires_per_player
        
        # Count uncertain copies for each value
        uncertain_counts = {}
        for value in self.config.wire_values:
            tracker = self.value_trackers[value]
            # Use tracker's uncertain property (same as distance filter)
            uncertain_counts[value] = max(0, tracker.uncertain) 
        
        # For each player, adjust uncertain count if they called this value
        # (they have it but position is uncertain)
        player_adjustments = {}
        for player_id in range(self.config.n_players):
            player_adjustments[player_id] = {}
            for value in self.config.wire_values:
                tracker = self.value_trackers[value]
                uncertain_for_player = uncertain_counts[value]
                
                # Add back 1 if this player called this value
                if player_id in tracker.called:
                    uncertain_for_player += 1
                # add back certain and revealed count if they belong to that player
                certain_count = sum(1 for p, pos in tracker.certain if p == player_id)
                revealed_count = sum(1 for p, pos in tracker.revealed if p == player_id)
                uncertain_for_player += certain_count + revealed_count
                
                player_adjustments[player_id][value] = uncertain_for_player
        
        # STEP 1: Existence filter - if a player has 0 copies of a value, remove it from all positions
        for player_id in range(self.config.n_players):
            for value in self.config.wire_values:
                uncertain_copies = player_adjustments[player_id][value]
                
                if uncertain_copies == 0:
                    # This player has 0 copies of this value - eliminate from ALL positions
                    for pos in range(W):
                        before_size = len(self.beliefs[player_id][pos])
                        self.beliefs[player_id][pos].discard(value)
                        if len(self.beliefs[player_id][pos]) < before_size:
                            changed = True
        
        # STEP 2: Position constraints - high values with few uncertain copies cannot appear too early
        # Build threshold: position before which this value cannot appear
        for player_id in range(self.config.n_players):
            threshold = W
            for value in sorted(self.config.wire_values, reverse=True):
                uncertain_copies = player_adjustments[player_id][value]
                
                # Skip zero-copy case (already handled by existence filter)
                if uncertain_copies == 0:
                    continue
                
                threshold -= uncertain_copies
                
                # Clamp threshold to valid range [0, W)
                if threshold > 0 and threshold < W:
                    # Eliminate this value from positions [0, threshold)
                    for pos in range(0, min(threshold, W)):
                        if pos < len(self.beliefs[player_id]):  # Safety check
                            before_size = len(self.beliefs[player_id][pos])
                            self.beliefs[player_id][pos].discard(value)
                            if len(self.beliefs[player_id][pos]) < before_size:
                                changed = True
        
        # STEP 3: Position constraints - low values with few uncertain copies cannot appear too late
        # Build threshold: position after which this value cannot appear
        for player_id in range(self.config.n_players):
            threshold = 0
            for value in sorted(self.config.wire_values):
                uncertain_copies = player_adjustments[player_id][value]
                
                # Skip zero-copy case (already handled by existence filter)
                if uncertain_copies == 0:
                    continue
                
                threshold += uncertain_copies
                
                # Clamp threshold to valid range (0, W]
                if threshold > 0 and threshold < W:
                    # Eliminate this value from positions [threshold, W)
                    for pos in range(max(0, threshold), W):
                        if pos < len(self.beliefs[player_id]):  # Safety check
                            before_size = len(self.beliefs[player_id][pos])
                            self.beliefs[player_id][pos].discard(value)
                            if len(self.beliefs[player_id][pos]) < before_size:
                                changed = True
        
        return changed
    
    def is_consistent(self) -> bool:
        """
        Check if the current belief state is consistent (no empty sets).
        
        Returns:
            True if consistent, False if any position has no possible values
        """
        for player_id in range(self.config.n_players):

            
            for position in range(self.config.wires_per_player):
                if len(self.beliefs[player_id][position]) == 0:
                    return False
        return True
    
    def get_certain_positions(self, player_id: int) -> Dict[int, int]:
        """
        Get positions where the value is certain (only one possibility).
        
        Args:
            player_id: The player to check
        
        Returns:
            Dict mapping position to certain value
        """
        certain = {}
        for position in range(self.config.wires_per_player):
            possible = self.beliefs[player_id][position]
            if len(possible) == 1:
                certain[position] = list(possible)[0]
        return certain
    
    def get_uncertain_positions(self, player_id: int) -> List[int]:
        """
        Get list of positions where the value is still uncertain.
        
        Args:
            player_id: The player to check
        
        Returns:
            List of position indices with multiple possible values
        """
        uncertain = []
        for position in range(self.config.wires_per_player):
            if len(self.beliefs[player_id][position]) > 1:
                uncertain.append(position)
        return uncertain
    
    def is_fully_deduced(self, player_id: int) -> bool:
        """
        Check if all positions for a player are certain.
        
        Args:
            player_id: The player to check
        
        Returns:
            True if all positions have only one possible value
        """
        for position in range(self.config.wires_per_player):
            if len(self.beliefs[player_id][position]) != 1:
                return False
        return True
    
    def print_beliefs(self, player_names: Dict[int, str] = None):
        """
        Print the current belief state in a readable format.
        Differentiates between revealed (via calls) and certain (via deduction).
        
        Args:
            player_names: Optional dict mapping player IDs to names {0: "Alice", 1: "Bob", ...}
        """
        my_name = player_names.get(self.my_player_id, f"Player {self.my_player_id}") if player_names else f"Player {self.my_player_id}"
        print(f"\nBelief State (from {my_name}'s perspective):")
        print("-" * 80)
        
        for player_id in range(self.config.n_players):
            player_name = player_names.get(player_id, f"Player {player_id}") if player_names else f"Player {player_id}"
            
            if player_id == self.my_player_id:
                print(f"\n👤 {player_name} (YOU):")
            else:
                print(f"\n{player_name}:")
            
            for position in range(self.config.wires_per_player):
                possible_values = self.beliefs[player_id][position]
                
                if len(possible_values) == 0:
                    print(f"  Position {position+1}: ⚠️  INCONSISTENT - No possible values!")
                elif len(possible_values) == 1:
                    value = list(possible_values)[0]
                    
                    # Check if this position is revealed or just certain
                    is_revealed = False
                    is_certain = False
                    
                    if value in self.value_trackers:
                        tracker = self.value_trackers[value]
                        # Check if this specific position is revealed
                        if any(p == player_id and pos == position for p, pos in tracker.revealed):
                            is_revealed = True
                        # Check if this specific position is certain
                        elif any(p == player_id and pos == position for p, pos in tracker.certain):
                            is_certain = True
                    
                    if is_revealed:
                        print(f"  Position {position+1}: [{value}] 🔓 REVEALED ")
                    elif is_certain:
                        print(f"  Position {position+1}: [{value}] ✓ CERTAIN")
                    else:
                        # Single value but not tracked (shouldn't happen normally)
                        print(f"  Position {position+1}: [{value}] ✓ WTF")
                else:
                    values_str = str(sorted(possible_values))
                    print(f"  Position {position+1}: {values_str} ({len(possible_values)} possibilities)")
        
        print("-" * 80)

    # --- Serialization helpers -------------------------------------------------
    def to_dict(self) -> Dict:
        """Serialize the BeliefModel (beliefs + value_trackers) to a JSON-serializable dict.

        Note: sets are converted to sorted lists for stable output.
        """
        beliefs_serialized: Dict[str, Dict[str, List[int]]] = {}
        for pid, pos_map in self.beliefs.items():
            beliefs_serialized[str(pid)] = {}
            for pos, poss in pos_map.items():
                beliefs_serialized[str(pid)][str(pos)] = sorted(list(poss))

        vt_serialized: Dict[str, Dict] = {}
        for val, tracker in self.value_trackers.items():
            vt_serialized[str(val)] = tracker.to_dict()

        return {
            "my_player_id": self.my_player_id,
            "beliefs": beliefs_serialized,
            "value_trackers": vt_serialized,
        }

    @classmethod
    def from_dict(cls, data: Dict, observation: GameObservation, config: GameConfig, player_names: Dict[int, str] = None) -> "BeliefModel":
        """Restore a BeliefModel from a dict. Requires the observation and config to
        create a proper instance (independence preserved) and then override internal
        state with the saved data.
        
        Args:
            data: Serialized belief model data
            observation: GameObservation for this player
            config: Game configuration
            player_names: Optional dict mapping player IDs to names for deserializing value trackers
        """
        bm = cls(observation, config)

        # Restore beliefs (convert lists back to sets)
        beliefs_data = data.get("beliefs", {})
        for pid_str, pos_map in beliefs_data.items():
            pid = int(pid_str)
            for pos_str, vals in pos_map.items():
                pos = int(pos_str)
                bm.beliefs[pid][pos] = set(vals)

        # Restore value trackers (convert string keys back to int or float)
        vt_data = data.get("value_trackers", {})
        for val_str, vt_dict in vt_data.items():
            # Try to convert to int first, then float
            try:
                val = int(val_str)
            except ValueError:
                val = float(val_str)
            # Get total from config
            total = config.wire_distribution.get(val, 0)
            bm.value_trackers[val] = ValueTracker.from_dict(vt_dict, val, total, player_names)

        return bm

    def save_to_folder(self, base_path: str, player_names: Dict[int, str] = None):
        """Save belief model and value tracker to a folder dedicated to this player.

        Directory layout created (if needed):
            base_path/player_{my_player_id}/belief.json
            base_path/player_{my_player_id}/value_tracker.json
            
        Args:
            base_path: Base directory path
            player_names: Optional dict mapping player IDs to names {0: "Alice", 1: "Bob", ...}
        """
        base = Path(base_path)
        player_dir = base / f"player_{self.my_player_id}"
        player_dir.mkdir(parents=True, exist_ok=True)

        # Write beliefs only (without value_trackers embedded)
        belief_file = player_dir / "belief.json"
        beliefs_serialized: Dict[str, Dict[str, List[Union[int, float]]]] = {}
        for pid, pos_map in self.beliefs.items():
            player_key = f"{pid}"
            if player_names and pid in player_names:
                player_key = f"{pid}_{player_names[pid]}"
            
            beliefs_serialized[player_key] = {}
            for pos, poss in pos_map.items():
                beliefs_serialized[player_key][str(pos)] = sorted(list(poss))
        
        belief_data = {
            "my_player_id": self.my_player_id,
            "beliefs": beliefs_serialized,
        }
        
        if player_names:
            belief_data["player_names"] = player_names
        
        with belief_file.open("w", encoding="utf-8") as fh:
            json.dump(belief_data, fh, indent=2)

        # Write value trackers separately for readability
        vt_file = player_dir / "value_tracker.json"
        vt_serialized = {str(v): t.to_dict(player_names) for v, t in self.value_trackers.items()}
        with vt_file.open("w", encoding="utf-8") as fh:
            json.dump(vt_serialized, fh, indent=2)

    @classmethod
    def load_from_folder(cls, base_path: str, player_id: int, observation: GameObservation, config: GameConfig) -> "BeliefModel":
        """Load a BeliefModel for given player_id from disk.

        If files are missing an exception is raised.
        """
        base = Path(base_path)
        player_dir = base / f"player_{player_id}"
        
        # Load belief data
        belief_file = player_dir / "belief.json"
        if not belief_file.exists():
            raise FileNotFoundError(f"Belief file not found: {belief_file}")
        
        with belief_file.open("r", encoding="utf-8") as fh:
            belief_data = json.load(fh)
        
        # Extract player names if available (for reference, not used in loading)
        player_names = belief_data.get("player_names", {})
        
        # Convert string keys to int keys if needed
        if player_names:
            player_names = {int(k): v for k, v in player_names.items()}
        
        # Parse beliefs - handle both old format (just ID) and new format (ID_Name)
        beliefs_dict = {}
        for player_key, pos_map in belief_data["beliefs"].items():
            # Extract player ID from key (format: "0" or "0_Alice")
            player_id_str = player_key.split("_")[0]
            pid = int(player_id_str)
            beliefs_dict[str(pid)] = pos_map
        
        # Load value tracker data
        vt_file = player_dir / "value_tracker.json"
        if not vt_file.exists():
            raise FileNotFoundError(f"Value tracker file not found: {vt_file}")
        
        with vt_file.open("r", encoding="utf-8") as fh:
            vt_data = json.load(fh)
        
        # Combine both into the format expected by from_dict
        combined_data = {
            "my_player_id": belief_data["my_player_id"],
            "beliefs": beliefs_dict,
            "value_trackers": vt_data,
        }
        
        return cls.from_dict(combined_data, observation, config, player_names)
