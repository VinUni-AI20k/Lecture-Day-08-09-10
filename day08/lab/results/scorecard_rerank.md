# Scorecard: variant_rerank
Generated: 2026-04-13 17:24

## Summary

| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.20/5 |
| Relevance | 4.50/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.70/5 |

## Per-Question Results

| ID | Category | Faithful | Relevant | Recall | Complete | Latency ms | Answered | Notes |
|----|----------|----------|----------|--------|----------|-----------|----------|-------|
| q01 | SLA | 4 | 4 | 5 | 2 | 11173.523900000873 | True | token_overlap=0.80, unsupported_numbers=[] |
| q02 | Refund | 5 | 5 | 5 | 5 | 3276.9409000029555 | True | token_overlap=0.94, unsupported_numbers=[] |
| q03 | Access Control | 5 | 5 | 5 | 5 | 6389.457599998423 | True | token_overlap=1.00, unsupported_numbers=[] |
| q04 | Refund | 5 | 5 | 5 | 1 | 5263.533299999835 | True | token_overlap=1.00, unsupported_numbers=['1'] |
| q05 | IT Helpdesk | 5 | 5 | 5 | 5 | 4549.44130000149 | True | token_overlap=1.00, unsupported_numbers=[] |
| q06 | SLA | 5 | 3 | 5 | 5 | 6756.911399999808 | True | token_overlap=0.86, unsupported_numbers=[] |
| q07 | Access Control | 2 | 4 | 5 | 3 | 4382.229699996969 | True | token_overlap=0.52, unsupported_numbers=[] |
| q08 | HR Policy | 5 | 5 | 5 | 5 | 6512.4395999991975 | True | token_overlap=0.88, unsupported_numbers=[] |
| q09 | Insufficient Context | 3 | 4 | None | 5 | 6300.252699998964 | True | token_overlap=0.09, unsupported_numbers=['403'] |
| q10 | Refund | 3 | 5 | 5 | 1 | 4424.585000000661 | True | token_overlap=0.56, unsupported_numbers=[] |

## Speed & Coverage

- Average latency: 5903 ms
- Answered rate: 100.0%
