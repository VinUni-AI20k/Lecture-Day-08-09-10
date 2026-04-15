import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
TEST_QUESTIONS_PATH = BASE_DIR / "data" / "test_questions.json"
LOGS_DIR = BASE_DIR / "logs" / "test"
RESULTS_DIR = BASE_DIR / "results" / "test"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def main() -> None:
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    sys.path.insert(0, str(BASE_DIR))
    from rag_answer import rag_answer

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    questions = json.loads(TEST_QUESTIONS_PATH.read_text(encoding="utf-8"))

    config = {
        "retrieval_mode": "hybrid",
        "top_k_search": 20,
        "top_k_select": 3,
        "use_rerank": True,
        "label": "test_hybrid_rerank",
    }

    run = []
    for q in questions:
        r = rag_answer(
            query=q["question"],
            retrieval_mode=config["retrieval_mode"],
            top_k_search=config["top_k_search"],
            top_k_select=config["top_k_select"],
            use_rerank=config["use_rerank"],
            verbose=False,
        )
        run.append(
            {
                "id": q["id"],
                "question": q["question"],
                "answer": r["answer"],
                "sources": r["sources"],
                "chunks_retrieved": len(r["chunks_used"]),
                "retrieval_mode": r["config"]["retrieval_mode"],
                "use_rerank": r["config"]["use_rerank"],
                "timestamp": now(),
            }
        )

    log_path = LOGS_DIR / "hybrid_rerank_run.json"
    log_path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# Test: hybrid + rerank")
    lines.append(f"Generated: {now()}")
    lines.append("")
    lines.append("Config:")
    lines.append("```")
    for k, v in config.items():
        lines.append(f"{k} = {v}")
    lines.append("```")
    lines.append("")
    lines.append("| ID | Sources | Answer (preview) |")
    lines.append("|----|---------|------------------|")
    for row in run:
        preview = (row["answer"] or "").replace("\n", " ")
        if len(preview) > 140:
            preview = preview[:140] + "..."
        lines.append(f"| {row['id']} | {', '.join(row['sources'])} | {preview} |")

    summary_path = RESULTS_DIR / "hybrid_rerank_summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote log: {log_path}")
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    main()

