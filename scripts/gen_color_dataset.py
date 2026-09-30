"""SYNTHETIC sticker colour samples for prototyping the scanner's classifier.

This is NOT a substitute for real webcam photos: it only models global lighting gain,
colour cast, per-sticker noise and glare on top of nominal sticker colours. Use it to
develop and unit-test the classification logic; collect real photos for the final numbers.

Each 'scan' is a full cube (54 mean-RGB patches) from a random scramble, so label
counts are always valid (9 per colour).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import csv
import json
import random

import numpy as np
from scipy.optimize import linear_sum_assignment

from rubik_tutor.cube import FACES, SOLVED, MOVES, apply_moves

rng = random.Random(7)
nrng = np.random.default_rng(7)

# Nominal sticker colours (RGB), keyed by the FACE LETTER whose centre carries that colour.
NOMINAL = {
    "U": (235, 235, 235),   # white
    "R": (190, 30, 40),     # red
    "F": (25, 150, 65),     # green
    "D": (240, 215, 40),    # yellow
    "L": (235, 110, 25),    # orange
    "B": (25, 70, 190),     # blue
}
CENTERS = [4, 13, 22, 31, 40, 49]
N_SCANS = 400
GLARE_RATE = 0.04


def rgb_to_lab(rgb):
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def rand_state():
    seq, last = [], ""
    while len(seq) < 20:
        m = rng.choice(list(MOVES))
        if m[0] != last:
            seq.append(m)
            last = m[0]
    return apply_moves(SOLVED, seq)


def make_scan(state):
    gain = rng.uniform(0.5, 1.3)                                   # dim room ... bright window
    cast = np.array([rng.uniform(0.85, 1.15) for _ in range(3)])   # warm/cool white balance
    rows = []
    for i, lab in enumerate(state):
        rgb = np.array(NOMINAL[lab], dtype=float) * gain * cast + nrng.normal(0, 8, 3)
        glare = rng.random() < GLARE_RATE and i not in CENTERS
        if glare:
            rgb = rgb + 70
        rows.append((i, lab, np.clip(rgb, 0, 255), glare, gain))
    return rows


# ------------------------------------------------------------------ classifiers
def clf_fixed(patch_lab, _centers):
    """Baseline: nearest NOMINAL colour (fixed references, no adaptation)."""
    ref = {k: rgb_to_lab(v) for k, v in NOMINAL.items()}
    return [min(ref, key=lambda k: np.linalg.norm(p - ref[k])) for p in patch_lab]


def clf_centers(patch_lab, centers_lab):
    """Nearest of the six centre stickers of THIS scan (centres never move)."""
    keys = list(centers_lab)
    return [min(keys, key=lambda k: np.linalg.norm(p - centers_lab[k])) for p in patch_lab]


def clf_centers_balanced(patch_lab, centers_lab):
    """Centre references + hard constraint 'each colour appears exactly 9 times' (8 non-centre
    stickers per colour), solved as an assignment problem."""
    keys = list(centers_lab)
    non_center = [i for i in range(54) if i not in CENTERS]
    cost = np.array([[np.linalg.norm(patch_lab[i] - centers_lab[k]) for k in keys for _ in range(8)]
                     for i in non_center])
    r, c = linear_sum_assignment(cost)
    out = {}
    for ri, ci in zip(r, c):
        out[non_center[ri]] = keys[ci // 8]
    return [out.get(i, None) for i in range(54)]


def main():
    scans, rows_out = [], []
    for sid in range(N_SCANS):
        st = rand_state()
        scan = make_scan(st)
        scans.append((sid, st, scan))
        for i, lab, rgb, glare, gain in scan:
            rows_out.append([sid, i, lab, int(round(rgb[0])), int(round(rgb[1])), int(round(rgb[2])),
                             int(glare), round(gain, 3)])
    with open("data/color_samples_synthetic.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scan_id", "facelet_idx", "true_label", "R", "G", "B", "glare", "lighting_gain"])
        w.writerows(rows_out)

    res = {name: {"all": [0, 0], "dim(<0.7)": [0, 0], "mid": [0, 0], "bright(>1.1)": [0, 0],
                  "no_glare": [0, 0], "glare": [0, 0]} for name in ("fixed_nominal", "centre_reference",
                                                                   "centre_reference+count_constraint")}
    for sid, st, scan in scans:
        patch_lab = np.array([rgb_to_lab(r[2]) for r in scan])
        centers_lab = {st[i]: patch_lab[i] for i in CENTERS}
        preds = {
            "fixed_nominal": clf_fixed(patch_lab, centers_lab),
            "centre_reference": clf_centers(patch_lab, centers_lab),
            "centre_reference+count_constraint": clf_centers_balanced(patch_lab, centers_lab),
        }
        gain = scan[0][4]
        bucket = "dim(<0.7)" if gain < 0.7 else ("bright(>1.1)" if gain > 1.1 else "mid")
        for name, pred in preds.items():
            for i, lab, _, glare, _ in scan:
                if i in CENTERS:
                    continue                                   # centres are the references
                ok = int(pred[i] == lab)
                for key in ("all", bucket, "glare" if glare else "no_glare"):
                    res[name][key][0] += ok
                    res[name][key][1] += 1
    summary = {n: {k: round(100 * v[0] / v[1], 2) for k, v in d.items() if v[1]} for n, d in res.items()}
    summary["_n_scans"] = N_SCANS
    summary["_note"] = "synthetic data; accuracy on the 48 non-centre stickers per scan"
    json.dump(summary, open("data/color_baseline_results.json", "w"), indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
