"""Beginner-method stages 4-7 (top cross, orient corners, position corners, position edges).

Each function takes a state with the first two layers solved and returns
(new_state, groups) where groups is a list of dicts {"kind", "moves", ...}.
The recognition rules and algorithms are the ones verified in tests/test_algorithms.py.

Whole-cube turns ("hold the cube so X is at the front-left") are modelled by relabelling the
faces inside the algorithm (rot_alg): executing F on the re-held cube is the same as executing R
on the original, and so on.
"""
from __future__ import annotations

from .cube import SOLVED, apply_moves

TOP_CROSS = "F R U R' U' F'"
SUNE = "R U R' U R U2 R'"
CORNER_PERM = "R' F R' B2 R F' R' B2 R2"
EDGE_PERM = "R U' R U R U R U' R' U' R2"

_SUB = {"F": "R", "R": "B", "B": "L", "L": "F", "U": "U", "D": "D"}   # one turn of the whole cube about the vertical axis


def rot_alg(alg: str, k: int) -> list[str]:
    """The algorithm as executed after holding the cube k quarter-turns differently."""
    out = []
    for m in alg.split():
        f, rest = m[0], m[1:]
        for _ in range(k):
            f = _SUB[f]
        out.append(f + rest)
    return out


U_TURNS = ([], ["U"], ["U2"], ["U'"])


def _edges_up(s):
    return {"back": s[1] == "U", "left": s[3] == "U", "right": s[5] == "U", "front": s[7] == "U"}


def _top_pattern(s):
    e = _edges_up(s)
    n = sum(e.values())
    if n == 0:
        return "dot"
    if n == 4:
        return "cross"
    return "line" if (e["left"] and e["right"]) or (e["back"] and e["front"]) else "L-shape"


def _corners_up(s):
    return sum(s[i] == "U" for i in (0, 2, 6, 8))


# ------------------------------------------------------------------ stage 4
def top_cross(s):
    groups = []
    want = [{"back": False, "left": True, "right": True, "front": False},     # horizontal line
            {"back": True, "left": True, "right": False, "front": False}]     # L at back-left
    while not all(_edges_up(s).values()):
        pattern = _top_pattern(s)
        turn = []
        for tr in U_TURNS:
            if _edges_up(apply_moves(s, tr)) in want:
                turn = tr
                break
        moves = list(turn) + TOP_CROSS.split()
        s = apply_moves(s, moves)
        groups.append({"kind": "top_cross_run", "moves": moves,
                       "pattern": pattern,
                       "algorithm": TOP_CROSS})
        if len(groups) > 3:
            raise RuntimeError("top cross did not converge")
    return s, groups


# ------------------------------------------------------------------ stage 5
_ORIENT_CONDS = {1: lambda t: t[6] == "U",                           # yellow corner at front-left
                 0: lambda t: t[38] == "U",                          # front-left corner's yellow faces left
                 2: lambda t: t[6] != "U" and t[18] == "U"}          # ...not on top, yellow faces front


def orient_corners(s):
    groups = []
    while _corners_up(s) != 4:
        c = _corners_up(s)
        for tr in U_TURNS:
            t = apply_moves(s, tr)
            if _ORIENT_CONDS[c](t):
                turn = tr
                break
        else:
            raise RuntimeError("no alignment for Sune")
        moves = list(turn) + SUNE.split()
        s = apply_moves(s, moves)
        groups.append({"kind": "sune_run", "moves": moves, "yellow_corners_before": c,
                       "algorithm": SUNE})
        if len(groups) > 3:
            raise RuntimeError("corner orientation did not converge")
    return s, groups


# ------------------------------------------------------------------ stages 6 and 7
_CORNERS = {8: (8, 20, 9), 2: (2, 45, 11), 0: (0, 36, 47), 6: (6, 18, 38)}
_CORNER_SIDES = {8: (20, 9), 2: (45, 11), 0: (36, 47), 6: (18, 38)}
_EDGES = {1: (1, 46), 3: (3, 37), 7: (7, 19), 5: (5, 10)}
_CORNER_AT_FRONT_LEFT = [6, 8, 2, 0]      # old-frame corner that sits front-left after k whole-cube turns
_EDGE_AT_BACK = [1, 3, 7, 5]


def _ok(s, idxs):
    return all(s[i] == SOLVED[i] for i in idxs)


def _good_corners(s):
    return [c for c, v in _CORNERS.items() if _ok(s, v)]


def _good_edges(s):
    return [e for e, v in _EDGES.items() if _ok(s, v)]


def _corner_parity_even(s):
    """Parity of the corner permutation (orientation assumed solved). The 3-cycle algorithm
    can only fix 'even' layouts; a U turn flips parity, so we choose the alignment."""
    home = {frozenset(SOLVED[i] for i in v): p for p, v in _CORNER_SIDES.items()}
    pos = list(_CORNER_SIDES)
    perm = [pos.index(home[frozenset(s[i] for i in _CORNER_SIDES[p])]) for p in pos]
    inv = sum(1 for i in range(4) for j in range(i + 1, 4) if perm[i] > perm[j])
    return inv % 2 == 0


def position_corners(s):
    groups = []
    for _ in range(6):
        best = None
        for tr in U_TURNS:
            t = apply_moves(s, tr)
            if not _corner_parity_even(t):
                continue
            g = _good_corners(t)
            if best is None or len(g) > len(best[1]):
                best = (tr, t, g)
        turn, t, g = best
        if len(g) == 4:
            if turn:
                groups.append({"kind": "align_top", "moves": list(turn)})
            return t, groups
        if g:
            k = _CORNER_AT_FRONT_LEFT.index(g[0])
            moves = list(turn) + rot_alg(CORNER_PERM, k)
            s = apply_moves(s, moves)
            groups.append({"kind": "corner_cycle", "moves": moves, "correct_corners": 1,
                           "algorithm": CORNER_PERM, "whole_cube_turns": k})
        else:
            moves = rot_alg(CORNER_PERM, 0)
            s = apply_moves(s, moves)
            groups.append({"kind": "corner_cycle", "moves": moves, "correct_corners": 0,
                           "algorithm": CORNER_PERM, "whole_cube_turns": 0})
    raise RuntimeError("corner positioning did not converge")


def position_edges(s):
    groups = []
    for _ in range(6):
        g = _good_edges(s)
        if len(g) == 4:
            return s, groups
        if len(g) == 1:
            k = _EDGE_AT_BACK.index(g[0])
        else:
            k = 0
        moves = rot_alg(EDGE_PERM, k)
        s = apply_moves(s, moves)
        groups.append({"kind": "edge_cycle", "moves": moves, "correct_edges": len(g),
                       "algorithm": EDGE_PERM, "whole_cube_turns": k})
    raise RuntimeError("edge positioning did not converge")
