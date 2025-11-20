## BombBuster 🔥💣  
Cooperative deduction on sorted hidden wires

BombBuster is a cooperative information‑deduction game engine. Each player holds a sorted list of hidden “wires” and the team works together, through calls and reveals, to fully reconstruct the hidden configuration before the bomb goes off.


## What this project provides 🎮

- A formal rules specification (`rules.tex`) describing the game at a mathematical level.
- A Python engine (`src/game.py`, `src/player.py`) that enforces turns, calls, double reveals, swaps and win/lose conditions.
- A belief system (`src/belief/belief_model.py`) that tracks, for every player and position, which values are still possible.
- A collection of filters that propagate global constraints and prune impossible beliefs.
- Utilities for both simulation and real‑life play (IRL), including a call suggester demo, human‑friendly input helpers, and a graphical interface.


## Core game idea 🧠

- Each player’s wire is a sorted sequence of hidden values drawn from a global multiset.
- On your turn you make a **call**, claiming that a certain position in another player’s wire has one of the values you hold.
- Correct calls reveal both wires; incorrect calls give the team a strike.
- The team wins if all wires are revealed or deduced; they lose after too many wrong calls.

The engine is agnostic to strategy: humans, scripted agents, and suggestion heuristics can all sit on top of the same core.


## Belief model & filtering 🔍

Each player maintains a belief model describing, for every player and position, a set of possible values. On top of this, a ValueTracker keeps global counts of how many copies of each value are revealed, certain, uncertain, or only “called”.

Whenever a public event happens (successful or failed call, double reveal, swap), beliefs are updated and filters are applied in a loop until no more changes occur. The main filters are:

- Ordering filter 📈 – enforces that each player’s wire is sorted: high values cannot appear too early, low values cannot appear too late.
- Distance / sliding‑window filter 📏 – uses how many copies of a value remain for a player to limit how far from known positions that value can still appear.
- Uncertain position–value filter 🎯 – combines global counts of remaining copies with ordering to rule out value and position pairs that can no longer be realized.
- Subset cardinality filter 🧩 – a Sudoku‑style hidden‑subset rule across all players: when a small set of values can only appear in a matching small set of positions, other values are removed from those positions.
- Remaining copies distance filter ⛓️ – checks if assigning a value would force a chain of identical values (due to sorting) that exceeds the total available copies of that value.
- Called value filter 📢 – leverages "I have a X" announcements to constrain beliefs, enforcing that called values must exist in the player's hand and deducing positions when options are limited.

Throughout, a Markovian assumption is used: only the current game state and the public history of actions matter for beliefs, not the exact order in which logically equivalent updates were applied.


## Interfaces & usage 🧩

- Simulation mode – generate wires, run games in code, and inspect belief states after each action. The engine handles validation of actions and win/loss detection.
- IRL helper mode – use `play_irl.py` and utilities in `src/utils.py` to drive the engine while you play with physical cards. Human‑friendly inputs (names, 1‑indexed positions) are converted to internal actions; strict consistency checks can be relaxed with an IRL flag.
- IRL GUI – use `play_irl_gui.py` for a graphical, click-based interface to track real-life games. It supports easy action recording, state visualization, and session saving/loading.
- Call suggester – given a belief model and the values a player holds, suggest promising calls, prioritizing certain calls and then those with minimal remaining uncertainty.


## Future directions 🚀

The project is designed as a playground for new inference tricks and variants of the game. Planned and potential extensions include:

- Refining and testing each filter in isolation, and tuning how they interact.
- Improving swap handling and exploring non‑Markovian effects when swap history matters.
- Centralizing statistics (entropy, uncertainty measures) and suggestion logic in a dedicated statistics module.
- Adding richer rule variants: non‑signalable bombs, multipliers, extra signaling systems and heuristic “no one keeps 4 wires” style constraints.
- Simulation tools that explore all consistent configurations to evaluate how complete the current filtering approach is.


## Assumptions & scope ⚠️

- Wires for each player are sorted by value and drawn from a fixed, known distribution.
- The wire distribution divides evenly among players and matches the configured parameters.
- Reasoning is Markovian with respect to the belief state and public history of game actions.
- In IRL mode, some validations are intentionally relaxed and consistency of human input is assumed.

Overall, BombBuster is meant as a compact testbed for belief propagation, constraint reasoning and cooperative deduction, rather than a polished end‑user game client.
