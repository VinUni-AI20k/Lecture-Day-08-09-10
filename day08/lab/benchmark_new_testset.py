import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from grade_grading_run import judge_one
from rag_answer import rag_answer


def main() -> None:
    lab = Path(__file__).resolve().parent
    qpath = lab / "data" / "test" / "grading_questions.json"
    questions = json.loads(qpath.read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in questions}

    configs = [
        {"label": "dense_k10_s3_no_rerank", "retrieval_mode": "dense", "top_k_search": 10, "top_k_select": 3, "use_rerank": False},
        {"label": "dense_k12_s4_no_rerank", "retrieval_mode": "dense", "top_k_search": 12, "top_k_select": 4, "use_rerank": False},
        {"label": "dense_k15_s4_rerank", "retrieval_mode": "dense", "top_k_search": 15, "top_k_select": 4, "use_rerank": True},
        {"label": "hybrid_k10_s3_no_rerank", "retrieval_mode": "hybrid", "top_k_search": 10, "top_k_select": 3, "use_rerank": False},
        {"label": "hybrid_k12_s4_no_rerank", "retrieval_mode": "hybrid", "top_k_search": 12, "top_k_select": 4, "use_rerank": False},
        {"label": "hybrid_k15_s4_rerank", "retrieval_mode": "hybrid", "top_k_search": 15, "top_k_select": 4, "use_rerank": True},
    ]

    max_raw = sum(float(q.get("points", q.get("max_points", 10))) for q in questions)
    results = []

    for cfg in configs:
        rows = []
        for q in questions:
            qq = q["question"]
            try:
                r = rag_answer(
                    query=qq,
                    retrieval_mode=cfg["retrieval_mode"],
                    top_k_search=cfg["top_k_search"],
                    top_k_select=cfg["top_k_select"],
                    use_rerank=cfg["use_rerank"],
                    verbose=False,
                    trace=False,
                )
                row = {
                    "id": q["id"],
                    "question": qq,
                    "answer": r.get("answer", ""),
                    "sources": r.get("sources", []),
                    "chunks_retrieved": len(r.get("chunks_used") or []),
                    "retrieval_mode": r.get("config", {}).get("retrieval_mode", cfg["retrieval_mode"]),
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                row = {
                    "id": q["id"],
                    "question": qq,
                    "answer": f"PIPELINE_ERROR: {e}",
                    "sources": [],
                    "chunks_retrieved": 0,
                    "retrieval_mode": cfg["retrieval_mode"],
                    "timestamp": datetime.now().isoformat(),
                }
            rows.append(row)

        per_q = []
        total_raw = 0.0
        for row in rows:
            rub = by_id[row["id"]]
            try:
                j = judge_one(rub, row)
                per_q.append(j)
                total_raw += float(j.get("points", 0) or 0)
            except Exception as e:
                per_q.append({"id": row["id"], "verdict": "ERROR", "points": 0, "reason": str(e)})

        projected = (total_raw / max_raw) * 30 if max_raw else 0.0
        verdicts = Counter(x.get("verdict", "ERROR") for x in per_q)

        out_log = lab / "logs" / f"grading_run_{cfg['label']}.json"
        out_log.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

        results.append(
            {
                "label": cfg["label"],
                "config": cfg,
                "raw": round(total_raw, 2),
                "max_raw": round(max_raw, 2),
                "projected_30": round(projected, 2),
                "verdicts": dict(verdicts),
            }
        )

    results = sorted(results, key=lambda x: x["projected_30"], reverse=True)
    summary_path = lab / "results" / "benchmark_new_testset.json"
    summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nSaved: {summary_path}")


if __name__ == "__main__":
    main()

