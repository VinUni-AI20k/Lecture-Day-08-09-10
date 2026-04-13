"""Benchmark tối ưu: chạy grading_questions với config tốt nhất."""
import json
import os
import sys
import importlib
from datetime import datetime
from pathlib import Path
from collections import Counter

lab = Path(__file__).resolve().parent
sys.path.insert(0, str(lab))

os.environ["WEAK_CONTEXT_SCORE_THRESHOLD"] = "0.05"

qpath = lab / "data" / "test" / "grading_questions.json"
questions = json.loads(qpath.read_text(encoding="utf-8"))
by_id = {q["id"]: q for q in questions}

configs = [
    {"label": "dense_k12_s5",  "retrieval_mode": "dense",  "top_k_search": 12, "top_k_select": 5, "use_rerank": False},
    {"label": "dense_k15_s6",  "retrieval_mode": "dense",  "top_k_search": 15, "top_k_select": 6, "use_rerank": False},
    {"label": "dense_k15_s5_rerank", "retrieval_mode": "dense", "top_k_search": 15, "top_k_select": 5, "use_rerank": True},
    {"label": "hybrid_k12_s5", "retrieval_mode": "hybrid", "top_k_search": 12, "top_k_select": 5, "use_rerank": False},
    {"label": "hybrid_k15_s6", "retrieval_mode": "hybrid", "top_k_search": 15, "top_k_select": 6, "use_rerank": False},
]

all_results = []

for cfg in configs:
    importlib.invalidate_caches()
    import rag_answer as ra_mod
    importlib.reload(ra_mod)
    from rag_answer import rag_answer
    from grade_grading_run import judge_one

    print(f"\n{'='*60}")
    print(f"Running: {cfg['label']}")
    print(f"  mode={cfg['retrieval_mode']} k_search={cfg['top_k_search']} k_select={cfg['top_k_select']} rerank={cfg['use_rerank']}")

    rows = []
    for q in questions:
        try:
            r = rag_answer(
                query=q["question"],
                retrieval_mode=cfg["retrieval_mode"],
                top_k_search=cfg["top_k_search"],
                top_k_select=cfg["top_k_select"],
                use_rerank=cfg["use_rerank"],
                verbose=False,
                trace=False,
            )
            row = {
                "id": q["id"],
                "question": q["question"],
                "answer": r.get("answer", ""),
                "sources": r.get("sources", []),
                "chunks_retrieved": len(r.get("chunks_used") or []),
                "retrieval_mode": cfg["retrieval_mode"],
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            row = {
                "id": q["id"],
                "question": q["question"],
                "answer": f"ERROR: {e}",
                "sources": [],
                "chunks_retrieved": 0,
                "retrieval_mode": cfg["retrieval_mode"],
                "timestamp": datetime.now().isoformat(),
            }
        rows.append(row)
        print(f"  {q['id']}: {row['answer'][:80]}...")

    out_log = lab / "logs" / f"grading_run_{cfg['label']}.json"
    out_log.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    per_q = []
    total_raw = 0.0
    max_raw = 0.0
    print(f"\n  --- Grading {cfg['label']} ---")
    for row in rows:
        rub = by_id[row["id"]]
        mp = float(rub.get("points", 10))
        max_raw += mp
        try:
            j = judge_one(rub, row)
            j["max_points"] = mp
            pts = float(j.get("points", 0))

            if j.get("verdict") == "Full":
                pts = mp
            elif j.get("verdict") == "Partial":
                pts = mp * 0.5
            elif j.get("verdict") == "Penalty":
                pts = -mp * 0.5
            else:
                pts = 0

            j["points"] = pts
            per_q.append(j)
            total_raw += pts
            print(f"  {j['id']}: {j.get('verdict','?')} => {pts}/{mp}  ({j.get('reason','')})")
        except Exception as e:
            per_q.append({"id": row["id"], "verdict": "ERROR", "points": 0, "max_points": mp})
            print(f"  {row['id']}: ERROR ({e})")

    projected = (total_raw / max_raw) * 30 if max_raw else 0.0
    verdicts = Counter(x.get("verdict", "ERROR") for x in per_q)

    entry = {
        "label": cfg["label"],
        "config": cfg,
        "raw": round(total_raw, 2),
        "max_raw": round(max_raw, 2),
        "projected_30": round(projected, 2),
        "verdicts": dict(verdicts),
        "per_question": per_q,
    }
    all_results.append(entry)
    print(f"\n  TOTAL: {total_raw}/{max_raw}  =>  {projected:.1f}/30  Verdicts: {dict(verdicts)}")

all_results.sort(key=lambda x: x["projected_30"], reverse=True)
summary = lab / "results" / "benchmark_optimized.json"
summary.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"\n{'='*60}")
print("RANKING (best → worst):")
for i, r in enumerate(all_results, 1):
    v = r["verdicts"]
    print(f"  #{i} {r['label']}: {r['projected_30']}/30  (Full={v.get('Full',0)}, Partial={v.get('Partial',0)}, Zero={v.get('Zero',0)}, Penalty={v.get('Penalty',0)})")
print(f"\nBest config: {all_results[0]['label']}")
print(f"Saved to: {summary}")
