"""Generates the state-based datasets. Every record is verified with the simulator
before it is written; the script aborts on any inconsistency."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os
import random
import time

import kociemba

from rubik_tutor.cube import (MOVES, SOLVED, apply_move, apply_moves, diff_states, invert,
                  is_valid_counts, stages_done)

OUT = "data"
os.makedirs(OUT, exist_ok=True)
rng = random.Random(2027)
ALL = list(MOVES)

N_SCRAMBLES, N_MISTAKES, N_STAGE_EACH = 2000, 500, 200


def rand_scramble(n=20):
    seq, last = [], ""
    while len(seq) < n:
        m = rng.choice(ALL)
        if m[0] != last:
            seq.append(m)
            last = m[0]
    return seq


# Algorithms verified to preserve the first layer / first two layers (see test_algorithms.py)
F2L_PRESERVING = ["F R U R' U' F'", "R U R' U R U2 R'", "U R U' L' U R' U' L",
                  "R U' R U R U R U' R' U' R2"]
FIRST_LAYER_PRESERVING = F2L_PRESERVING + ["U R U' R' U' F' U F", "U' L' U L U F U' F'"]


def main():
    t0 = time.time()

    # ---------------------------------------------------------------- scrambles.jsonl
    scrambles = []
    for i in range(N_SCRAMBLES):
        sc = rand_scramble(rng.randint(10, 25))
        st = apply_moves(SOLVED, sc)
        sol = kociemba.solve(st).split()
        assert apply_moves(st, sol) == SOLVED, "solution failed simulator check"
        scrambles.append({
            "id": f"scr_{i:05d}",
            "scramble": " ".join(sc),
            "facelets": st,
            "solution": " ".join(sol),
            "solution_len": len(sol),
            "stages_done_at_start": stages_done(st),
        })
    with open(f"{OUT}/scrambles.jsonl", "w") as f:
        for r in scrambles:
            f.write(json.dumps(r) + "\n")
    print(f"scrambles: {len(scrambles)}  ({time.time() - t0:.0f}s)")

    # ---------------------------------------------------------------- mistake_cases.jsonl
    def wrong_move(expected):
        face, mod = expected[0], expected[1:]
        kind = rng.choices(["wrong_direction", "wrong_amount", "wrong_face"], [0.4, 0.2, 0.4])[0]
        if kind == "wrong_direction":
            if mod == "2":            # a half-turn has no direction; fall back to wrong amount
                kind = "wrong_amount"
            else:
                return kind, face + ("'" if mod == "" else "")
        if kind == "wrong_amount":
            opts = [face, face + "'", face + "2"]
            opts.remove(expected)
            if mod == "2":
                return kind, rng.choice([face, face + "'"])
            return kind, face + "2"
        other = rng.choice([c for c in "URFDLB" if c != face])
        return "wrong_face", other + rng.choice(["", "'", "2"])

    mistakes = []
    for i in range(N_MISTAKES):
        rec = scrambles[rng.randrange(len(scrambles))]
        sol = rec["solution"].split()
        k = rng.randrange(len(sol))
        before = apply_moves(rec["facelets"], sol[:k])
        expected = sol[k]
        kind, actual = wrong_move(expected)
        assert actual != expected
        after = apply_move(before, actual)
        assert diff_states(before, after) == [actual]      # diff tool must recover it
        recovery = invert([actual])                        # undoing the mistake
        assert apply_moves(after, recovery) == before
        replan = kociemba.solve(after).split()
        assert apply_moves(after, replan) == SOLVED
        mistakes.append({
            "id": f"mis_{i:04d}",
            "source_scramble": rec["id"],
            "step_index": k,
            "state_before": before,
            "expected_move": expected,
            "actual_move": actual,
            "error_type": kind,
            "state_after": after,
            "recovery_moves": recovery,
            "replan_solution_len": len(replan),
        })
    with open(f"{OUT}/mistake_cases.jsonl", "w") as f:
        for r in mistakes:
            f.write(json.dumps(r) + "\n")
    print(f"mistake cases: {len(mistakes)}")

    # ---------------------------------------------------------------- stage_states.jsonl
    stage_rows = []

    def add(kind, state, must_have):
        d = stages_done(state)
        for s in must_have:
            assert s in d, (kind, s, d)
        stage_rows.append({"id": f"stg_{len(stage_rows):04d}", "kind": kind,
                           "facelets": state, "stages_done": d})

    for _ in range(N_STAGE_EACH):                       # nothing guaranteed
        add("random", apply_moves(SOLVED, rand_scramble()), [])
    for _ in range(N_STAGE_EACH):                       # first layer guaranteed
        seq = []
        for _ in range(rng.randint(3, 8)):
            seq += rng.choice(FIRST_LAYER_PRESERVING + ["U", "U'", "U2"]).split()
        add("first_layer_built", apply_moves(SOLVED, seq), ["cross", "first_layer"])
    for _ in range(N_STAGE_EACH):                       # first two layers guaranteed
        seq = []
        for _ in range(rng.randint(3, 8)):
            seq += rng.choice(F2L_PRESERVING + ["U", "U'", "U2"]).split()
        add("first_two_layers_built", apply_moves(SOLVED, seq),
            ["cross", "first_layer", "first_two_layers"])
    assert all(is_valid_counts(r["facelets"]) for r in stage_rows)
    with open(f"{OUT}/stage_states.jsonl", "w") as f:
        for r in stage_rows:
            f.write(json.dumps(r) + "\n")
    print(f"stage states: {len(stage_rows)}")

    # ---------------------------------------------------------------- stats for README
    lens = [r["solution_len"] for r in scrambles]
    stats = {
        "scrambles": len(scrambles),
        "solution_len_min": min(lens), "solution_len_max": max(lens),
        "solution_len_mean": round(sum(lens) / len(lens), 2),
        "mistakes": len(mistakes),
        "mistake_types": {t: sum(1 for m in mistakes if m["error_type"] == t)
                          for t in ("wrong_direction", "wrong_amount", "wrong_face")},
        "stage_states": len(stage_rows),
    }
    json.dump(stats, open(f"{OUT}/stats_state_datasets.json", "w"), indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
