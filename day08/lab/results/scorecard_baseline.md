# Scorecard: Baseline (Dense)

Generated: 2026-04-13 17:11
Config: `retrieval_mode=dense | top_k_search=10 | top_k_select=3 | use_rerank=False | threshold=0.15`

## Summary

| Metric | Average Score |
|--------|:------------:|
| Faithfulness | 4.90/5 |
| Relevance | 4.20/5 |
| Context Recall | 4.44/5 |
| Completeness | 4.10/5 |

## Per-Question Results (grading_questions.json)

| ID | Kỹ năng RAG | F | R | Rc | C | Verdict | Điểm | Notes |
|----|-------------|---|---|----|----|---------|:----:|-------|
| gq01 | Freshness & version | 5 | 5 | 5 | 5 | Full | 10/10 | Nêu đúng 6h→4h, cite v2026.1 |
| gq02 | Multi-doc synthesis | 5 | 4 | 4 | 4 | Partial | 5/10 | Đúng nội dung nhưng chỉ cite [1], thiếu citation từ 2 nguồn |
| gq03 | Exception completeness | 5 | 5 | 5 | 5 | Full | 10/10 | Nêu đủ 2 ngoại lệ Flash Sale + kích hoạt |
| gq04 | Numeric fact | 5 | 4 | 5 | 4 | Partial | 4/8 | Đúng 110% nhưng thiếu citation rõ từ Điều 5 |
| gq05 | Multi-section retrieval | 4 | 1 | 2 | 1 | Zero | 0/10 | **Abstain sai** — chunk score < threshold, pipeline từ chối dù doc có info |
| gq06 | Cross-doc multi-hop | 5 | 4 | 4 | 4 | Partial | 6/12 | Đúng quy trình escalation, thiếu ext. 9999 |
| gq07 | Abstain / anti-hallucination | 5 | 5 | None | 5 | Full | 10/10 | Abstain đúng, không bịa mức phạt |
| gq08 | Disambiguation | 5 | 5 | 5 | 5 | Full | 10/10 | Phân biệt rõ 2 ngữ cảnh "3 ngày" |
| gq09 | Multi-detail FAQ | 5 | 4 | 5 | 3 | Partial | 4/8 | Đúng 90 ngày + 7 ngày nhắc, thiếu URL SSO/ext. 9000 |
| gq10 | Temporal scoping | 5 | 5 | 5 | 5 | Full | 10/10 | Nêu đúng effective_date, phân biệt v3/v4 |

## Tổng kết

- **Raw score:** 69/98
- **Quy đổi 30 điểm:** 69/98 × 30 = **21.1/30**
- **Full:** 5 | **Partial:** 4 | **Zero:** 1
- **Hallucination:** 0

### Điểm yếu chính
1. `gq05` — Abstain sai do `WEAK_CONTEXT_SCORE_THRESHOLD=0.15` quá cao, chunk về "contractor" + "Admin Access" bị reject trước khi tới LLM.
2. `gq09` — Thiếu chi tiết URL/ext vì `top_k_select=3` quá ít, FAQ chunk với thông tin reset password không lọt top 3.
3. `gq02` — LLM gom citation vào [1] dù info đến từ 2 doc khác nhau.
