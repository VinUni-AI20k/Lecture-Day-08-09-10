"""
ablation.py — Chạy A/B single-variable để chọn variant tốt nhất theo đúng luật đề bài.

Baseline: dense, top_k_search=10, top_k_select=3, use_rerank=False
Variant A (Hybrid-only):   đổi retrieval_mode  → hybrid
Variant B (Rerank-only):   đổi use_rerank      → True

Mỗi variant khác baseline ĐÚNG 1 biến. Kết quả dùng cho docs/tuning-log.md.
"""

import json
from pathlib import Path

from eval import (
    BASELINE_CONFIG,
    TEST_QUESTIONS_PATH,
    RESULTS_DIR,
    run_scorecard,
    generate_scorecard_summary,
    compare_ab,
)

VARIANT_A = {
    "retrieval_mode": "hybrid",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,
    "label": "variant_A_hybrid_only",
}

VARIANT_B = {
    "retrieval_mode": "dense",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": True,
    "label": "variant_B_rerank_only",
}


def _avg(results, key):
    vals = [r[key] for r in results if r.get(key) is not None]
    return sum(vals) / len(vals) if vals else None


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        qs = json.load(f)

    runs = {}
    for cfg in [BASELINE_CONFIG, VARIANT_A, VARIANT_B]:
        print(f"\n{'='*60}\nRunning: {cfg['label']}\n{'='*60}")
        res = run_scorecard(config=cfg, test_questions=qs, verbose=True)
        md = generate_scorecard_summary(res, cfg["label"])
        (RESULTS_DIR / f"scorecard_{cfg['label']}.md").write_text(md, encoding="utf-8")
        runs[cfg["label"]] = res

    print("\n" + "=" * 70)
    print("ABLATION SUMMARY — mỗi variant đổi ĐÚNG 1 biến so với baseline")
    print("=" * 70)
    header = f"{'Metric':<18}{'Baseline':>12}{'A: Hybrid':>12}{'B: Rerank':>12}"
    print(header)
    print("-" * len(header))
    for m in ["faithfulness", "relevance", "context_recall", "completeness"]:
        row = [m]
        for lbl in [BASELINE_CONFIG["label"], VARIANT_A["label"], VARIANT_B["label"]]:
            v = _avg(runs[lbl], m)
            row.append(f"{v:.2f}" if v is not None else "N/A")
        print(f"{row[0]:<18}{row[1]:>12}{row[2]:>12}{row[3]:>12}")

    print("\nA/B Comparison — Baseline vs A (Hybrid-only):")
    compare_ab(runs[BASELINE_CONFIG["label"]], runs[VARIANT_A["label"]],
               output_csv="ab_A_hybrid.csv")
    print("\nA/B Comparison — Baseline vs B (Rerank-only):")
    compare_ab(runs[BASELINE_CONFIG["label"]], runs[VARIANT_B["label"]],
               output_csv="ab_B_rerank.csv")


if __name__ == "__main__":
    main()
