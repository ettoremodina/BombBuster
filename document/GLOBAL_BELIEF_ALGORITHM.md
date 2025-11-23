# Global Belief Algorithm and Optimization

This document explains the Global Consistency Algorithm used in `GlobalBeliefModel` and the optimizations implemented to improve its performance.

## Algorithm Overview

The Global Belief Model uses a **Propagated Dynamic Programming** approach to enforce global consistency across all players' hands. Unlike local filtering, which only considers one player at a time, this algorithm ensures that the combination of all players' hands respects the global resource limits (the total deck).

The algorithm proceeds in three phases:

### Phase 1: Local Candidate Generation (Signatures)

For each player, we generate all possible "signatures" (resource vectors) that are valid given their local constraints.

*   **Input**: Local beliefs (possible values per position), "called" value constraints, and specific signal constraints (copy counts, adjacency).
*   **Process**: A backtracking search generates all valid sorted hands for the player.
*   **Output**: A set of valid signatures $V_p$ for each player $p$. A signature is a vector of length $K$ (number of unique card values) where the $i$-th element is the count of the $i$-th card value in the hand.

### Phase 2: Forward-Backward Global Filtering

This phase determines which signatures are part of a globally valid assignment.

*   **Forward Pass ($\alpha$)**: Computes the set of reachable resource states after the first $i$ players.
    *   $\alpha_0 = \{ \vec{0} \}$
    *   $\alpha_{i+1} = \{ \vec{a} + \vec{s} \mid \vec{a} \in \alpha_i, \vec{s} \in V_i, \vec{a} + \vec{s} \le \text{TotalDeck} \}$
*   **Backward Pass ($\beta$)**: Computes the set of required resource states for the remaining players $i \dots N-1$.
    *   $\beta_N = \{ \vec{0} \}$
    *   $\beta_i = \{ \vec{s} + \vec{b} \mid \vec{s} \in V_i, \vec{b} \in \beta_{i+1}, \vec{s} + \vec{b} \le \text{TotalDeck} \}$

### Phase 3: Projection to Minimal Domains

For each player, we identify which signatures are compatible with the global constraints and project them back to per-position domains.

*   A signature $\vec{s} \in V_p$ is valid if there exists a prefix $\vec{a} \in \alpha_p$ and a suffix $\vec{b} \in \beta_{p+1}$ such that $\vec{a} + \vec{s} + \vec{b} = \text{TotalDeck}$.
*   The valid signatures are used to reconstruct the possible values for each position in the player's hand.

## Optimizations Implemented

To speed up the algorithm, we introduced **Parallelization** and **Caching**.

### 1. Parallelization with `ProcessPoolExecutor`

The most computationally intensive parts of the algorithm are Phase 1 (Generation) and Phase 3 (Projection). These operations are independent for each player, making them ideal candidates for parallel execution.

*   **Worker Functions**: We extracted the core logic into standalone functions in `src/belief/global_belief_utils.py` to make them picklable and executable by worker processes.
    *   `generate_signatures_worker`: Performs the backtracking search for a single player.
    *   `filter_signatures_worker`: Checks signature validity against $\alpha$ and $\beta$ sets and projects to domains.
*   **Process Pool**: We use a global `ProcessPoolExecutor` to manage a pool of worker processes. This avoids the overhead of creating new processes for every filter step.
*   **Concurrent Execution**:
    *   In Phase 1, signature generation for all players runs in parallel.
    *   In Phase 3, filtering and projection for all players runs in parallel.

### 2. Caching

Signature generation (Phase 1) can be expensive, especially early in the game when constraints are loose. However, a player's local constraints often don't change between every single step (e.g., if another player makes a move that doesn't affect this player).

*   **Signature Cache**: We implemented a caching mechanism `_signature_cache` in `GlobalBeliefModel`.
*   **Cache Key**: The key is a tuple containing:
    *   Player ID
    *   Hash of current beliefs (frozen sets)
    *   Hash of copy count constraints
    *   Hash of adjacent constraints
    *   Hash of minimum count constraints
*   **Behavior**: Before submitting a generation task to the process pool, we check if the result is already in the cache. If so, we skip the computation for that player.

### 3. Algorithmic Optimization in Filtering

In Phase 3, checking the condition $\vec{a} + \vec{s} + \vec{b} = \text{TotalDeck}$ naively would require iterating over all pairs in $\alpha_p \times \beta_{p+1}$.

*   **Remainder Lookup**: We rewrite the equation as $\vec{a} + \vec{b} = \text{TotalDeck} - \vec{s} = \vec{R}$.
*   **Smallest Set Iteration**: To find if such a pair $(\vec{a}, \vec{b})$ exists, we iterate over the smaller of the two sets ($\alpha_p$ or $\beta_{p+1}$) and check for the existence of the complement in the larger set.
    *   If $|\alpha_p| < |\beta_{p+1}|$: Iterate $\vec{a} \in \alpha_p$, check if $\vec{R} - \vec{a} \in \beta_{p+1}$.
    *   Else: Iterate $\vec{b} \in \beta_{p+1}$, check if $\vec{R} - \vec{b} \in \alpha_p$.
*   This reduces the complexity from $O(|\alpha| \cdot |\beta|)$ to $O(\min(|\alpha|, |\beta|))$.

## File Structure

*   `src/belief/global_belief_model.py`: Main class managing the global consistency logic, caching, and process pool coordination.
*   `src/belief/global_belief_utils.py`: Standalone worker functions for parallel execution.


Read [](file:///c%3A/Users/modin/Desktop/programming/BombBuster/src/belief/global_belief_utils.py)

Here is a detailed breakdown of the **Global Belief Model** logic and code.

### 1. The Problem: Why Global Consistency?

In *BombBuster*, standard logic (like "I have two 1s, so you can't have five 1s") is **local**. It looks at one player or one constraint at a time.

**Global Consistency** solves a harder problem:
> *Is there ANY valid way to distribute the remaining cards in the deck to all players such that everyone's constraints are satisfied simultaneously?*

If Player A *must* have three `1`s, and Player B *must* have two `1`s, but there are only four `1`s in the deck, a local check might miss this conflict until it's too late. The Global Belief Model catches this immediately by treating the game state as a **resource allocation problem**.

---

### 2. Core Concept: The "Signature"

The algorithm abstracts a player's hand into a **Signature**.
A signature is a **Resource Vector**: a tuple of integers representing the count of each card value in a hand, ignoring the specific order of cards.

*   **Example**: If the card values are `[1, 2, 3, 4, 5]` and a player holds `[1, 1, 3, 4, 4]`.
*   **Signature**: `(2, 0, 1, 2, 0)` (Two 1s, zero 2s, one 3, two 4s, zero 5s).

This abstraction drastically reduces the search space. We don't care *where* the `1` is in the hand for the global check, only that the player consumes two `1`s from the global deck.

---

### 3. The Algorithm: Propagated Dynamic Programming

The algorithm runs in three phases inside `_solve_global_consistency`.

#### Phase 1: Local Candidate Generation
**Goal**: For each player, find every possible "Signature" they could hold given their personal constraints (what they see, what they've been told).

*   **Code**: `generate_signatures_worker` in global_belief_utils.py.
*   **Logic**: It uses **Backtracking** (Depth First Search) to build valid hands card by card.
    *   **Pruning**: It stops early if a partial hand violates "sorted" rules, "adjacent" clues, or "copy count" clues.
    *   **Output**: A set of valid vectors $V_p$ for each player $p$.

#### Phase 2: Forward-Backward Global Filtering
**Goal**: Determine which combinations of signatures can actually coexist to form a complete deck.

We define two sets for each step $i$ (between player $i-1$ and player $i$):
1.  **$\alpha_i$ (Alpha - Forward)**: The set of all possible "consumed resources" by players $0$ to $i-1$.
2.  **$\beta_i$ (Beta - Backward)**: The set of all possible "required resources" by players $i$ to $N-1$ to complete the deck.

*   **Forward Pass**: Start with `(0,0,...)`. Add every valid signature from Player 0. Then add every valid signature from Player 1 to those sums, and so on.
*   **Backward Pass**: Start with `(0,0,...)` at the end. Add signatures from the last player, then the second to last, etc.

#### Phase 3: Projection
**Goal**: Filter the local candidates. A signature $S$ for Player $p$ is valid **only if**:
$$ \exists A \in \alpha_p, \exists B \in \beta_{p+1} \text{ such that } A + S + B = \text{TotalDeck} $$

In simple terms: "Can I find a valid history of previous players ($A$) and a valid future of remaining players ($B$) that, combined with my hand ($S$), uses exactly every card in the deck?"

If yes, we keep $S$. If no, $S$ is impossible globally. We then convert the surviving signatures back into specific card possibilities for each slot.

---

### 4. Code Walkthrough

#### `src/belief/global_belief_model.py`

**Initialization (`__init__`)**
We precompute the `total_deck` vector. This is our target sum.
```python
# Precompute total deck vector
total_deck = [0] * self.K
for v in self.sorted_values:
    total_deck[self.val_to_idx[v]] = config.get_copies(v)
self.total_deck = tuple(total_deck)
```

**Phase 1 Execution (`_solve_global_consistency`)**
We use `ProcessPoolExecutor` to run generation in parallel. We also check a `_signature_cache` to avoid re-computing if a player's constraints haven't changed.

```python
# Inside _solve_global_consistency
for i in range(N):
    # ... calculate cache key ...
    if cache_key in self._signature_cache:
        V.append(self._signature_cache[cache_key])
    else:
        # Submit to worker
        futures.append(get_executor().submit(generate_signatures_worker, *args))
```

**Phase 2 Execution (Forward Pass)**
We iterate through players. For each player, we take every valid "previous state" (`prev_res`) and add every valid "current hand" (`sig`). If the sum doesn't exceed the total deck, it's a valid state for the next step.

```python
Alpha[0].add(zero_vector)
for i in range(N):
    for prev_res in Alpha[i]:
        for sig in V[i]:
            new_res = tuple(a + b for a, b in zip(prev_res, sig))
            if all(x <= y for x, y in zip(new_res, self.total_deck)):
                Alpha[i+1].add(new_res)
```

**Phase 3 Execution (Projection)**
We send the sets $\alpha_p$, $\beta_{p+1}$, and $V_p$ to a worker to find the valid intersection.

```python
futures.append(get_executor().submit(filter_signatures_worker, *args))
```

---

#### global_belief_utils.py

**`generate_signatures_worker`**
This is a recursive backtracking function.
1.  **Base Case**: `pos == hand_size`. We have a full hand. Check final constraints (like "I have exactly two 1s") and add the signature to the set.
2.  **Recursive Step**: Try putting every possible card value in the current slot `pos`.
    *   **Constraint Check**: Is this card allowed by local beliefs? (`val in possible_values`)
    *   **Sorted Check**: Is it $\ge$ the previous card? (`range(min_val_idx, K)`)
    *   **Adjacent Check**: Does it satisfy clues like "Your card 1 equals card 2"?

```python
def backtrack(pos, min_val_idx, current_counts):
    # ... pruning logic ...
    for v_idx in range(min_val_idx, K):
        # ... checks ...
        current_hand[pos] = val
        current_counts[v_idx] += 1
        backtrack(pos + 1, v_idx, current_counts)
        # ... backtrack ...
```

**`filter_signatures_worker`**
This function performs the critical check: $A + S + B = \text{TotalDeck}$.
Rearranging the equation: $A + B = \text{TotalDeck} - S$. Let $R = \text{TotalDeck} - S$.
We need to find if $A + B = R$ for any $A \in \alpha, B \in \beta$.

**Optimization**: Instead of checking every pair $A, B$ (which is $O(|\alpha| \cdot |\beta|)$), we iterate the **smaller** set and look up the required complement in the **larger** set. This is $O(\min(|\alpha|, |\beta|))$.

```python
# Calculate what remains of the deck after taking out this signature
remainder = tuple(t - s for t, s in zip(total_deck, sig))

# Optimization: Iterate smaller set
if len(Alpha_p) < len(Beta_next):
    for prev in Alpha_p:
        # What do we need from the future?
        needed_next = tuple(r - a for r, a in zip(remainder, prev))
        if needed_next in Beta_next:
            is_valid = True; break
else:
    # Iterate Beta, look in Alpha
    for next_vec in Beta_next:
        needed_prev = tuple(r - n for r, n in zip(remainder, next_vec))
        if needed_prev in Alpha_p:
            is_valid = True; break
```

Finally, if a signature is valid, we "unpack" it back into card values. Since hands are always sorted, a signature like `(2, 0, 1...)` (two 1s, one 3) unambiguously means the hand is `[1, 1, 3, ...]`.

```python
for sig in valid_signatures:
    # Reconstruct sorted hand
    hand = []
    for v_idx, count in enumerate(sig):
        hand.extend([sorted_values[v_idx]] * count)
    
    # Add these values to the allowed domains for each position
    for pos in range(hand_size):
        new_domains[pos].add(hand[pos])
```

### 5. Key Optimizations Summary

1.  **Parallelization**: `ProcessPoolExecutor` allows all players to generate signatures and filter them simultaneously. This scales well with CPU cores.
2.  **Caching**: The `_signature_cache` is vital. In a 5-player game, if Player 0 gives a clue to Player 1, Player 2, 3, and 4's local constraints haven't changed. We reuse their generated signatures instantly.
3.  **Set Intersection Optimization**: The "iterate smaller set" trick in `filter_signatures_worker` can speed up the check by orders of magnitude when one side of the board is very constrained (small set) and the other is open (large set).