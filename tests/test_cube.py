import random

import kociemba

from rubik_tutor.cube import (MOVES, SOLVED, apply_move, apply_moves, diff_states, invert,
                  is_valid_counts, stages_done)

ALL = list(MOVES)
rng = random.Random(0)


def rand_scramble(n=20):
    seq, last = [], ""
    while len(seq) < n:
        m = rng.choice(ALL)
        if m[0] != last:
            seq.append(m)
            last = m[0]
    return seq


def test_basic_orders():
    for f in "URFDLB":
        assert apply_moves(SOLVED, [f] * 4) == SOLVED
        assert apply_moves(SOLVED, [f + "2"] * 2) == SOLVED
        assert apply_move(apply_move(SOLVED, f), f + "'") == SOLVED
        assert apply_moves(SOLVED, [f, f]) == apply_move(SOLVED, f + "2")
    assert apply_moves(SOLVED, "R U R' U'".split() * 6) == SOLVED   # sexy move has order 6


def test_u_move_direction():
    # U clockwise: front top row goes to the left face
    s = apply_move(SOLVED, "U")
    assert s[36:39] == "FFF" and s[45:48] == "LLL" and s[9:12] == "BBB" and s[18:21] == "RRR"


def test_scramble_then_inverse():
    for _ in range(200):
        sc = rand_scramble()
        assert apply_moves(apply_moves(SOLVED, sc), invert(sc)) == SOLVED


def test_counts_valid():
    for _ in range(100):
        assert is_valid_counts(apply_moves(SOLVED, rand_scramble()))


def test_against_kociemba():
    """Independent check: an external solver must solve states produced by my simulator,
    and applying its solution with my simulator must return to SOLVED."""
    for _ in range(300):
        st = apply_moves(SOLVED, rand_scramble())
        sol = kociemba.solve(st).split()
        assert apply_moves(st, sol) == SOLVED


def test_stages():
    assert set(stages_done(SOLVED)) == {"cross", "first_layer", "first_two_layers",
                                        "top_cross", "top_face", "solved"}
    # a single U turn leaves the D layer, E slice and the (uniform) U face intact,
    # but the cube as a whole is no longer solved
    d = stages_done(apply_move(SOLVED, "U"))
    assert "first_two_layers" in d and "top_face" in d and "solved" not in d
    # an R turn breaks the first layer and the top face
    d = stages_done(apply_move(SOLVED, "R"))
    assert "first_layer" not in d and "top_face" not in d
    # a D turn breaks the cross
    assert "cross" not in stages_done(apply_move(SOLVED, "D"))


def test_diff_states():
    for _ in range(200):
        st = apply_moves(SOLVED, rand_scramble())
        m = rng.choice(ALL)
        assert diff_states(st, apply_move(st, m)) == [m]
    assert diff_states(SOLVED, SOLVED) == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
