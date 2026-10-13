"""
Export reference games for the reduced engine of the portfolio website.

The portfolio page of this project runs a small re-implementation of the engine in the
browser (TypeScript, a reduced game: fewer wires, calls and double reveals only). This script
lets the real engine play that same reduced game and writes down, after every move, what each
player's belief system considers possible. The website's check replays the same moves and
compares its own deductions with these.

    python export_reference_games.py --out path/to/bomb-buster-reference.json

Nothing in the engine is changed. The script only:

  - builds a GameConfig for the reduced game instead of the one in config/game_config.py, and
    switches the VOID player off for this process;
  - plays with a seeded random policy (any legal call), so that the moves do not depend on the
    beliefs and the same game can be replayed by another engine;
  - follows play_auto.py for what a move does: a failed call is followed by the target
    signalling the real value of the wire; whoever holds the last two copies reveals both.

Each game is played twice with the same moves, once per belief model, and both are exported:
`filters` is BeliefModel (the local filters), `global` is GlobalBeliefModel.

A set of possible values is written as an integer with one bit per value (bit 3 set means
"3 is possible"), by viewer, then by player, then by position.
"""
import argparse
import contextlib
import io
import json
import random
from pathlib import Path

import config.game_config as game_config

# The VOID player belongs to the full game; it is looked up when a Game is created.
game_config.USE_VOID_PLAYER = False

from config.game_config import GameConfig  # noqa: E402
from src.game import Game  # noqa: E402
from src.player import Player  # noqa: E402

# The reduced games exported: (players, values, copies of each value, number of games).
SETUPS = [
    (3, 9, 2, 30),
    (3, 6, 2, 20),
    (4, 4, 4, 20),
]


def as_mask(values) -> int:
    """Encode a set of possible values as an integer with one bit per value."""
    mask = 0
    for value in values:
        mask |= 1 << int(value)
    return mask


def deal(players: int, values: int, copies: int, rng: random.Random):
    """Shuffle the deck and deal sorted hands."""
    deck = [value for value in range(1, values + 1) for _ in range(copies)]
    rng.shuffle(deck)
    size = len(deck) // players
    return [sorted(deck[player * size:(player + 1) * size]) for player in range(players)]


def play(players: int, values: int, copies: int, seed: int, use_global: bool):
    """
    Play one reduced game with a seeded random policy.

    Returns:
        (hands, moves, beliefs) where beliefs[k] is the state after moves[k]:
        beliefs[k][viewer][player][position] is a bit mask of possible values.
    """
    rng = random.Random(seed)
    hands = deal(players, values, copies, rng)
    size = len(hands[0])
    config = GameConfig(
        wire_distribution={value: copies for value in range(1, values + 1)},
        n_players=players,
        max_wrong_calls=10 ** 6,
        playing_irl=False,
        use_global_belief=use_global,
        auto_filter=True,
    )
    seats = [Player(player, list(hands[player]), config) for player in range(players)]
    game = Game(seats, config)
    cut = [[False] * size for _ in range(players)]
    moves, beliefs = [], []

    def snapshot():
        beliefs.append([
            [[as_mask(seat.belief_system.beliefs[player][position]) for position in range(size)] for player in range(players)]
            for seat in seats
        ])

    # Opening: every player signals one wire.
    for player in range(players):
        position = rng.randrange(size)
        game.signal_value(player, hands[player][position], position)
        moves.append({"kind": "hint", "player": player, "position": position, "value": hands[player][position]})
        snapshot()

    turn = 0
    while not all(all(row) for row in cut) and not game.is_game_over() and len(moves) < 400:
        mine = [position for position in range(size) if not cut[turn][position]]
        if not mine:
            turn = (turn + 1) % players
            continue

        # The last two copies of a value, both in this hand: reveal them together.
        pair = None
        for value in sorted({hands[turn][position] for position in mine}):
            own = [position for position in mine if hands[turn][position] == value]
            elsewhere = any(
                hands[other][position] == value and not cut[other][position]
                for other in range(players) if other != turn for position in range(size)
            )
            if len(own) >= 2 and not elsewhere:
                pair = (own[0], own[1], value)
                break

        if pair:
            game.double_reveal(turn, pair[2], pair[0], pair[1])
            cut[turn][pair[0]] = cut[turn][pair[1]] = True
            moves.append({"kind": "pair", "player": turn, "positions": [pair[0], pair[1]], "value": pair[2]})
        else:
            value = hands[turn][rng.choice(mine)]
            wire = next(position for position in mine if hands[turn][position] == value)
            targets = [(other, position) for other in range(players) if other != turn
                       for position in range(size) if not cut[other][position]]
            target, position = rng.choice(targets)
            record = game.auto_make_call(turn, target, position, value)
            truth = hands[target][position]
            if record.success:
                wire = record.caller_position
                cut[target][position] = cut[turn][wire] = True
            elif not game.is_game_over():
                # The failed call may itself have settled everything: then nothing is left to signal.
                game.signal_value(target, truth, position)
            moves.append({
                "kind": "call", "caller": turn, "wire": wire, "target": target, "position": position,
                "value": value, "hit": bool(record.success), "truth": truth, "among": mine,
            })
        snapshot()
        turn = (turn + 1) % players

    return hands, moves, beliefs


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True, help="Where to write the JSON file")
    args = parser.parse_args()

    games = []
    for players, values, copies, count in SETUPS:
        for seed in range(1, count + 1):
            # The engine prints its progress; none of it is wanted here.
            with contextlib.redirect_stdout(io.StringIO()):
                hands, moves, by_filters = play(players, values, copies, seed, use_global=False)
                same_hands, same_moves, by_global = play(players, values, copies, seed, use_global=True)
            # The two models may end the game at different moves: keep what both played.
            shared = min(len(moves), len(same_moves))
            assert hands == same_hands and moves[:shared] == same_moves[:shared], "The two runs diverged"
            games.append({
                "setup": {"players": players, "values": values, "copies": copies},
                "seed": seed,
                "hands": hands,
                "moves": moves[:shared],
                "filters": by_filters[:shared],
                "global": by_global[:shared],
            })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "source": "BombBuster/export_reference_games.py",
        "games": games,
    }, separators=(",", ":")), encoding="utf-8")
    print(f"{args.out}: {len(games)} games, {sum(len(game['moves']) for game in games)} moves")


if __name__ == "__main__":
    main()
