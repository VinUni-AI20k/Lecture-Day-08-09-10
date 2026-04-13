# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13  
**Config:**
```
retrieval_mode = "dense"
chunk_size = not specified trong eval.py
overlap = not specified trong eval.py
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = not specified trong eval.py
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 3.30 /5 |
| Answer Relevance | 3.80 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 2.80 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> q04 (Refund) - Faithfulness 1, Relevance 2, Completeness 1: answer không trả lời đúng nội dung chính và vẫn ghi "không tìm thấy thông tin" mặc dù source đã retrieve.
> q07 (Access Control) - Faithfulness 1, Relevance 2, Completeness 1: response sai hướng khi hỏi về Approval Matrix / Access Control SOP.
> q10 (Refund) - Faithfulness 1, Relevance 2, Completeness 1: câu trả lời không nắm được quy trình hoàn tiền cho khách VIP và bỏ qua key point là không có quy trình đặc biệt.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding
- [x] Generation: Context quá dài → lost in the middle

**Nhận xét bổ sung:**
- Context Recall 5.00/5 cho thấy retriever đã tìm đúng nguồn cần thiết.
- Điểm thấp nhất nằm ở Faithfulness/Relevance/Completeness, nên lỗi chính là chất lượng generation hoặc cách prompt sử dụng context.
- Một số câu như q04, q07, q10 cho thấy mô hình trả lời kiểu "không tìm thấy" ngay cả khi source có sẵn, đây là dấu hiệu của grounding/prompting yếu.

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13   
**Biến thay đổi:** Chuyển `retrieval_mode` từ `dense` sang `hybrid` và bật `use_rerank=True`.
**Lý do chọn biến này:**
> `eval.py` hiện tại cấu hình baseline là `dense` và `use_rerank=False`.
> Sau khi chạy baseline, retrieval recall là 5.00/5 nên việc chuyển sang hybrid kỳ vọng giúp câu hỏi alias / mã lỗi được xử lý tốt hơn, đồng thời rerank có thể cải thiện chất lượng evidence ranking.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
use_rerank = True
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 3.30 /5 | 3.40 /5 | +0.10 |
| Answer Relevance | 3.80 /5 | 3.80 /5 | 0.00 |
| Context Recall | 5.00 /5 | 5.00 /5 | 0.00 |
| Completeness | 2.80 /5 | 2.50 /5 | -0.30 |

**Nhận xét:**
> Variant 1 không tạo ra cải thiện tổng thể rõ ràng. Context recall vẫn duy trì 5.00/5, nhưng completeness giảm, nghĩa là câu trả lời vẫn thiếu thông tin dù evidence đã có.
> Cải thiện duy nhất rõ ràng là faithfulness của q02 tăng từ 4 lên 5.
> Một số câu như q01, q06, q08 có completeness giảm so với baseline, chỉ ra rằng bước generation hoặc phrasing vẫn là điểm yếu lớn.

**Kết luận:**
> Variant 1 không tốt hơn baseline theo toàn bộ metrics. Kết quả cho thấy thay đổi hybrid + rerank chỉ ảnh hưởng nhẹ đến faithfulness, còn completeness thậm chí có xu hướng giảm.
> Do baseline đã có recall hoàn hảo, giới hạn hiện tại nằm ở generation/prompt hơn là retrieval.
> Quan trọng: `eval.py` đã thay đổi đồng thời hai biến (`hybrid` và `rerank`), nên cần tách thử nghiệm thành các variant đơn lẻ để biết chính xác biến nào tác động.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** Không có variant thứ hai được triển khai trong phạm vi hiện tại.
**Config:**
```
# Không có variant 2 đã thực hiện.
```

**Gợi ý Variant 2:**
- `use_rerank=True` với `retrieval_mode="dense"` để đánh giá riêng tác động của rerank.
- Hoặc giữ `retrieval_mode="hybrid"` và `use_rerank=False` để so sánh riêng retrieval strategy.

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 3.30 | 3.40 | N/A | 3.40 |
| Answer Relevance | 3.80 | 3.80 | N/A | 3.80 |
| Context Recall | 5.00 | 5.00 | N/A | 5.00 |
| Completeness | 2.80 | 2.50 | N/A | 2.80 |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Lỗi chính là generation/prompting, không phải retrieval. Dù recall đạt 5/5, nhiều câu trả lời vẫn sai hoặc thiếu thông tin.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Với dữ liệu hiện có, retrieval strategy chỉ ảnh hưởng rất nhỏ; biến tác động lớn hơn có thể là cách tạo prompt / cấu hình LLM.
   > Tuy nhiên, theo cấu hình trong `eval.py`, `hybrid` + `rerank` là biến đã được thử và chỉ cải thiện faithfulness nhẹ.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Chạy thêm experiment tách biệt: chỉ đổi `hybrid` hoặc chỉ bật `rerank` để đảm bảo A/B Rule.
   > Điều chỉnh prompt để ép model trả lời đúng từ context và hạn chế hallucination, đặc biệt với các câu như q04, q07, q10.
   > Nếu có thể, bổ sung variant chỉ tập trung vào query transform / alias handling để test mục tiêu retrieval alias riêng.
