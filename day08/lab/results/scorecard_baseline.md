# Scorecard: baseline_dense
Generated: 2026-04-13 16:37

## Summary

| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.20/5 |
| Answer Relevance | 4.70/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.50/5 |

## Quick Notes

- Config label: `baseline_dense`
- Weakest questions: q09, q04, q07
- Strongest questions: q06, q05, q03

## Per-Question Results

| ID | Category | Faithful | Relevant | Recall | Complete | Notes |
|----|----------|----------|----------|--------|----------|-------|
| q01 | SLA | 5 | 5 | 5 | 3 | The answer is fully supported by the retrieved chunks, which state that the init |
| q02 | Refund | 4 | 5 | 5 | 4 | The answer is mostly supported by the retrieved chunks, but it omits the term 'l |
| q03 | Access Control | 5 | 5 | 5 | 5 | The answer is fully supported by the retrieved chunks, which explicitly state th |
| q04 | Refund | 2 | 4 | 5 | 2 | The answer does not reflect the information in the retrieved chunks, which clear |
| q05 | IT Helpdesk | 5 | 5 | 5 | 5 | The answer is directly supported by the retrieved chunk, which states the same f |
| q06 | SLA | 5 | 5 | 5 | 5 | The answer is fully supported by the retrieved chunks, specifically stating that |
| q07 | Access Control | 4 | 5 | 5 | 3 | The answer correctly identifies the document as 'it/access-control-sop.md', but  |
| q08 | HR Policy | 5 | 5 | 5 | 4 | The answer is fully supported by the retrieved chunks, specifically stating that |
| q09 | Insufficient Context | 2 | 3 | None | 2 | The answer states insufficient data, which is partially true, but it fails to ac |
| q10 | Refund | 5 | 5 | 5 | 2 | The answer correctly states that there is insufficient data to determine if the  |
