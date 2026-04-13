# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 13/04/2026  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 3.7/5 |
| Answer Relevance | 4.0/5 |
| Context Recall | 5/5 |
| Completeness | 3.9/5 |

**Câu hỏi yếu nhất (điểm thấp):**
> q7, q9 và q10

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 13/04/2026  
**Biến thay đổi:** retrieval_mode  
**Lý do chọn biến này:**
> Chọn hybrid retrieval vì corpus chứa cả văn bản tự nhiên lẫn từ khóa/ thuật ngữ đặc thù, giúp kết hợp ưu điểm của semantic và keyword matching để tăng recall.

**Config thay đổi:**
```
retrieval_mode = "hybrid"   
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 3.7/5 | 3.9/5 | +0.2 |
| Answer Relevance | 4.0/5 | 4.4/5 | +0.4 |
| Context Recall | 5.0/5 | 5.0/5 | n/a |
| Completeness | 3.9/5 | 3.9/5 | n/a |

**Nhận xét:**
> Variant 1 cải thiện ở q6 q7, do keyword matching có thể giúp trong 2 trường hợp này.
> Variant 1 kém hơn ở q9, do context của variant 1 làm LLM hoang tưởng và trả lời thay vì đề xuất người dùng liên hệ IT helpdesk.

**Kết luận:**
> Variant 1 có cải thiện nhẹ so với baseline, đặc biệt trong các trường hợp liên quan đến tìm kiếm chính xác như q6 và q7.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** ___________  
**Config:**
```
# TODO
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
   > Faithful điểm trung bình thấp nhất

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > retrieval_mode

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Sử dụng các hàm heuristic để hậu xử lý các chunk dựa trên metadata
