from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = BASE_DIR / "results"
LOGS_DIR = BASE_DIR / "logs"


def main() -> None:
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    sys.path.insert(0, str(BASE_DIR))
    import eval as eval_mod

    config = {
        "retrieval_mode": "hybrid",
        "top_k_search": 20,
        "top_k_select": 3,
        "use_rerank": True,
        "label": "hybrid_rerank",
    }

    with open(eval_mod.TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        test_questions = eval_mod.json.load(f)

    results = eval_mod.run_scorecard(config, test_questions=test_questions, verbose=True)
    md = eval_mod.generate_scorecard_summary(results, config["label"])

    out_path = RESULTS_DIR / "scorecard_hybrid_rerank.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"\nWrote hybrid+rerank scorecard: {out_path}")

    src_log = LOGS_DIR / f"grading_run_{config['label']}.json"
    if src_log.exists():
        dst_log = LOGS_DIR / "grading_run_hybrid_rerank.json"
        dst_log.write_text(src_log.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Wrote hybrid+rerank grading log copy: {dst_log}")


if __name__ == "__main__":
    main()

