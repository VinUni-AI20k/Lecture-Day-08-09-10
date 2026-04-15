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
| Faithfulness | 4.80 /5 |
| Answer Relevance | 2.40 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 2.10 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> gq01 (SLA thay đổi theo phiên bản): retrieve đúng nguồn nhưng answer vẫn theo hướng "không tìm thấy", làm relevance/completeness thấp.
>
> gq02 (Remote + VPN + số thiết bị): lấy đúng 2 nguồn nhưng generation không tổng hợp, dẫn tới completeness thấp.
>
> gq03 (Flash Sale + đã kích hoạt): chưa trả lời đầy đủ logic ngoại lệ kép dù evidence có trong corpus.

**Giả thuyết nguyên nhân (Error Tree):**
- [x] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding
- [x] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 13/04/2026  
**Biến thay đổi:** retrieval_mode: dense -> hybrid (Dense + BM25 + RRF)  
**Lý do chọn biến này:**
> Chọn hybrid vì baseline dense trả lời chưa tốt các câu multi-signal trong grading set, đặc biệt các câu cần tổng hợp nhiều chi tiết trong cùng chủ đề.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
# Các tham số còn lại giữ nguyên như baseline
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.80/5 | 4.70/5 | -0.10 |
| Answer Relevance | 2.40/5 | 2.30/5 | -0.10 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 2.10/5 | 2.10/5 | 0.00 |

**Nhận xét:**
> Trên grading_questions, hybrid không tạo cải thiện đáng kể so với baseline.
>
> Context recall giữ nguyên 5.0 nhưng relevance giảm nhẹ, cho thấy vấn đề chính nằm ở generation tổng hợp hơn là ở retrieve.
>
> Một số câu vẫn trả lời theo mẫu "không tìm thấy" dù đã có context phù hợp.

**Kết luận:**
> Variant 1 chưa tốt hơn baseline trên bộ grading_questions. Delta gần như không cải thiện, trong khi relevance giảm nhẹ. Baseline dense vẫn là cấu hình ổn định hơn để nộp.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** Chưa chạy (N/A)  
**Config:**
```
# Chưa thực hiện trong phiên hiện tại
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.80 | 4.70 | N/A | Baseline |
| Answer Relevance | 2.40 | 2.30 | N/A | Baseline |
| Context Recall | 5.00 | 5.00 | N/A | Tie |
| Completeness | 2.10 | 2.10 | N/A | Tie |

---

## Tóm tắt học được

Hoàn thành sau evaluation ngày 13/04/2026.

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Generation chưa tận dụng đủ context đã retrieve, hay trả lời an toàn kiểu "không tìm thấy" dù evidence đã có.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Prompt và logic generation tác động mạnh hơn retrieval_mode trong bộ grading hiện tại, vì cả baseline và hybrid đều đạt recall cao nhưng answer quality vẫn thấp.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Thử variant 2 với rerank (giữ retrieval_mode cố định) và siết prompt theo format bắt buộc: trả lời theo bullet, trích rõ điều khoản, chỉ abstain khi toàn bộ top-k không chứa evidence.
