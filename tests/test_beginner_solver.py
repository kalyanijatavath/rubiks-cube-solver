import json
import random
from pathlib import Path

import pytest

from rubik_tutor import beginner_solver as bs
from rubik_tutor.cube import MOVES, SOLVED, apply_moves, stages_done

ALL = list(MOVES)
DATA = Path(__file__).resolve().parent.parent / "data"


def scramble(rng, n=25):
    seq, last = [], ""
    while len(seq) < n:
        m = rng.choice(ALL)
        if m[0] != last:
            seq.append(m)
            last = m[0]
    return seq


def replay(state, steps):
    for s in steps:
        state = apply_moves(state, s["moves"])
    return state


def test_solves_random_scrambles():
    rng = random.Random(1)
    for _ in range(150):
        st = apply_moves(SOLVED, scramble(rng))
        steps = bs.beginner_solve(st)
        assert replay(st, steps) == SOLVED


def test_stage_labels_are_monotonic_and_truthful():
    rng = random.Random(2)
    st = apply_moves(SOLVED, scramble(rng))
    steps = bs.beginner_solve(st)
    assert [s["stage"] for s in steps] == sorted(s["stage"] for s in steps)
    s, checks = st, {1: "cross", 2: "first_layer", 3: "first_two_layers", 4: "top_cross", 5: "top_face", 7: "solved"}
    last_of = {}
    for i, step in enumerate(steps):
        last_of[step["stage"]] = i
    for i, step in enumerate(steps):
        s = apply_moves(s, step["moves"])
        if last_of[step["stage"]] == i and step["stage"] in checks:
            assert checks[step["stage"]] in stages_done(s)


def test_handles_solved_and_partial_states():
    assert bs.beginner_solve(SOLVED) == []
    rows = [json.loads(l) for l in (DATA / "stage_states.jsonl").read_text().splitlines()[:150]]
    for r in rows:
        steps = bs.beginner_solve(r["facelets"])
        assert replay(r["facelets"], steps) == SOLVED
        if "first_layer" in r["stages_done"]:
            assert all(s["stage"] >= 3 for s in steps)          # never redoes a finished layer


def test_replans_from_mistake_states():
    rows = [json.loads(l) for l in (DATA / "mistake_cases.jsonl").read_text().splitlines()[:100]]
    for r in rows:
        assert replay(r["state_after"], bs.beginner_solve(r["state_after"])) == SOLVED


def test_rejects_invalid_cubes():
    bad_counts = SOLVED[:1] + "R" + SOLVED[2:]
    with pytest.raises(bs.InvalidCube):
        bs.validate(bad_counts)
    s = list(SOLVED)
    s[8], s[9], s[20] = s[9], s[20], s[8]                 # twisted corner: right counts, impossible cube
    with pytest.raises(bs.InvalidCube):
        bs.validate("".join(s))
    with pytest.raises(bs.InvalidCube):
        bs.validate("not a cube")


def test_move_budget():
    rng = random.Random(3)
    totals = [bs.total_moves(bs.beginner_solve(apply_moves(SOLVED, scramble(rng)))) for _ in range(60)]
    assert max(totals) < 260 and sum(totals) / len(totals) < 180
