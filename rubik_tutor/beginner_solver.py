"""Beginner (layer-by-layer) solver that returns teachable, stage-labelled move groups.

Stage 1 (cross): optimal search over a precomputed table for the four cross edges.
Stage 2 (bottom corners) and 3 (middle edges): for each piece, pick the shortest combination of
  [lift] + [align with U] + [repeated trigger / edge algorithm] that places it and keeps everything
  already built intact. Every candidate is verified in the simulator; nothing is assumed.
Stages 4-7: verified last-layer procedures (see last_layer.py).

The full result is re-applied in the simulator and must end SOLVED, otherwise an error is raised.
"""
from __future__ import annotations

import os
import pickle
from collections import deque
from functools import lru_cache

import kociemba

from .cube import GEO, MOVES, SOLVED, STAGE_SETS, apply_moves, is_valid_counts
from .last_layer import (orient_corners, position_corners, position_edges, rot_alg,
                         top_cross)

STAGES = {
    1: ("cross", "Build the bottom cross"),
    2: ("first_layer", "Place the bottom corners"),
    3: ("first_two_layers", "Place the middle-layer edges"),
    4: ("top_cross", "Make the top cross"),
    5: ("top_face", "Orient the top corners"),
    6: ("corners_placed", "Position the top corners"),
    7: ("solved", "Position the top edges"),
}

TRIGGER = "R U R' U'"
RIGHT_INSERT = "U R U' R' U' F' U F"
LEFT_INSERT = "U' L' U L U F U' F'"


class InvalidCube(ValueError):
    pass


def validate(state: str) -> None:
    """Raise InvalidCube unless `state` is a legal, solvable cube."""
    if len(state) != 54 or set(state) - set("URFDLB") or not is_valid_counts(state):
        raise InvalidCube("Each of the six colours must appear exactly nine times.")
    try:
        kociemba.solve(state)
    except ValueError:
        raise InvalidCube("This layout cannot occur on a real cube (a piece is impossible, "
                          "flipped/twisted, or two pieces are swapped). Rescan or fix a sticker.")


# ------------------------------------------------------------------ geometry helpers
def _cubies():
    by_pos = {}
    for i, (pos, _n) in enumerate(GEO):
        by_pos.setdefault(pos, []).append(i)
    return by_pos


_BY_POS = _cubies()
_EDGE_SLOTS = [tuple(v) for p, v in _BY_POS.items() if sum(1 for c in p if c) == 2]
_CORNER_SLOTS = [tuple(v) for p, v in _BY_POS.items() if sum(1 for c in p if c) == 3]


def _home(colors, slots):
    """Solved indices (ordered as `colors`) of the cubie whose solved letters are `colors`."""
    for slot in slots:
        letters = [SOLVED[i] for i in slot]
        if set(letters) == set(colors):
            return tuple(slot[letters.index(c)] for c in colors)
    raise KeyError(colors)


# ------------------------------------------------------------------ stage 1: cross
_CROSS_EDGES = [("D", "F"), ("D", "R"), ("D", "B"), ("D", "L")]
_CROSS_GOAL = tuple(i for pair in _CROSS_EDGES for i in _home(pair, _EDGE_SLOTS))
_DEST = {m: [0] * 54 for m in MOVES}
for _m, _perm in MOVES.items():
    for _d, _src in enumerate(_perm):
        _DEST[_m][_src] = _d


def _locate_cross(s):
    out = []
    for c1, c2 in _CROSS_EDGES:
        for a, b in _EDGE_SLOTS:
            if (s[a], s[b]) == (c1, c2):
                out += [a, b]
                break
            if (s[b], s[a]) == (c1, c2):
                out += [b, a]
                break
    return tuple(out)


_CACHE = os.environ.get("RUBIK_CACHE_DIR", os.path.join(os.path.expanduser("~"), ".cache"))
_CROSS_FILE = os.path.join(_CACHE, "rubik_tutor_cross_v1.pkl")


@lru_cache(maxsize=1)
def cross_table():
    """Distance-to-solved for every arrangement of the four cross edges (190,080 states)."""
    try:
        with open(_CROSS_FILE, "rb") as f:
            return pickle.load(f)
    except Exception:
        pass
    dist = {_CROSS_GOAL: 0}
    frontier = deque([_CROSS_GOAL])
    while frontier:
        st = frontier.popleft()
        d = dist[st] + 1
        for m in MOVES:
            dest = _DEST[m]
            nxt = tuple(dest[p] for p in st)
            if nxt not in dist:
                dist[nxt] = d
                frontier.append(nxt)
    try:
        os.makedirs(_CACHE, exist_ok=True)
        with open(_CROSS_FILE, "wb") as f:
            pickle.dump(dist, f, protocol=pickle.HIGHEST_PROTOCOL)
    except OSError:
        pass
    return dist


def solve_cross(s):
    table = cross_table()
    st = _locate_cross(s)
    d = table[st]
    moves = []
    while d > 0:
        for m in MOVES:
            nxt = tuple(_DEST[m][p] for p in st)
            if table.get(nxt, 10 ** 6) == d - 1:
                moves.append(m)
                st, d = nxt, d - 1
                break
    return moves


# ------------------------------------------------------------------ stages 2 and 3
_U_TURNS = ([], ["U"], ["U2"], ["U'"])
_CORNER_TARGETS = [("D", "F", "R"), ("D", "R", "B"), ("D", "B", "L"), ("D", "L", "F")]
_EDGE_TARGETS = [("F", "R"), ("R", "B"), ("B", "L"), ("L", "F")]


def _ok(s, idxs):
    return all(s[i] == SOLVED[i] for i in idxs)


def _search(s, candidates, keep, target):
    """Shortest candidate (by move count) after which `keep` and `target` stickers are solved."""
    for c in sorted(candidates, key=lambda c: len(c["moves"])):
        t = apply_moves(s, c["moves"])
        if _ok(t, keep) and _ok(t, target):
            return t, c
    raise RuntimeError("no macro found (state should have been rejected by validate())")


def place_corners(s):
    groups, placed = [], []
    keep_base = list(STAGE_SETS["cross"])
    for colors in _CORNER_TARGETS:
        target = _home(colors, _CORNER_SLOTS)
        if _ok(s, target):
            placed += target
            continue
        cands = []
        for lift in (None, 0, 1, 2, 3):
            for u in _U_TURNS:
                for k in range(4):
                    for r in range(1, 6):
                        pre = rot_alg(TRIGGER, lift) if lift is not None else []
                        mv = pre + u + rot_alg(TRIGGER, k) * r
                        cands.append({"moves": mv, "lift": lift is not None, "u": u, "reps": r})
        s, c = _search(s, cands, keep_base + placed, target)
        placed += target
        groups.append({"kind": "corner_insert", "moves": c["moves"], "corner": "".join(colors),
                       "lifted_first": c["lift"], "trigger_repeats": c["reps"],
                       "algorithm": TRIGGER})
    return s, groups


def place_edges(s):
    groups, placed = [], []
    keep_base = list(STAGE_SETS["first_layer"])
    for colors in _EDGE_TARGETS:
        target = _home(colors, _EDGE_SLOTS)
        if _ok(s, target):
            placed += target
            continue
        cands = []
        for pop in (None, 0, 1, 2, 3):
            for u in _U_TURNS:
                for k in range(4):
                    for side, alg in (("right", RIGHT_INSERT), ("left", LEFT_INSERT)):
                        pre = rot_alg(RIGHT_INSERT, pop) if pop is not None else []
                        cands.append({"moves": pre + u + rot_alg(alg, k), "popped": pop is not None,
                                      "side": side})
        s, c = _search(s, cands, keep_base + placed, target)
        placed += target
        groups.append({"kind": "edge_insert", "moves": c["moves"], "edge": "".join(colors),
                       "popped_first": c["popped"], "direction": c["side"]})
    return s, groups


# ------------------------------------------------------------------ public API
def beginner_solve(state: str):
    """Return a list of step dicts: {stage, stage_key, stage_title, kind, moves, ...}.
    Raises InvalidCube for illegal states."""
    validate(state)
    steps, s = [], state

    def add(stage, groups):
        key, title = STAGES[stage]
        for g in groups:
            g = dict(g)
            g.update(stage=stage, stage_key=key, stage_title=title)
            steps.append(g)

    cross = solve_cross(s)
    if cross:
        s = apply_moves(s, cross)
        add(1, [{"kind": "cross", "moves": cross}])
    s, g = place_corners(s)
    add(2, g)
    s, g = place_edges(s)
    add(3, g)
    s, g = top_cross(s)
    add(4, g)
    s, g = orient_corners(s)
    add(5, g)
    s, g = position_corners(s)
    add(6, g)
    s, g = position_edges(s)
    add(7, g)
    if s != SOLVED:
        raise RuntimeError("internal error: beginner solution did not solve the cube")
    return steps


def total_moves(steps):
    return sum(len(x["moves"]) for x in steps)
