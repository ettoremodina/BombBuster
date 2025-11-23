# Logic Explanation: `_apply_remaining_copies_distance_filter`

This document explains the logic behind the `_apply_remaining_copies_distance_filter` method in `src/belief/belief_model.py`.

## Purpose

The goal of this filter is to eliminate possible values for a specific card position by checking if assigning that value would require more copies of the card than are available in the game.

It leverages the **non-decreasing order constraint** of the wires to identify "chains" of identical values that would be forced by a specific assignment.

## Core Concept: Forced Chains

In BombBuster, wires are sorted. If you have a sequence of cards, and you know that `card[i] == X`, then:
- Any card to the left (`card[i-1]`) must be `<= X`.
- Any card to the right (`card[i+1]`) must be `>= X`.

However, if we know that `card[i-1]` cannot be smaller than `X` (i.e., `min(possible_values[i-1]) == X`), then `card[i-1]` **MUST** be `X`.

This creates a "forced chain". If assigning `X` to position `i` forces position `i-1` to also be `X`, and that in turn forces `i-2` to be `X`, we need multiple copies of `X` to satisfy this arrangement.

## Algorithm Steps

The filter iterates through every player, every position, and every candidate value currently considered possible for that position.

For a specific `player`, `position`, and candidate `value`:

### 1. Hypothesis
Assume `beliefs[player][position] == value`.

### 2. Calculate Required Copies (The Chain)
We determine how many copies of `value` are strictly required to support this hypothesis.
- Start with **1** (for the current position).
- **Scan Left**: Look at `position - 1`, `position - 2`, etc.
    - If `min(beliefs[left_pos]) > value`: **Impossible**. Ordering violation.
    - If `min(beliefs[left_pos]) == value`: This neighbor **MUST** be `value` (it can't be smaller, and it can't be larger due to sorting). Increment required copies.
    - If `min(beliefs[left_pos]) < value`: The chain breaks. The neighbor *could* be smaller, so it's not forced to be `value`.
- **Scan Right**: Look at `position + 1`, `position + 2`, etc.
    - If `max(beliefs[right_pos]) < value`: **Impossible**. Ordering violation.
    - If `max(beliefs[right_pos]) == value`: This neighbor **MUST** be `value`. Increment required copies.
    - If `max(beliefs[right_pos]) > value`: The chain breaks.

### 3. Calculate Available Copies
We determine how many copies of `value` are theoretically available to this player to satisfy the chain.
- **Uncertain Copies**: Copies not yet identified (in the deck or other players' unknown hands).
- **+ Own Revealed/Certain in Chain**: If the player *already* has `value` revealed or certain at one of the positions in our "forced chain", we count those. They are available to satisfy the requirement because they are literally the cards we are counting.
- **+ Own Called Copies**: If the player has announced they have `value` (via a "Call" or "Has Value" action) but the position is unknown, these "floating" copies are available to be placed in our chain.

### 4. Verification
Compare `Required` vs `Available`.
- If `Required Copies > Available Copies`: The hypothesis is false. `value` is removed from `beliefs[player][position]`.

## Example

**Scenario:**
- Player A has 5 wires.
- We are checking Position 3 (0-indexed). Candidate value is **10**.
- Beliefs for Player A:
    - Pos 0: `{8, 9}`
    - Pos 1: `{10}` (Min is 10)
    - Pos 2: `{10, 11}` (Min is 10)
    - Pos 3: `{10, 11, 12}` (Target)
    - Pos 4: `{12, 13}`

**Hypothesis:** `Pos 3 == 10`.

**Left Scan:**
- **Pos 2**: `min({10, 11})` is 10. Since Pos 3 is 10, Pos 2 must be `<= 10`. Since min is 10, Pos 2 **MUST** be 10. **(Chain: Pos 3, Pos 2)**
- **Pos 1**: `min({10})` is 10. Since Pos 2 is 10, Pos 1 must be `<= 10`. Since min is 10, Pos 1 **MUST** be 10. **(Chain: Pos 3, Pos 2, Pos 1)**
- **Pos 0**: `min({8, 9})` is 8. This is `< 10`. Chain breaks.

**Right Scan:**
- **Pos 4**: `max({12, 13})` is 13. This is `> 10`. Chain breaks.

**Total Required Copies:** 3 (Pos 1, Pos 2, Pos 3).

**Check Availability:**
- Suppose there are 4 copies of '10' in the entire game.
- Player B has 1 revealed '10'.
- Player C has 1 revealed '10'.
- **Available Uncertain:** 4 (total) - 2 (revealed elsewhere) = **2**.

**Result:**
- Required (3) > Available (2).
- Therefore, `Pos 3` **cannot** be 10.
- Remove 10 from `beliefs[Player A][Pos 3]`.
