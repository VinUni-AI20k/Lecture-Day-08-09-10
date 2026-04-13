# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** ___________  
**Config:**
```
retrieval_mode = "dense"
chunk_size = _____ tokens
overlap = _____ tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = _____
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | ? /5 |
| Answer Relevance | ? /5 |
| Context Recall | ? /5 |
| Completeness | ? /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> TODO: Liệt kê 2-3 câu hỏi có điểm thấp nhất và lý do tại sao.
> Ví dụ: "q07 (Approval Matrix) - context recall = 1/5 vì dense bỏ lỡ alias."

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** `retrieval_mode`: `"dense"` → `"hybrid"` (Dense + BM25 + RRF)  
**Lý do chọn biến này:**
> Chọn **hybrid retrieval** vì corpus có hai kiểu tín hiệu khác nhau:
> 1) câu tự nhiên dài trong policy/SOP (dense làm tốt), và  
> 2) từ khóa đặc thù như mã lỗi, SLA label, tên quy trình (BM25 làm tốt hơn).
>
> Baseline dense có rủi ro bỏ sót exact-match query (ví dụ kiểu `ERR-403-AUTH`, `P1`, `Level 3`) khi embedding ưu tiên ngữ nghĩa tổng quát.  
> Hybrid dùng **Reciprocal Rank Fusion (RRF)** để hợp nhất ưu điểm của dense và sparse, giúp tăng **context recall** mà vẫn giữ grounded generation.
>
> Nhóm chỉ đổi **1 biến retrieval_mode** để tuân thủ A/B Rule; các tham số khác giữ nguyên để so sánh công bằng.

**Config thay đổi:**
```
retrieval_mode = "hybrid"   # hoặc biến khác
top_k_search = 10
top_k_select = 3
use_rerank = False
# Giữ nguyên các biến còn lại so với baseline để đo đúng tác động của retrieval_mode
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | ?/5 | ?/5 | +/- |
| Answer Relevance | ?/5 | ?/5 | +/- |
| Context Recall | ?/5 | ?/5 | +/- |
| Completeness | ?/5 | ?/5 | +/- |

**Nhận xét:**
> TODO: Variant 1 cải thiện ở câu nào? Tại sao?
> Có câu nào kém hơn không? Tại sao?

**Kết luận:**
> TODO: Variant 1 có tốt hơn baseline không?
> Bằng chứng là gì? (điểm số, câu hỏi cụ thể)

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
   > _____________

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > _____________

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > _____________
