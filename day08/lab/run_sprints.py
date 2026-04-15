import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
RESULTS_ROOT = BASE_DIR / "results"
LOGS_ROOT = BASE_DIR / "logs"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    for p in [
        RESULTS_ROOT / "sprint1",
        RESULTS_ROOT / "sprint2",
        RESULTS_ROOT / "sprint3",
        RESULTS_ROOT / "sprint4",
        LOGS_ROOT / "sprint1",
        LOGS_ROOT / "sprint2",
        LOGS_ROOT / "sprint3",
        LOGS_ROOT / "sprint4",
    ]:
        p.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sprint1_index() -> Dict[str, Any]:
    from index import build_index, inspect_metadata_coverage, CHROMA_DB_DIR, COLLECTION_NAME

    build_index()

    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    metas = collection.get(include=["metadatas"])["metadatas"]

    total = len(metas)
    missing = {"source": 0, "section": 0, "effective_date": 0}
    for m in metas:
        if not m.get("source"):
            missing["source"] += 1
        if not m.get("section"):
            missing["section"] += 1
        if not m.get("effective_date") or m.get("effective_date") in ("unknown",):
            missing["effective_date"] += 1

    report = {
        "timestamp": _now(),
        "collection": COLLECTION_NAME,
        "total_chunks": total,
        "missing_metadata_counts": missing,
    }

    try:
        inspect_metadata_coverage()
    except Exception:
        pass

    return report


def _sprint2_baseline_answers() -> List[Dict[str, Any]]:
    from rag_answer import rag_answer

    test_path = BASE_DIR / "data" / "test_questions.json"
    questions = json.loads(test_path.read_text(encoding="utf-8"))

    out: List[Dict[str, Any]] = []
    for q in questions:
        r = rag_answer(q["question"], retrieval_mode="dense", use_rerank=False, verbose=False)
        out.append(
            {
                "id": q["id"],
                "question": q["question"],
                "answer": r["answer"],
                "sources": r["sources"],
                "retrieval_mode": "dense",
                "use_rerank": False,
                "timestamp": _now(),
            }
        )
    return out


def _sprint3_retrieval_debug() -> Dict[str, Any]:
    from rag_answer import retrieve_dense, retrieve_sparse, retrieve_hybrid, TOP_K_SEARCH

    queries = [
        "Approval Matrix để cấp quyền hệ thống là tài liệu nào?",
        "ERR-403-AUTH là lỗi gì?",
    ]

    def pack(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        packed = []
        for c in chunks:
            meta = c.get("metadata", {})
            packed.append(
                {
                    "source": meta.get("source", ""),
                    "section": meta.get("section", ""),
                    "effective_date": meta.get("effective_date", ""),
                    "score": float(c.get("score", 0.0)),
                    "text_preview": (c.get("text", "") or "")[:200],
                }
            )
        return packed

    result: Dict[str, Any] = {"timestamp": _now(), "top_k_search": TOP_K_SEARCH, "queries": []}
    for q in queries:
        result["queries"].append(
            {
                "query": q,
                "dense": pack(retrieve_dense(q, top_k=TOP_K_SEARCH)),
                "sparse": pack(retrieve_sparse(q, top_k=TOP_K_SEARCH)),
                "hybrid": pack(retrieve_hybrid(q, top_k=TOP_K_SEARCH)),
            }
        )
    return result


def _sprint4_eval() -> Dict[str, Any]:
    import eval as eval_mod

    baseline = eval_mod.run_scorecard(eval_mod.BASELINE_CONFIG, verbose=False)
    variant = eval_mod.run_scorecard(eval_mod.VARIANT_CONFIG, verbose=False)

    ab_csv = (RESULTS_ROOT / "sprint4" / "ab_comparison.csv").as_posix()
    eval_mod.compare_ab(baseline, variant, output_csv=ab_csv)

    return {
        "timestamp": _now(),
        "baseline_label": eval_mod.BASELINE_CONFIG.get("label"),
        "variant_label": eval_mod.VARIANT_CONFIG.get("label"),
        "baseline_rows": len(baseline),
        "variant_rows": len(variant),
        "ab_csv": ab_csv,
    }


def main() -> None:
    if hasattr(os.sys.stdout, "reconfigure"):
        os.sys.stdout.reconfigure(encoding="utf-8")

    _ensure_dirs()

    s1 = _sprint1_index()
    _write_json(LOGS_ROOT / "sprint1" / "index_report.json", s1)

    s2 = _sprint2_baseline_answers()
    _write_json(LOGS_ROOT / "sprint2" / "baseline_answers.json", s2)

    s3 = _sprint3_retrieval_debug()
    _write_json(LOGS_ROOT / "sprint3" / "retrieval_debug.json", s3)

    s4 = _sprint4_eval()
    _write_json(LOGS_ROOT / "sprint4" / "eval_run.json", s4)

    (RESULTS_ROOT / "sprint1" / "README.txt").write_text(
        "Sprint 1 outputs are mainly under logs/sprint1/index_report.json\n",
        encoding="utf-8",
    )
    (RESULTS_ROOT / "sprint2" / "README.txt").write_text(
        "Sprint 2 outputs are mainly under logs/sprint2/baseline_answers.json\n",
        encoding="utf-8",
    )
    (RESULTS_ROOT / "sprint3" / "README.txt").write_text(
        "Sprint 3 outputs are mainly under logs/sprint3/retrieval_debug.json\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

