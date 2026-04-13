# Scorecard: baseline_dense
Generated: 2026-04-13 17:56

## Summary

| Metric | Average Score |
|--------|--------------|
| Faithfulness | 3.60/5 |
| Relevance | 3.40/5 |
| Context Recall | 5.00/5 |
| Completeness | 2.70/5 |

## Per-Question Results

| ID | Category | Faithful | Relevant | Recall | Complete | Latency ms | Answered | Notes |
|----|----------|----------|----------|--------|----------|-----------|----------|-------|
| gq01 | SLA | 1 | 5 | 5 | 1 | 15308.111900001677 | True | token_overlap=0.12, unsupported_numbers=[] |
| gq02 | Cross-Document | 5 | 2 | 5 | 5 | 2926.706299997022 | True | token_overlap=1.00, unsupported_numbers=['1'] |
| gq03 | Refund | 5 | 1 | 5 | 1 | 2977.5613999991037 | True | token_overlap=1.00, unsupported_numbers=['1'] |
| gq04 | Refund | 4 | 4 | 5 | 5 | 3175.2534000006563 | True | token_overlap=0.82, unsupported_numbers=[] |
| gq05 | Access Control | 2 | 1 | 5 | 1 | 3531.362800000352 | True | token_overlap=0.50, unsupported_numbers=[] |
| gq06 | Cross-Document | 5 | 4 | 5 | 3 | 3579.4695999975374 | True | token_overlap=0.89, unsupported_numbers=[] |
| gq07 | Insufficient Context | 1 | 2 | None | 1 | 2873.5035999998217 | True | token_overlap=0.38, unsupported_numbers=['1'] |
| gq08 | HR Policy | 5 | 5 | 5 | 5 | 3242.1962000007625 | True | token_overlap=0.88, unsupported_numbers=[] |
| gq09 | IT Helpdesk | 5 | 5 | 5 | 2 | 2918.4879000022192 | True | token_overlap=1.00, unsupported_numbers=[] |
| gq10 | Refund | 3 | 5 | 5 | 3 | 3517.403400001058 | True | token_overlap=0.59, unsupported_numbers=[] |

## Speed & Coverage

- Average latency: 4405 ms
- Answered rate: 100.0%
