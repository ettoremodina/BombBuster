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
from src.statistics import GameStatistics
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
        self.root.state('zoomed')  # Open in full screen (maximized)
        
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
        self.reveals = []
        self.not_present = []
        self.has_values = []
        
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
                self.reveals = old_history.get("reveals", [])
                self.not_present = old_history.get("not_present", [])
                self.has_values = old_history.get("has_values", [])
        
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
            reveals=self.reveals,
            not_present=self.not_present,
            has_values=self.has_values,
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
        
        # Scrollable container for action panels
        container_frame = tk.Frame(self.root)
        container_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(container_frame)
        scrollbar = tk.Scrollbar(container_frame, orient="vertical", command=self.canvas.yview)
        self.action_container = tk.Frame(self.canvas)
        
        self.action_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.action_container, anchor="nw")
        
        # Configure canvas to resize the window
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Mousewheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create all action panels
        self.setup_action_panels()
        
        # Game state
        self.setup_game_state()
        
        # Show default panel
        self.switch_action_panel("call")

    def _on_canvas_configure(self, event):
        """Handle canvas resize to adjust inner frame width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def setup_title_bar(self):
        """Setup the title bar with action buttons."""
        title_frame = tk.Frame(self.root, bg="#1565C0", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text="BOMBBUSTER - IRL TRACKER", 
                font=("Arial", 16, "bold"), bg="#1565C0", fg="white").pack(side=tk.LEFT, padx=20)
        
        button_frame = tk.Frame(title_frame, bg="#1565C0")
        button_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Button(button_frame, text="SAVE & REFRESH", command=self.save_and_refresh,
                 bg="#FFC107", fg="black", padx=15, pady=5, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
    
    def setup_action_selector(self):
        """Setup action type selector buttons."""
        selector_frame = tk.Frame(self.root, bg="#ECEFF1", height=70)
        selector_frame.pack(fill=tk.X, padx=10, pady=5)
        selector_frame.pack_propagate(False)
        
        tk.Label(selector_frame, text="ACTION TYPE:", bg="#ECEFF1", 
                font=("Arial", 11, "bold"), fg="#455A64").pack(side=tk.LEFT, padx=10)
        
        actions = [
            ("CALL", "call"),
            ("SWAP", "swap"),
            ("DOUBLE REVEAL", "double_reveal"),
            ("SIGNAL", "signal"),
            ("NOT PRESENT", "not_present"),
            ("HAS VALUE", "has_value"),
            ("SUGGESTIONS", "suggestions")
        ]
        
        self.action_buttons = {}
        for label, action_type in actions:
            btn = tk.Button(selector_frame, text=label, 
                          command=lambda at=action_type: self.switch_action_panel(at),
                          padx=15, pady=8, font=("Arial", 9, "bold"))
            btn.pack(side=tk.LEFT, padx=5)
            self.action_buttons[action_type] = btn
    
    def setup_action_panels(self):
        """Create all action panels."""
        self.call_panel = CallActionPanel(self.action_container, self)
        self.swap_panel = SwapActionPanel(self.action_container, self)
        self.double_reveal_panel = DoubleRevealActionPanel(self.action_container, self)
        self.signal_panel = SignalActionPanel(self.action_container, self)
        self.not_present_panel = NotPresentActionPanel(self.action_container, self)
        self.has_value_panel = HasValueActionPanel(self.action_container, self)
        self.suggester_panel = SuggesterPanel(self.action_container, self)
        
        self.panels = {
            "call": self.call_panel,
            "swap": self.swap_panel,
            "double_reveal": self.double_reveal_panel,
            "signal": self.signal_panel,
            "not_present": self.not_present_panel,
            "has_value": self.has_value_panel,
            "suggestions": self.suggester_panel
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
    
    def draw_player_hand(self, parent_frame, player_id, title=None, position_key=None, panel=None, player_key=None, highlight_positions=None, playable_values=None):
        """Draw a player's hand visualization in the given frame.
        
        Args:
            parent_frame: The frame to draw in
            player_id: The player whose hand to display
            title: Optional title text (defaults to player name)
            position_key: If provided, highlights selected positions from this key
            panel: The panel to check for selections
            player_key: The key identifying the player in the panel (e.g. 'caller', 'target')
            highlight_positions: Optional list of position indices to highlight directly
            playable_values: Optional set of values that are playable (for coloring suggestions)
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
        
        if title:
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
            font = ("Arial", 12, "bold")
            
            # Check if this position is currently selected
            is_selected = False
            if highlight_positions is not None:
                if pos in highlight_positions:
                    is_selected = True
            elif panel and position_key:
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
            # Use fixed size to ensure all cards are same size regardless of content
            frame_width = 100
            frame_height = 120
            
            # If in suggestion mode (playable_values set), we might need more space
            if playable_values is not None:
                frame_width = 100
                frame_height = 120
                
            card_frame = tk.Frame(cards_frame, relief=tk.RIDGE, borderwidth=border_width,
                                 highlightbackground=border_color, highlightthickness=border_width,
                                 bg=border_color, width=frame_width, height=frame_height)
            card_frame.pack_propagate(False)
            card_frame.grid(row=0, column=display_col, padx=2)
            
            # Position label below
            pos_label = tk.Label(card_frame, text=f"Pos {pos+1}", 
                               font=("Arial", 8), bg="#f0f0f0")
            pos_label.pack(side=tk.BOTTOM, fill=tk.X)
            
            # Determine content
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
                
                value_label = tk.Label(card_frame, text=display_value, width=4, height=3,
                                      bg=bg_color, font=font)
                value_label.pack(expand=True, fill=tk.BOTH)
                
            elif playable_values is not None:
                # Suggestion mode: Show all values, colored
                # Use a grid of labels for better layout control
                
                # Create a container frame for the grid
                grid_frame = tk.Frame(card_frame, bg=bg_color)
                grid_frame.pack(expand=True, fill=tk.BOTH, padx=2, pady=2)
                
                sorted_vals = sorted(list(pos_beliefs))
                num_vals = len(sorted_vals)
                
                # Determine grid dimensions
                # If few values, 1 column. If many, 2 or 3 columns.
                if num_vals <= 4:
                    columns = 1
                elif num_vals <= 8:
                    columns = 2
                else:
                    columns = 3
                    
                for i, val in enumerate(sorted_vals):
                    row = i // columns
                    col = i % columns
                    
                    fg_color = "red" if val in playable_values else "black"
                    font_weight = "bold" if val in playable_values else "normal"
                    
                    # Adjust font size based on count
                    font_size = 14
                    if num_vals > 8:
                        font_size = 10
                    elif num_vals > 4:
                        font_size = 12
                        
                    lbl = tk.Label(grid_frame, text=str(val), 
                                  fg=fg_color, bg=bg_color,
                                  font=("Arial", font_size, font_weight))
                    
                    # Center in its cell
                    lbl.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                    
                # Configure grid weights to distribute space
                for c in range(columns):
                    grid_frame.columnconfigure(c, weight=1)
                for r in range((num_vals + columns - 1) // columns):
                    grid_frame.rowconfigure(r, weight=1)
                
                # Bind click events to the grid frame and all labels
                if panel and player_key is not None:
                    handler = lambda e, p=pos: self._on_hand_click(panel, player_key, p)
                    grid_frame.bind("<Button-1>", handler)
                    for child in grid_frame.winfo_children():
                        child.bind("<Button-1>", handler)

            elif len(pos_beliefs) < 5:
                # Uncertain but few possibilities
                display_value = "\n".join(str(v) for v in sorted(pos_beliefs))
                font = ("Arial", 10)
                value_label = tk.Label(card_frame, text=display_value, width=4, height=3,
                                      bg=bg_color, font=font)
                value_label.pack(expand=True, fill=tk.BOTH)
            else:
                # Many possibilities
                display_value = f"#{len(pos_beliefs)}"
                font = ("Arial", 12, "bold")
                value_label = tk.Label(card_frame, text=display_value, width=4, height=3,
                                      bg=bg_color, font=font)
                value_label.pack(expand=True, fill=tk.BOTH)

            # Bind click events if panel is provided
            if panel and player_key is not None:
                # Use partial or lambda with default arg to capture pos
                handler = lambda e, p=pos: self._on_hand_click(panel, player_key, p)
                card_frame.bind("<Button-1>", handler)
                if 'value_label' in locals():
                    value_label.bind("<Button-1>", handler)
                pos_label.bind("<Button-1>", handler)
                
                # Change cursor to hand
                value_label.config(cursor="hand2")
                pos_label.config(cursor="hand2")
        
        # Legend (compact version)
        legend_frame = tk.Frame(parent_frame)
        legend_frame.pack(pady=5)
        
    def _on_hand_click(self, panel, player_key, position):
        """Handle click on a hand card."""
        if hasattr(panel, 'handle_hand_click'):
            panel.handle_hand_click(player_key, position)
    
    def setup_game_state(self):
        """Setup the game state display."""
        state_frame = tk.Frame(self.root, bg="#f0f0f0", height=50)
        state_frame.pack(fill=tk.X, padx=10, pady=5)
        state_frame.pack_propagate(False)
        
        self.state_label = tk.Label(state_frame, text="", bg="#f0f0f0", 
                                    font=("Arial", 10))
        self.state_label.pack(pady=10)
        
        self.update_game_state()
    
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
            elif action_type == "reveal":
                self.reveals.append(action_data)
            elif action_type == "not_present":
                self.not_present.append(action_data)
            elif action_type == "has_value":
                self.has_values.append(action_data)
            
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
            self.update_game_state()
            
            # Refresh hand viewers in the current action panel
            current_panel = self.panels.get(self.current_action_type)
            if current_panel:
                if hasattr(current_panel, 'refresh'):
                    current_panel.refresh()
                elif hasattr(current_panel, 'hand_viewer_frame'):
                    # Refresh all hand frames in the panel
                    for player_key in ['caller', 'target', 'player', 'player1', 'player2']:
                        if player_key in current_panel.selections and hasattr(current_panel, f'{player_key}_hand_frame'):
                            frame = getattr(current_panel, f'{player_key}_hand_frame')
                            player_id = current_panel.selections[player_key]
                            position_key = current_panel.get_position_key_for_player(player_key)
                            self.draw_player_hand(frame, player_id, position_key=position_key, panel=current_panel, player_key=player_key)
            
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
        self.vars = {}  # Store Tk variables
    
    def create_player_buttons(self, parent, label, key):
        """Create player selection buttons."""
        frame = tk.Frame(parent, bg="#E3F2FD", padx=5, pady=5, relief=tk.GROOVE, borderwidth=1)
        frame.pack(fill=tk.X, pady=5, padx=5)
        
        tk.Label(frame, text=label, width=20, anchor=tk.W, bg="#E3F2FD", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        button_frame = tk.Frame(frame, bg="#E3F2FD")
        button_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.vars[key] = tk.IntVar(value=-1)
        
        for pid, name in self.app.player_names.items():
            btn = tk.Radiobutton(button_frame, text=name, width=10,
                               variable=self.vars[key], value=pid,
                               indicatoron=0, bg="white", selectcolor="#4A90E2",
                               font=("Arial", 9),
                               command=lambda k=key, p=pid: self.select_player(k, p))
            btn.pack(side=tk.LEFT, padx=2)
    
    def create_position_buttons(self, parent, label, key):
        """Create position selection buttons."""
        frame = tk.Frame(parent, bg="#FFF3E0", padx=5, pady=5, relief=tk.GROOVE, borderwidth=1)
        frame.pack(fill=tk.X, pady=5, padx=5)
        
        tk.Label(frame, text=label, anchor=tk.W, bg="#FFF3E0", font=("Arial", 10, "bold")).pack()
        
        button_frame = tk.Frame(frame, bg="#FFF3E0")
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.vars[key] = tk.IntVar(value=-1)
        
        for pos in range(self.app.config.wires_per_player):
            btn = tk.Radiobutton(button_frame, text=str(pos + 1), width=4,
                               variable=self.vars[key], value=pos,
                               indicatoron=0, bg="white", selectcolor="#F5A623",
                               font=("Arial", 9, "bold"),
                               command=lambda k=key, p=pos: self.select_position(k, p))
            btn.pack(side=tk.LEFT, padx=2)
    
    def create_value_buttons(self, parent, label, key):
        """Create value selection buttons."""
        frame = tk.Frame(parent, bg="#F3E5F5", padx=5, pady=5, relief=tk.GROOVE, borderwidth=1)
        frame.pack(fill=tk.X, pady=5, padx=5)
        
        tk.Label(frame, text=label, anchor=tk.W, bg="#F3E5F5", font=("Arial", 10, "bold")).pack()
        
        button_frame = tk.Frame(frame, bg="#F3E5F5")
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.vars[key] = tk.IntVar(value=-1)
        
        for value in self.app.config.wire_values:
            btn = tk.Radiobutton(button_frame, text=str(value), width=5,
                               variable=self.vars[key], value=value,
                               indicatoron=0, bg="white", selectcolor="#BD10E0",
                               font=("Arial", 9, "bold"),
                               command=lambda k=key, v=value: self.select_value(k, v))
            btn.pack(side=tk.LEFT, padx=2)
    
    def init_position_var(self, key):
        """Initialize position variable without creating buttons."""
        self.vars[key] = tk.IntVar(value=-1)

    def handle_hand_click(self, player_key, position):
        """Handle click on a hand card. Can be overridden."""
        key = self.get_position_key_for_player(player_key)
        if key:
            if key in self.vars:
                self.vars[key].set(position)
            self.select_position(key, position)

    def select_player(self, key, player_id):
        """Handle player button selection."""
        self.selections[key] = player_id
        
        # Update hand display if this panel has a hand viewer frame
        if hasattr(self, 'hand_viewer_frame') and hasattr(self, f'{key}_hand_frame'):
            frame = getattr(self, f'{key}_hand_frame')
            # Determine the position key for highlighting selected positions
            position_key = self.get_position_key_for_player(key)
            self.app.draw_player_hand(frame, player_id, position_key=position_key, panel=self, player_key=key)
    
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
        
        # Redraw hand viewer to show selection if applicable
        if hasattr(self, 'hand_viewer_frame'):
            # Redraw all visible hand frames to ensure highlights are correct
            for player_key in ['caller', 'target', 'player', 'player1', 'player2']:
                if player_key in self.selections and hasattr(self, f'{player_key}_hand_frame'):
                    frame = getattr(self, f'{player_key}_hand_frame')
                    position_key = self.get_position_key_for_player(player_key)
                    self.app.draw_player_hand(frame, self.selections[player_key], 
                                             position_key=position_key, panel=self, player_key=player_key)
    
    def select_value(self, key, value):
        """Handle value button selection."""
        self.selections[key] = value
    
    def clear_selections(self):
        """Clear all selections."""
        self.selections = {}
        for var in self.vars.values():
            var.set(-1)
        
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
        
        tk.Label(self, text="CALL ACTION", font=("Arial", 14, "bold"), fg="#333333").pack(pady=10)
        
        self.create_player_buttons(self, "Caller:", "caller")
        
        # Hand viewer for caller
        self.caller_hand_frame = tk.Frame(self)
        self.caller_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Initialize caller position variable
        self.init_position_var("caller_position")
        
        self.create_player_buttons(self, "Target:", "target")
        
        # Hand viewer for target (visual reference only)
        self.target_hand_frame = tk.Frame(self)
        self.target_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Position selection buttons
        self.init_position_var("position")
        
        # Value selection
        self.create_value_buttons(self, "Value:", "value")
        
        # Result
        result_frame = tk.Frame(self, bg="#E8F5E9", padx=10, pady=10, relief=tk.GROOVE, borderwidth=1)
        result_frame.pack(fill=tk.X, pady=10, padx=5)
        tk.Label(result_frame, text="Result:", width=10, anchor=tk.W, bg="#E8F5E9", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.result_var = tk.StringVar(value="success")
        tk.Radiobutton(result_frame, text="SUCCESS", variable=self.result_var, 
                      value="success",
                      bg="#E8F5E9", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(result_frame, text="FAIL", variable=self.result_var, 
                      value="fail",
                      bg="#E8F5E9", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="ADD CALL", command=self.add_call,
                 bg="#4CAF50", fg="white", padx=30, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="CLEAR", command=self.clear,
                 bg="#F44336", fg="white", padx=20, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
    
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
        
        tk.Label(self, text="SWAP ACTION", font=("Arial", 14, "bold"), fg="#333333").pack(pady=10)
        
        # --- Player 1 Section ---
        self.create_player_buttons(self, "Player 1:", "player1")
        
        # Hand viewer for player 1
        self.player1_hand_frame = tk.Frame(self)
        self.player1_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Position selection variables
        self.init_position_var("init_pos1")
        self.init_position_var("final_pos1")
        
        # --- Player 2 Section ---
        self.create_player_buttons(self, "Player 2:", "player2")
        
        # Hand viewer for player 2
        self.player2_hand_frame = tk.Frame(self)
        self.player2_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Position selection variables
        self.init_position_var("init_pos2")
        self.init_position_var("final_pos2")
        
        # Mode selector for position selection
        mode_frame = tk.Frame(self, bg="#E8F5E9", padx=10, pady=5, relief=tk.GROOVE, borderwidth=1)
        mode_frame.pack(fill=tk.X, pady=5, padx=5)
        tk.Label(mode_frame, text="Selecting:", width=10, anchor=tk.W, bg="#E8F5E9", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.selection_mode = tk.StringVar(value="initial")
        tk.Radiobutton(mode_frame, text="INITIAL Positions (to remove)", variable=self.selection_mode, 
                      value="initial", bg="#E8F5E9", font=("Arial", 10), command=self.update_highlights).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(mode_frame, text="FINAL Positions (to insert)", variable=self.selection_mode, 
                      value="final", bg="#E8F5E9", font=("Arial", 10), command=self.update_highlights).pack(side=tk.LEFT, padx=10)
        
        # Received value (only needed if I'm one of the players)
        self.received_value_frame = tk.Frame(self, bg="#FFF8DC", padx=10, pady=10, relief=tk.GROOVE, borderwidth=1)
        self.received_value_frame.pack(fill=tk.X, pady=10, padx=5)
        tk.Label(self.received_value_frame, text="Value I Received (if I'm involved):", 
                bg="#FFF8DC", font=("Arial", 10, "bold")).pack()
        self.create_value_buttons(self.received_value_frame, "", "received_value")
        
        tk.Label(self, text="ℹ️ Only select received value if you are Player 1 or Player 2",
                font=("Arial", 9, "italic"), fg="#666666").pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="ADD SWAP", command=self.add_swap,
                 bg="#4CAF50", fg="white", padx=30, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="CLEAR", command=self.clear,
                 bg="#F44336", fg="white", padx=20, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
    
    def get_position_key_for_player(self, player_key):
        """Override to return correct key based on selection mode."""
        mode = self.selection_mode.get()
        if player_key == 'player1':
            return 'init_pos1' if mode == 'initial' else 'final_pos1'
        elif player_key == 'player2':
            return 'init_pos2' if mode == 'initial' else 'final_pos2'
        return None

    def update_highlights(self):
        """Redraw hands to update highlights based on current mode."""
        if "player1" in self.selections:
            self.select_player("player1", self.selections["player1"])
        if "player2" in self.selections:
            self.select_player("player2", self.selections["player2"])

    def add_swap(self):
        """Add the swap action."""
        required = ["player1", "player2", "init_pos1", "init_pos2", "final_pos1", "final_pos2"]
        if not all(k in self.selections for k in required):
            messagebox.showwarning("Incomplete", "Please complete all fields (Initial and Final positions for both players)")
            return
        
        p1_id = self.selections["player1"]
        p2_id = self.selections["player2"]
        p1 = self.app.player_names[p1_id]
        p2 = self.app.player_names[p2_id]
        
        # Check if I'm involved in the swap
        i_am_involved = (p1_id == self.app.my_player_id or p2_id == self.app.my_player_id)
        
        # If I'm involved, received_value is required
        if i_am_involved and "received_value" not in self.selections:
            messagebox.showwarning("Incomplete", "Please select the value you received (since you're involved in the swap)")
            return
        
        # Convert to 1-indexed and build action tuple
        if i_am_involved:
            action = (
                p1, p2,
                self.selections["init_pos1"] + 1,
                self.selections["init_pos2"] + 1,
                self.selections["final_pos1"] + 1,
                self.selections["final_pos2"] + 1,
                self.selections["received_value"]
            )
        else:
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
        self.selection_mode.set("initial")
        self.update_highlights()


class DoubleRevealActionPanel(ActionPanel):
    """Panel for double reveal actions."""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.hand_viewer_frame = True  # Flag to enable hand viewing
        
        tk.Label(self, text="DOUBLE REVEAL ACTION", font=("Arial", 14, "bold"), fg="#333333").pack(pady=10)
        
        self.create_player_buttons(self, "Player:", "player")
        
        # Hand viewer for player (visual reference only)
        self.player_hand_frame = tk.Frame(self)
        self.player_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Show which positions are selected
        self.position_status_frame = tk.Frame(self)
        self.position_status_frame.pack(pady=5)
        self.position_status_label = tk.Label(self.position_status_frame, text="Select 2 positions on the hand",
                                             font=("Arial", 10, "italic"), fg="#666666")
        self.position_status_label.pack()
        
        # Initialize position variables
        self.init_position_var("position1")
        self.init_position_var("position2")
        
        self.create_value_buttons(self, "Value:", "value")
        
        tk.Label(self, text="ℹ️ Use when revealing the last 2 copies of a value",
                font=("Arial", 9, "italic"), fg="#666666").pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="ADD DOUBLE REVEAL", command=self.add_reveal,
                 bg="#4CAF50", fg="white", padx=30, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="CLEAR", command=self.clear,
                 bg="#F44336", fg="white", padx=20, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
    
    def handle_hand_click(self, player_key, position):
        """Handle click on hand for double reveal (toggle 2 positions)."""
        # Check if position is already selected
        p1 = self.selections.get("position1")
        p2 = self.selections.get("position2")
        
        if p1 == position:
            # Deselect p1
            del self.selections["position1"]
            self.vars["position1"].set(-1)
        elif p2 == position:
            # Deselect p2
            del self.selections["position2"]
            self.vars["position2"].set(-1)
        else:
            # Select new position
            if p1 is None:
                self.selections["position1"] = position
                self.vars["position1"].set(position)
            elif p2 is None:
                self.selections["position2"] = position
                self.vars["position2"].set(position)
            else:
                # Both full, replace p1 (or maybe shift?)
                # Let's replace p1
                self.selections["position1"] = position
                self.vars["position1"].set(position)
        
        # Redraw
        self.select_position("position1", self.selections.get("position1", -1))

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
        
        tk.Label(self, text="SIGNAL ACTION", font=("Arial", 14, "bold"), fg="#333333").pack(pady=10)
        
        self.create_player_buttons(self, "Player:", "player")
        
        # Hand viewer for player (visual reference only)
        self.player_hand_frame = tk.Frame(self)
        self.player_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Position selection buttons
        self.init_position_var("position")
        
        self.create_value_buttons(self, "Value:", "value")
        
        # Action type selector
        type_frame = tk.Frame(self, bg="#E8F5E9", padx=10, pady=10, relief=tk.GROOVE, borderwidth=1)
        type_frame.pack(fill=tk.X, pady=10, padx=5)
        tk.Label(type_frame, text="Action Type:", width=12, anchor=tk.W, bg="#E8F5E9", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.action_type_var = tk.StringVar(value="signal")
        tk.Radiobutton(type_frame, text="SIGNAL (Certain)", variable=self.action_type_var, 
                      value="signal", bg="#E8F5E9", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(type_frame, text="REVEAL (Show)", variable=self.action_type_var, 
                      value="reveal", bg="#E8F5E9", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        
        tk.Label(self, text="ℹ️ Use SIGNAL when deduced, REVEAL when shown to others",
                font=("Arial", 9, "italic"), fg="#666666").pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="ADD ACTION", command=self.add_signal,
                 bg="#4CAF50", fg="white", padx=30, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="CLEAR", command=self.clear,
                 bg="#F44336", fg="white", padx=20, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
    
    def add_signal(self):
        """Add the signal or reveal action."""
        required = ["player", "value", "position"]
        if not all(k in self.selections for k in required):
            messagebox.showwarning("Incomplete", "Please complete all fields")
            return
        
        player = self.app.player_names[self.selections["player"]]
        value = self.selections["value"]
        position = self.selections["position"] + 1
        
        action = (player, value, position)
        
        # Determine action type based on radio button selection
        action_type = self.action_type_var.get()
        self.app.add_action(action_type, action)
        self.clear()
    
    def clear(self):
        """Clear all selections."""
        self.clear_selections()
        self.selected_values.clear()
        self.update_value_buttons_state()


class NotPresentActionPanel(ActionPanel):
    """Panel for not present actions."""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.hand_viewer_frame = True  # Flag to enable hand viewing
        
        tk.Label(self, text="NOT PRESENT ACTION", font=("Arial", 14, "bold"), fg="#333333").pack(pady=10)
        
        self.create_player_buttons(self, "Player:", "player")
        
        # Hand viewer for player
        self.player_hand_frame = tk.Frame(self)
        self.player_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Scope selector
        scope_frame = tk.Frame(self, bg="#E8F5E9", padx=10, pady=10, relief=tk.GROOVE, borderwidth=1)
        scope_frame.pack(fill=tk.X, pady=10, padx=5)
        tk.Label(scope_frame, text="Scope:", width=12, anchor=tk.W, bg="#E8F5E9", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.scope_var = tk.StringVar(value="all")
        tk.Radiobutton(scope_frame, text="ANYWHERE (Default)", variable=self.scope_var, 
                      value="all", bg="#E8F5E9", font=("Arial", 10), command=self.toggle_position_selection).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(scope_frame, text="SPECIFIC POSITION", variable=self.scope_var, 
                      value="specific", bg="#E8F5E9", font=("Arial", 10), command=self.toggle_position_selection).pack(side=tk.LEFT, padx=10)
        
        # Initialize position var (needed for hand selection)
        self.init_position_var("position")
        
        # Multi-select value buttons
        self.create_multi_value_buttons(self, "Values (Select multiple):")
        
        tk.Label(self, text="ℹ️ Use when a player announces they don't have this value",
                font=("Arial", 9, "italic"), fg="#666666").pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="ADD NOT PRESENT", command=self.add_not_present,
                 bg="#4CAF50", fg="white", padx=30, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="CLEAR", command=self.clear,
                 bg="#F44336", fg="white", padx=20, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
        
        # Initial state
        self.toggle_position_selection()

    def create_multi_value_buttons(self, parent, label):
        """Create value selection buttons allowing multiple selections."""
        frame = tk.Frame(parent, bg="#F3E5F5", padx=5, pady=5, relief=tk.GROOVE, borderwidth=1)
        frame.pack(fill=tk.X, pady=5, padx=5)
        
        tk.Label(frame, text=label, anchor=tk.W, bg="#F3E5F5", font=("Arial", 10, "bold")).pack()
        
        button_frame = tk.Frame(frame, bg="#F3E5F5")
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.value_buttons = {}
        self.selected_values = set()
        
        for value in self.app.config.wire_values:
            btn = tk.Button(button_frame, text=str(value), width=5,
                           bg="white", font=("Arial", 9, "bold"),
                           command=lambda v=value: self.toggle_value(v))
            btn.pack(side=tk.LEFT, padx=2)
            self.value_buttons[value] = btn

    def toggle_value(self, value):
        """Toggle selection of a value."""
        if value in self.selected_values:
            self.selected_values.remove(value)
            self.value_buttons[value].config(bg="white", fg="black", relief=tk.RAISED)
        else:
            self.selected_values.add(value)
            self.value_buttons[value].config(bg="#BD10E0", fg="white", relief=tk.SUNKEN)

    def update_value_buttons_state(self):
        """Update state of value buttons based on selected position beliefs."""
        # First, ensure buttons reflect selection state (visual reset)
        for v, btn in self.value_buttons.items():
            if v in self.selected_values:
                btn.config(bg="#BD10E0", fg="white", relief=tk.SUNKEN, state=tk.NORMAL)
            else:
                btn.config(bg="white", fg="black", relief=tk.RAISED, state=tk.NORMAL)

        # If specific position is selected, disable values that are already known not to be there
        if self.scope_var.get() == "specific" and "player" in self.selections and "position" in self.selections:
            player_id = self.selections["player"]
            position = self.selections["position"]
            
            # Get beliefs
            if self.app.my_player and self.app.my_player.belief_system:
                possible_values = self.app.my_player.belief_system.beliefs[player_id][position]
                
                for value, btn in self.value_buttons.items():
                    if value not in possible_values:
                        # Value is already known to be not present
                        btn.config(state=tk.DISABLED, bg="#E0E0E0", fg="#999999")
                        # If it was selected, deselect it
                        if value in self.selected_values:
                            self.selected_values.remove(value)

    def select_player(self, key, player_id):
        super().select_player(key, player_id)
        self.update_value_buttons_state()

    def select_position(self, key, position):
        super().select_position(key, position)
        self.update_value_buttons_state()

    def toggle_position_selection(self):
        if self.scope_var.get() == "specific":
            # Position selection is enabled (via hand click)
            pass
        else:
            self.vars["position"].set(-1)
            if "position" in self.selections:
                del self.selections["position"]
            # Redraw hand to clear selection highlight
            if "player" in self.selections:
                self.select_player("player", self.selections["player"])
        
        self.update_value_buttons_state()
    
    def add_not_present(self):
        """Add the not present action."""
        if not "player" in self.selections:
            messagebox.showwarning("Incomplete", "Please select a player")
            return
            
        if not self.selected_values:
            messagebox.showwarning("Incomplete", "Please select at least one value")
            return

        if self.scope_var.get() == "specific" and "position" not in self.selections:
             messagebox.showwarning("Incomplete", "Please select a position from the hand")
             return
        
        player = self.app.player_names[self.selections["player"]]
        
        for value in list(self.selected_values):
            if self.scope_var.get() == "specific":
                position = self.selections["position"] + 1  # Convert to 1-based for consistency
                action = (player, value, position)
            else:
                action = (player, value)
            
            self.app.add_action("not_present", action)
            
        self.clear()
    
    def clear(self):
        """Clear all selections."""
        self.clear_selections()
        self.scope_var.set("all")
        self.toggle_position_selection()


class HasValueActionPanel(ActionPanel):
    """Panel for has value actions - signal that a player has a specific value (position unknown)."""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.hand_viewer_frame = True  # Flag to enable hand viewing
        
        tk.Label(self, text="HAS VALUE ACTION", font=("Arial", 14, "bold"), fg="#333333").pack(pady=10)
        
        self.create_player_buttons(self, "Player:", "player")
        
        # Hand viewer for player
        self.player_hand_frame = tk.Frame(self)
        self.player_hand_frame.pack(fill=tk.X, pady=5, padx=10)
        
        self.create_value_buttons(self, "Value:", "value")
        
        tk.Label(self, text="ℹ️ Use when a player announces they have this value (position unknown)",
                font=("Arial", 9, "italic"), fg="#666666").pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="ADD HAS VALUE", command=self.add_has_value,
                 bg="#4CAF50", fg="white", padx=30, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="CLEAR", command=self.clear,
                 bg="#F44336", fg="white", padx=20, pady=10, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
    
    def add_has_value(self):
        """Add the has value action."""
        required = ["player", "value"]
        if not all(k in self.selections for k in required):
            messagebox.showwarning("Incomplete", "Please complete all fields")
            return
        
        player = self.app.player_names[self.selections["player"]]
        value = self.selections["value"]
        
        action = (player, value)
        
        self.app.add_action("has_value", action)
        self.clear()
    
    def clear(self):
        """Clear all selections."""
        self.clear_selections()


class SuggesterPanel(tk.Frame):
    """Panel for viewing call suggestions."""
    
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        
        # Header
        header_frame = tk.Frame(self, bg="#FAFAFA", relief=tk.RIDGE, borderwidth=2)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(header_frame, text="CALL SUGGESTIONS", font=("Arial", 14, "bold"), 
                fg="#333333", bg="#FAFAFA").pack(pady=10)
        
        # Refresh button
        tk.Button(header_frame, text="REFRESH", command=self.refresh,
                 bg="#FFC107", fg="black", padx=10, pady=5, font=("Arial", 10, "bold")).pack(pady=5)
        
        # Content container (no internal scrollbar, relies on main window scroll)
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def refresh(self):
        """Refresh the suggestions list."""
        # Clear existing items
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        if not self.app.my_player or not self.app.my_player.belief_system:
            return
            
        # Initialize statistics
        # IMPORTANT: Use the player's CURRENT wire from the game object, not the initial self.app.my_wire
        # The player's wire changes after swaps!
        current_wire = self.app.my_player.get_wire()
        stats = GameStatistics(self.app.my_player.belief_system, self.app.config, current_wire)
        
        # Get suggestions (now filtered in statistics.py)
        suggestions = stats.get_all_call_suggestions()
        
        # Process suggestions to group by Player
        suggestions_by_player = {} # target_id -> list of (position, value, uncertainty)
        
        all_calls = suggestions['certain'] + suggestions['uncertain']
        
        for target_id, position, value, uncertainty in all_calls:
            if target_id not in suggestions_by_player:
                suggestions_by_player[target_id] = []
            suggestions_by_player[target_id].append((position, value, uncertainty))
            
        # Sort and display
        sorted_player_ids = sorted(suggestions_by_player.keys(), key=lambda pid: self.app.player_names.get(pid, str(pid)))
        
        for target_id in sorted_player_ids:
            # Create player section
            player_frame = tk.Frame(self.content_frame, relief=tk.GROOVE, borderwidth=2, padx=10, pady=10, bg="#FAFAFA")
            player_frame.pack(fill=tk.X, padx=10, pady=10)
            
            player_name = self.app.player_names.get(target_id, f"Player {target_id}")
            tk.Label(player_frame, text=player_name, font=("Arial", 16, "bold"), bg="#FAFAFA").pack(anchor="w")
            
            # Draw hand
            hand_frame = tk.Frame(player_frame, bg="#FAFAFA")
            hand_frame.pack(fill=tk.X, pady=5)
            
            suggested_positions = [p for p, _, _ in suggestions_by_player[target_id]]
            
            # Extract playable values for this player
            playable_values = set()
            for _, val, _ in suggestions_by_player[target_id]:
                playable_values.add(val)
                
            self.app.draw_player_hand(hand_frame, target_id, title="", 
                                     highlight_positions=suggested_positions,
                                     playable_values=playable_values)

if __name__ == "__main__":
    app = BombBusterGUI()
    app.run()
