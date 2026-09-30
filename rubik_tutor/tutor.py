"""Tutor layer.

Design rule: the LLM never decides moves. The solver and simulator produce every move; the LLM (if
configured) only rephrases a grounded fact sheet, and its output is rejected if it mentions any cube
move that is not in the allowed set. Without an API key everything works with deterministic text.
"""
from __future__ import annotations

import os
import re
from typing import Callable, Optional

from .cube import MOVES, apply_moves, diff_states, invert, stages_done
from .rag import get_index

MOVE_TOKEN = re.compile(r"(?<![A-Za-z0-9'])[URFDLB](?:2|')?(?![A-Za-z0-9'])")

SYSTEM_PROMPT = (
    "You are a friendly Rubik's Cube tutor for a complete beginner. Use plain, encouraging language "
    "and at most 120 words. You will receive a FACT SHEET that came from a verified solver. Explain it; "
    "do not change it. Never invent, alter, reorder, or add cube moves: if you mention a move, it must "
    "appear exactly in the fact sheet or the reference notes. If you are unsure, say so."
)


def moves_in_text(text: str) -> set[str]:
    return set(MOVE_TOKEN.findall(text))


def guard(text: str, allowed: set[str]) -> bool:
    """True if every move mentioned in `text` is in `allowed`."""
    return moves_in_text(text) <= allowed


# ------------------------------------------------------------------ deterministic explanations
def _fmt(moves):
    return " ".join(moves)


def describe_step(step: dict) -> str:
    kind, mv = step["kind"], _fmt(step["moves"])
    if kind == "cross":
        return (f"Build the cross on the bottom face. These moves bring the four bottom-colour edges "
                f"into place so each edge's second colour matches its side centre: {mv}.")
    if kind == "corner_insert":
        lift = "First lift the corner out of the bottom layer, " if step.get("lifted_first") else ""
        return (f"{lift}Bring the {step['corner']} corner home. The pattern R U R' U' (shown as it applies "
                f"to this corner's slot) is repeated {step['trigger_repeats']} time(s) after lining the "
                f"corner up with the top layer: {mv}.")
    if kind == "edge_insert":
        pop = "First pop the wrongly placed edge out of the middle layer, " if step.get("popped_first") else ""
        return (f"{pop}Insert the {step['edge']} edge into the middle layer, moving it to the "
                f"{step['direction']}. Turn the top layer until the edge lines up, then run the "
                f"insertion algorithm: {mv}.")
    if kind == "top_cross_run":
        return (f"Top cross: the top currently shows a {step['pattern']}. Align the top layer, then run "
                f"F R U R' U' F' to bring more yellow edges to the top: {mv}.")
    if kind == "sune_run":
        n = step["yellow_corners_before"]
        return (f"Orient the corners: {n} corner(s) show yellow on top now. Turn the top layer so the "
                f"right corner is front-left, then run the Sune algorithm: {mv}.")
    if kind == "align_top":
        return f"Turn the top layer so its corners match the side centres: {mv}."
    if kind == "corner_cycle":
        return (f"Position the top corners: this algorithm cycles three corners while keeping the top "
                f"yellow: {mv}.")
    if kind == "edge_cycle":
        return (f"Position the top edges: this algorithm cycles three top edges and leaves the corners "
                f"alone. Repeat if the edges cycle the wrong way: {mv}.")
    return f"Do these moves: {mv}."


def step_allowed_moves(step: dict) -> set[str]:
    allowed = set(step["moves"])
    for alg in (step.get("algorithm"),):
        if alg:
            allowed |= set(alg.split())
    if step["kind"] == "corner_insert":
        allowed |= {"R", "U", "R'", "U'"}
    if step["kind"] == "edge_insert":
        allowed |= set("U R U' R' U' F' U F U' L' U L U F U' F'".split())
    return allowed


# ------------------------------------------------------------------ LLM adapters
LLM = Callable[[str, str], str]           # (system, user) -> text


def anthropic_llm_from_env() -> Optional[LLM]:
    """Return an LLM callable if ANTHROPIC_API_KEY is set and the SDK is installed, else None."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    client = anthropic.Anthropic(api_key=key)
    model = os.environ.get("TUTOR_MODEL", "claude-sonnet-5")

    def call(system: str, user: str) -> str:
        resp = client.messages.create(model=model, max_tokens=400, system=system,
                                      messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()

    return call


class Tutor:
    def __init__(self, llm: Optional[LLM] = None):
        self.llm = llm

    # -------------------------------------------------- explain a step
    def explain(self, step: dict, question: Optional[str] = None) -> dict:
        base = describe_step(step)
        query = f"{step['stage_title']} {step['kind'].replace('_', ' ')} {question or ''}"
        notes = get_index().search(query, 2)
        if not self.llm:
            return {"text": base, "source": "template", "notes": [n["id"] for n in notes]}
        user = ("FACT SHEET:\n" + base + "\nStage: " + step["stage_title"] +
                "\n\nREFERENCE NOTES:\n" + "\n".join(f"- {n['title']}: {n['text']}" for n in notes) +
                ("\n\nLEARNER QUESTION: " + question if question else "\n\nExplain this step."))
        allowed = step_allowed_moves(step)
        for n in notes:
            allowed |= moves_in_text(n["text"])
        try:
            text = self.llm(SYSTEM_PROMPT, user)
        except Exception:
            return {"text": base, "source": "template", "notes": [n["id"] for n in notes]}
        if not text or not guard(text, allowed):
            return {"text": base, "source": "template (LLM output rejected by move guard)",
                    "notes": [n["id"] for n in notes]}
        return {"text": text, "source": "llm", "notes": [n["id"] for n in notes]}

    # -------------------------------------------------- free-form Q&A
    def ask(self, question: str, step: Optional[dict] = None) -> dict:
        notes = get_index().search(question, 3)
        if not notes:
            return {"answer": "I don't have a note on that yet. Try rephrasing, or ask about a stage, "
                              "an algorithm, notation, or scanning.", "source": "none", "notes": []}
        allowed = set()
        for n in notes:
            allowed |= moves_in_text(n["text"])
        if step:
            allowed |= step_allowed_moves(step)
        if self.llm:
            user = ("REFERENCE NOTES:\n" + "\n".join(f"- {n['title']}: {n['text']}" for n in notes) +
                    (f"\n\nCURRENT STEP FACTS: {describe_step(step)}" if step else "") +
                    f"\n\nQUESTION: {question}\nAnswer using only the notes.")
            try:
                text = self.llm(SYSTEM_PROMPT, user)
                if text and guard(text, allowed):
                    return {"answer": text, "source": "llm", "notes": [n["id"] for n in notes]}
            except Exception:
                pass
        top = notes[0]
        return {"answer": f"{top['title']}: {top['text']}", "source": "notes",
                "notes": [n["id"] for n in notes]}


# ------------------------------------------------------------------ mistake diagnosis
def diagnose(state_before: str, actual_state: str, expected_move: Optional[str] = None) -> dict:
    """Compare the cube the camera saw with the plan.

    `state_before` is the cube before the learner's move, `expected_move` the move the plan asked for
    (None when only checking that the cube is unchanged or explaining a change).
    """
    if expected_move:
        if actual_state == apply_moves(state_before, [expected_move]):
            return {"status": "match", "message": f"That matches the plan: {expected_move}. Nice work!"}
    if actual_state == state_before:
        return {"status": "no_change", "message": "The cube hasn't changed yet."}
    found = diff_states(state_before, actual_state, max_len=2)
    if found is None:
        return {"status": "unknown",
                "message": "I can't tell what happened. Rescan, or let me re-plan from your cube as it is."}
    undo = invert(found)
    said = f"You did {' '.join(found)}"
    if expected_move:
        said += f" instead of {expected_move}"
    return {"status": "different_move", "moves_made": found, "undo_with": undo,
            "message": f"{said}. Undo it with {' '.join(undo)}"
                       + (f", then do {expected_move}." if expected_move else ".")
                       + " Or ask me to re-plan from your cube."}


def stage_progress(state: str) -> list[str]:
    return stages_done(state)
