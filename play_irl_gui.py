"""
BombBuster IRL GUI - Graphical interface for real-life gameplay.
A simple, click-based interface for recording game actions without typing.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

from config.game_config import GameConfig
from src.game import Game
from src.player import Player
from src.utils import (
    run_irl_game_session,
    save_action_history,
    load_action_history
)
from gui_config import (
    MY_PLAYER_NAME,
    MY_WIRE,
    PLAYER_NAMES,
    BELIEF_FOLDER,
    AUTO_SAVE,
    LOAD_EXISTING
)


class BombBusterGUI:
    """Main GUI application for BombBuster IRL gameplay."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BombBuster - IRL Tracker")
        self.root.geometry("1200x900")
        
        # Load configuration from gui_config.py
        self.my_wire = MY_WIRE
        self.player_names = {i: name for i, name in enumerate(PLAYER_NAMES)}
        self.belief_folder = BELIEF_FOLDER
        self.auto_save = AUTO_SAVE
        self.load_existing = LOAD_EXISTING
        
        # Find my player ID
        self.my_player_id = 0
        for pid, name in self.player_names.items():
            if name == MY_PLAYER_NAME:
                self.my_player_id = pid
                break
        
        # Action history
        self.calls = []
        self.double_reveals = []
        self.swaps = []
        self.signals = []
        self.not_present = []
        
        # Game objects
        self.game = None
        self.my_player = None
        
        # UI state
        self.current_action_type = "call"
        
        # Create config
        self.config = GameConfig(playing_irl=True)
        
        # Load existing actions if available
        if self.load_existing:
            old_history = load_action_history(self.belief_folder, self.my_player_id)
            if old_history:
                self.calls = old_history.get("calls", [])
                self.double_reveals = old_history.get("double_reveals", [])
                self.swaps = old_history.get("swaps", [])
                self.signals = old_history.get("signals", [])
                self.not_present = old_history.get("not_present", [])
        
        # Initialize game
        self.initialize_game()
        
        # Setup UI
        self.setup_main_ui()
    
    def initialize_game(self):
        """Initialize the game with current settings."""
        result = run_irl_game_session(
            my_wire=self.my_wire,
            my_player_id=self.my_player_id,
            calls=self.calls,
            config=self.config,
            belief_folder=self.belief_folder,
            player_names=self.player_names,
            double_reveals=self.double_reveals,
            swaps=self.swaps,
            signals=self.signals,
            not_present=self.not_present,
            save_to_json=self.auto_save,
            load_from_json=self.load_existing
        )
        
        self.game = result['game']
        self.my_player = result['my_player']
    
    def setup_main_ui(self):
        """Setup the main application interface."""
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Title bar
        self.setup_title_bar()
        
        # Action type selector
        self.setup_action_selector()
        
        # Action panels container
        self.action_container = tk.Frame(self.root)
        self.action_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create all action panels
        self.setup_action_panels()
        
        # Action log
        self.setup_action_log()
        
        # Game state
        self.setup_game_state()
        
        # Show default panel
        self.switch_action_panel("call")
    
    def setup_title_bar(self):
        """Setup the title bar with action buttons."""
        title_frame = tk.Frame(self.root, bg="#4A90E2", height=50)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text="BOMBBUSTER - IRL TRACKER", 
                font=("Arial", 14, "bold"), bg="#4A90E2", fg="white").pack(side=tk.LEFT, padx=20)
        
        button_frame = tk.Frame(title_frame, bg="#4A90E2")
        button_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Button(button_frame, text="Save & Refresh", command=self.save_and_refresh,
                 bg="white", padx=10).pack(side=tk.LEFT, padx=5)
    
    def setup_action_selector(self):
        """Setup action type selector buttons."""
        selector_frame = tk.Frame(self.root, bg="#f0f0f0", height=60)
        selector_frame.pack(fill=tk.X, padx=10, pady=5)
        selector_frame.pack_propagate(False)
        
        tk.Label(selector_frame, text="ACTION TYPE:", bg="#f0f0f0", 
                font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
        
        actions = [
            ("CALL", "call"),
            ("SWAP", "swap"),
            ("DOUBLE REVEAL", "double_reveal"),
            ("SIGNAL", "signal"),
            ("NOT PRESENT", "not_present")
        ]
        
        self.action_buttons = {}
        for label, action_type in actions:
            btn = tk.Button(selector_frame, text=label, 
                          command=lambda at=action_type: self.switch_action_panel(at),
                          padx=15, pady=5, font=("Arial", 9))
            btn.pack(side=tk.LEFT, padx=5)
            self.action_buttons[action_type] = btn
    
    def setup_action_panels(self):
        """Create all action panels."""
        self.call_panel = CallActionPanel(self.action_container, self)
        self.swap_panel = SwapActionPanel(self.action_container, self)
        self.double_reveal_panel = DoubleRevealActionPanel(self.action_container, self)
        self.signal_panel = SignalActionPanel(self.action_container, self)
        self.not_present_panel = NotPresentActionPanel(self.action_container, self)
        
        self.panels = {
            "call": self.call_panel,
            "swap": self.swap_panel,
            "double_reveal": self.double_reveal_panel,
            "signal": self.signal_panel,
            "not_present": self.not_present_panel
        }
    
    def switch_action_panel(self, action_type):
        """Switch to the specified action panel."""
        # Hide all panels
        for panel in self.panels.values():
            panel.pack_forget()
        
        # Show selected panel
        self.panels[action_type].pack(fill=tk.BOTH, expand=True)
        
        # Update button styles
        for at, btn in self.action_buttons.items():
            if at == action_type:
                btn.config(bg="#4A90E2", fg="white", relief=tk.SUNKEN)
            else:
                btn.config(bg="white", fg="black", relief=tk.RAISED)
        
        self.current_action_type = action_type
    
    def draw_player_hand(self, parent_frame, player_id, title=None, position_key=None, panel=None):
        """Draw a player's hand visualization in the given frame.
        
        Args:
            parent_frame: The frame to draw in
            player_id: The player whose hand to display
            title: Optional title text (defaults to player name)
            position_key: If provided, highlights selected positions from this key
            panel: The panel to check for selections
        """
        # Clear the frame
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        if not self.my_player or not self.my_player.belief_system:
            return
        
        player_name = self.player_names.get(player_id, f"Player {player_id}")
        
        # Title
        if title is None:
            title = f"{player_name}'s Hand"
        
        title_label = tk.Label(parent_frame, text=title, font=("Arial", 10, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Wire cards frame
        cards_frame = tk.Frame(parent_frame)
        cards_frame.pack()
        
        # Get beliefs for this player
        beliefs = self.my_player.belief_system.beliefs[player_id]
        value_trackers = self.my_player.belief_system.value_trackers
        
        # Determine if we need to reverse (if viewing another player, show reversed)
        positions = range(self.config.wires_per_player)
        if player_id != self.my_player_id:
            positions = reversed(positions)
            positions = list(positions)  # Convert to list for indexing
        
        for display_col, pos in enumerate(positions):
            pos_beliefs = beliefs[pos]
            
            # Determine the state of this position
            display_value = ""
            bg_color = "white"
            border_width = 2
            border_color = "black"
            
            if len(pos_beliefs) == 1:
                # Single value - either revealed or certain
                value = list(pos_beliefs)[0]
                display_value = str(value)
                
                # Check if it's revealed
                is_revealed = False
                for rev_pid, rev_pos in value_trackers[value].revealed:
                    if rev_pid == player_id and rev_pos == pos:
                        is_revealed = True
                        bg_color = "#7ED321"  # Green for revealed
                        break
                
                if not is_revealed:
                    # It's certain (deduced)
                    bg_color = "#F8E71C"  # Yellow for certain
            
            # Check if this position is currently selected
            is_selected = False
            if panel and position_key:
                # Check if this position matches any selection
                if position_key in panel.selections and panel.selections[position_key] == pos:
                    is_selected = True
                # For double reveal, check both positions
                if 'position1' in panel.selections and panel.selections['position1'] == pos:
                    is_selected = True
                if 'position2' in panel.selections and panel.selections['position2'] == pos:
                    is_selected = True
            
            if is_selected:
                border_width = 4
                border_color = "#F5A623"  # Orange border for selected
            
            # Create card frame
            card_frame = tk.Frame(cards_frame, relief=tk.RIDGE, borderwidth=border_width,
                                 highlightbackground=border_color, highlightthickness=border_width,
                                 bg=border_color)
            card_frame.grid(row=0, column=display_col, padx=2)
            
            # Value display (non-clickable, just visual reference)
            value_label = tk.Label(card_frame, text=display_value, width=4, height=3,
                                  bg=bg_color, font=("Arial", 12, "bold"))
            value_label.pack()
            
            # Position label below
            pos_label = tk.Label(card_frame, text=f"Pos {pos+1}", 
                               font=("Arial", 8), bg="#f0f0f0")
            pos_label.pack(fill=tk.X)
        
        # Legend (compact version)
        legend_frame = tk.Frame(parent_frame)
        legend_frame.pack(pady=5)
        
        tk.Label(legend_frame, text="🟢 Revealed  ", font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
        tk.Label(legend_frame, text="🟡 Certain  ", font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
        tk.Label(legend_frame, text="⚪ Uncertain  ", font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
        tk.Label(legend_frame, text="🟠 Selected", font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
    
    def setup_action_log(self):
        """Setup the recent actions log."""
        log_frame = tk.LabelFrame(self.root, text="RECENT ACTIONS (Last 10)",
                                 font=("Arial", 10, "bold"), padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.action_log = scrolledtext.ScrolledText(log_frame, height=8, width=80,
                                                     font=("Courier", 9))
        self.action_log.pack(fill=tk.BOTH, expand=True)
        self.action_log.config(state=tk.DISABLED)
        
        self.update_action_log()
    
    def setup_game_state(self):
        """Setup the game state display."""
        state_frame = tk.Frame(self.root, bg="#f0f0f0", height=50)
        state_frame.pack(fill=tk.X, padx=10, pady=5)
        state_frame.pack_propagate(False)
        
        self.state_label = tk.Label(state_frame, text="", bg="#f0f0f0", 
                                    font=("Arial", 10))
        self.state_label.pack(pady=10)
        
        self.update_game_state()
    
    def update_action_log(self):
        """Update the action log display."""
        self.action_log.config(state=tk.NORMAL)
        self.action_log.delete("1.0", tk.END)
        
        # Show last 10 actions
        all_actions = []
        for i, call in enumerate(self.calls):
            all_actions.append(("CALL", i, call))
        for i, reveal in enumerate(self.double_reveals):
            all_actions.append(("REVEAL", i, reveal))
        for i, swap in enumerate(self.swaps):
            all_actions.append(("SWAP", i, swap))
        for i, signal in enumerate(self.signals):
            all_actions.append(("SIGNAL", i, signal))
        for i, np in enumerate(self.not_present):
            all_actions.append(("NOT_PRESENT", i, np))
        
        recent = all_actions[-10:]
        
        for i, (action_type, idx, action) in enumerate(reversed(recent)):
            turn_num = len(all_actions) - len(recent) + len(recent) - i
            self.action_log.insert(tk.END, f"Turn {turn_num}: ")
            
            if action_type == "CALL":
                caller = self.player_names.get(action[0] if isinstance(action[0], int) else 0, action[0])
                target = self.player_names.get(action[1] if isinstance(action[1], int) else 0, action[1])
                result = "SUCCESS" if action[4] else "FAIL"
                self.action_log.insert(tk.END, f"{caller} → {target}[{action[2]+1}] = {action[3]} [{result}]\n")
            elif action_type == "SIGNAL":
                player = self.player_names.get(action[0] if isinstance(action[0], int) else 0, action[0])
                self.action_log.insert(tk.END, f"{player} SIGNALS [{action[2]+1}] = {action[1]}\n")
            elif action_type == "NOT_PRESENT":
                player = self.player_names.get(action[0] if isinstance(action[0], int) else 0, action[0])
                self.action_log.insert(tk.END, f"{player} NOT PRESENT value={action[1]}\n")
            else:
                self.action_log.insert(tk.END, f"{action}\n")
        
        self.action_log.config(state=tk.DISABLED)
    
    def update_game_state(self):
        """Update the game state display."""
        if self.game:
            state = self.game.get_game_state()
            status = "🟢 ONGOING"
            if state['game_over']:
                status = "🎉 WON!" if state['team_won'] else "💥 LOST!"
            
            text = (f"Turn: {state['turn']}  |  "
                   f"Total Actions: {state['total_calls']}  |  "
                   f"Wrong Calls: {state['wrong_calls_count']}/{self.config.max_wrong_calls}  |  "
                   f"Status: {status}")
            self.state_label.config(text=text)
    
    def add_action(self, action_type, action_data):
        """Add an action and refresh the game."""
        try:
            if action_type == "call":
                self.calls.append(action_data)
            elif action_type == "swap":
                self.swaps.append(action_data)
            elif action_type == "double_reveal":
                self.double_reveals.append(action_data)
            elif action_type == "signal":
                self.signals.append(action_data)
            elif action_type == "not_present":
                self.not_present.append(action_data)
            
            # Refresh game
            self.save_and_refresh()
            
            messagebox.showinfo("Success", "Action added successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add action:\n{str(e)}")
    
    def save_and_refresh(self):
        """Save current state and refresh the game."""
        try:
            # Re-initialize game with all actions
            self.initialize_game()
            
            # Refresh displays
            self.update_action_log()
            self.update_game_state()
            
            # Refresh hand viewers in the current action panel
            current_panel = self.panels.get(self.current_action_type)
            if current_panel and hasattr(current_panel, 'hand_viewer_frame'):
                # Refresh all hand frames in the panel
                for player_key in ['caller', 'target', 'player', 'player1', 'player2']:
                    if player_key in current_panel.selections and hasattr(current_panel, f'{player_key}_hand_frame'):
                        frame = getattr(current_panel, f'{player_key}_hand_frame')
                        player_id = current_panel.selections[player_key]
                        position_key = current_panel.get_position_key_for_player(player_key)
                        self.draw_player_hand(frame, player_id, position_key=position_key, panel=current_panel)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh:\n{str(e)}")
    
    def run(self):
        """Run the GUI application."""
        self.root.mainloop()


class ActionPanel(tk.Frame):
    """Base class for action panels."""
    
    def __init__(self, parent, app):
        super().__init__(parent, relief=tk.RIDGE, borderwidth=2)
        self.app = app
        self.selections = {}
    
    def create_player_buttons(self, parent, label, key):
        """Create player selection buttons."""
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        tk.Label(frame, text=label, width=20, anchor=tk.W).pack(side=tk.LEFT)
        
        button_frame = tk.Frame(frame)
        button_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        for pid, name in self.app.player_names.items():
            btn = tk.Button(button_frame, text=name, width=10,
                          command=lambda p=pid: self.select_player(key, p))
            btn.pack(side=tk.LEFT, padx=2)
            if f"{key}_buttons" not in self.selections:
                self.selections[f"{key}_buttons"] = []
            self.selections[f"{key}_buttons"].append((pid, btn))
    
    def create_position_buttons(self, parent, label, key):
        """Create position selection buttons."""
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        tk.Label(frame, text=label, anchor=tk.W).pack()
        
        button_frame = tk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        for pos in range(self.app.config.wires_per_player):
            btn = tk.Button(button_frame, text=str(pos + 1), width=3,
                          command=lambda p=pos: self.select_position(key, p))
            btn.pack(side=tk.LEFT, padx=1)
            if f"{key}_buttons" not in self.selections:
                self.selections[f"{key}_buttons"] = []
            self.selections[f"{key}_buttons"].append((pos, btn))
    
    def create_value_buttons(self, parent, label, key):
        """Create value selection buttons."""
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        tk.Label(frame, text=label, anchor=tk.W).pack()
        
        button_frame = tk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        for value in self.app.config.wire_values:
            btn = tk.Button(button_frame, text=str(value), width=4,
                          command=lambda v=value: self.select_value(key, v))
            btn.pack(side=tk.LEFT, padx=1)
            if f"{key}_buttons" not in self.selections:
                self.selections[f"{key}_buttons"] = []
            self.selections[f"{key}_buttons"].append((value, btn))
    
    def select_player(self, key, player_id):
        """Handle player button selection."""
        self.selections[key] = player_id
        for pid, btn in self.selections.get(f"{key}_buttons", []):
            if pid == player_id:
                btn.config(bg="#4A90E2", fg="white", relief=tk.SUNKEN)
            else:
                btn.config(bg="white", fg="black", relief=tk.RAISED)
        
        # Update hand display if this panel has a hand viewer frame
        if hasattr(self, 'hand_viewer_frame') and hasattr(self, f'{key}_hand_frame'):
            frame = getattr(self, f'{key}_hand_frame')
            # Determine the position key for highlighting selected positions
            position_key = self.get_position_key_for_player(key)
            self.app.draw_player_hand(frame, player_id, position_key=position_key, panel=self)
    
    def get_position_key_for_player(self, player_key):
        """Get the corresponding position key for a player selection.
        Override in subclasses if needed.
        """
        # Default mapping for most panels
        position_map = {
            'caller': 'caller_position',  # Caller can select position on their hand (optional)
            'target': 'position',
            'player': 'position',
            'player1': 'init_pos1',
            'player2': 'init_pos2',
        }
        return position_map.get(player_key, None)
    
    def select_position(self, key, position):
        """Handle position button selection."""
        self.selections[key] = position
        for pos, btn in self.selections.get(f"{key}_buttons", []):
            if pos == position:
                btn.config(bg="#F5A623", fg="white", relief=tk.SUNKEN)
            else:
                btn.config(bg="white", fg="black", relief=tk.RAISED)
        
        # Redraw hand viewer to show selection if applicable
        if hasattr(self, 'hand_viewer_frame'):
            # Find which player's hand to redraw
            for player_key in ['caller', 'target', 'player', 'player1', 'player2']:
                if player_key in self.selections and hasattr(self, f'{player_key}_hand_frame'):
                    frame = getattr(self, f'{player_key}_hand_frame')
                    position_key = self.get_position_key_for_player(player_key)
                    self.app.draw_player_hand(frame, self.selections[player_key], 
                                             position_key=position_key, panel=self)
                    break
    
    def select_value(self, key, value):
        """Handle value button selection."""
        self.selections[key] = value
        for val, btn in self.selections.get(f"{key}_buttons", []):
            if val == value:
                btn.config(bg="#BD10E0", fg="white", relief=tk.SUNKEN)
            else:
                btn.config(bg="white", fg="black", relief=tk.RAISED)
    
    def clear_selections(self):
        """Clear all selections."""
        # Reset button styles before clearing selections dict
        for key in list(self.selections.keys()):
            if key.endswith("_buttons"):
                for _, btn in self.selections[key]:
                    btn.config(bg="white", fg="black", relief=tk.RAISED)
        
        # Clear selections
        self.selections = {}
        
        # Clear hand viewer frames
        for player_key in ['caller', 'target', 'player', 'player1', 'player2']:
            if hasattr(self, f'{player_key}_hand_frame'):
                frame = getattr(self, f'{player_key}_hand_frame')
                for widget in frame.winfo_children():
                    widget.destroy()


class CallActionPanel(ActionPanel):
    """Panel for making calls."""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.hand_viewer_frame = True  # Flag to enable hand viewing
        
        tk.Label(self, text="CALL ACTION", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.create_player_buttons(self, "Caller:", "caller")
        
        # Hand viewer for caller
        self.caller_hand_frame = tk.Frame(self)
        self.caller_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Caller position (optional, shown based on result)
        self.caller_pos_frame = tk.Frame(self)
        self.caller_pos_frame.pack(fill=tk.X, pady=5, padx=10)  # Pack it by default (success is default)
        tk.Label(self.caller_pos_frame, text="Caller Position (optional):", anchor=tk.W).pack()
        self.create_position_buttons(self.caller_pos_frame, "", "caller_position")
        
        self.create_player_buttons(self, "Target:", "target")
        
        # Hand viewer for target (visual reference only)
        self.target_hand_frame = tk.Frame(self)
        self.target_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Position selection buttons
        self.create_position_buttons(self, "Position:", "position")
        
        # Value selection
        self.create_value_buttons(self, "Value:", "value")
        
        # Result
        result_frame = tk.Frame(self)
        result_frame.pack(fill=tk.X, pady=10)
        tk.Label(result_frame, text="Result:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        
        self.result_var = tk.StringVar(value="success")
        tk.Radiobutton(result_frame, text="SUCCESS", variable=self.result_var, 
                      value="success", command=self.toggle_caller_position).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(result_frame, text="FAIL", variable=self.result_var, 
                      value="fail", command=self.toggle_caller_position).pack(side=tk.LEFT, padx=10)
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Add Call", command=self.add_call,
                 bg="#7ED321", fg="white", padx=20, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear", command=self.clear,
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)
    
    def toggle_caller_position(self):
        """Enable/disable caller position based on result."""
        if self.result_var.get() == "success":
            # Show caller position frame if not already visible
            if not self.caller_pos_frame.winfo_ismapped():
                # Pack it after caller_hand_frame
                self.caller_pos_frame.pack(after=self.caller_hand_frame, fill=tk.X, pady=5, padx=10)
        else:
            self.caller_pos_frame.pack_forget()
    
    def add_call(self):
        """Add the call action."""
        if "caller" not in self.selections or "target" not in self.selections:
            messagebox.showwarning("Incomplete", "Please select both caller and target")
            return
        
        if "position" not in self.selections or "value" not in self.selections:
            messagebox.showwarning("Incomplete", "Please select position and value")
            return
        
        caller_name = self.app.player_names[self.selections["caller"]]
        target_name = self.app.player_names[self.selections["target"]]
        position = self.selections["position"] + 1  # Convert to 1-indexed
        value = self.selections["value"]
        success = self.result_var.get() == "success"
        
        # Build action tuple
        if success and "caller_position" in self.selections:
            caller_pos = self.selections["caller_position"] + 1
            action = (caller_name, target_name, position, value, success, caller_pos)
        else:
            action = (caller_name, target_name, position, value, success)
        
        self.app.add_action("call", action)
        self.clear()
    
    def clear(self):
        """Clear all selections."""
        self.clear_selections()
        self.result_var.set("success")


class SwapActionPanel(ActionPanel):
    """Panel for swap actions."""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.hand_viewer_frame = True  # Flag to enable hand viewing
        
        tk.Label(self, text="SWAP ACTION", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.create_player_buttons(self, "Player 1:", "player1")
        
        # Hand viewer for player 1 (visual reference only)
        self.player1_hand_frame = tk.Frame(self)
        self.player1_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Position selection buttons
        self.create_position_buttons(self, "Initial Position (P1):", "init_pos1")
        
        self.create_player_buttons(self, "Player 2:", "player2")
        
        # Hand viewer for player 2 (visual reference only)
        self.player2_hand_frame = tk.Frame(self)
        self.player2_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Position selection buttons
        self.create_position_buttons(self, "Initial Position (P2):", "init_pos2")
        
        tk.Label(self, text="─── After removing wires ───", font=("Arial", 9, "italic")).pack(pady=5)
        
        self.create_position_buttons(self, "Final Position (P1):", "final_pos1")
        self.create_position_buttons(self, "Final Position (P2):", "final_pos2")
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Add Swap", command=self.add_swap,
                 bg="#7ED321", fg="white", padx=20, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear", command=self.clear,
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)
    
    def add_swap(self):
        """Add the swap action."""
        required = ["player1", "player2", "init_pos1", "init_pos2", "final_pos1", "final_pos2"]
        if not all(k in self.selections for k in required):
            messagebox.showwarning("Incomplete", "Please complete all fields")
            return
        
        p1 = self.app.player_names[self.selections["player1"]]
        p2 = self.app.player_names[self.selections["player2"]]
        
        # Convert to 1-indexed
        action = (
            p1, p2,
            self.selections["init_pos1"] + 1,
            self.selections["init_pos2"] + 1,
            self.selections["final_pos1"] + 1,
            self.selections["final_pos2"] + 1
        )
        
        self.app.add_action("swap", action)
        self.clear()
    
    def clear(self):
        """Clear all selections."""
        self.clear_selections()


class DoubleRevealActionPanel(ActionPanel):
    """Panel for double reveal actions."""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.hand_viewer_frame = True  # Flag to enable hand viewing
        
        tk.Label(self, text="DOUBLE REVEAL ACTION", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.create_player_buttons(self, "Player:", "player")
        
        # Hand viewer for player (visual reference only)
        self.player_hand_frame = tk.Frame(self)
        self.player_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Show which positions are selected
        self.position_status_frame = tk.Frame(self)
        self.position_status_frame.pack(pady=5)
        self.position_status_label = tk.Label(self.position_status_frame, text="Select 2 positions below",
                                             font=("Arial", 9, "italic"))
        self.position_status_label.pack()
        
        # Position selection buttons
        self.create_position_buttons(self, "Position 1:", "position1")
        self.create_position_buttons(self, "Position 2:", "position2")
        
        self.create_value_buttons(self, "Value:", "value")
        
        tk.Label(self, text="ℹ️ Use when revealing the last 2 copies of a value",
                font=("Arial", 9, "italic")).pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Add Double Reveal", command=self.add_reveal,
                 bg="#7ED321", fg="white", padx=20, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear", command=self.clear,
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)
    
    def select_position(self, key, position):
        """Override to update hand display and redraw it."""
        super().select_position(key, position)
        # Redraw hand to show selection highlight
        if 'player' in self.selections:
            self.app.draw_player_hand(self.player_hand_frame, self.selections['player'], 
                                     position_key='position1', panel=self)
    
    def add_reveal(self):
        """Add the double reveal action."""
        required = ["player", "value", "position1", "position2"]
        if not all(k in self.selections for k in required):
            messagebox.showwarning("Incomplete", "Please complete all fields")
            return
        
        player = self.app.player_names[self.selections["player"]]
        value = self.selections["value"]
        pos1 = self.selections["position1"] + 1
        pos2 = self.selections["position2"] + 1
        
        action = (player, value, pos1, pos2)
        
        self.app.add_action("double_reveal", action)
        self.clear()
    
    def clear(self):
        """Clear all selections."""
        self.clear_selections()
        self.position_status_label.config(text="Select 2 positions below")


class SignalActionPanel(ActionPanel):
    """Panel for signal actions."""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.hand_viewer_frame = True  # Flag to enable hand viewing
        
        tk.Label(self, text="SIGNAL ACTION", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.create_player_buttons(self, "Player:", "player")
        
        # Hand viewer for player (visual reference only)
        self.player_hand_frame = tk.Frame(self)
        self.player_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Position selection buttons
        self.create_position_buttons(self, "Position:", "position")
        
        self.create_value_buttons(self, "Value:", "value")
        
        tk.Label(self, text="ℹ️ Use when a player announces they know a specific wire",
                font=("Arial", 9, "italic")).pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Add Signal", command=self.add_signal,
                 bg="#7ED321", fg="white", padx=20, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear", command=self.clear,
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)
    
    def add_signal(self):
        """Add the signal action."""
        required = ["player", "value", "position"]
        if not all(k in self.selections for k in required):
            messagebox.showwarning("Incomplete", "Please complete all fields")
            return
        
        player = self.app.player_names[self.selections["player"]]
        value = self.selections["value"]
        position = self.selections["position"] + 1
        
        action = (player, value, position)
        
        self.app.add_action("signal", action)
        self.clear()
    
    def clear(self):
        """Clear all selections."""
        self.clear_selections()


class NotPresentActionPanel(ActionPanel):
    """Panel for not present actions."""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.hand_viewer_frame = True  # Flag to enable hand viewing
        
        tk.Label(self, text="NOT PRESENT ACTION", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.create_player_buttons(self, "Player:", "player")
        
        # Hand viewer for player
        self.player_hand_frame = tk.Frame(self)
        self.player_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        self.create_value_buttons(self, "Value:", "value")
        
        tk.Label(self, text="ℹ️ Use when a player announces they don't have this value",
                font=("Arial", 9, "italic")).pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Add Not Present", command=self.add_not_present,
                 bg="#7ED321", fg="white", padx=20, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear", command=self.clear,
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)
    
    def add_not_present(self):
        """Add the not present action."""
        required = ["player", "value"]
        if not all(k in self.selections for k in required):
            messagebox.showwarning("Incomplete", "Please complete all fields")
            return
        
        player = self.app.player_names[self.selections["player"]]
        value = self.selections["value"]
        
        action = (player, value)
        
        self.app.add_action("not_present", action)
        self.clear()
    
    def clear(self):
        """Clear all selections."""
        self.clear_selections()


if __name__ == "__main__":
    app = BombBusterGUI()
    app.run()
