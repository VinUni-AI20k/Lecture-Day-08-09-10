# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

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
query_transform = None
llm_model = openai-gpt-4o
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.60/5 |
| Answer Relevance | 3.00/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.50/5 |

**Câu hỏi yếu nhất (điểm thấp):**
> q06 (SLA) - Answer Relevance = 1/5, Completeness = 2/5 vì câu hỏi dễ kéo nhiều ngữ cảnh nhưng baseline dense vẫn chưa chọn đúng chunk ưu tiên.
> q09 (Insufficient Context) - Completeness = 2/5 vì mô hình đã abstain đúng hướng, nhưng không đủ nội dung để trả lời đầy đủ như các câu có evidence rõ.
> q10 (Refund) - Completeness = 2/5 vì query có xu hướng thiếu chính xác keyword, nên câu trả lời khá ngắn và chưa đủ cụ thể.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [x] Retrieval: Thứ tự ranking chunk chưa tối ưu trước khi generate
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** `use_rerank = True` (dense + LLM rerank)  
**Lý do chọn biến này:**
> Chọn rerank vì baseline dense đã có context recall rất tốt, nhưng một số câu vẫn bị giảm relevance/completeness do thứ tự chunk chưa tối ưu.
> Rerank giúp sắp xếp lại candidate chunks theo mức độ trả lời câu hỏi thực tế, đặc biệt hữu ích với các query có nhiều chunk gần đúng nhưng chỉ một chunk thật sự chứa evidence chính.

**Config thay đổi:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = True
query_transform = None
llm_model = openai-gpt-4o
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.60/5 | 4.70/5 | +0.10 |
| Answer Relevance | 3.00/5 | 3.20/5 | +0.20 |
| Context Recall | 5.00/5 | 5.00/5 | +0.00 |
| Completeness | 3.50/5 | 3.60/5 | +0.10 |

**Nhận xét:**
> Variant 1 cải thiện đều ở Faithfulness (+0.10), Relevance (+0.20), và Completeness (+0.10), trong khi Context Recall giữ nguyên 5.00/5.
> Cải thiện thấy rõ ở q04 (Relevant 3 -> 4) và q06 (Complete 2 -> 3), cho thấy rerank giúp chọn thứ tự evidence phù hợp hơn trước khi generate.
> Một số câu vẫn khó như q06 (Relevant = 1) và q09/q10 (Complete = 2) do bản chất câu hỏi thiếu context hoặc cần tổng hợp nhiều ý.

**Kết luận:**
> Variant 1 tốt hơn baseline theo tổng thể: tăng 3/4 metric và không làm giảm Context Recall.
> Nhóm chọn `dense + rerank` làm cấu hình ưu tiên cho grading vì cân bằng tốt hơn giữa độ đúng (faithfulness) và độ phù hợp câu trả lời (relevance/completeness).
> Bằng chứng: Faithfulness 4.60 -> 4.70, Relevance 3.00 -> 3.20, Completeness 3.50 -> 3.60, Context Recall giữ 5.00.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** Chưa chạy  
**Config:**
```
# Chưa có
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.60 | 4.70 | N/A | Variant 1 |
| Answer Relevance | 3.00 | 3.20 | N/A | Variant 1 |
| Context Recall | 5.00 | 5.00 | N/A | Tie |
| Completeness | 3.50 | 3.60 | N/A | Variant 1 |

---

## Tóm tắt học được

> TODO (Sprint 4): Điền sau khi hoàn thành evaluation.

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > _____________

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > _____________

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > _____________
