# Scorecard: Variant (Dense Optimized)

Generated: 2026-04-13 17:40
Config: `retrieval_mode=dense | top_k_search=20 | top_k_select=8 | use_rerank=False | threshold=0.05`
Single-variable changes vs baseline: `top_k_select` (3→8), `top_k_search` (10→20), `threshold` (0.15→0.05), prompt rules improved

## Summary

| Metric | Average Score |
|--------|:------------:|
| Faithfulness | 5.00/5 |
| Relevance | 5.00/5 |
| Context Recall | 4.89/5 |
| Completeness | 4.70/5 |

## Per-Question Results (grading_questions.json)

| ID | Kỹ năng RAG | F | R | Rc | C | Verdict | Điểm | Notes |
|----|-------------|---|---|----|----|---------|:----:|-------|
| gq01 | Freshness & version | 5 | 5 | 5 | 5 | Full | 10/10 | Prompt "stay focused" loại bỏ info thừa v2025.3 |
| gq02 | Multi-doc synthesis | 5 | 5 | 5 | 4 | Partial | 5/10 | Đúng VPN + 2 thiết bị, vẫn gom citation [1] |
| gq03 | Exception completeness | 5 | 5 | 5 | 5 | Full | 10/10 | Nêu đủ cả 2 ngoại lệ với citation |
| gq04 | Numeric fact | 5 | 5 | 5 | 4 | Partial | 4/8 | Đúng 110%, tùy chọn, nhưng judge đòi tên Điều 5 |
| gq05 | Multi-section retrieval | 5 | 5 | 5 | 5 | Full | 10/10 | **FIX:** k_select=8 kéo cả Section 1 (scope) + Section 2 (Level 4) |
| gq06 | Cross-doc multi-hop | 5 | 5 | 4 | 4 | Partial | 6/12 | Đúng quy trình, vẫn thiếu ext. 9999 (chunk rank thấp) |
| gq07 | Abstain / anti-hallucination | 5 | 5 | None | 5 | Full | 10/10 | Abstain đúng, không bịa |
| gq08 | Disambiguation | 5 | 5 | 5 | 5 | Full | 10/10 | Phân biệt rõ ràng, citation đầy đủ |
| gq09 | Multi-detail FAQ | 5 | 5 | 5 | 5 | Full | 8/8 | **FIX:** k_select=8 kéo được chunk SSO URL + ext. 9000 |
| gq10 | Temporal scoping | 5 | 5 | 5 | 5 | Full | 10/10 | Nêu rõ effective_date, phân biệt v3/v4 |

## Tổng kết

- **Raw score:** 83/98
- **Quy đổi 30 điểm:** 83/98 × 30 = **25.4/30**
- **Full:** 7 | **Partial:** 3 | **Zero:** 0
- **Hallucination:** 0

### Cải thiện so với Baseline
1. `gq05`: Zero → **Full** (+10 điểm) — threshold=0.05 + k_select=8 giải quyết false abstain.
2. `gq09`: Partial → **Full** (+4 điểm) — k_select=8 kéo được FAQ URL chunk.
3. `gq01`: Giữ Full — prompt "stay focused" không thêm info thừa.
4. Tổng cộng: +14 raw points, từ 21.1 lên **25.4/30**.

## Comparison vs Baseline

| Metric | Baseline | Variant | Delta |
|--------|:--------:|:-------:|:-----:|
| Faithfulness | 4.90 | **5.00** | +0.10 |
| Relevance | 4.20 | **5.00** | **+0.80** |
| Context Recall | 4.44 | **4.89** | +0.44 |
| Completeness | 4.10 | **4.70** | **+0.60** |

**Kết luận:** Variant thắng ở mọi metric. top_k_select=8 cho coverage tốt hơn cho câu cross-doc/multi-section. Prompt cải thiện giúp LLM extract đúng detail hơn.
