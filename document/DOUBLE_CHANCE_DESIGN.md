# Double Chance Suggester Design

## Problem Definition
The goal is to implement a "Double Chance" suggester. This mechanic allows a player to select **two wires of the same opponent** and call a specific **value**. The call is successful if **at least one** of the two selected wires holds that value.

We want to find the optimal combination of:
1.  **Target Player** ($P$)
2.  **Wire Pair** ($i, j$)
3.  **Value** ($v$)

...that maximizes the probability of success: $P(W_i = v \lor W_j = v)$.

## Mathematical Formulation

Let $H$ be the random variable representing the hand of player $P$.
Let $S_P$ be the set of all valid hands for player $P$ that are consistent with:
1.  **Current Beliefs**: $H[k] \in \text{Beliefs}[P][k]$ for all wire positions $k$.
2.  **Sorted Constraint**: $H[k] \le H[k+1]$ (assuming wires are sorted).
3.  **Global Constraints**: The hand must not use more copies of a card than available in the deck (minus known cards elsewhere).

The probability of success for a call $(i, j, v)$ is:

$$ P(\text{Success}) = \frac{\text{Count}(h \in S_P \mid h[i] = v \lor h[j] = v)}{|S_P|} $$

## Algorithm

### 1. Generate Valid Hands
Since the number of wires per player is small (typically 4 or 5) and the number of card values is limited, we can exhaustively generate all valid hands for a specific player.

We will implement a helper method `_generate_valid_hands(player_id)`:
*   **Input**: `player_id`
*   **Output**: A list of valid hands (tuples).
*   **Logic**:
    *   Use a backtracking approach (similar to `generate_signatures_worker` but returning hands).
    *   Iterate through positions $0$ to $K-1$.
    *   At each position, try all values in `beliefs[player_id][position]`.
    *   Prune if:
        *   Value < previous value (violation of sorted order).
        *   Count of value in current hand > total copies available in deck.
        *   (Optional) Other constraints like "not equal to adjacent" if applicable.

### 2. Evaluate Double Chance Probabilities
We will implement `get_double_chance_suggestions()` in `GameStatistics`:

1.  **Identify Playable Values**: Get the set of values the current player can call (usually values they hold in their own hand).
2.  **Iterate Opponents**: For each opponent $P$:
    *   Generate $S_P$ (all valid hands).
    *   If $S_P$ is empty (contradiction), skip.
3.  **Iterate Pairs**: For each pair of indices $(i, j)$ with $i < j$:
    *   **Iterate Values**: For each value $v$ in `playable_values`:
        *   Check if $v$ is possible in position $i$ OR position $j$ (optimization).
        *   Count $N_{success} = 0$.
        *   For each hand $h \in S_P$:
            *   If $h[i] == v$ OR $h[j] == v$: $N_{success} += 1$.
        *   Calculate $Prob = N_{success} / |S_P|$.
        *   Store suggestion $(P, i, j, v, Prob)$.
4.  **Sort and Return**: Sort suggestions by probability (descending).

## Implementation Plan

### New Methods in `GameStatistics`

1.  `_generate_valid_hands(self, player_id: int) -> List[Tuple[int, ...]]`
    *   Helper to generate hands.
    *   Needs access to `self.belief_model.beliefs` and `self.config`.

2.  `get_double_chance_suggestions(self) -> List[Dict]`
    *   Main method to compute probabilities.
    *   Returns a list of dictionaries:
        ```python
        {
            'target_id': int,
            'positions': Tuple[int, int],
            'value': Union[int, float],
            'probability': float,
            'is_certain': bool  # True if probability == 1.0
        }
        ```

3.  `print_double_chance_suggestions(self, player_names=None)`
    *   Pretty printer for the suggestions.

### Integration
*   We will add these methods to `src/statistics.py`.
*   We will assume that `self.belief_model.beliefs` is already filtered and up-to-date.

## Example Scenario
*   Player 1 has beliefs:
    *   Pos 0: {1, 2}
    *   Pos 1: {2, 3}
*   Valid hands (assuming sorted): (1, 2), (1, 3), (2, 2), (2, 3).
*   Double Chance Call on (0, 1) with value 2:
    *   (1, 2): Success (Pos 1 is 2)
    *   (1, 3): Fail
    *   (2, 2): Success (Pos 0 is 2, Pos 1 is 2)
    *   (2, 3): Success (Pos 0 is 2)
    *   Probability = 3/4 = 75%.
