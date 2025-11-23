# BombBuster: Problem Definition & Formalization

## 1. Setup and Distribution

Let there be $N$ players, denoted as $P = \{p_1, p_2, \dots, p_N\}$.

There exists a global multiset of "wires" (or cards) $W$.
The total number of wires is $M = |W|$.
Each wire $w \in W$ has an associated value $v(w) \in V$, where $V = \{v_1, v_2, \dots, v_K\}$ is the set of possible values (types).
The distribution of values is fixed and known: for each value $v_k \in V$, there are exactly $r_k$ copies in $W$.
Thus, $M = \sum_{k=1}^{K} r_k$.

The wires are distributed uniformly among the $N$ players.
Each player $p_i$ receives a hand $H_i$ consisting of $n_i = M/N$ wires.
The partition is disjoint: $W = \bigsqcup_{i=1}^{N} H_i$.

**Constraint (Sorting):**
Crucially, each player's hand $H_i$ is sorted in ascending order of values.
Let $H_i = (h_{i,1}, h_{i,2}, \dots, h_{i,n_i})$.
Then, $v(h_{i,1}) \le v(h_{i,2}) \le \dots \le v(h_{i,n_i})$.

*Note: While the values are sorted, the specific identity of identical values is indistinguishable, but their position in the sorted sequence is distinct.*

## 2. Information and Constraints

The game is a partial information cooperative game.
- **Private Information:** Player $p_i$ knows the exact values in their own hand $H_i$.
- **Public Information:** All players know the global distribution $\{r_k\}$, the number of players $N$, the hand size $n_i$, and the history of all public actions (calls and reveals).

We can categorize the information available into specific constraints on the unknown values. Let $X_{i,j}$ be the random variable representing the value of the wire at position $j$ for player $i$.

### Types of Information
1.  **Position-Specific Positive Information:**
    - "Player $i$ has value $v$ at position $j$."
    - Formal: $X_{i,j} = v$.
    - Source: Successful calls, self-knowledge, or deduction.

2.  **Position-Specific Negative Information:**
    - "Player $i$ does NOT have value $v$ at position $j$."
    - Formal: $X_{i,j} \neq v$.
    - Source: Failed calls, deduction (e.g., if $X_{i,j}=u$, then $X_{i,j} \neq v$ for $u \neq v$).

3.  **General Positive Information (Existence):**
    - "Player $i$ possesses at least one copy of value $v$ somewhere in their hand."
    - Formal: $\exists j \in \{1, \dots, n_i\} \text{ s.t. } X_{i,j} = v$.
    - Source: A player declaring a call using value $v$ (since they must hold $v$ to call with it).

4.  **General Negative Information (Absence):**
    - "Player $i$ possesses NO copies of value $v$."
    - Formal: $\forall j \in \{1, \dots, n_i\}, X_{i,j} \neq v$.
    - Source: Deduction (e.g., all copies of $v$ are accounted for elsewhere).

5.  **Ordering Constraints:**
    - Due to the sorted nature of hands, values at specific positions constrain their neighbors.
    - Formal: $X_{i,j} \le X_{i, j+1}$ for all valid $j$.
    - Implication: If $X_{i,j} = v$, then $\forall k < j, X_{i,k} \le v$ and $\forall k > j, X_{i,k} \ge v$.

## 3. Game Dynamics

The game proceeds in turns.

**The Call:**
Active player $p_a$ chooses:
1.  A position $s$ in their own hand $H_a$ with value $v = v(h_{a,s})$.
2.  A target player $p_b$ ($b \neq a$).
3.  A target position $t$ in $p_b$'s hand.
4.  Declares: "Player $p_b$ has value $v$ at position $t$."

**Outcomes:**
-   **Success:** If $v(h_{b,t}) = v$, the call is correct.
    -   $h_{b,t}$ is revealed to be $v$.
    -   $h_{a,s}$ is revealed to be $v$ (the caller proves they had the value).
    -   This becomes public knowledge: $X_{b,t} = v$ and $X_{a,s} = v$.
-   **Failure:** If $v(h_{b,t}) \neq v$, the call is incorrect.
    -   The team incurs a strike (cost).
    -   Public knowledge gained: $X_{b,t} \neq v$.
    -   Also implies caller has $v$ somewhere (General Positive Info).

**Win Condition:**
The team wins when the value of every wire $X_{i,j}$ is known (either revealed or deduced with certainty) for all $i, j$.

**Loss Condition:**
The team loses if the number of incorrect calls reaches a threshold $L_{max}$.

## 4. The Inference Problem

The core computational challenge is to maintain a **Belief State** $\mathcal{B}$ that is consistent with all accumulated constraints.

Let $\Omega$ be the set of all possible global assignments of wires to players that satisfy:
1.  The global multiset count (exactly $r_k$ copies of $v_k$).
2.  The sorting constraint for every player.
3.  All revealed $X_{i,j} = v$.
4.  All negative constraints $X_{i,j} \neq v$.

The goal of the filtering system is to compute, for every unrevealed $X_{i,j}$, the set of feasible values:
$D_{i,j} = \{ v \in V \mid \exists \omega \in \Omega \text{ s.t. } \omega_{i,j} = v \}$.

If $|D_{i,j}| = 1$, the value is deduced.
If $D_{i,j} = \emptyset$, a contradiction has occurred (impossible state).

### Necessary Filtering Logic

To solve this efficiently without enumerating $\Omega$ (which is huge), we apply local consistency checks and propagators:

1.  **Domain Consistency:** Maintain candidate sets $C_{i,j} \subseteq V$. Initially $C_{i,j} = V$.
2.  **Sorting Propagator:**
    -   $min(C_{i,j}) \ge min(C_{i, j-1})$
    -   $max(C_{i,j}) \le max(C_{i, j+1})$
3.  **Global Cardinality Constraint (GCC):**
    -   Ensure the total assignment of value $v$ across all players does not exceed $r_k$.
    -   Ensure it is possible to assign remaining copies of $v$ to available slots.
4.  **Sliding Window / Distance Filter:**
    -   If player $i$ has $k$ remaining copies of value $v$, and the range of indices compatible with $v$ is small, it constrains where $v$ can be.
5.  **Subset/Sudoku Constraints:**
    -   If a set of $k$ positions can only take values from a set of $k$ values, those values cannot appear elsewhere.

# GEMINI 

Here is the formal specification for the **Global Consistency Algorithm via Propagated Dynamic Programming**.

This document defines the mathematical model to compute the **Minimal Domain** (the most stringent belief system) for every card slot.

-----

# BombBuster Inference Engine: The Global Consistency Algorithm

## 1\. Problem Formalization

### 1.1 Variables and Domains

Let the game state be defined by:

  * **$P = \{1, \dots, N\}$**: The set of players.
  * **$K$**: The number of distinct card values.
  * **$R_{total} \in \mathbb{N}^K$**: The global "Parikh Vector" (frequency array) representing the total deck composition.
      * $R_{total}[v]$ = total count of value $v$ in the deck.
  * **$H_i$**: The hand of player $i$, consisting of $L$ slots (where $L = M/N$).
  * **$x_{i,j}$**: The variable representing the value of the card at player $i$, slot $j$.

### 1.2 The Goal

For every player $i$ and slot $j$, find the **Minimal Domain** $D_{i,j}^*$:
$$D_{i,j}^* = \{ v \in V \mid \exists \text{ global assignment } \Omega \text{ satisfying all constraints where } \Omega_{i,j} = v \}$$

-----

## 2\. Phase I: Local Candidate Generation

Before analyzing interactions between players, we must generate the "Possibility Space" for each player individually.

### 2.1 Local Hand Validity

A hand assignment $h = (c_1, c_2, \dots, c_L)$ for player $i$ is **Locally Valid** if:

1.  **Sorted:** $c_1 \le c_2 \le \dots \le c_L$.
2.  **Positive Constraints:** For all slots $j$ where we know $x_{i,j}=v$, $c_j = v$.
3.  **Negative Constraints:** For all slots $j$ where we know $x_{i,j} \neq v$, $c_j \neq v$.
4.  **Caller Constraint:** If player $i$ has previously "called" (revealed) a value $v$ somewhere, then $v \in h$.

### 2.2 Signature Compression

Because the global constraints are based on *sums*, we distinguish between the specific **Hand Configuration** and its **Resource Signature**.

  * Let $\mathcal{S}_i$ be the set of all Locally Valid hands for player $i$.
  * Let $\sigma(h)$ be the mapping of a hand $h$ to its frequency vector (signature).
      * Example: $h=(1,1,5) \implies \sigma(h) = [2, 0, 0, 0, 1]$.

We define the set of valid signatures for player $i$:
$$V_i = \{ \sigma(h) \mid h \in \mathcal{S}_i \}$$

> **Implementation Note:** We map multiple hands to a single signature to speed up the DP. We must maintain a map `Map_Sig_to_Hands[signature] -> List of Hands` for the final projection step.

-----

## 3\. Phase II: The Forward-Backward Algorithm (Global Filtering)

This phase eliminates "Phantom Signatures"—hands that look valid for a player but require resources that do not exist or are monopolized by others.

We model the game as a pathfinding problem on a lattice graph where nodes are **Resource States**.

[Image of Trellis Diagram]

### 3.1 The Forward Pass (Reachability)

Let $\alpha_i$ be the set of **Consumed Resource Vectors** reachable after player $i$ has selected a hand.

  * **Initialization:** $\alpha_0 = \{ \vec{0} \}$ (The zero vector).

  * **Recurrence (for $i = 1$ to $N$):**
    $$\alpha_i = \{ \vec{r} + \vec{v} \mid \vec{r} \in \alpha_{i-1}, \vec{v} \in V_i, \text{ subject to } (\vec{r} + \vec{v}) \le R_{total} \}$$
    *(Note: $\le$ is element-wise comparison).*

  * **Pruning:** If $\alpha_i = \emptyset$, a contradiction exists (game state is impossible).

### 3.2 The Backward Pass (Sufficiency)

Let $\beta_i$ be the set of **Required Resource Vectors** needed by players $i \dots N$ to complete the game validly.

  * **Initialization:** $\beta_{N+1} = \{ \vec{0} \}$.
  * **Recurrence (for $i = N$ down to $1$):**
    $$\beta_i = \{ \vec{req} + \vec{v} \mid \vec{req} \in \beta_{i+1}, \vec{v} \in V_i, \text{ subject to } (\vec{req} + \vec{v}) \le R_{total} \}$$

> *Concept Check:* $\alpha_i$ represents "What players $1 \dots i$ can **take**." $\beta_i$ represents "What players $i \dots N$ **need**."

-----

## 4\. Phase III: Intersection & Belief Projection

We now combine the Forward and Backward sets to determine the "most stringent" validity.

### 4.1 Global Validity Condition

A signature $\vec{v} \in V_i$ (for player $i$) is **Globally Valid** if and only if there exists a valid "Past" and a valid "Future" that connect through it.

Formally, $\vec{v}$ is valid iff:
$$\exists \vec{prev} \in \alpha_{i-1} \text{ AND } \exists \vec{next} \in \beta_{i+1} \text{ such that: }$$
$$\vec{prev} + \vec{v} + \vec{next} = R_{total}$$

[Image of Set Intersection Diagram]

### 4.2 Filtering the Signatures

For the target player $i$:

1.  Iterate through every signature $\vec{v} \in V_i$.
2.  Check the Global Validity Condition (using the equation above).
3.  Construct the set of **Globally Valid Signatures** $V_i^* \subseteq V_i$.

### 4.3 Projection to Minimal Domains

Now we map the valid signatures back to the specific hands and slot values.

1.  **Recover Hands:** Retrieve the specific sorted hands associated with the valid signatures:
    $$\mathcal{S}_i^* = \bigcup_{\vec{v} \in V_i^*} \{ h \in \mathcal{S}_i \mid \sigma(h) = \vec{v} \}$$
2.  **Domain Reduction:**
    For each slot $j \in \{1, \dots, L\}$:
    $$D_{i,j}^* = \{ h[j] \mid h \in \mathcal{S}_i^* \}$$

**Result:** The set $D_{i,j}^*$ contains *only* the values that are possible in at least one fully consistent "World". Any value not in this set is mathematically impossible.

-----

## 5\. Algorithm Summary (Pseudocode)

```python
def solve_smallest_belief_model(N, Deck_Total, Player_Constraints):
    
    # --- Phase 1: Local Generation ---
    # List of Sets of signatures. V[i] stores unique vectors for player i
    V = [] 
    # Map to retrieve concrete hands from signatures
    Sig_Map = [{} for _ in range(N)] 
    
    for i in range(N):
        valid_hands = generate_sorted_hands(Player_Constraints[i])
        V_i = set()
        for hand in valid_hands:
            sig = compute_signature(hand)
            V_i.add(sig)
            if sig not in Sig_Map[i]: Sig_Map[i][sig] = []
            Sig_Map[i][sig].append(hand)
        V.append(V_i)

    # --- Phase 2: Forward Pass (Alpha) ---
    # Alpha[i] = set of consumed resource vectors after player i
    Alpha = [set() for _ in range(N + 1)]
    Alpha[0].add(Zero_Vector)

    for i in range(N): # Players 0 to N-1
        for prev_res in Alpha[i]:
            for sig in V[i]:
                new_res = prev_res + sig
                if new_res <= Deck_Total:
                    Alpha[i+1].add(new_res)

    # Check for global contradiction
    if Deck_Total not in Alpha[N]:
        return "IMPOSSIBLE_STATE"

    # --- Phase 2: Backward Pass (Beta) ---
    # Beta[i] = set of resource vectors NEEDED by players i...N
    Beta = [set() for _ in range(N + 2)]
    Beta[N+1].add(Zero_Vector)

    for i in range(N, 0, -1): # Players N down to 1
        player_idx = i - 1
        for needed_res in Beta[i+1]:
            for sig in V[player_idx]:
                total_needed = needed_res + sig
                if total_needed <= Deck_Total:
                    Beta[i].add(total_needed)

    # --- Phase 3: Projection (For Target Player P) ---
    # Example for a specific player P
    Final_Domains = [set() for _ in range(Hand_Size)]
    
    for sig in V[P]:
        # Check if this signature bridges Alpha and Beta
        # Optimization: Instead of full O(N^2) loop, we check existence
        is_globally_valid = False
        
        # We need: prev + sig + next = Total
        # So: prev + next = Total - sig
        # We check if any combination of Alpha[P] and Beta[P+2] sums to (Total - sig)
        
        target_remainder = Deck_Total - sig
        # Efficient check:
        for prev in Alpha[P]:
            needed_next = target_remainder - prev
            if needed_next in Beta[P+2]:
                is_globally_valid = True
                break
        
        if is_globally_valid:
            # Retrieve concrete hands and add values to domains
            for hand in Sig_Map[P][sig]:
                for slot in range(Hand_Size):
                    Final_Domains[slot].add(hand[slot])

    return Final_Domains
```

-----

## 6\. Complexity & Optimization Notes

### Why this works efficiently

While the number of *Hands* can be large, the number of distinct *Signatures* (count vectors) is much smaller.

  * **Example:** If hands are size 5 and values are 1-5.
      * There are thousands of permutations.
      * There are only a few dozen valid ways to sum to 5 cards.
      * The DP state space collapses collisions, making this extremely fast ($<10ms$) for typical game sizes.

### Optimization: Hashing

Since vectors (arrays) are not hashable by default in many languages, implement a simple hash function to store Resource Vectors in sets:
$$Hash(\vec{v}) = \sum_{k=1}^{K} v[k] \times (M+1)^k$$
This treats the vector as a base-$(M+1)$ integer, allowing $O(1)$ set lookups.

### Optimization: Bitmasks

If the card counts are small (e.g., max 4 copies of any card), you can pack the entire Resource Vector into a single 64-bit integer.

  * 3 bits per card type $\times$ 5 types = 15 bits.
  * Vector addition becomes integer addition.
  * Vector comparison ($\le$) can be done via bitwise logic (checking for borrows/overflows).