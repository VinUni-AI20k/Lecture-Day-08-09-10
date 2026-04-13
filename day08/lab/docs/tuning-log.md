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
| Faithfulness | 4.50/5 |
| Answer Relevance | 3.30/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.80/5 |

**Câu hỏi yếu nhất (điểm thấp):**
> q06 (SLA) - Answer Relevance = 1/5, Completeness = 2/5 vì câu hỏi dễ kéo nhiều ngữ cảnh nhưng baseline dense vẫn chưa chọn đúng chunk ưu tiên.
> q09 (Insufficient Context) - Completeness = 2/5 vì mô hình đã abstain đúng hướng, nhưng không đủ nội dung để trả lời đầy đủ như các câu có evidence rõ.
> q10 (Refund) - Completeness = 2/5 vì query có xu hướng thiếu chính xác keyword, nên câu trả lời khá ngắn và chưa đủ cụ thể.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [x] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
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
| Faithfulness | 4.50/5 | 4.60/5 | +0.10 |
| Answer Relevance | 3.30/5 | 3.00/5 | -0.30 |
| Context Recall | 5.00/5 | 5.00/5 | +0.00 |
| Completeness | 3.80/5 | 3.50/5 | -0.30 |

**Nhận xét:**
> Variant 1 cải thiện nhẹ faithfulness, đặc biệt ở các câu cần giữ câu trả lời an toàn hơn, ví dụ q01 và q07.
> Tuy nhiên relevance và completeness giảm nhẹ ở một số câu như q06, cho thấy rerank làm model ưu tiên chunk an toàn hơn nhưng đôi khi bỏ mất chunk có thông tin phụ trợ cần thiết.
> Context recall giữ nguyên 5.0/5, tức là retrieval vẫn lấy đúng evidence, khác biệt nằm ở thứ tự chunk trước khi generate.

**Kết luận:**
> Variant 1 chỉ tốt hơn baseline ở faithfulness, nhưng không vượt baseline về relevance và completeness.
> Nếu mục tiêu chính là câu trả lời ngắn, chắc chắn, ít hallucination thì rerank đáng giữ; nếu mục tiêu là trả lời đầy đủ hơn, baseline dense lại cân bằng hơn.
> Bằng chứng: Faithfulness tăng từ 4.50 lên 4.60, trong khi Relevance giảm từ 3.30 xuống 3.00 và Completeness giảm từ 3.80 xuống 3.50.

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
| Faithfulness | ? | ? | ? | ? |
| Answer Relevance | ? | ? | ? | ? |
| Context Recall | ? | ? | ? | ? |
| Completeness | ? | ? | ? | ? |

---

## Tóm tắt học được

> TODO (Sprint 4): Điền sau khi hoàn thành evaluation.

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > _____________

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > _____________

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > _____________
