# Known issue: a called value can be counted twice

Found on 2026-10-09 while building the reduced, in-browser version of this engine for the
portfolio website. Nothing in the engine was changed; this note only records what was seen,
where it comes from, and a fix that was tried in memory.

## What happens

Sometimes a belief model crosses out a value that is still possible — occasionally the true
one. After that the model is wrong for the rest of the game, and so is every suggestion
computed from it.

It was measured by letting the engine play 70 small games (`export_reference_games.py`) and
comparing, wire by wire and for every player's point of view, what the belief model holds
possible with an exhaustive enumeration of every deal consistent with the public history
(33,120 comparisons):

| Belief model | Crossed out a possible value | … the true value |
|---|---|---|
| `GlobalBeliefModel` | 10 wires | 2 |
| `BeliefModel` (iterative filters only) | 886 wires | 606 |

The games are reduced (3–4 players, 4–6 wires each, 2 or 4 copies of each value) and played
with a random calling policy, which fails often and so produces many "called" values. In a
real game the situation is rarer, but nothing about it depends on the game being small.
`TODO.md` already suspected both spots: "iterative filter may have a problem" and
"_apply_called_values_filter (not sure the logic is correct)".

## A case that can be replayed

Three players, values 1–9 in two copies, seed 28 of `export_reference_games.py`:

    hands  P0 [1,1,6,7,8,9]   P1 [4,4,5,5,7,8]   P2 [2,2,3,3,6,9]

After the opening signals, four double reveals and one successful call, what is still hidden
from P2 is the last wire of P0 and the last two of P1. Then:

    move 9   P0 calls "8" on P2's last wire: wrong (it is a 9). So P0 holds an 8.
    move 10  P1 calls "7" on P0's fifth wire: wrong, and P0 signals that it is an 8.

For P2 two deals remain possible: P0's last wire is the 9 and P1's is the 8 (the truth), or
the other way round. `GlobalBeliefModel` concludes that P0's last wire is an 8 and P1's a 9:
it has crossed out the truth.

## Where it comes from

`GlobalBeliefModel._get_min_counts` requires, for every value a player has *called*, one
copy more than the positions already certain to hold it:

    for pos in range(hand_size):
        if len(player_beliefs[pos]) == 1:
            min_counts[val] += 1            # every certain position
    for val, tracker in self.value_trackers.items():
        if player_id in tracker.called:
            min_counts[val] += 1            # plus one for the call

A player leaves `tracker.called` only when `_update_value_trackers` runs, at the end of
`apply_filters`. In between, a position can become certain by other means — in the case
above `_process_failed_call` discards 7 from P0's fifth wire and leaves `{8}` — and that
position may well be the very copy the player called with. For one pass the same wire is
counted both as "certain 8" and as "the 8 that was called", P0 is required to hold two 8s,
and the other deal is thrown away.

`ValueTracker.uncertain` does the same sum for the iterative filters
(`total - revealed - certain - called`), which is the likely reason `BeliefModel` shows the
problem far more often; that path was measured but not investigated further.

## A fix that was tried

A call proves one uncut copy. Copies revealed before the call cannot be it; a copy that is
merely certain can. So the requirement is one copy beyond the *revealed* ones, and never an
addition on top of the certain ones:

    def _get_min_counts(self, player_id):
        min_counts = collections.defaultdict(int)
        for pos in range(self.config.wires_per_player):
            beliefs = self.beliefs[player_id][pos]
            if len(beliefs) == 1:
                min_counts[next(iter(beliefs))] += 1
        for val, tracker in self.value_trackers.items():
            if player_id in tracker.called:
                revealed = sum(1 for pid, _ in tracker.revealed if pid == player_id)
                min_counts[val] = max(min_counts[val], revealed + 1)
        return dict(min_counts)

With this replacement applied in memory (not in the repository) the same 70 games give 0
wires crossed out wrongly for `GlobalBeliefModel`, and it still agrees with the exhaustive
enumeration everywhere else. `BeliefModel` is unchanged by it.

## How to check again

    python export_reference_games.py --out reference.json
    cd <portfolio-website>
    BOMB_BUSTER_REFERENCE=<path to reference.json> node scripts/check-bomb-buster-engine.mjs

The last table printed counts, for each belief model, the wires where a possible value was
crossed out.

## Fix applied (2026-11-16)

The replacement of `_get_min_counts` above is now in `src/belief/global_belief_model.py`.
Same 70 games, same check:

| Belief model | Crossed out a possible value, before → after | … the true value |
|---|---|---|
| `GlobalBeliefModel` | 10 → 0 | 2 → 0 |
| `BeliefModel` | 886 → 886 | 606 → 606 |

`BeliefModel` is not touched by the fix: its beliefs are identical, move by move, in the two
exports. One detail can mislead a re-run: the export keeps only the moves played by both models,
and before the fix the wrong deduction in seed 28 (the case above) ended the global game one
move early. With the fix that game lasts one move more, so the raw check compares 36 more wires
(33,156 instead of 33,120) and `BeliefModel` shows 889 instead of 886, all on that extra move.
Cut at the old length, the numbers are those in the table.

Still open: the same double count in `ValueTracker.uncertain`, used by the iterative filters of
`BeliefModel`. The test suite fails the same way with and without the fix (28 of 30 tests stop
on a wire-length `ValueError` while building the game): it is out of date with the code.
