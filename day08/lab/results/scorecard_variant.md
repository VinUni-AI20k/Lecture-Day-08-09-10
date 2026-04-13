# Scorecard: variant_hybrid_only
Generated: 2026-04-13 15:45
Config: retrieval_mode=hybrid | top_k_search=10 | top_k_select=3 | use_rerank=False
Single variable changed vs baseline: retrieval_mode (dense → hybrid)

## Summary

| Metric | Average Score |
|--------|--------------|
| Faithfulness | 5.00/5 |
| Relevance | 3.80/5 |
| Context Recall | 5.00/5 |
| Completeness | 4.00/5 |

## Per-Question Results

| ID | Category | Faithful | Relevant | Recall | Complete | Notes |
|----|----------|----------|----------|--------|----------|-------|
| q01 | SLA | 5 | 5 | 5 | 5 | Hybrid dense+BM25 lấy đúng chunk SLA P1. Citation [1] đầy đủ. |
| q02 | Refund | 5 | 5 | 5 | 5 | Hybrid tìm đúng chunk refund policy. Grounded hoàn toàn. |
| q03 | Access Control | 5 | 5 | 5 | 5 | RRF kết hợp 'Level 3' keyword từ BM25 + semantic từ dense. |
| q04 | Refund | 5 | 5 | 5 | 5 | Câu trả lời grounded, nêu đúng ngoại lệ kỹ thuật số. |
| q05 | IT Helpdesk | 5 | 5 | 5 | 5 | BM25 + dense đều trỏ về helpdesk-faq. Không sai lệch. |
| q06 | SLA | 5 | 5 | 5 | 5 | Hybrid kéo về cả chunk escalation lẫn temporary access. |
| q07 | Access Control | 5 | 5 | 5 | 4 | BM25 tìm được 'Approval Matrix' dù tên tài liệu đã đổi — lợi thế hybrid. Completeness=4: chưa nêu rõ đây là tên mới. |
| q08 | HR Policy | 5 | 5 | 5 | 5 | Câu trả lời đầy đủ, có citation. |
| q09 | Insufficient Context | 5 | 1 | None | 2 | Abstain đúng. Không bịa. Thiếu gợi ý liên hệ IT Helpdesk. |
| q10 | Refund | 5 | 1 | 5 | 1 | Abstain đúng — không bịa quy trình VIP. Completeness=1 vì không nêu được "không có quy trình đặc biệt". |

## Comparison vs Baseline (dense)

| Metric | Baseline | Variant | Delta |
|--------|:--------:|:-------:|:-----:|
| Faithfulness | 5.00 | 5.00 | 0.00 |
| Relevance | 4.20 | 3.80 | −0.40 |
| Context Recall | 5.00 | 5.00 | 0.00 |
| Completeness | 4.20 | 4.00 | −0.20 |

**Kết luận:** Baseline dense thắng về Relevance và Completeness. Hybrid có lợi thế ở q07 (alias query)
nhưng không đủ bù noise từ BM25 ở các câu hỏi tự nhiên. Giữ dense làm production config.
