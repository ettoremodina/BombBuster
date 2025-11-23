# Entropy-Based Call Suggester Design

## 1. Formalization of the Idea

The goal is to select an uncertain call that maximizes the **Expected Information Gain** (or equivalently, minimizes the **Expected Posterior Entropy**).

### Definitions

*   **$B$**: The current belief state of the game.
*   **$H(B)$**: The entropy of the belief state $B$. This is calculated as the sum of entropies of all individual positions across all players (System Entropy).
    *   $H(B) = \sum_{p, i} H(pos_{p,i})$
    *   $H(pos_{p,i}) = \log_2(|PossibleValues_{p,i}|)$ (assuming uniform distribution within the set of possible values).
*   **Candidate Call**: A tuple $(p, i, v)$ where player $p$, wire $i$ has value $v$ in their set of possible values, but $|PossibleValues_{p,i}| > 1$.

### Simulation Process (One Step Ahead)

For a given candidate call $c = (p, i, v)$ on a position with $k = |PossibleValues_{p,i}|$ candidates:

1.  **Determine Probabilities (Uniform Assumption):**
    *   Probability of Success ($v$ is correct): $P_{success} = \frac{1}{k}$
    *   Probability of Failure ($v$ is incorrect): $P_{failure} = \frac{k-1}{k}$

2.  **Simulate Outcomes:**
    *   **Scenario A (Success):**
        *   Create a temporary belief state $B_{success}$.
        *   Apply the constraint: `Player p, Position i IS v`.
        *   Run constraint propagation (filtering).
        *   Calculate resulting system entropy: $H_{success} = H(B_{success})$.
    *   **Scenario B (Failure):**
        *   Create a temporary belief state $B_{failure}$.
        *   Apply the constraint: `Player p, Position i IS NOT v`.
        *   Run constraint propagation (filtering).
        *   Calculate resulting system entropy: $H_{failure} = H(B_{failure})$.

3.  **Calculate Expected Entropy:**
    $$E[H|c] = P_{success} \cdot H_{success} + P_{failure} \cdot H_{failure}$$

### Decision Rule

Select the call $c^*$ that minimizes the expected entropy:
$$c^* = \arg\min_{c} E[H|c]$$

This is equivalent to maximizing the Information Gain: $IG(c) = H(B) - E[H|c]$.

---

## 2. Consideration of Other Aspects (Global Frequency)

**Question:** *Do I have to keep into account other aspects? For example, the value 4 appears in other 12 positions and the value 5 only in other 5, is that a usable information?*

**Answer:** **Yes, this is highly usable information**, and it is critical for high-level play.

### Why it matters
In BombBuster (and similar deduction games), resources are finite. If there are only two '4's in the entire deck, but '4' appears as a candidate in 12 different positions, '4' is a **highly contended resource**.
*   **Finding a '4' (Success):** If you confirm a '4' in one spot, you consume one of the scarce copies. This might force the other 11 positions to *not* be '4' (if the limit is reached), causing a massive collapse in uncertainty across the board.
*   **Eliminating a '4' (Failure):** If you confirm a spot is *not* '4', you force the scarce '4's to be in the remaining 11 spots.

### How to handle it
You do **not** need to add a separate manual heuristic for this *if* your simulation uses a robust belief model.

1.  **Implicit Handling (Recommended):**
    If your simulation step (`Run constraint propagation`) uses the `GlobalBeliefModel` (or any model that enforces "Total Card Counts"), the entropy calculation will **automatically** capture this.
    *   When you simulate "Success: This is a 4", the global solver will see that one '4' is used. If '4's are scarce, the solver will remove '4' from many other players' possibilities.
    *   This results in a much lower $H_{success}$, making the weighted score $E[H|c]$ lower (better).
    *   Therefore, the "Entropy Based Suggester" naturally prefers calls that resolve global bottlenecks.

2.  **Explicit Heuristic (Fallback):**
    If running the full `GlobalBeliefModel` for every simulation is too slow (computationally expensive), you can use the frequency as a heuristic tie-breaker or weight:
    *   Weight the "Success" branch by the "Contention Ratio" of value $v$: $\frac{\text{Count of positions with } v}{\text{Total copies of } v}$.
    *   However, since you have a `GlobalBeliefModel` implemented, relying on the simulation is more accurate.

### Conclusion
The "Simulation" approach is the correct formalization. The "Global Frequency" aspect is a specific instance of constraint propagation. By using a belief model that enforces global counts during the simulation, you automatically account for the value of resolving contended numbers.
