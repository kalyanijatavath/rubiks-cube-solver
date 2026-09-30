"""Rubik's Cube simulator on the 54-character facelet string (URFDLB order).

Facelet order matches the `kociemba` package: U0-8, R9-17, F18-26, D27-35, L36-44, B45-53.
Moves are derived from 3D sticker geometry (not hand-typed permutation tables), so the
tables cannot contain a typo. test_cube.py cross-checks them against the Kociemba solver.

Coordinates: x = right(R+), y = up(U+), z = front(F+).
"""
from __future__ import annotations

import numpy as np

SOLVED = "U" * 9 + "R" * 9 + "F" * 9 + "D" * 9 + "L" * 9 + "B" * 9
FACES = "URFDLB"
NORMALS = {
    "U": (0, 1, 0), "R": (1, 0, 0), "F": (0, 0, 1),
    "D": (0, -1, 0), "L": (-1, 0, 0), "B": (0, 0, -1),
}


def _facelet_geometry():
    """Return list of (position, normal) for each facelet index 0..53."""
    geo = []
    for f in FACES:
        for r in range(3):
            for c in range(3):
                if f == "U":
                    pos = (c - 1, 1, r - 1)
                elif f == "R":
                    pos = (1, 1 - r, 1 - c)
                elif f == "F":
                    pos = (c - 1, 1 - r, 1)
                elif f == "D":
                    pos = (c - 1, -1, 1 - r)
                elif f == "L":
                    pos = (-1, 1 - r, c - 1)
                else:  # B
                    pos = (1 - c, 1 - r, -1)
                geo.append((pos, NORMALS[f]))
    return geo


GEO = _facelet_geometry()
_INDEX = {(p, n): i for i, (p, n) in enumerate(GEO)}


def _rot(v, axis, quarter_turns):
    """Rotate integer vector v about a signed axis by clockwise quarter turns
    (clockwise as seen looking at the face from outside)."""
    ax = int(np.argmax(np.abs(axis)))
    sign = int(axis[ax])
    theta = -np.pi / 2 * quarter_turns * sign  # clockwise = negative right-hand rotation
    c, s = int(round(np.cos(theta))), int(round(np.sin(theta)))
    x, y, z = v
    if ax == 0:      # about x
        return (x, c * y - s * z, s * y + c * z)
    if ax == 1:      # about y
        return (c * x + s * z, y, -s * x + c * z)
    return (c * x - s * y, s * x + c * y, z)  # about z


def _build_move(face: str, turns: int):
    axis = NORMALS[face]
    ax = int(np.argmax(np.abs(axis)))
    sign = int(axis[ax])
    perm = list(range(54))  # perm[dest] = source
    for i, (pos, nrm) in enumerate(GEO):
        if pos[ax] * sign == 1:  # sticker in the turning layer
            new_pos, new_nrm = _rot(pos, axis, turns), _rot(nrm, axis, turns)
            perm[_INDEX[(new_pos, new_nrm)]] = i
    return perm


MOVES = {}
for _f in FACES:
    MOVES[_f] = _build_move(_f, 1)
    MOVES[_f + "2"] = _build_move(_f, 2)
    MOVES[_f + "'"] = _build_move(_f, 3)


def apply_move(state: str, move: str) -> str:
    p = MOVES[move]
    return "".join(state[p[i]] for i in range(54))


def apply_moves(state: str, moves) -> str:
    if isinstance(moves, str):
        moves = moves.split()
    for m in moves:
        state = apply_move(state, m)
    return state


def invert(moves) -> list[str]:
    if isinstance(moves, str):
        moves = moves.split()
    out = []
    for m in reversed(moves):
        out.append(m if m.endswith("2") else (m[0] if m.endswith("'") else m + "'"))
    return out


def is_valid_counts(state: str) -> bool:
    return len(state) == 54 and all(state.count(f) == 9 for f in FACES)


def diff_states(before: str, after: str, max_len: int = 2):
    """Find the shortest move sequence (<= max_len moves) turning `before` into `after`.
    Returns a list of moves, [] if identical, or None if not found."""
    if before == after:
        return []
    layer1 = list(MOVES)
    for m in layer1:
        if apply_move(before, m) == after:
            return [m]
    if max_len >= 2:
        for m in layer1:
            s = apply_move(before, m)
            for m2 in layer1:
                if apply_move(s, m2) == after:
                    return [m, m2]
    return None


# ---------------------------------------------------------------- stage detectors
# First layer = D layer, last layer = U layer (white on the bottom while teaching).
def _idx(pred):
    return [i for i, (p, n) in enumerate(GEO) if pred(p, n)]


def _nz(p):
    return sum(1 for v in p if v != 0)


STAGE_SETS = {
    # white cross: D-layer edge cubies (all their stickers) + D center
    "cross": _idx(lambda p, n: p[1] == -1 and _nz(p) <= 2),
    # first layer: whole D layer
    "first_layer": _idx(lambda p, n: p[1] == -1),
    # first two layers
    "first_two_layers": _idx(lambda p, n: p[1] <= 0 and not (p[1] == 0 and _nz(p) == 1)),
    # top cross: U face stickers of U edges + center
    "top_cross": _idx(lambda p, n: n == (0, 1, 0) and _nz(p) <= 2),
    # top face: whole U face
    "top_face": _idx(lambda p, n: n == (0, 1, 0)),
}
# first two layers must also include the centers; the mask above includes them
# (centers on y=0 have _nz == 1 and are excluded from the E-slice test only because
# centers never move, so they are trivially "solved").
STAGE_ORDER = ["cross", "first_layer", "first_two_layers", "top_cross", "top_face", "solved"]


def stages_done(state: str) -> list[str]:
    """Stages whose stickers are all in solved position (order-independent)."""
    done = []
    for name in STAGE_ORDER[:-1]:
        if all(state[i] == SOLVED[i] for i in STAGE_SETS[name]):
            done.append(name)
    if state == SOLVED:
        done.append("solved")
    return done
