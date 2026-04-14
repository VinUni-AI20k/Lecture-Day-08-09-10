# Day08 Baseline Run Report (dense)

Generated on: 2026-04-14

## What I ran

- `python index.py`
- `python eval.py` (baseline config: `baseline_dense`)

## Baseline config

```json
{
  "retrieval_mode": "dense",
  "top_k_search": 10,
  "top_k_select": 3,
  "use_rerank": false,
  "label": "baseline_dense"
}
```

## Key results (baseline)

Source: `results/scorecard_baseline.md`

| Metric | Average |
|--------|---------|
| Faithfulness | 5.00/5 |
| Relevance | 2.80/5 |
| Context Recall | 4.60/5 |
| Completeness | 2.60/5 |

## Output files to review

- **Scorecard (Markdown)**: `results/scorecard_baseline.md`
- **Full grading log (JSON)**: `logs/grading_run_baseline_dense.json`
- **A/B comparison CSV (also produced by eval)**: `results/ab_comparison.csv`

## Notes

- The baseline is **very grounded** (Faithfulness 5.0) and retrieves expected sources well (Context Recall 4.6), but **answer quality is often incomplete / over-abstains**, which drags down Relevance and Completeness.

