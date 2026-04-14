"""
A/B Comparison: Baseline (baseline_dense) vs Variant (variant_hybrid_rerank)
Reads from results/ab_comparison.csv and prints a comparison table
matching the required schema:
  - Summary: Metric | Baseline | Variant | Delta
  - Per-question: Câu | Baseline F/R/Rc/C | Variant F/R/Rc/C | Better?
"""

import csv
from collections import defaultdict

CSV_PATH = "results/ab_comparison.csv"

METRICS = ["faithfulness", "relevance", "context_recall", "completeness"]
METRIC_LABELS = {
    "faithfulness": "faithfulness",
    "relevance": "relevance",
    "context_recall": "context_recall",
    "completeness": "completeness",
}

BASELINE_LABEL = "baseline_dense"
VARIANT_LABEL  = "variant_hybrid_rerank"

# ── Load CSV ──────────────────────────────────────────────────────────────────
rows = defaultdict(dict)  # rows[(id, config_label)] = row dict

with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        key = (row["id"], row["config_label"])
        rows[key] = row

# Collect all question IDs (preserve insertion order)
seen_ids = []
for (qid, label) in rows:
    if qid not in seen_ids:
        seen_ids.append(qid)

# ── Build per-question data ───────────────────────────────────────────────────
per_q = []
for qid in seen_ids:
    base = rows.get((qid, BASELINE_LABEL), {})
    var  = rows.get((qid, VARIANT_LABEL), {})

    def safe_int(d, k):
        try:
            return int(d[k])
        except (KeyError, ValueError, TypeError):
            return None

    bf = safe_int(base, "faithfulness")
    br = safe_int(base, "relevance")
    brc = safe_int(base, "context_recall")
    bc = safe_int(base, "completeness")

    vf = safe_int(var, "faithfulness")
    vr = safe_int(var, "relevance")
    vrc = safe_int(var, "context_recall")
    vc = safe_int(var, "completeness")

    def score(f, r, rc, c):
        vals = [x for x in [f, r, rc, c] if x is not None]
        return sum(vals) / len(vals) if vals else 0

    base_score = score(bf, br, brc, bc)
    var_score  = score(vf, vr, vrc, vc)

    if var_score > base_score:
        better = "Variant"
    elif base_score > var_score:
        better = "Baseline"
    else:
        better = "Tie"

    def fmt(f, r, rc, c):
        def s(x): return str(x) if x is not None else "N/A"
        return f"{s(f)}/{s(r)}/{s(rc)}/{s(c)}"

    per_q.append({
        "id": qid,
        "base_fmt": fmt(bf, br, brc, bc),
        "var_fmt":  fmt(vf, vr, vrc, vc),
        "better":   better,
        "base_scores": (bf, br, brc, bc),
        "var_scores":  (vf, vr, vrc, vc),
    })

# ── Compute summary averages ──────────────────────────────────────────────────
def avg_metric(label, metric):
    vals = []
    for qid in seen_ids:
        row = rows.get((qid, label), {})
        try:
            vals.append(int(row[metric]))
        except (KeyError, ValueError, TypeError):
            pass
    return sum(vals) / len(vals) if vals else 0.0

summary = []
for m in METRICS:
    b = avg_metric(BASELINE_LABEL, m)
    v = avg_metric(VARIANT_LABEL,  m)
    delta = v - b
    if abs(delta) < 0.005:
        delta_str = "N/A"
    else:
        delta_str = f"{delta:+.2f}"
    summary.append((METRIC_LABELS[m], b, v, delta_str))

# ── Print ─────────────────────────────────────────────────────────────────────
W = 70
print("=" * W)
print("A/B Comparison: Baseline vs Variant")
print("=" * W)
print(f"{'Metric':<24}{'Baseline':>10}{'Variant':>10}{'Delta':>10}")
print("-" * W)
for label, b, v, d in summary:
    print(f"{label:<24}{b:>10.2f}{v:>10.2f}{d:>10}")

print()
print(f"{'Câu':<8}{'Baseline F/R/Rc/C':<22}{'Variant F/R/Rc/C':<22}{'Better?'}")
print("-" * W)
for q in per_q:
    print(f"{q['id']:<8}{q['base_fmt']:<22}{q['var_fmt']:<22}{q['better']}")

print()
# Winner summary
variant_wins  = sum(1 for q in per_q if q["better"] == "Variant")
baseline_wins = sum(1 for q in per_q if q["better"] == "Baseline")
ties          = sum(1 for q in per_q if q["better"] == "Tie")
print(f"Variant wins: {variant_wins}  |  Baseline wins: {baseline_wins}  |  Ties: {ties}")
print("=" * W)
