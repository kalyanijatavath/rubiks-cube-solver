"""Flask API + static front end.

Run locally:   python -m rubik_tutor.server
Production:    gunicorn "rubik_tutor.server:create_app()" --bind 0.0.0.0:$PORT
Set ANTHROPIC_API_KEY to enable LLM phrasing; without it every endpoint still works.
"""
from __future__ import annotations

import os
import random
import time
from collections import defaultdict, deque
from pathlib import Path

import kociemba
from flask import Flask, jsonify, request, send_from_directory

from . import beginner_solver as bs
from .cube import MOVES, SOLVED, apply_moves, stages_done
from .scan import ScanError, classify_patches
from .tutor import Tutor, anthropic_llm_from_env, describe_step, diagnose

STATIC = Path(__file__).resolve().parent / "static"
LLM_LIMIT_PER_MINUTE = int(os.environ.get("LLM_LIMIT_PER_MINUTE", "20"))


def _states_after_each_move(state, moves):
    out, s = [], state
    for m in moves:
        s = apply_moves(s, [m])
        out.append(s)
    return out


def build_plan(state: str, mode: str = "beginner") -> dict:
    """Solve `state` and return steps annotated with the state after every move."""
    bs.validate(state)
    if mode == "fast":
        raw = [{"stage": 0, "stage_key": "fast", "stage_title": "Fast solution", "kind": "fast",
                "moves": kociemba.solve(state).split()}] if state != SOLVED else []
    else:
        raw = bs.beginner_solve(state)
    steps, s = [], state
    for i, st in enumerate(raw):
        after = _states_after_each_move(s, st["moves"])
        step = dict(st, index=i, before=s, states=after, after=after[-1] if after else s,
                    text=describe_step(st), stages_done=stages_done(after[-1] if after else s))
        steps.append(step)
        s = step["after"]
    assert s == SOLVED
    return {"mode": mode, "start": state, "steps": steps,
            "total_moves": sum(len(x["moves"]) for x in steps),
            "stages": [{"stage": k, "key": v[0], "title": v[1]} for k, v in bs.STAGES.items()]
            if mode == "beginner" else []}


def create_app(llm=None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    tutor = Tutor(llm if llm is not None else anthropic_llm_from_env())
    hits = defaultdict(deque)

    def rate_limited() -> bool:
        if not tutor.llm:
            return False
        now, ip = time.time(), request.headers.get("X-Forwarded-For", request.remote_addr)
        q = hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= LLM_LIMIT_PER_MINUTE:
            return True
        q.append(now)
        return False

    def err(msg, code=400):
        return jsonify({"error": msg}), code

    def body():
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "index.html")

    @app.get("/static/<path:name>")
    def static_files(name):
        return send_from_directory(STATIC, name)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "llm": bool(tutor.llm)})

    @app.post("/api/classify")
    def classify():
        try:
            res = classify_patches(body().get("patches"))
        except (ScanError, TypeError, ValueError) as e:
            return err(str(e))
        try:
            bs.validate(res["facelets"])
            res.update(valid=True, message="Scan looks like a valid cube.")
        except bs.InvalidCube as e:
            res.update(valid=False, message=str(e))
        return jsonify(res)

    @app.post("/api/validate")
    def validate():
        state = body().get("facelets", "")
        try:
            bs.validate(state)
            return jsonify({"valid": True, "message": "Valid cube."})
        except bs.InvalidCube as e:
            return jsonify({"valid": False, "message": str(e)})

    @app.post("/api/solve")
    def solve():
        data = body()
        mode = data.get("mode", "beginner")
        if mode not in ("beginner", "fast"):
            return err("mode must be 'beginner' or 'fast'")
        try:
            return jsonify(build_plan(data.get("facelets", ""), mode))
        except bs.InvalidCube as e:
            return err(str(e))

    @app.post("/api/scramble")
    def scramble():
        rng, seq, last = random.Random(), [], ""
        while len(seq) < 20:
            m = rng.choice(list(MOVES))
            if m[0] != last:
                seq.append(m)
                last = m[0]
        return jsonify({"scramble": " ".join(seq), "facelets": apply_moves(SOLVED, seq)})

    @app.post("/api/apply")
    def apply_():
        data = body()
        moves = data.get("moves", [])
        if not isinstance(moves, list) or not all(m in MOVES for m in moves) or len(moves) > 50:
            return err("moves must be a list of up to 50 valid moves like R, U', F2")
        try:
            bs.validate(data.get("facelets", ""))
        except bs.InvalidCube as e:
            return err(str(e))
        return jsonify({"facelets": apply_moves(data["facelets"], moves)})

    @app.post("/api/check")
    def check():
        data = body()
        before, actual, expected = data.get("state_before", ""), data.get("actual_state", ""), data.get("expected_move")
        if expected is not None and expected not in MOVES:
            return err("expected_move is not a valid move")
        try:
            bs.validate(before)
            bs.validate(actual)
        except bs.InvalidCube as e:
            return err(str(e))
        return jsonify(diagnose(before, actual, expected))

    @app.post("/api/explain")
    def explain():
        if rate_limited():
            return err("Too many requests, try again in a minute.", 429)
        data = body()
        step = data.get("step")
        if not isinstance(step, dict) or "kind" not in step or "moves" not in step:
            return err("step is required")
        step = {k: step.get(k) for k in ("kind", "moves", "stage_title", "algorithm", "corner", "edge",
                                         "pattern", "direction", "trigger_repeats", "lifted_first",
                                         "popped_first", "yellow_corners_before") if k in step}
        step.setdefault("stage_title", "Step")
        if not isinstance(step["moves"], list) or not all(m in MOVES for m in step["moves"]):
            return err("step contains invalid moves")
        q = data.get("question")
        return jsonify(tutor.explain(step, q if isinstance(q, str) else None))

    @app.post("/api/ask")
    def ask():
        if rate_limited():
            return err("Too many requests, try again in a minute.", 429)
        q = body().get("question", "")
        if not isinstance(q, str) or not q.strip() or len(q) > 500:
            return err("question must be 1-500 characters")
        return jsonify(tutor.ask(q.strip()))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
