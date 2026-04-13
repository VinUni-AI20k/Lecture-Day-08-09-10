"""
compare_modes.py - So sanh so lieu Dense vs Sparse vs Hybrid vs HyDE vs Multi-Query
Chay: python compare_modes.py
"""

import json
from pathlib import Path

from eval import generate_scorecard_summary, run_scorecard

TEST_QUESTIONS_PATH = Path("data/test_questions.json")
BASELINE_LABEL = "dense"

CONFIGS = [
    {
        "retrieval_mode": "dense",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": True,
        "label": "dense",
    },
    {
        "retrieval_mode": "sparse",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": True,
        "label": "sparse",
    },
    {
        "retrieval_mode": "hybrid",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": True,
        "label": "hybrid",
    },
    {
        "retrieval_mode": "hyde",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": True,
        "label": "hyde",
    },
    {
        "retrieval_mode": "multi_query",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": True,
        "label": "multi_query",
    },
]

METRICS = ["faithfulness", "relevance", "context_recall", "completeness"]

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
B = "\033[94m"
BOLD = "\033[1m"
X = "\033[0m"

MODE_DESCRIPTIONS = {
    "dense": "embed query truc tiep",
    "sparse": "BM25 keyword retrieval",
    "hybrid": "dense + BM25 + RRF",
    "hyde": "LLM sinh hypothetical answer -> embed -> hybrid RRF",
    "multi_query": "LLM tao nhieu query paraphrase -> fusion",
}


def avg(results, metric):
    scores = [r[metric] for r in results if r.get(metric) is not None]
    return sum(scores) / len(scores) if scores else 0.0


def color_delta(d):
    if d > 0.05:
        return f"{G}+{d:.2f}{X}"
    if d < -0.05:
        return f"{R}{d:.2f}{X}"
    return f"{Y}{d:+.2f}{X}"


def pct_change(new_val, base_val):
    if abs(base_val) < 1e-9:
        return "n/a"
    diff = (new_val - base_val) / base_val * 100
    trend = "tang" if diff > 0 else "giam"
    return f"{abs(diff):.1f}% {trend}"


def run():
    with open(TEST_QUESTIONS_PATH, encoding="utf-8") as f:
        questions = json.load(f)

    labels = [cfg["label"] for cfg in CONFIGS]
    delta_labels = [label for label in labels if label != BASELINE_LABEL]

    all_results = {}
    for cfg in CONFIGS:
        label = cfg["label"]
        print(f"\nDang chay {label.upper()}...")
        all_results[label] = run_scorecard(config=cfg, test_questions=questions, verbose=False)

    print("\n" + "=" * 100)
    print(f"{BOLD}  BANG SO LIEU: DENSE vs SPARSE vs HYBRID vs HYDE vs MULTI_QUERY{X}")
    print("=" * 100)

    mode_col = 12
    delta_col = 15
    header = f"  {'Metric':<18}"
    for label in labels:
        header += f"  {label.upper():^{mode_col}}"
    for label in delta_labels:
        header += f"  {label.upper()}-DENSE".center(delta_col + 2)
    print(BOLD + header + X)
    print("  " + "-" * (18 + (mode_col + 2) * len(labels) + (delta_col + 2) * len(delta_labels)))

    for metric in METRICS:
        scores = {label: avg(all_results[label], metric) for label in labels}
        row = f"  {metric:<18}"
        for label in labels:
            row += f"  {scores[label]:.2f}/5".ljust(mode_col + 2)
        for label in delta_labels:
            row += f"  {color_delta(scores[label] - scores[BASELINE_LABEL]):^{delta_col}}"
        print(row)

    print("  " + "-" * (18 + (mode_col + 2) * len(labels) + (delta_col + 2) * len(delta_labels)))
    overall = {
        label: sum(avg(all_results[label], metric) for metric in METRICS) / len(METRICS)
        for label in labels
    }

    row = f"  {BOLD}{'TRUNG BINH':<18}{X}"
    for label in labels:
        row += f"  {BOLD}{overall[label]:.2f}/5{X}".ljust(mode_col + 2)
    for label in delta_labels:
        row += f"  {color_delta(overall[label] - overall[BASELINE_LABEL]):^{delta_col}}"
    print(row)

    print("\n" + "=" * 100)
    print(f"{BOLD}  TUNG CAU - COMPLETENESS{X}")
    print("=" * 100)

    q_header = f"  {'ID':<10}"
    for label in labels:
        q_header += f"  {label:^9}"
    q_header += "  winner"
    print(BOLD + q_header + X)
    print("  " + "-" * (14 + 11 * len(labels) + 10))

    def fmt(v):
        if v is None:
            return "   -    "
        return f" {v}/5 ".ljust(9)

    for q in questions:
        qid = q["id"]
        row_scores = {}
        for label in labels:
            result = next((x for x in all_results[label] if x["id"] == qid), None)
            row_scores[label] = result["completeness"] if result else None

        vals = {k: v for k, v in row_scores.items() if v is not None}
        if vals:
            best_score = max(vals.values())
            winners = [k for k, v in vals.items() if v == best_score]
            winner_str = " & ".join(winners) if len(winners) < len(labels) else "tie"
            if len(winners) == 1 and winners[0] != BASELINE_LABEL:
                winner_color = G
            elif len(winners) == 1:
                winner_color = B
            else:
                winner_color = Y
        else:
            winner_str = "?"
            winner_color = X

        line = f"  {qid:<10}"
        for label in labels:
            line += f"  {fmt(row_scores[label])}"
        line += f"  {winner_color}{winner_str}{X}"
        print(line)

    print("\n" + "=" * 100)
    print(f"{BOLD}  KET LUAN{X}")
    print("=" * 100)

    best_mode = max(overall, key=overall.get)
    worst_mode = min(overall, key=overall.get)

    print(f"\n  Mode tot nhat : {G}{BOLD}{best_mode.upper()}{X} ({overall[best_mode]:.2f}/5)")
    print(f"  Mode kem nhat : {R}{worst_mode.upper()}{X} ({overall[worst_mode]:.2f}/5)")

    for label in delta_labels:
        delta = overall[label] - overall[BASELINE_LABEL]
        print(
            f"  {label.upper():<12} vs DENSE: {color_delta(delta)} "
            f"({pct_change(overall[label], overall[BASELINE_LABEL])})"
        )

    print("\n  -> Bien thay doi duy nhat (A/B Rule): retrieval_mode")
    for label in labels:
        print(f"     {label}='{MODE_DESCRIPTIONS.get(label, 'n/a')}'")

    Path("results").mkdir(exist_ok=True)
    for label in labels:
        scorecard_md = generate_scorecard_summary(all_results[label], f"variant_{label}")
        output_path = Path(f"results/scorecard_variant_{label}.md")
        output_path.write_text(scorecard_md, encoding="utf-8")
    print("\n  Da luu scorecard tung mode vao thu muc results/")
    print("=" * 100)


if __name__ == "__main__":
    run()

