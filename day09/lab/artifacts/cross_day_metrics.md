# Cross-Day Metrics Bridge (Day08 -> Day09)

Generated: 2026-04-14T12:41:49.941738

## Conversion notes
- Day08 confidence is converted from 1-5 metrics using weighted normalization.
- When Day08 context_recall is missing (no expected source), recall bridge rewards safe abstain.
- Additional cross-day tests are heuristic and intended for comparative trend analysis.

## Aligned metrics
| Metric | Day08 (single) | Day09 (multi) | Delta (Day09-Day08) |
|---|---:|---:|---:|
| avg_confidence | 0.754 | 0.851 | 0.097 |
| avg_latency_ms | 3977.624 | 1078.467 | -2899.157 |
| answered_rate_percent | 100.0 | 100.0 | 0.0 |
| abstain_rate_percent | 30.0 | 6.67 | -23.33 |
| citation_rate_percent | 20.0 | 93.33 | 73.33 |
| source_recall_rate_percent | 100.0 | 100.0 | 0.0 |
| numeric_consistency_rate_percent | 64.58 | 63.78 | -0.8 |
| mcp_usage_rate_percent | 0.0 | 40.0 | 40.0 |
| hitl_rate_percent | 0.0 | 6.67 | 6.67 |
| route_accuracy_percent | None | 100.0 | None |

## Additional tests
### Day08
| Test | Applicable | Passed/Total | Pass rate % |
|---|---|---|---:|
| abstain_behavior | True | 0/1 | 0.0 |
| citation_presence | True | 2/9 | 22.22 |
| source_coverage_full | True | 9/9 | 100.0 |
| numeric_fidelity | True | 4/8 | 50.0 |
| multi_hop_support | False | 0/0 | None |
| route_correctness | False | 0/0 | None |

### Day09
| Test | Applicable | Passed/Total | Pass rate % |
|---|---|---|---:|
| abstain_behavior | True | 1/1 | 100.0 |
| citation_presence | True | 14/14 | 100.0 |
| source_coverage_full | True | 14/14 | 100.0 |
| numeric_fidelity | True | 6/15 | 40.0 |
| multi_hop_support | True | 3/3 | 100.0 |
| route_correctness | True | 15/15 | 100.0 |
