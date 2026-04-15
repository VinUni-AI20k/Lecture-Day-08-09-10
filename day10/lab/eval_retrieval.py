#!/usr/bin/env python3
"""
Đánh giá retrieval đơn giản — before/after khi pipeline đổi dữ liệu embed.

Không bắt buộc LLM: chỉ kiểm tra top-k chunk có chứa keyword kỳ vọng hay không
(tiếp nối tinh thần Day 08/09 nhưng tập trung data layer).

Embed Owner (Trần Tiến Dũng):
  - Thêm --scenario để tag từng lần chạy (before / after_fix / after_inject) vào CSV.
  - Thêm --collection-info để in số lượng vector trong collection trước khi query
    → chứng minh embed idempotent (rerun không làm tăng count).
  - Default top-k nâng lên 5 để đồng nhất với grading_run.py.
  - In summary pass/fail sau khi chạy.

Ví dụ Sprint 3:
  # Chạy sau pipeline chuẩn (after fix)
  python eval_retrieval.py --scenario after_fix --out artifacts/eval/eval_after_fix.csv

  # Chạy sau inject bad
  python eval_retrieval.py --scenario after_inject --out artifacts/eval/eval_after_inject.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 10 retrieval eval — before/after")
    parser.add_argument(
        "--questions",
        default=str(ROOT / "data" / "test_questions.json"),
        help="JSON danh sách câu hỏi golden (retrieval)",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "artifacts" / "eval" / "before_after_eval.csv"),
        help="CSV kết quả",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Số chunk top-k truy vấn (mặc định 5, đồng nhất grading_run.py)",
    )
    parser.add_argument(
        "--scenario",
        default="",
        help="Nhãn kịch bản ghi vào cột 'scenario' (vd: before, after_fix, after_inject)",
    )
    parser.add_argument(
        "--collection-info",
        action="store_true",
        help="In số lượng vector trong collection trước khi query (kiểm tra idempotency)",
    )
    args = parser.parse_args()

    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        print("Install: pip install chromadb sentence-transformers", file=sys.stderr)
        return 1

    qpath = Path(args.questions)
    if not qpath.is_file():
        print(f"questions not found: {qpath}", file=sys.stderr)
        return 1

    questions = json.loads(qpath.read_text(encoding="utf-8"))
    db_path = os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db"))
    collection_name = os.environ.get("CHROMA_COLLECTION", "day10_kb")
    model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=db_path)
    emb = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
    try:
        col = client.get_collection(name=collection_name, embedding_function=emb)
    except Exception as e:
        print(f"Collection error: {e}", file=sys.stderr)
        return 2

    # In thông tin collection để verify idempotency
    if args.collection_info:
        try:
            count = col.count()
            print(f"collection={collection_name} vector_count={count}")
        except Exception as e:
            print(f"WARN: cannot get collection count: {e}", file=sys.stderr)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    use_scenario = bool(args.scenario)
    fieldnames = [
        "scenario",
        "question_id",
        "question",
        "top1_doc_id",
        "top1_preview",
        "contains_expected",
        "hits_forbidden",
        "top1_doc_expected",
        "top_k_used",
    ]

    rows_out = []
    for q in questions:
        text = q["question"]
        res = col.query(query_texts=[text], n_results=args.top_k)
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        top_doc = (metas[0] or {}).get("doc_id", "") if metas else ""
        preview = (docs[0] or "")[:180].replace("\n", " ") if docs else ""
        blob = " ".join(docs).lower()
        must_any = [x.lower() for x in q.get("must_contain_any", [])]
        forbidden = [x.lower() for x in q.get("must_not_contain", [])]
        ok_any = any(m in blob for m in must_any) if must_any else True
        bad_forb = any(m in blob for m in forbidden) if forbidden else False
        want_top1 = (q.get("expect_top1_doc_id") or "").strip()
        top1_expected = ""
        if want_top1:
            top1_expected = "yes" if top_doc == want_top1 else "no"
        rows_out.append(
            {
                "scenario": args.scenario,
                "question_id": q.get("id", ""),
                "question": text,
                "top1_doc_id": top_doc,
                "top1_preview": preview,
                "contains_expected": "yes" if ok_any else "no",
                "hits_forbidden": "yes" if bad_forb else "no",
                "top1_doc_expected": top1_expected,
                "top_k_used": args.top_k,
            }
        )

    with out_path.open("w", encoding="utf-8", newline="") as fcsv:
        # Bỏ cột scenario nếu không dùng --scenario (giữ tương thích ngược)
        active_fields = fieldnames if use_scenario else [f for f in fieldnames if f != "scenario"]
        w = csv.DictWriter(fcsv, fieldnames=active_fields, extrasaction="ignore")
        w.writeheader()
        for row in rows_out:
            w.writerow(row)

    # Summary pass/fail
    total = len(rows_out)
    pass_count = sum(
        1 for r in rows_out
        if r["contains_expected"] == "yes" and r["hits_forbidden"] == "no"
    )
    fail_count = total - pass_count
    print(f"Wrote {out_path}")
    print(f"Summary: {pass_count}/{total} pass (contains_expected=yes AND hits_forbidden=no), {fail_count} fail")
    if fail_count > 0:
        for r in rows_out:
            if r["contains_expected"] != "yes" or r["hits_forbidden"] != "no":
                print(f"  FAIL [{r['question_id']}] contains_expected={r['contains_expected']} hits_forbidden={r['hits_forbidden']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
