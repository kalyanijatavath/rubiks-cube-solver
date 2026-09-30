# Rubik's Cube Tutor Agent

Show your cube to the webcam (or type the colours in, or take a random scramble) and learn to solve it
step by step. A verified solver produces every move; an LLM (optional) only explains them.

```
 camera / manual edit          Flask API                              browser
 ┌───────────────┐   54 RGB   ┌──────────────────────────────────────────────┐
 │ 3x3 grid      │──────────▶ │ scan.py     colours → 54-char cube string    │
 │ sampling      │            │ beginner_solver.py  stage-labelled moves     │ ─▶ net view,
 └───────────────┘            │ cube.py     simulator + stage detectors      │    move chips,
                              │ tutor.py    explain / ask / diagnose mistakes│    Q&A, re-scan
                              │ rag.py      BM25 over 16 teaching notes      │
                              └──────────────────────────────────────────────┘
                                   optional: Anthropic API (phrasing only, move-guarded)
```

**Key design rule:** the LLM never decides a move. The solver + simulator produce every move; the LLM only
rewrites a fact sheet, and its answer is thrown away (falling back to built-in text) if it mentions any
cube move that is not in the allowed set. With no API key the whole app still works.

## Features

- **Scan** six faces with the camera. Colours are read on your device; only 54 RGB numbers go to the server.
  Each sticker is compared to the six centre stickers, and the rule "each colour appears exactly nine
  times" is enforced. Uncertain stickers get a pink outline; click any sticker to fix it.
- **Beginner method solver**: seven labelled stages (cross → corners → middle edges → top cross → orient
  corners → position corners → position edges), average ≈151 moves. A **fast mode** (Kociemba, ≈19 moves) is also available.
- **Mistake handling**: scan again after a move and the app tells you which move you made instead, how to
  undo it, or re-plans from your cube as it is. Or pick "I did a different move".
- **Ask questions** answered from 16 original teaching notes (BM25 retrieval, optional LLM phrasing).

## Quick start

```bash
pip install -r requirements.txt
python -m rubik_tutor.server            # http://127.0.0.1:5000
```

Camera access needs HTTPS or `localhost`. No cube handy? Press **Random scramble**.

Optional AI phrasing: `export ANTHROPIC_API_KEY=...` (model via `TUTOR_MODEL`, default `claude-sonnet-5`).
LLM endpoints are rate-limited per IP (`LLM_LIMIT_PER_MINUTE`, default 20).

## Deploy

Everything is configured; hosting needs your own account.

**Render (free tier, HTTPS included)**
1. Push this repo to GitHub.
2. Render dashboard → New → **Blueprint** → select the repo (`render.yaml` is picked up).
3. Optional: set `ANTHROPIC_API_KEY` in the service environment.

**Hugging Face Spaces (Docker)**
1. Create a Space with SDK **Docker**. Add this header to the top of the Space's `README.md`:
   ```yaml
   ---
   title: Rubik's Cube Tutor
   sdk: docker
   app_port: 7860
   ---
   ```
2. Push the repo to the Space's git remote. Add `ANTHROPIC_API_KEY` as a Space secret if wanted.

**Docker anywhere**: `docker build -t rubik-tutor . && docker run -p 7860:7860 rubik-tutor`

## API

| Endpoint | Body | Returns |
|---|---|---|
| `POST /api/classify` | `{patches: [[r,g,b] x 54]}` (facelet order URFDLB) | `facelets, palette, low_confidence, valid, message` |
| `POST /api/validate` | `{facelets}` | `{valid, message}` |
| `POST /api/solve` | `{facelets, mode: "beginner"｜"fast"}` | steps with `stage, kind, moves, states, before, after, text` |
| `POST /api/check` | `{state_before, actual_state, expected_move?}` | `status` (`match`／`different_move`／…), `moves_made`, `undo_with` |
| `POST /api/apply` | `{facelets, moves}` | new `facelets` |
| `POST /api/explain` | `{step, question?}` | `text, source (llm／template), notes` |
| `POST /api/ask` | `{question}` | `answer, source, notes` |
| `POST /api/scramble` | `{}` | random `facelets` and its scramble |
| `GET /api/health` | | `{ok, llm}` |

Cube string: 54 characters in U R F D L B order (Kociemba format). Letters name the face whose *centre*
carries that colour, so any colour scheme works. Teaching assumes the first-layer colour is on the **bottom**.

## How it is verified

`python -m pytest tests -q` (37 tests) and `tests/frontend` (10 DOM checks in jsdom):

- The simulator's moves are derived from 3D geometry, then cross-checked against an independent solver.
- Every algorithm in the teaching notes is run in the simulator: which layers it keeps, its order, the
  exact case-recognition rules, and the complete procedures (top cross ≤3 runs, corner orientation ≤3
  runs, last-layer permutation including parity cases).
- The beginner solver replays every solution in the simulator and must end solved; it is tested on random
  scrambles, partially built cubes, and cubes after a deliberate wrong move.
- The move guard, mistake diagnosis, scanner, retrieval and every API endpoint have tests.

Measured results (`data/*.json`, regenerate with `scripts/`):

| Component | Result |
|---|---|
| Beginner solver, 500 random scrambles | 500/500 solved; mean 151.2 moves (88–213); 0.05 s per solve |
| Fast mode (Kociemba) | ≈19 moves |
| Retrieval, 40 questions | BM25 hit@1 = 82.5%, hit@3 = 90% (TF-IDF baseline 72.5% / 80%) |
| Colour reading, synthetic scans | 99.98% of stickers with centre reference + count constraint (fixed colours: 94.7%) |

## Data (`data/`)

Scrambles with verified solutions (2,000), wrong-move cases for testing recovery (500), stage-labelled
states (600), synthetic sticker-colour samples (21,600), and 16 teaching notes with 40 retrieval
questions. Schemas and generation details are in `scripts/` and the JSON stats files.

## Known limitations

- **The camera flow has not been tried with a real camera and a real cube.** The DOM test runs the real
  page but cannot provide a camera. Face-orientation instructions follow the facelet layout; try one full
  scan and use the pink low-confidence outlines and click-to-fix as the safety net.
- **The LLM path is tested with a fake model only.** It has not been run against the live API from this
  build environment. Without a key the deterministic text is used.
- **The Dockerfile has not been built here** (no Docker available). The same install and the same
  `gunicorn` command were run and exercised over HTTP from a clean virtual environment.
- Colour-reading numbers come from **synthetic** data; real lighting (shadows, uneven light) will be harder.
- The 40 retrieval questions were written by the same author as the notes, so they flatter the retriever.
- Beginner solutions are long (about 150 moves) by design. Use fast mode for short solutions.
- Rate limiting is in memory per process; use a shared store if you scale beyond one worker.
- The LLM move guard is a token check: an English "B"/"F" used as a word would be flagged and the answer
  replaced by built-in text (safe, but conservative).

## Project layout

```
rubik_tutor/   cube.py  beginner_solver.py  last_layer.py  scan.py  rag.py  tutor.py  server.py  static/
tests/         pytest suite + frontend/ (jsdom DOM smoke test)
scripts/       dataset generators and benchmarks
data/          datasets, teaching notes, measured results
Dockerfile  render.yaml  .github/workflows/ci.yml
```

## License

MIT (see `LICENSE`; replace the copyright holder with your name).
