# Tuning Log — RAG Pipeline (Day 08 Lab)

> Ghi lại mỗi thay đổi và kết quả quan sát được.  
> A/B Rule: chỉ đổi **một biến** mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = Groq llama-3.1-8b-instant / fallback gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 3.90 /5 |
| Answer Relevance | 4.60 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 3.20 /5 |
| Avg latency | 3805 ms |
| % Questions Answered | 100.0% |

**Câu hỏi yếu nhất (điểm thấp):**
> q01 và q10 thấp ở completeness vì thiếu các chi tiết số học quan trọng (15 phút, 7 ngày, 3-5 ngày).  
> q06 thấp ở relevance/completeness vì answer kéo sang quy trình escalation khác, không khớp expected answer.  
> q07 thấp ở faithfulness/completeness vì answer quá thận trọng, chưa nêu rõ tên mới của tài liệu.

**Giả thuyết nguyên nhân (Error Tree):**
- [x] Indexing: Chunking cắt giữa điều khoản
- [x] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [x] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding
- [x] Generation: Context quá dài → lost in the middle

---

## Variant 1 — Hybrid RRF

**Ngày:** 2026-04-13  
**Biến thay đổi:** Hybrid RRF retrieval (dense + sparse, no rerank)  
**Lý do chọn biến này:**
> Chọn hybrid vì corpus có cả ngôn ngữ tự nhiên (policy, FAQ) lẫn tên riêng/mã lỗi/alias (Approval Matrix, ERR-403, P1). Hybrid giữ recall tốt mà không cần thêm reranker nặng hoặc query rewrite LLM, nên là biến cải thiện tốt nhất theo cost/token.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
dense_weight = 0.8
sparse_weight = 0.2
top_k_search = 10
top_k_select = 3
use_rerank = False
```

**Baseline vs Variant:**
| Metric | Baseline | Hybrid | Delta |
|--------|----------|--------|-------|
| Faithfulness | 3.90/5 | 3.80/5 | -0.10 |
| Answer Relevance | 4.60/5 | 4.60/5 | +0.00 |
| Context Recall | 5.00/5 | 5.00/5 | +0.00 |
| Completeness | 3.20/5 | 2.80/5 | -0.40 |
| Avg latency | 3805 ms | 4191 ms | +387 ms |
| % Questions Answered | 100.0% | 100.0% | +0.0% |

**Nhận xét:**
> Hybrid không khác baseline quá xa vì dense baseline đã đạt context recall 5/5 trên toàn bộ test set; khác biệt chủ yếu nằm ở cách sắp xếp và grounding của câu trả lời.

**Kết luận:**
> Hybrid không phải là biến tốt nhất ở bộ test này, nhưng vẫn là cấu hình an toàn để giữ recall ổn định và chi phí retrieval thấp. Nếu ưu tiên chất lượng câu trả lời, rerank tỏ ra mạnh hơn; nếu ưu tiên latency, baseline dense vẫn tốt hơn.

---

## Variant 2 — Rerank

**Ngày:** 2026-04-13  
**Biến thay đổi:** Dense retrieval + cross-encoder rerank  
**Config thay đổi:**
```
retrieval_mode = "rerank"
use_rerank = True
top_k_search = 10
top_k_select = 3
```

**Baseline vs Variant:**
| Metric | Baseline | Rerank | Delta |
|--------|----------|--------|-------|
| Faithfulness | 3.90/5 | 4.20/5 | +0.30 |
| Answer Relevance | 4.60/5 | 4.50/5 | -0.10 |
| Context Recall | 5.00/5 | 5.00/5 | +0.00 |
| Completeness | 3.20/5 | 3.70/5 | +0.50 |
| Avg latency | 3805 ms | 5903 ms | +2098 ms |
| % Questions Answered | 100.0% | 100.0% | +0.0% |

**Nhận xét:**
> Rerank giúp câu trả lời bám context tốt hơn ở các câu cần lọc lại thứ tự evidence, đặc biệt là q06 và q07, nhưng latency tăng đáng kể vì cross-encoder được gọi cho từng query.

**Kết luận:**
> Rerank là biến cải thiện chất lượng rõ nhất, nhưng không phải lựa chọn mặc định nếu nhóm muốn giữ tốc độ tốt.

---

## Variant 3 — Query Transform

**Ngày:** 2026-04-13  
**Biến thay đổi:** Local query transform expansion + retrieval  
**Config thay đổi:**
```
retrieval_mode = "query_transform"
use_query_transform = True
query_transform_strategy = "expansion"
top_k_search = 10
top_k_select = 3
```

**Baseline vs Variant:**
| Metric | Baseline | Query Transform | Delta |
|--------|----------|-----------------|-------|
| Faithfulness | 3.90/5 | 4.00/5 | +0.10 |
| Answer Relevance | 4.60/5 | 4.60/5 | +0.00 |
| Context Recall | 5.00/5 | 5.00/5 | +0.00 |
| Completeness | 3.20/5 | 3.20/5 | +0.00 |
| Avg latency | 3805 ms | 6885 ms | +3080 ms |
| % Questions Answered | 100.0% | 100.0% | +0.0% |

**Nhận xét:**
> Query transform giúp một số câu alias và câu thiếu keyword rõ ràng, nhưng latency cao nhất vì phải tạo thêm biến thể query. Với test set nhỏ này, cải thiện chưa đủ lớn để vượt rerank.

**Kết luận:**
> Query transform hữu ích cho alias coverage, nhưng chỉ nên bật khi cần cứu các query mơ hồ hoặc tên cũ.

---

## Tổng hợp so sánh

| Metric | Baseline | Hybrid | Rerank | Query Transform |
|---|---:|---:|---:|---:|
| Faithfulness | 3.90 | 3.80 | 4.20 | 4.00 |
| Relevance | 4.60 | 4.60 | 4.50 | 4.60 |
| Context Recall | 5.00 | 5.00 | 5.00 | 5.00 |
| Completeness | 3.20 | 2.80 | 3.70 | 3.20 |
| Avg latency | 3805 ms | 4191 ms | 5903 ms | 6885 ms |
| % Questions Answered | 100.0% | 100.0% | 100.0% | 100.0% |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Thiếu grounding trong generation: answer có thể đúng ý nhưng thiếu chi tiết số học hoặc lệch sang câu hỏi gần nghĩa.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Rerank giúp faithfulness và completeness tăng rõ nhất, nhưng latency tăng mạnh.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Tinh chỉnh query transform rules theo alias thực tế và cache/warmup reranker để giảm latency.
