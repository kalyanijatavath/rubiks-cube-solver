import random

import pytest

from rubik_tutor.cube import MOVES, SOLVED, apply_moves
from rubik_tutor.server import create_app

NOMINAL = {"U": (240, 215, 40), "R": (235, 110, 25), "F": (25, 150, 65),
           "D": (235, 235, 235), "L": (190, 30, 40), "B": (25, 70, 190)}


@pytest.fixture(scope="module")
def client():
    return create_app(llm=None).test_client()


def test_health_and_index(client):
    assert client.get("/api/health").get_json() == {"ok": True, "llm": False}
    r = client.get("/")
    assert r.status_code == 200 and b"Rubik" in r.data
    assert client.get("/static/app.js").status_code == 200


def test_scramble_solve_roundtrip(client):
    sc = client.post("/api/scramble", json={}).get_json()
    for mode in ("beginner", "fast"):
        plan = client.post("/api/solve", json={"facelets": sc["facelets"], "mode": mode}).get_json()
        assert plan["steps"] and plan["total_moves"] > 0
        s = sc["facelets"]
        for step in plan["steps"]:
            assert len(step["states"]) == len(step["moves"])
            s = apply_moves(s, step["moves"])
            assert step["after"] == s and step["before"]
        assert s == SOLVED
    fast = client.post("/api/solve", json={"facelets": sc["facelets"], "mode": "fast"}).get_json()
    beg = client.post("/api/solve", json={"facelets": sc["facelets"], "mode": "beginner"}).get_json()
    assert fast["total_moves"] < 25 < beg["total_moves"]


def test_solved_cube_has_empty_plan(client):
    assert client.post("/api/solve", json={"facelets": SOLVED}).get_json()["steps"] == []


def test_validation_errors(client):
    r = client.post("/api/solve", json={"facelets": "UUU"})
    assert r.status_code == 400 and "error" in r.get_json()
    twisted = list(SOLVED)
    twisted[8], twisted[9], twisted[20] = twisted[9], twisted[20], twisted[8]
    assert client.post("/api/validate", json={"facelets": "".join(twisted)}).get_json()["valid"] is False
    assert client.post("/api/solve", json={"facelets": SOLVED, "mode": "nope"}).status_code == 400
    assert client.post("/api/solve", data="not json", content_type="text/plain").status_code == 400


def test_classify_endpoint(client):
    rng = random.Random(8)
    seq = [rng.choice(list(MOVES)) for _ in range(20)]
    st = apply_moves(SOLVED, seq)
    patches = [list(NOMINAL[c]) for c in st]
    r = client.post("/api/classify", json={"patches": patches}).get_json()
    assert r["facelets"] == st and r["valid"] is True
    assert client.post("/api/classify", json={"patches": [[1, 2, 3]]}).status_code == 400


def test_check_endpoint(client):
    before = apply_moves(SOLVED, ["R", "U", "F"])
    r = client.post("/api/check", json={"state_before": before, "actual_state": apply_moves(before, ["R'"]),
                                        "expected_move": "R"}).get_json()
    assert r["status"] == "different_move" and r["undo_with"] == ["R"]
    assert client.post("/api/check", json={"state_before": before, "actual_state": before,
                                           "expected_move": "Z"}).status_code == 400


def test_apply_endpoint(client):
    r = client.post("/api/apply", json={"facelets": SOLVED, "moves": ["R", "R'"]}).get_json()
    assert r["facelets"] == SOLVED
    assert client.post("/api/apply", json={"facelets": SOLVED, "moves": ["X"]}).status_code == 400


def test_explain_and_ask(client):
    step = {"kind": "top_cross_run", "moves": ["F", "R", "U", "R'", "U'", "F'"], "stage_title": "Make the top cross",
            "pattern": "dot"}
    r = client.post("/api/explain", json={"step": step}).get_json()
    assert r["source"] == "template" and "dot" in r["text"]
    assert client.post("/api/explain", json={"step": {"kind": "x", "moves": ["Q"]}}).status_code == 400
    a = client.post("/api/ask", json={"question": "How many corners does a cube have?"}).get_json()
    assert "n02_anatomy" in a["notes"]
    assert client.post("/api/ask", json={"question": ""}).status_code == 400


def test_llm_rate_limit():
    calls = []
    app = create_app(llm=lambda s, u: calls.append(1) or "R U R'")
    c = app.test_client()
    codes = [c.post("/api/ask", json={"question": "what is notation"}).status_code for _ in range(25)]
    assert 429 in codes and codes.count(200) == 20
