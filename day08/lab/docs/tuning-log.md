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
| Faithfulness | 4.20/5 |
| Answer Relevance | 4.70/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.50/5 |

**Câu hỏi yếu nhất (điểm thấp):**
- `q09` - Faithfulness = 2/5, Relevance = 3/5, Completeness = 2/5. Hệ thống trả lời "không đủ dữ liệu", nhưng chưa nói rõ đây có thể là lỗi liên quan đến authentication và chưa gợi ý liên hệ IT Helpdesk.
- `q04` - Faithfulness = 2/5, Completeness = 2/5. Hệ thống trả lời "không đủ dữ liệu" trong khi tài liệu có nêu rõ sản phẩm kỹ thuật số không được hoàn tiền.
- `q07` - Completeness = 3/5. Hệ thống tìm đúng tài liệu `access-control-sop.md` nhưng bỏ sót chi tiết tài liệu này là tên mới của "Approval Matrix for System Access".

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

**Nhận xét baseline:**
Baseline dense đã có `Context Recall = 5.00/5`, nghĩa là hệ thống thường lấy đúng tài liệu cần thiết. Vấn đề lớn hơn nằm ở pha generation: câu trả lời đúng hướng nhưng hay thiếu chi tiết, dẫn đến `Completeness = 3.50/5`.

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
| Faithfulness | 4.20/5 | 4.20/5 | 0.00 |
| Answer Relevance | 4.70/5 | 4.60/5 | -0.10 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.50/5 | 3.20/5 | -0.30 |

**Nhận xét:**
- Cải thiện:
  - `q02`: Completeness tăng từ 4/5 lên 5/5. Variant đã trả lời đủ cụm "7 ngày làm việc".
  - `q04`: Faithfulness tăng từ 2/5 lên 5/5, vì câu trả lời abstain khớp hơn với context đã retrieve trong lần chấm này.
- Không đổi đáng kể:
  - `q03`, `q05`, `q07`, `q08`, `q10` gần như giữ nguyên.
- Kém hơn:
  - `q01`: Faithfulness giảm từ 5/5 xuống 3/5, Completeness giảm từ 3/5 xuống 2/5.
  - `q06`: Faithfulness giảm từ 5/5 xuống 2/5, Relevance giảm từ 5/5 xuống 3/5, Completeness giảm từ 5/5 xuống 2/5. Hybrid kéo sang context về temporary access, làm model trả lời lệch ý hỏi về escalation của sự cố P1.

**Kết luận:**
Variant `hybrid` không tốt hơn baseline trong bộ test này. Bằng chứng là:
- `Completeness` giảm từ `3.50` xuống `3.20`
- `Answer Relevance` giảm từ `4.70` xuống `4.60`
- `Faithfulness` và `Context Recall` không cải thiện

Điều này cho thấy bài toán của nhóm không nằm ở việc "không retrieve được đúng tài liệu", vì cả baseline và variant đều đạt `Context Recall = 5.00/5`. Nút thắt chính có thể nằm ở:
- prompt generation chưa ép model tổng hợp đủ ý của expected answer
- top-3 chunk đưa vào prompt chưa đủ sạch, gây nhiễu cho query đã truy xuất đúng tài liệu
- hybrid đưa thêm chunk keyword match nhưng không liên quan nhất, làm model bị lệch trọng tâm

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
1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > *Retrieve đúng tài liệu nhưng generation bỏ sót chi tiết quan trọng, nên điểm Completeness thấp hơn các metric còn lại.*

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > *Trong kết quả hiện tại, đổi retrieval từ dense sang hybrid không giúp tổng thể. Biến có khả năng tác động lớn hơn là rerank hoặc chỉnh prompt generation.*

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > *Thử dense + rerank, hoặc sửa prompt để bắt buộc model tổng hợp đủ các chi tiết chính thay vì trả lời ngắn chỉ một ý.*
