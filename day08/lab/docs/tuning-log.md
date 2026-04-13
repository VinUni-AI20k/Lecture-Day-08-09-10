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
llm_model = Deepseek Chat
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
- [x] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Prompt không đủ grounding
- [x] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 13/04/2026  
**Biến thay đổi:** `retrieval_mode` (đổi từ "dense" sang "hybrid")  
**Lý do chọn biến này:**
> Ở Baseline, kết quả có thể kém đi đối với những câu hỏi có chứa mã quy trình (như ERR-403-AUTH). Do tập tài liệu Helpdesk & CS chứa trộn lẫn cả ngôn ngữ tự nhiên dài (chính sách v4) và các mã code/tên nhãn cứng (ticket P1, SLA). BM25 (Sparse) trong Hybrid sẽ bắt dính các mã cứng này tốt hơn nhiều so với việc chỉ phán đoán ngữ nghĩa của Dense search thuần túy.

**Config thay đổi:**
```python
retrieval_mode = "hybrid"   
# Các tham số còn lại (top_k, chunk_size, llm_model...) giữ nguyên để so sánh chuẩn xác với Baseline.
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

> Tóm tắt quá trình phát triển hệ thống RAG:

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > LLM đưa ra câu trả lời sai (hallucination) do đoạn Context truyền vào không chứa thông tin chính xác. Nguyên nhân sâu xa thường bắt nguồn từ Retrieval (như dùng Dense search hụt các mốc mã số/keyword chuyên nghiệp) hoặc Chunking lúc tách làm mất đoạn ý nghĩa quan trọng.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Chiến lược Retrieval (Đổi sang Hybrid để cân bằng độ phủ Context) và thiết kế System Prompt (Bắt buộc Code phải format Context có Label citation để ép LLM không được trả lời ở ngoài) mang lại độ ổn định lớn nhất.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Nhóm sẽ thực hiện setup thêm một bộ Cross-Encoder Reranker để loại bỏ đi các chunks rác vô tình bị Keyword BM25 mang vào Context. Bên cạnh đó có thể update module lọc Metadata ngày có hiệu lực (Effective Date) để AI không tự ý lấy văn bản chính sách phiên bản cũ.
