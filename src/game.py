"""
Game class manages the game state, enforces rules, and coordinates player actions.
This is the central orchestrator for BombBuster gameplay.
"""

from typing import List, Optional, Dict, Union
from src.data_structures import CallRecord, DoubleRevealRecord, SwapRecord, SignalRecord, NotPresentRecord, GameObservation
from src.player import Player
from config.game_config import GameConfig


class Game:
    """
    Manages game state, validates actions, and broadcasts updates to all players.
    
    This is a COLLABORATIVE game where all players work together to deduce all wires.
    - WIN: All positions across all players become revealed/certain
    - LOSE: Make W wrong calls (config.max_wrong_calls)
    
    The Game class is the single source of truth for:
    - Current game state (turn count, wrong calls, game over)
    - Call history (public information)
    - Win/loss conditions
    - Rule enforcement
    
    Attributes:
        players: List of Player objects (all working together)
        config: Game configuration (rules, values, max_wrong_calls)
        call_history: List of all calls made (public information)
        current_turn: Current turn number
        wrong_calls_count: Number of wrong calls made (lose if >= max_wrong_calls)
        game_over: Whether the game has ended
        team_won: True if team won, False if team lost, None if game ongoing
    """
    
    def __init__(self, players: List[Player], config: GameConfig):
        """
        Initialize a new collaborative game with players and configuration.
        
        Args:
            players: List of Player objects participating in the game
            config: Game configuration with rules and parameters
        """
        self.players = players
        self.config = config
        self.call_history: List[CallRecord] = []
        self.current_turn = 0
        self.wrong_calls_count = 0
        self.game_over = False
        self.team_won: Optional[bool] = None
        
        # Initialize belief systems for all players
        self._initialize_belief_systems()
    
    def _initialize_belief_systems(self):
        """
        Create and link belief systems to each player.
        This is called once at game start.
        """
        from src.belief.belief_model import BeliefModel
        from src.belief.global_belief_model import GlobalBeliefModel
        
        for player in self.players:
            # In IRL mode, only initialize belief system for player 0 (us)
            if self.config.playing_irl and player.player_id != 0:
                player.belief_system = None
                continue

            # Create observation for this player
            observation = self.get_observation_for_player(player.player_id)
            
            # Create and link belief system
            if self.config.use_global_belief:
                player.belief_system = GlobalBeliefModel(observation, self.config)
            else:
                player.belief_system = BeliefModel(observation, self.config)
    
    def make_call(self, caller_id: int, target_id: int, position: int, value: Union[int, float], 
                  success: bool, caller_position: Optional[int] = None) -> CallRecord:
        """
        Process a call between two players.
        This is the primary game action and updates all game state.
        
        IMPORTANT: For real-life gameplay, the caller manually provides the success result
        since other players' wires are not accessible.
        
        Args:
            caller_id: ID of the player making the call
            target_id: ID of the player being called
            position: Wire position being called (0-indexed)
            value: The value being called (can be int or float)
            success: Whether the call was successful (correct) - provided by caller
            caller_position: Position in caller's wire where they have this value (0-indexed, 
                           only needed for successful calls to reveal caller's position)
        
        Returns:
            CallRecord with the result of the call
        
        Raises:
            ValueError: If the call is invalid (game over, invalid player, etc.)
        """
        # Validate the call
        self._validate_call(caller_id, target_id, position, value)
        
        # Create call record
        call_record = CallRecord(
            caller_id=caller_id,
            target_id=target_id,
            position=position,
            value=value,
            success=success,
            caller_position=caller_position,
            turn_number=self.current_turn
        )
        
        # Add to history
        self.call_history.append(call_record)
        
        # Update wrong calls count if unsuccessful
        if not success:
            self.wrong_calls_count += 1
        
        # Broadcast to all players
        self._broadcast_call(call_record)
        
        # Check win/loss conditions
        self._check_win_condition()
        
        # Increment turn
        self.current_turn += 1
        
        return call_record
    
    def double_reveal(self, player_id: int, value: Union[int, float], position1: int, position2: int) -> DoubleRevealRecord:
        """
        Process a double reveal action.
        When a player has the last 2 copies of a value, they can reveal both at once.
        
        Args:
            player_id: ID of the player revealing the wires
            value: The value being revealed
            position1: First wire position (0-indexed)
            position2: Second wire position (0-indexed)
        
        Returns:
            DoubleRevealRecord with the result
        
        Raises:
            ValueError: If the double reveal is invalid
        """
        # Validate the double reveal
        self._validate_double_reveal(player_id, value, position1, position2)
        
        # Create double reveal record
        reveal_record = DoubleRevealRecord(
            player_id=player_id,
            value=value,
            position1=position1,
            position2=position2,
            turn_number=self.current_turn
        )
        
        # Broadcast to all players
        self._broadcast_double_reveal(reveal_record)
        
        # Check win condition
        self._check_win_condition()
        
        # Increment turn
        self.current_turn += 1
        
        return reveal_record
    
    def signal_value(self, player_id: int, value: Union[int, float], position: int) -> SignalRecord:
        """
        Process a signal where a player announces they have a certain value at a position.
        This is a direct knowledge announcement, useful for speeding up IRL gameplay.
        
        Args:
            player_id: ID of the player making the signal
            value: The value at the position (can be int or float)
            position: Wire position being signaled (0-indexed)
        
        Returns:
            SignalRecord with the result
        
        Raises:
            ValueError: If the signal is invalid
        """
        # Validate the signal
        self._validate_signal(player_id, value, position)
        
        # Create signal record
        signal_record = SignalRecord(
            player_id=player_id,
            value=value,
            position=position,
            turn_number=self.current_turn
        )
        
        # Broadcast to all players
        self._broadcast_signal(signal_record)
        
        # Check win condition
        self._check_win_condition()
        
        # Increment turn
        self.current_turn += 1
        
        return signal_record
    
    def reveal_value(self, player_id: int, value: Union[int, float], position: int) -> SignalRecord:
        """
        Process a reveal where a player reveals a specific value at a position.
        Similar to signal but marks the position as revealed instead of certain.
        
        Args:
            player_id: ID of the player revealing
            value: The value at the position (can be int or float)
            position: Wire position being revealed (0-indexed)
        
        Returns:
            SignalRecord with the result
        
        Raises:
            ValueError: If the reveal is invalid
        """
        # Validate the reveal (uses same validation as signal)
        self._validate_signal(player_id, value, position)
        
        # Create signal record (reuse structure)
        reveal_record = SignalRecord(
            player_id=player_id,
            value=value,
            position=position,
            turn_number=self.current_turn
        )
        
        # Broadcast to all players (use reveal processing)
        self._broadcast_reveal(reveal_record)
        
        # Check win condition
        self._check_win_condition()
        
        # Increment turn
        self.current_turn += 1
        
        return reveal_record
    
    def _validate_signal(self, player_id: int, value: Union[int, float], position: int):
        """
        Validate that a signal is legal according to game rules.
        
        Args:
            player_id: ID of the player signaling
            value: The value being signaled
            position: The position being signaled
        
        Raises:
            ValueError: If the signal violates game rules
        """
        # Check if game is over
        if self.game_over:
            raise ValueError("Game is already over")
        
        # Check if player ID is valid
        if player_id < 0 or player_id >= len(self.players):
            raise ValueError(f"Invalid player_id: {player_id}")
        
        # Check if position is valid
        if position < 0 or position >= self.config.wires_per_player:
            raise ValueError(f"Invalid position: {position}. Must be in [0, {self.config.wires_per_player-1}]")
        
        # Check if value is valid
        if value not in self.config.wire_values:
            raise ValueError(f"Invalid value: {value}. Must be in {self.config.wire_values}")
        
        # When not in IRL mode, validate that the player actually has this value at this position
        if not self.config.playing_irl:
            player = self.players[player_id]
            if player.wire[position] != value:
                raise ValueError(f"Player {player_id} does not have value {value} at position {position}")
    
    def _broadcast_signal(self, signal_record: SignalRecord):
        """
        Broadcast a signal to all players so they can update their beliefs.
        
        Args:
            signal_record: The signal to broadcast
        """
        # Each player's belief system processes the signal
        for player in self.players:
            if player.belief_system is not None:
                player.belief_system.process_signal(signal_record)
    
    def _broadcast_reveal(self, reveal_record: SignalRecord):
        """
        Broadcast a reveal to all players so they can update their beliefs.
        
        Args:
            reveal_record: The reveal to broadcast
        """
        # Each player's belief system processes the reveal
        for player in self.players:
            if player.belief_system is not None:
                player.belief_system.process_reveal(reveal_record)
    
    def announce_not_present(self, player_id: int, value: Union[int, float], position: Optional[int] = None) -> NotPresentRecord:
        """
        Process an announcement where a player declares they don't have a specific value.
        This removes the value from all of the player's possible positions,
        or from a specific position if specified.
        
        Args:
            player_id: ID of the player making the announcement
            value: The value they don't have (can be int or float)
            position: Optional specific position (0-indexed) where the value is not present
        
        Returns:
            NotPresentRecord with the result
        
        Raises:
            ValueError: If the announcement is invalid
        """
        # Validate the announcement
        self._validate_not_present(player_id, value, position)
        
        # Create not present record
        not_present_record = NotPresentRecord(
            player_id=player_id,
            value=value,
            position=position,
            turn_number=self.current_turn
        )
        
        # Broadcast to all players
        self._broadcast_not_present(not_present_record)
        
        # Check win condition
        self._check_win_condition()
        
        # Increment turn
        self.current_turn += 1
        
        return not_present_record
    
    def announce_has_value(self, player_id: int, value: Union[int, float]):
        """
        Process an announcement where a player declares they have a specific value.
        This adds the player to the 'called' list for that value (position unknown).
        
        Args:
            player_id: ID of the player making the announcement
            value: The value they have (can be int or float)
        
        Raises:
            ValueError: If the announcement is invalid
        """
        # Validate the announcement
        self._validate_has_value(player_id, value)
        
        # Broadcast to all players to update their value trackers
        self._broadcast_has_value(player_id, value)
        
        # Increment turn
        self.current_turn += 1
    
    def _validate_has_value(self, player_id: int, value: Union[int, float]):
        """
        Validate that a has-value announcement is legal according to game rules.
        
        Args:
            player_id: ID of the player making the announcement
            value: The value being announced
        
        Raises:
            ValueError: If the announcement violates game rules
        """
        # Check if game is over
        if self.game_over:
            raise ValueError("Game is already over")
        
        # Check if player ID is valid
        if player_id < 0 or player_id >= len(self.players):
            raise ValueError(f"Invalid player_id: {player_id}")
        
        # Check if value is valid
        if value not in self.config.wire_values:
            raise ValueError(f"Invalid value: {value}. Must be in {self.config.wire_values}")
        
        # When not in IRL mode, validate that the player actually has this value
        if not self.config.playing_irl:
            player = self.players[player_id]
            if value not in player.wire:
                raise ValueError(f"Player {player_id} cannot announce having value {value} - they don't possess it")
    
    def _broadcast_has_value(self, player_id: int, value: Union[int, float]):
        """
        Broadcast a has-value announcement to all players so they can update their value trackers.
        
        Args:
            player_id: The player who has the value
            value: The value they have
        """
        # Each player's belief system processes the has-value announcement
        for player in self.players:
            if player.belief_system is not None:
                player.belief_system.process_has_value(player_id, value)
    
    def _validate_not_present(self, player_id: int, value: Union[int, float], position: Optional[int] = None):
        """
        Validate that a not-present announcement is legal according to game rules.
        
        Args:
            player_id: ID of the player making the announcement
            value: The value being announced as not present
            position: Optional specific position (0-indexed)
        
        Raises:
            ValueError: If the announcement violates game rules
        """
        # Check if game is over
        if self.game_over:
            raise ValueError("Game is already over")
        
        # Check if player ID is valid
        if player_id < 0 or player_id >= len(self.players):
            raise ValueError(f"Invalid player_id: {player_id}")
        
        # Check if value is valid
        if value not in self.config.wire_values:
            raise ValueError(f"Invalid value: {value}. Must be in {self.config.wire_values}")
            
        # Check if position is valid if provided
        if position is not None:
            if position < 0 or position >= self.config.wires_per_player:
                raise ValueError(f"Invalid position: {position}. Must be in [0, {self.config.wires_per_player-1}]")
        
        # When not in IRL mode, validate that the player actually doesn't have this value
        if not self.config.playing_irl:
            player = self.players[player_id]
            if position is not None:
                if player.wire[position] == value:
                    raise ValueError(f"Player {player_id} cannot announce not having value {value} at pos {position} - they have it")
            else:
                if value in player.wire:
                    raise ValueError(f"Player {player_id} cannot announce not having value {value} - they possess it")
    
    def _broadcast_not_present(self, not_present_record: NotPresentRecord):
        """
        Broadcast a not-present announcement to all players so they can update their beliefs.
        
        Args:
            not_present_record: The not-present announcement to broadcast
        """
        # Each player's belief system processes the not-present announcement
        for player in self.players:
            if player.belief_system is not None:
                player.belief_system.process_not_present(not_present_record)
    
    def _validate_double_reveal(self, player_id: int, value: Union[int, float], position1: int, position2: int):
        """
        Validate that a double reveal is legal according to game rules.
        
        Args:
            player_id: ID of the player revealing
            value: The value being revealed
            position1: First position
            position2: Second position
        
        Raises:
            ValueError: If the double reveal violates game rules
        """
        # Check if game is over
        if self.game_over:
            raise ValueError("Game is already over")
        
        # Check if player ID is valid
        if player_id < 0 or player_id >= len(self.players):
            raise ValueError(f"Invalid player_id: {player_id}")
        
        # Check if positions are valid
        if position1 < 0 or position1 >= self.config.wires_per_player:
            raise ValueError(f"Invalid position1: {position1}. Must be in [0, {self.config.wires_per_player-1}]")
        if position2 < 0 or position2 >= self.config.wires_per_player:
            raise ValueError(f"Invalid position2: {position2}. Must be in [0, {self.config.wires_per_player-1}]")
        
        # Check if positions are different
        if position1 == position2:
            raise ValueError("position1 and position2 must be different")
        
        # Check if value is valid
        if value not in self.config.wire_values:
            raise ValueError(f"Invalid value: {value}. Must be in {self.config.wire_values}")
        
        # When playing IRL, skip validation that these are actually the last 2 copies
        if not self.config.playing_irl:
            player = self.players[player_id]
            # Check that player actually has this value at these positions
            if player.wire[position1] != value:
                raise ValueError(f"Player {player_id} does not have value {value} at position {position1}")
            if player.wire[position2] != value:
                raise ValueError(f"Player {player_id} does not have value {value} at position {position2}")
            
            # Check that these are indeed the last 2 copies
            # Count how many are already revealed across all players
            revealed_count = 0
            for p in self.players:
                if p.belief_system:
                    revealed_count += p.belief_system.value_trackers[value].get_revealed_count()
            
            total_copies = self.config.wire_distribution[value]
            if revealed_count != total_copies - 2:
                raise ValueError(f"Not the last 2 copies: {revealed_count} already revealed out of {total_copies}")
    
    def _broadcast_double_reveal(self, reveal_record: DoubleRevealRecord):
        """
        Broadcast a double reveal to all players so they can update their beliefs.
        
        Args:
            reveal_record: The double reveal to broadcast
        """
        # Each player's belief system processes the double reveal
        for player in self.players:
            if player.belief_system is not None:
                player.belief_system.process_double_reveal(reveal_record)
    
    def swap_wires(self, player1_id: int, player2_id: int, 
                   init_pos1: int, init_pos2: int,
                   final_pos1: int, final_pos2: int,
                   player1_received_value: Optional[Union[int, float]] = None,
                   player2_received_value: Optional[Union[int, float]] = None) -> SwapRecord:
        """
        Process a wire swap between two players.
        Players exchange wires which are then inserted into their sorted positions.
        
        Args:
            player1_id: ID of first player
            player2_id: ID of second player
            init_pos1: Initial position in player1's wire (0-indexed)
            init_pos2: Initial position in player2's wire (0-indexed)
            final_pos1: Final position where player1 receives the wire (0-indexed, in shortened list)
            final_pos2: Final position where player2 receives the wire (0-indexed, in shortened list)
            player1_received_value: Optional value that player1 received (for IRL override)
            player2_received_value: Optional value that player2 received (for IRL override)
        
        Returns:
            SwapRecord with the result
        
        Raises:
            ValueError: If the swap is invalid
        """
        
        final_pos1 = final_pos1 + 1 if final_pos1 >= init_pos1 else final_pos1
        final_pos2 = final_pos2 + 1 if final_pos2 >= init_pos2 else final_pos2
        
        # Get the actual wires
        player1 = self.players[player1_id]
        player2 = self.players[player2_id]
        
        # Extract values being swapped
        value_from_p1 = player1.wire[init_pos1]
        value_from_p2 = player2.wire[init_pos2]
        
        # Use provided received values if specified (IRL mode), otherwise use swapped values
        value_p1_receives = player1_received_value if player1_received_value is not None else value_from_p2
        value_p2_receives = player2_received_value if player2_received_value is not None else value_from_p1
        
        # Validate the swap
        self._validate_swap(player1_id, player2_id, init_pos1, init_pos2, final_pos1, final_pos2)
       
        # Replace initial positions with None (keeps indexing stable)
        player1.wire[init_pos1] = None
        player2.wire[init_pos2] = None
        
        # Insert received wires at final positions
        player1.wire.insert(final_pos1, value_p1_receives)
        player2.wire.insert(final_pos2, value_p2_receives)
        
        # Remove None values
        player1.wire = [v for v in player1.wire if v is not None]
        player2.wire = [v for v in player2.wire if v is not None]
        
        # Create swap record with values (both players know what they received)
        swap_record = SwapRecord(
            player1_id=player1_id,
            player2_id=player2_id,
            player1_init_pos=init_pos1,
            player2_init_pos=init_pos2,
            player1_final_pos=final_pos1,
            player2_final_pos=final_pos2,
            player1_received_value=value_p1_receives,
            player2_received_value=value_p2_receives,
            turn_number=self.current_turn
        )
        
        # Broadcast to all players
        self._broadcast_swap(swap_record)
        
        # Check win condition
        self._check_win_condition()
        
        # Increment turn
        self.current_turn += 1
        
        return swap_record
    
    def _validate_swap(self, player1_id: int, player2_id: int,
                       init_pos1: int, init_pos2: int,
                       final_pos1: int, final_pos2: int):
        """
        Validate that a swap is legal according to game rules.
        
        Args:
            player1_id: ID of first player
            player2_id: ID of second player
            init_pos1: Initial position in player1's wire
            init_pos2: Initial position in player2's wire
            final_pos1: Final position for player1
            final_pos2: Final position for player2
        
        Raises:
            ValueError: If the swap violates game rules
        """
        # Check if game is over
        if self.game_over:
            raise ValueError("Game is already over")
        
        # Check if player IDs are valid
        if player1_id < 0 or player1_id >= len(self.players):
            raise ValueError(f"Invalid player1_id: {player1_id}")
        if player2_id < 0 or player2_id >= len(self.players):
            raise ValueError(f"Invalid player2_id: {player2_id}")
        
        # Check if players are different
        if player1_id == player2_id:
            raise ValueError("Cannot swap wires with yourself")
        
        # Check if initial positions are valid
        if init_pos1 < 0 or init_pos1 >= self.config.wires_per_player:
            raise ValueError(f"Invalid init_pos1: {init_pos1}")
        if init_pos2 < 0 or init_pos2 >= self.config.wires_per_player:
            raise ValueError(f"Invalid init_pos2: {init_pos2}")
        
        # Check if final positions are valid
        # Note: After removing a wire, valid range is [0, wires_per_player-1]
        # if final_pos1 < 0 or final_pos1 >= self.config.wires_per_player:
        #     raise ValueError(f"Invalid final_pos1: {final_pos1}")
        # if final_pos2 < 0 or final_pos2 >= self.config.wires_per_player:
        #     raise ValueError(f"Invalid final_pos2: {final_pos2}")
        
        # When not in IRL mode, validate that final positions maintain sorted order
        if not self.config.playing_irl:
            player1 = self.players[player1_id]
            player2 = self.players[player2_id]
            
            value_from_p1 = player1.wire[init_pos1]
            value_from_p2 = player2.wire[init_pos2]
            
            # Simulate the swap to validate sorting using the same None-replacement approach
            # Check if inserting value_from_p2 at final_pos1 maintains order for player1
            temp_wire1 = player1.wire.copy()
            temp_wire1[init_pos1] = None  # Replace with None instead of pop
            temp_wire1.insert(final_pos1, value_from_p2)
            temp_wire1 = [v for v in temp_wire1 if v is not None]  # Remove None
            if temp_wire1 != sorted(temp_wire1):
                raise ValueError(f"Player1 final position {final_pos1} would break sorting")
            
            # Check if inserting value_from_p1 at final_pos2 maintains order for player2
            temp_wire2 = player2.wire.copy()
            temp_wire2[init_pos2] = None  # Replace with None instead of pop
            temp_wire2.insert(final_pos2, value_from_p1)
            temp_wire2 = [v for v in temp_wire2 if v is not None]  # Remove None
            if temp_wire2 != sorted(temp_wire2):
                raise ValueError(f"Player2 final position {final_pos2} would break sorting")
    
    def _broadcast_swap(self, swap_record: SwapRecord):
        """
        Broadcast a swap to all players so they can update their beliefs.
        
        Args:
            swap_record: The swap to broadcast
        """
        # Each player's belief system processes the swap
        for player in self.players:
            if player.belief_system is not None:
                player.belief_system.process_swap(swap_record)
    
    def _validate_call(self, caller_id: int, target_id: int, position: int, value: Union[int, float]):
        """
        Validate that a call is legal according to game rules.
        Does NOT check if the call is correct (that's provided by the user).
        
        Args:
            caller_id: ID of the player making the call
            target_id: ID of the player being called
            position: Wire position being called
            value: The value being called (can be int or float)
        
        Raises:
            ValueError: If the call violates game rules
        """
        # Check if game is over
        if self.game_over:
            raise ValueError("Game is already over")
        
        # Check if caller and target are different
        if caller_id == target_id:
            raise ValueError("Cannot call yourself")
        
        # Check if player IDs are valid
        if caller_id < 0 or caller_id >= len(self.players):
            raise ValueError(f"Invalid caller_id: {caller_id}")
        if target_id < 0 or target_id >= len(self.players):
            raise ValueError(f"Invalid target_id: {target_id}")
        
        # Check if position is valid
        if position < 0 or position >= self.config.wires_per_player:
            raise ValueError(f"Invalid position: {position}. Must be in [0, {self.config.wires_per_player-1}]")
        
        # Check if value is valid
        if value not in self.config.wire_values:
            raise ValueError(f"Invalid value: {value}. Must be in {self.config.wire_values}")
        
        # Check if caller possesses this value (can only call values you have)
        # Skip this check when playing IRL to avoid inconsistencies with physical cards
        if not self.config.playing_irl:
            caller = self.players[caller_id]
            if not caller.has_value(value):
                raise ValueError(f"Player {caller_id} cannot call value {value} - they don't possess it")
    
    def _broadcast_call(self, call_record: CallRecord):
        """
        Broadcast a call to all players so they can update their beliefs.
        This maintains independence: each player updates based on public information.
        
        Args:
            call_record: The call to broadcast
        """
        # Each player's belief system processes the call
        for player in self.players:
            if player.belief_system is not None:
                player.belief_system.process_call(call_record)
    
    def _check_win_condition(self):
        """
        Check if the team has won or lost.
        
        WIN: All positions across all players are revealed/certain
        LOSE: wrong_calls_count >= max_wrong_calls
        """
        # Check loss condition first
        if self.wrong_calls_count >= self.config.max_wrong_calls:
            self.game_over = True
            self.team_won = False
            return
        
        # Check win condition
        if self._check_all_positions_revealed():
            self.game_over = True
            self.team_won = True
            return
    
    def _check_all_positions_revealed(self) -> bool:
        """
        Check if all positions across all players are revealed/certain.
        
        A position is "revealed" if all players' belief systems agree it's certain,
        not just if the owning player knows it.
        
        Returns:
            True if all positions are deduced by everyone
        """
        # Check if every player's belief system has deduced all positions for all players
        for player in self.players:
            if player.belief_system is None:
                if self.config.playing_irl:
                    continue
                return False
            
            # Check if this player has deduced all positions for all players
            for target_player_id in range(self.config.n_players):
                if not player.belief_system.is_fully_deduced(target_player_id):
                    return False
        
        return True
    
    def get_wrong_calls_remaining(self) -> int:
        """
        Get how many wrong calls are allowed before losing.
        
        Returns:
            Number of wrong calls remaining before game over
        """
        return max(0, self.config.max_wrong_calls - self.wrong_calls_count)
    
    def get_game_state(self) -> Dict:
        """
        Get the current public game state.
        
        Returns:
            Dictionary with public game information:
            - turn: current turn number
            - wrong_calls_count: number of wrong calls made
            - wrong_calls_remaining: allowed wrong calls before loss
            - game_over: whether game has ended
            - team_won: True/False/None for win/loss/ongoing
            - total_calls: total number of calls made
        """
        return {
            'turn': self.current_turn,
            'wrong_calls_count': self.wrong_calls_count,
            'wrong_calls_remaining': self.get_wrong_calls_remaining(),
            'game_over': self.game_over,
            'team_won': self.team_won,
            'total_calls': len(self.call_history)
        }
    
    def get_observation_for_player(self, player_id: int) -> GameObservation:
        """
        Get the observation (available information) for a specific player.
        This ensures independence: only information available to this player.
        
        Args:
            player_id: The player to get observation for
        
        Returns:
            GameObservation with all information available to this player
        """
        player = self.players[player_id]
        
        return GameObservation(
            player_id=player_id,
            my_wire=player.wire if player.wire is not None else [],
            my_revealed_positions=player.revealed_positions.copy(),
            call_history=self.call_history.copy(),
            n_players=self.config.n_players,
            wire_length=self.config.wires_per_player
        )
    
    def is_game_over(self) -> bool:
        """
        Check if the game has ended (win or loss).
        
        Returns:
            True if game is over
        """
        return self.game_over
    
    def has_team_won(self) -> Optional[bool]:
        """
        Check if the team won or lost.
        
        Returns:
            True if team won, False if team lost, None if game ongoing
        """
        return self.team_won
    
    def reset(self):
        """
        Reset the game to initial state.
        Useful for playing multiple games in sequence.
        """
        self.call_history = []
        self.current_turn = 0
        self.wrong_calls_count = 0
        self.game_over = False
        self.team_won = None
        
        # Reinitialize belief systems
        self._initialize_belief_systems()
