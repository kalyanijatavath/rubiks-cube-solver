import random

import numpy as np
import pytest

from rubik_tutor.cube import MOVES, SOLVED, apply_moves
from rubik_tutor.rag import evaluate, get_index
from rubik_tutor.scan import ScanError, classify_patches
from rubik_tutor.tutor import Tutor, diagnose, guard, moves_in_text

NOMINAL = {"U": (240, 215, 40), "R": (235, 110, 25), "F": (25, 150, 65),
           "D": (235, 235, 235), "L": (190, 30, 40), "B": (25, 70, 190)}


def fake_scan(rng, nrng, state):
    gain = rng.uniform(0.6, 1.25)
    cast = np.array([rng.uniform(0.9, 1.1) for _ in range(3)])
    return [np.clip(np.array(NOMINAL[c]) * gain * cast + nrng.normal(0, 6, 3), 0, 255) for c in state]


def test_scan_reads_synthetic_cubes():
    rng, nrng = random.Random(4), np.random.default_rng(4)
    exact = 0
    for _ in range(100):
        seq, last = [], ""
        while len(seq) < 20:
            m = rng.choice(list(MOVES))
            if m[0] != last:
                seq.append(m)
                last = m[0]
        st = apply_moves(SOLVED, seq)
        out = classify_patches(fake_scan(rng, nrng, st))
        exact += out["facelets"] == st
        assert all(out["facelets"].count(c) == 9 for c in "URFDLB")
    assert exact >= 95


def test_scan_rejects_bad_input():
    with pytest.raises(ScanError):
        classify_patches([[0, 0, 0]] * 10)
    with pytest.raises(ScanError):
        classify_patches([[10, 10, 10]] * 54)              # all centres identical


def test_retrieval_quality():
    r = evaluate()
    assert r["hit@1"] >= 0.8 and r["hit@3"] >= 0.88
    assert get_index().search("what does the prime mark mean", 1)[0]["id"] == "n01_notation"


STEP = {"kind": "sune_run", "moves": ["U", "R", "U'", "R'", "U", "R", "U2", "R'"],
        "stage_title": "Orient the top corners", "algorithm": "R U R' U R U2 R'",
        "yellow_corners_before": 1}


def test_guard_detects_foreign_moves():
    assert moves_in_text("do R then U' and finally R2") == {"R", "U'", "R2"}
    assert guard("Run R U R'", {"R", "U", "R'"})
    assert not guard("Run R U F", {"R", "U", "R'"})
    assert moves_in_text("I will B careful") == {"B"}      # known limitation, documented


def test_llm_output_is_used_only_if_faithful():
    good = Tutor(lambda system, user: "Turn U, then R, then U' and R'. This twists corners toward yellow.")
    assert good.explain(STEP)["source"] == "llm"
    bad = Tutor(lambda system, user: "Do F2 then D' to fix it.")
    r = bad.explain(STEP)
    assert r["source"].startswith("template") and "F2" not in r["text"]
    boom = Tutor(lambda system, user: (_ for _ in ()).throw(RuntimeError("api down")))
    assert boom.explain(STEP)["source"] == "template"
    assert Tutor(None).explain(STEP)["source"] == "template"


def test_ask_without_llm_returns_notes():
    r = Tutor(None).ask("What does a solved cube look like?")
    assert r["source"] == "notes" and "n16_solved" in r["notes"]


def test_diagnose():
    before = apply_moves(SOLVED, "R U F".split())
    assert diagnose(before, apply_moves(before, ["R"]), "R")["status"] == "match"
    d = diagnose(before, apply_moves(before, ["R'"]), "R")
    assert d["status"] == "different_move" and d["moves_made"] == ["R'"] and d["undo_with"] == ["R"]
    assert diagnose(before, before, "R")["status"] == "no_change"
    d = diagnose(before, apply_moves(before, "U R".split()))
    assert d["status"] == "different_move" and d["moves_made"] == ["U", "R"]
