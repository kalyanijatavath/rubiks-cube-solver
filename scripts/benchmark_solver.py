"""Benchmark the beginner solver on random scrambles -> data/beginner_solver_benchmark.json."""
import json
import os
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rubik_tutor import beginner_solver as bs  # noqa: E402
from rubik_tutor.cube import MOVES, SOLVED, apply_moves  # noqa: E402

N = 500
rng = random.Random(2027)
bs.cross_table()                                     # exclude one-off table build from timings
totals, times = [], []
per_stage = {k: [] for k in bs.STAGES}
for _ in range(N):
    seq, last = [], ""
    while len(seq) < 25:
        m = rng.choice(list(MOVES))
        if m[0] != last:
            seq.append(m)
            last = m[0]
    st = apply_moves(SOLVED, seq)
    t = time.time()
    steps = bs.beginner_solve(st)
    times.append(time.time() - t)
    s = st
    for g in steps:
        s = apply_moves(s, g["moves"])
    assert s == SOLVED
    totals.append(bs.total_moves(steps))
    for k in per_stage:
        per_stage[k].append(sum(len(g["moves"]) for g in steps if g["stage"] == k))
res = {
    "scrambles": N, "all_solved": True,
    "moves_mean": round(statistics.mean(totals), 1), "moves_min": min(totals), "moves_max": max(totals),
    "moves_per_stage_mean": {f"{k}: {bs.STAGES[k][1]}": round(statistics.mean(v), 1) for k, v in per_stage.items()},
    "solve_seconds_mean": round(statistics.mean(times), 3), "solve_seconds_max": round(max(times), 3),
}
json.dump(res, open("data/beginner_solver_benchmark.json", "w"), indent=2)
print(json.dumps(res, indent=2))
