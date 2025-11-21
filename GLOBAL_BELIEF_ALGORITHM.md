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
