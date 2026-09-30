"""Evaluate the BM25 retriever on data/rag_eval.jsonl and write data/rag_bm25_results.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rubik_tutor.rag import evaluate  # noqa: E402

res = evaluate()
json.dump(res, open("data/rag_bm25_results.json", "w"), indent=2)
print({k: v for k, v in res.items() if k != "misses"}, f"({len(res['misses'])} top-1 misses)")
