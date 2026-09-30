"""Small dependency-free BM25 retriever over the teaching notes."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_STOP = set("""a an the is are was were be been do does did i my me we our you your it its of to in on at for
with and or but if so as by from that this these those what which who how why can could should would will
about into than then there here have has had not no""".split())
_TOKEN = re.compile(r"[a-z0-9]+'?")


def _stem(w: str) -> str:
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 4 and w.endswith("es"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def tokenize(text: str):
    return [_stem(t) for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class NoteIndex:
    def __init__(self, notes, k1=1.5, b=0.75, title_weight=2):
        self.notes = notes
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(n["title"]) * title_weight + tokenize(n["text"])) for n in notes]
        self.len = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.len) / len(self.len)
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, k: int = 3):
        q = tokenize(query)
        scores = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in q:
                f = d.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
            scores.append(s)
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [dict(self.notes[i], score=round(scores[i], 3)) for i in order if scores[i] > 0]


def load_notes(path=None):
    path = Path(path or DATA_DIR / "rag_corpus.jsonl")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


_INDEX = None


def get_index() -> NoteIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = NoteIndex(load_notes())
    return _INDEX


def evaluate(index=None, eval_path=None):
    index = index or get_index()
    eval_path = Path(eval_path or DATA_DIR / "rag_eval.jsonl")
    qs = [json.loads(l) for l in eval_path.read_text().splitlines() if l.strip()]
    h1 = h3 = 0
    misses = []
    for q in qs:
        ids = [r["id"] for r in index.search(q["question"], 3)]
        h1 += bool(ids) and ids[0] == q["gold_note_id"]
        h3 += q["gold_note_id"] in ids
        if not ids or ids[0] != q["gold_note_id"]:
            misses.append({"question": q["question"], "gold": q["gold_note_id"], "got": ids[:1]})
    return {"n": len(qs), "hit@1": round(h1 / len(qs), 3), "hit@3": round(h3 / len(qs), 3), "misses": misses}
