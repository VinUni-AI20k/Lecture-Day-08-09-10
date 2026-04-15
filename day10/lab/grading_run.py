#!/usr/bin/env python3
"""
Chạy bộ câu grading (retrieval + keyword) — output JSONL cho giảng viên.

  python grading_run.py --out artifacts/eval/grading_run.jsonl

Yêu cầu: đã chạy `python etl_pipeline.py run` trước để có collection Chroma.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent
DEFAULT_GRADING_QUESTIONS = ROOT / "data" / "grading_questions.json"
FALLBACK_TEST_QUESTIONS = ROOT / "data" / "test_questions.json"


def _resolve_questions_path(raw_path: str) -> Path:
    qpath = Path(raw_path)
    if qpath.is_file():
        return qpath

    # Keep CLI behavior stable: when default grading file is missing, use test questions.
    if qpath == DEFAULT_GRADING_QUESTIONS and FALLBACK_TEST_QUESTIONS.is_file():
        print(
            f"WARN: missing {DEFAULT_GRADING_QUESTIONS.name}; fallback to {FALLBACK_TEST_QUESTIONS.name}",
            file=sys.stderr,
        )
        return FALLBACK_TEST_QUESTIONS

    return qpath


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--questions",
        default=str(DEFAULT_GRADING_QUESTIONS),
    )
    p.add_argument(
        "--out",
        default=str(ROOT / "artifacts" / "eval" / "grading_run.jsonl"),
    )
    p.add_argument("--top-k", type=int, default=5)
    args = p.parse_args()

    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        print("pip install chromadb sentence-transformers", file=sys.stderr)
        return 1

    qpath = _resolve_questions_path(args.questions)
    if not qpath.is_file():
        print(f"questions not found: {qpath}", file=sys.stderr)
        return 1

    qs = json.loads(qpath.read_text(encoding="utf-8"))
    db_path = os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db"))
    collection_name = os.environ.get("CHROMA_COLLECTION", "day10_kb")
    model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=db_path)
    emb = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
    col = client.get_collection(name=collection_name, embedding_function=emb)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        for q in qs:
            text = q["question"]
            res = col.query(query_texts=[text], n_results=args.top_k)
            docs = (res.get("documents") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            blob = " ".join(docs).lower()
            must_any = [x.lower() for x in q.get("must_contain_any", [])]
            forbidden = [x.lower() for x in q.get("must_not_contain", [])]
            ok_any = any(m in blob for m in must_any) if must_any else True
            bad_forb = any(m in blob for m in forbidden) if forbidden else False
            top_doc = (metas[0] or {}).get("doc_id", "") if metas else ""
            want_top1 = (q.get("expect_top1_doc_id") or "").strip()
            top1_ok = True
            if want_top1:
                top1_ok = top_doc == want_top1
            rec = {
                "id": q.get("id"),
                "question": text,
                "top1_doc_id": top_doc,
                "contains_expected": ok_any,
                "hits_forbidden": bad_forb,
                "top1_doc_matches": top1_ok if want_top1 else None,
                "top_k_used": args.top_k,
                "grading_criteria": q.get("grading_criteria", []),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
