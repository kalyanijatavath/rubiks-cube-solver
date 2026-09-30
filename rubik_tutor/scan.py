"""Turn 54 sampled sticker colours into a facelet string.

The client samples the mean RGB of each sticker (facelet order URFDLB, 9 per face). The six centre
stickers never move, so they are used as this scan's colour references. Non-centre stickers are
assigned to colours with the constraint that every colour appears exactly nine times
(an assignment problem), which fixes most glare / shadow misreads.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

CENTERS = {"U": 4, "R": 13, "F": 22, "D": 31, "L": 40, "B": 49}
LETTERS = "URFDLB"
MIN_CENTER_DISTANCE = 10.0        # CIELAB distance below which two centres are "the same colour"
LOW_CONFIDENCE_MARGIN = 6.0       # best-vs-second-best distance gap flagged as uncertain


class ScanError(ValueError):
    pass


def rgb_to_lab(rgb) -> np.ndarray:
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def classify_patches(patches):
    """patches: 54 [r, g, b] values. Returns dict(facelets, palette, low_confidence)."""
    arr = np.asarray(patches, dtype=float)
    if arr.shape != (54, 3) or not np.isfinite(arr).all() or arr.min() < 0 or arr.max() > 255:
        raise ScanError("Expected 54 RGB triples with values between 0 and 255.")
    lab = rgb_to_lab(arr)
    ref = np.stack([lab[CENTERS[k]] for k in LETTERS])          # 6 x 3
    for i in range(6):
        for j in range(i + 1, 6):
            if np.linalg.norm(ref[i] - ref[j]) < MIN_CENTER_DISTANCE:
                raise ScanError(f"The {LETTERS[i]} and {LETTERS[j]} centre colours look the same. "
                                "Rescan in even light without glare.")
    others = [i for i in range(54) if i not in CENTERS.values()]
    dist = np.linalg.norm(lab[others][:, None, :] - ref[None, :, :], axis=-1)      # 48 x 6
    cost = np.repeat(dist, 8, axis=1)                                             # 8 slots per colour
    rows, cols = linear_sum_assignment(cost)
    out = [None] * 54
    for letter, idx in CENTERS.items():
        out[idx] = letter
    for r, c in zip(rows, cols):
        out[others[r]] = LETTERS[c // 8]
    low = []
    for n, i in enumerate(others):
        d = np.sort(dist[n])
        assigned = LETTERS.index(out[i])
        if dist[n][assigned] - d[0] > 1e-9 or d[1] - d[0] < LOW_CONFIDENCE_MARGIN:
            low.append(i)                                     # constraint overrode it, or a near tie
    palette = {k: [int(round(v)) for v in arr[CENTERS[k]]] for k in LETTERS}
    return {"facelets": "".join(out), "palette": palette, "low_confidence": low}
