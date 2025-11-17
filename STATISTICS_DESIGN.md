# Statistics and Entropy Measures for BombBuster

## Overview
This document describes the mathematical framework for measuring uncertainty in the belief system and guiding optimal decisions.

## Entropy Measures

### 1. Shannon Entropy (Position-Level)
For a single position, Shannon entropy measures the uncertainty about which value is at that position.

**Formula:**
```
H(position) = -Σ P(value) × log₂(P(value))
```

Where:
- `P(value)` is the probability that this value is at this position
- For uniform belief: `P(value) = 1 / |possible_values|`
- For certain position (1 value): `H = 0` (no uncertainty)
- For maximum uncertainty (all K values possible): `H = log₂(K)`

**Example:**
- Position with 1 possible value: `H = 0` (certain)
- Position with 2 possible values: `H = 1.0` (1 bit of uncertainty)
- Position with 4 possible values: `H = 2.0` (2 bits of uncertainty)

### 2. Player-Level Entropy
Total uncertainty for one player's entire wire.

**Formula:**
```
H(player) = Σ H(position) for all positions in player's wire
```

**Normalized version (0 to 1):**
```
H_norm(player) = H(player) / (N × log₂(K))
```

Where:
- `N` = number of positions per player
- `K` = number of distinct wire values
- Maximum entropy = `N × log₂(K)` (all positions maximally uncertain)

### 3. System-Level Entropy
Total uncertainty across all players.

**Formula:**
```
H(system) = Σ H(player) for all players
```

## Call Quality Metrics

### 1. Information Gain
Expected reduction in entropy if a call succeeds.

**For certain call (belief set size = 1):**
```
IG = H(position_before) - H(position_after)
    = log₂(1) - 0 = 0
```
*Note: Certain call has 0 information gain because we already know the answer*

**For uncertain call:**
```
IG = P(success) × [H_before - 0] + P(fail) × [H_before - H_after_fail]
```

Where:
- `P(success) = 1 / |possible_values|` (uniform assumption)
- `P(fail) = 1 - P(success)`
- `H_after_fail` depends on how many values remain after eliminating one

### 2. Call Priority Score
Combined metric for ranking calls:

**Formula:**
```
Score(call) = α × Certainty + β × IG + γ × Cascade_Potential
```

Where:
- `Certainty = 1 / |possible_values|` (higher is better)
- `IG` = Information Gain (higher is better)
- `Cascade_Potential` = expected constraint propagation (filters activated)
- `α, β, γ` = weights (default: α=10, β=1, γ=0.5)

**Simplified version (current implementation):**
```
Score(call) = 1 / |possible_values|
```

Prioritize certain calls (score = 1.0), then minimum uncertainty.

## Uncertainty Statistics

### Per-Player Statistics
For each player, track:

1. **Total Entropy**: `H(player)`
2. **Normalized Entropy**: `H_norm(player)` (0 to 1 scale)
3. **Certain Positions Count**: Number of positions with `|possible| = 1`
4. **Average Position Uncertainty**: `mean(|possible_values|)` across positions
5. **Progress Percentage**: `100 × certain_count / total_positions`

### System-Wide Statistics

1. **Total System Entropy**: `H(system)`
2. **Average Player Entropy**: `H(system) / num_players`
3. **Completion Percentage**: Percentage of all positions that are certain
4. **Most Uncertain Player**: Player with highest `H(player)`
5. **Convergence Rate**: Change in entropy per turn/call

## Call Suggestion Strategy

### Current Implementation (Simple)
1. Filter for values the player has
2. Find certain calls (`|possible| = 1`)
3. If no certain calls, suggest minimum uncertainty (`min |possible|`)

### Future Enhancements
1. **Expected Value Optimization**: Maximize `E[IG]` over all possible calls
2. **Risk-Adjusted Scoring**: Weight by `P(success) × IG - P(fail) × penalty`
3. **Cascade Analysis**: Prefer calls that trigger constraint propagation
4. **Value Rarity**: Prioritize rare values (few remaining uncertain copies)
5. **Position Clustering**: Target positions near already-revealed positions

## Implementation Notes

### Computational Complexity
- **Per-position entropy**: O(|possible_values|) ≈ O(K) worst case
- **Per-player entropy**: O(N × K) where N = positions per player
- **System entropy**: O(P × N × K) where P = number of players

For typical game (P=5, N=10, K=14): ~700 operations per entropy calculation.

### Update Frequency
- Recalculate after each call/reveal (when beliefs change)
- Cache results to avoid redundant calculations
- Only update affected players when possible

### Numerical Stability
- Use `log₂(x)` from math library
- Handle `|possible| = 1` specially (entropy = 0, avoid log(1) = 0)
- Return 0 for empty sets (shouldn't occur in valid game state)

## Example Calculation

**Game State:**
- Player 0, Position 0: {1, 2, 3} → `H = log₂(3) ≈ 1.58 bits`
- Player 0, Position 1: {5} → `H = 0 bits` (certain)
- Player 0, Position 2: {2, 4, 6, 8} → `H = log₂(4) = 2.0 bits`

**Player 0 Total Entropy:**
```
H(Player 0) = 1.58 + 0 + 2.0 = 3.58 bits
```

**Normalized (if 10 positions, 14 distinct values):**
```
H_max = 10 × log₂(14) ≈ 10 × 3.807 = 38.07 bits
H_norm = 3.58 / 38.07 ≈ 0.094 (9.4% of maximum uncertainty)
```

This means Player 0's wire is ~90.6% resolved!
