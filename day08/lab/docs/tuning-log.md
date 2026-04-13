# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** **13/04/2026**  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 800 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.50/5 |
| Answer Relevance | 4.80/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.90/5 |

**Câu hỏi yếu nhất (điểm thấp):**
- `q09` - Faithfulness = 3/5, Relevance = 4/5, Completeness = 2/5. Hệ thống abstain đúng, nhưng chưa nói ERR-403-AUTH có thể liên quan đến authentication và chưa gợi ý liên hệ IT Helpdesk.
- `q07` - Faithfulness = 2/5, Relevance = 4/5, Completeness = 2/5. Hệ thống trả về tên cũ "Approval Matrix for System Access", trong khi expected answer yêu cầu nêu rõ tên hiện tại là `Access Control SOP`.
- `q10` - Completeness = 2/5. Hệ thống trả lời "không đủ dữ liệu" là đúng hướng, nhưng chưa bổ sung ngữ cảnh rằng tài liệu hiện hành không có quy trình riêng cho VIP và quy trình chuẩn vẫn là 3-5 ngày làm việc.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Retrieval: Dense bỏ lỡ tài liệu cần thiết
- [ ] Retrieval: Top-k quá ít nên thiếu evidence
- [x] Generation: Câu trả lời còn ngắn, thiếu các chi tiết phụ nhưng quan trọng trong expected answer
- [ ] Generation: Context quá dài gây lost in the middle

**Nhận xét baseline:**
Baseline dense đang là cấu hình tốt nhất trong repo hiện tại. `Context Recall = 5.00/5` cho thấy hệ thống retrieve đúng tài liệu rất ổn. Điểm còn yếu chủ yếu nằm ở generation: model thường trả lời đúng ý chính nhưng chưa tổng hợp đủ chi tiết nền hoặc thông tin đổi tên/ngữ cảnh bổ sung, nên `Completeness` vẫn thấp hơn các metric còn lại.

---

## Variant 1 (Sprint 3)

**Ngày:** 13/04/2026  
**Biến thay đổi:** `retrieval_mode`: từ `dense` sang `hybrid`  
**Lý do chọn biến này:**
Nhóm thử hybrid retrieval vì corpus có cả câu văn tự nhiên lẫn keyword đặc thù như `P1`, `Level 3`, `Approval Matrix`, `ERR-403-AUTH`. Giả thuyết ban đầu là BM25 sẽ giúp bắt tốt hơn exact keyword và alias, từ đó cải thiện các câu query có mã lỗi, tên tài liệu, hoặc cú pháp không giống với văn bản trong chunk.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
chunk_size = 800 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.50/5 | 4.30/5 | -0.20 |
| Answer Relevance | 4.80/5 | 4.40/5 | -0.40 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.90/5 | 3.70/5 | -0.20 |

**Nhận xét:**
- Giữ nguyên:
  - `q01`, `q02`, `q03`, `q04`, `q05`, `q08` gần như không thay đổi; cả baseline và hybrid đều trả lời tốt.
- Cải thiện nhẹ:
  - `q09`: Faithfulness tăng từ 3/5 lên 4/5, nhưng Relevance vẫn giảm xuống 3/5 và Completeness không đổi.
  - `q10`: Completeness tăng từ 2/5 lên 3/5, nhưng đây chỉ là cải thiện nhỏ.
- Kém hơn:
  - `q06`: Faithfulness giảm từ 5/5 xuống 2/5, Relevance giảm từ 5/5 xuống 3/5, Completeness giảm từ 5/5 xuống 2/5. Hybrid kéo model sang context về temporary access thay vì escalation của ticket P1.
  - `q07`: Relevance giảm từ 4/5 xuống 3/5, các lỗi về tên tài liệu vẫn không được sửa.

**Kết luận:**
Variant `hybrid` không tốt hơn baseline trong bộ test này. Bằng chứng là:
- `Faithfulness` giảm từ `4.50` xuống `4.30`
- `Answer Relevance` giảm từ `4.80` xuống `4.40`
- `Completeness` giảm từ `3.90` xuống `3.70`
- `Context Recall` không tăng, vẫn là `5.00/5`

Điều này cho thấy bài toán hiện tại của nhóm không nằm ở việc thiếu recall, vì cả hai cấu hình đều retrieve đúng nguồn. Vấn đề chính nằm ở chất lượng chunk đưa vào generation và cách model tổng hợp câu trả lời từ context. Trong trường hợp `q06`, hybrid còn làm tăng nhiễu do đưa thêm chunk keyword match nhưng không đúng trọng tâm của câu hỏi.

---

## Variant 2 (nếu có thời gian)

**Biến đề xuất:** thêm `rerank` sau retrieval, giữ nguyên `retrieval_mode = "dense"`

**Lý do:**
Vì baseline đã có recall tốt, thay đổi hợp lý tiếp theo không phải là mở rộng retrieval mà là làm sạch top chunks trước khi đưa vào prompt. Rerank có khả năng giải quyết đúng failure mode đang thấy ở `q06`, `q07`, `q09`, `q10` tốt hơn hybrid.

**Config dự kiến:**
```
retrieval_mode = "dense"
use_rerank = True
# Các tham số khác giữ nguyên như baseline
```

**Kỳ vọng đo lường:**
- Tăng `Completeness` cho `q07`, `q09`, `q10`
- Giữ hoặc tăng `Faithfulness`
- Không làm giảm `Context Recall`

---

## Tóm tắt học được
1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > *Retrieve đúng tài liệu nhưng generation chưa tổng hợp đủ các chi tiết phụ quan trọng, nên điểm Completeness thấp hơn Faithfulness và Relevance.*

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > *Trong dữ liệu hiện tại, đổi retrieval từ dense sang hybrid không giúp tổng thể, thậm chí còn làm giảm chất lượng ở một số câu. Dense baseline vẫn là lựa chọn tốt hơn.*

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > *Thử dense + rerank, hoặc sửa prompt để bắt buộc model tổng hợp đủ các chi tiết chính thay vì trả lời ngắn chỉ một ý.*
