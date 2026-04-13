# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** ___________  
**Config:**
```
retrieval_mode = "dense"
chunking_strategy = "semantic split"
top_k_search = 10
top_k_select = 3
use_rerank = False
threshold = 0.35
llm_model = "gpt-4o-mini"

**System Prompt:** "Chỉ trả lời dựa trên CONTEXT được cung cấp. Nếu không tìm thấy thông tin → trả lời: 'Không tìm thấy thông tin...'. Luôn trích dẫn nguồn."
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 1.00 /5 |
| Answer Relevance | 3.00 /5 |
| Context Recall | 0.50 /5 |
| Completeness | 3.00 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
*   Tất cả các câu hỏi (đặc biệt các câu q01, q02, q03) đều có phần Recall = 0.
*   Hiện tượng: "No retrieved chunks, answer likely not faithful", có nghĩa là hệ thống Dense baseline ở mức khởi điểm không trả về đúng/đủ chunk cho các tài liệu tương ứng, dẫn tới Faithfulness thấp chạm mốc 1.0. (Riêng q09 về Insufficient Context có recall 5 vì vốn dĩ không có expected_sources).

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias (Do tính chất của dữ liệu CS & IT)
- [x] Retrieval: Không retrieve được chunk nào (Do pipeline Dense đang chưa setup đầy đủ hoặc vector query không khớp vector metadata)
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** ___________  
**Biến thay đổi:** ___________  
**Lý do chọn biến này:**
> TODO: Giải thích theo evidence từ baseline results.
> Ví dụ: "Chọn hybrid vì q07 (alias query) và q09 (mã lỗi ERR-403) đều thất bại với dense.
> Corpus có cả ngôn ngữ tự nhiên (policy) lẫn tên riêng/mã lỗi (ticket code, SLA label)."

**Config thay đổi:**
```
retrieval_mode = "hybrid"   # hoặc biến khác
# Các tham số còn lại giữ nguyên như baseline
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
