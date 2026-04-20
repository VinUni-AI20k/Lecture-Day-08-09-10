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
llm_model = "gpt-4o-mini"
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 3.70 /5 |
| Answer Relevance | 3.70 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 2.80 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
1. **"Approval Matrix để cấp quyền là tài liệu nào?"** - Kết quả: Abstain ("Tôi xin lỗi..."). 
   - **Phân tích Sâu:** Keyword này tồn tại trong file `access_control_sop.txt` (dòng 7). Tuy nhiên, logic `preprocess_document` trong `index.py` đang lọc bỏ các dòng text nằm giữa Metadata Header và Section Header đầu tiên. Do đó, thông tin này chưa bao giờ được đưa vào Vector Store.
2. **"Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP..."** - Kết quả: Abstain. Lý do: Đúng (Dữ liệu không có quy trình riêng cho VIP).

**Giả thuyết nguyên nhân (Error Tree):**
- [x] Indexing: Preprocess lọc mất Note quan trọng ở đầu file.
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài hoặc mờ nhạt

---

## Variant 1 (Sprint 3)

**Ngày:** ___________  
**Biến thay đổi:** `retrieval_mode = "hybrid"` 
**Lý do chọn biến này:**
Chọn hybrid vì câu hỏi "Approval Matrix" thất bại với dense. Hy vọng phần Sparse (BM25) sẽ bắt được keyword "Approval Matrix" xuất hiện trong Note của tài liệu SOP để giúp LLM có bằng chứng trả lời.

**Config thay đổi:**
```
retrieval_mode = "hybrid"   # hoặc biến khác
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 3.70/5 | 3.30/5 | -0.40 |
| Answer Relevance | 3.70/5 | 3.50/5 | -0.20 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 2.80/5 | 2.70/5 | -0.10 |

**Nhận xét:**
Hybrid search mang lại kết quả Recall cao hơn (ví dụ: truy vấn ERR-403 lấy về được `helpdesk-faq.md`). Tuy nhiên, với các lỗi do Indexing (như Approval Matrix), thay đổi chiến thuật Retrieval không giải quyết được vấn đề tận gốc. Hệ thống hiện tại rất an toàn (không bịa đặt) nhưng đang bị "lọc quá đà" ở đầu vào.

**Kết luận:**
Nhóm thống nhất sử dụng **Hybrid Search + Rerank** làm cấu hình cuối cùng để nộp bài vì nó đảm bảo tính chính xác cho các thuật ngữ chuyên môn (P1, ticket code) và tránh được các kết quả nhiễu.

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
| Faithfulness | 3.70 | 3.30 | — | Baseline |
| Answer Relevance | 3.70 | 3.50 | — | Baseline |
| Context Recall | 5.00 | 5.00 | — | Tie |
| Completeness | 2.80 | 2.70 | — | Baseline |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Indexing error: `preprocess_document` lọc bỏ nội dung quan trọng (Note, header phụ) nằm phía trên section header đầu tiên. Dẫn đến LLM không có evidence và trả về abstain ngay cả khi thông tin thực sự tồn tại trong tài liệu gốc. Điển hình: câu hỏi về "Approval Matrix" và contractor access.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Chất lượng chunking và preprocessing có tác động lớn nhất — vượt qua cả lựa chọn retrieval mode. Chuyển từ dense sang hybrid không giải quyết được lỗi do indexing vì dữ liệu chưa bao giờ được đưa vào vector store. Context Recall đạt 5.00/5 cho thấy retrieval tốt, nhưng Completeness thấp (2.80/5) phản ánh ngưỡng abstain quá cao.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Điều chỉnh `preprocess_document` để giữ lại toàn bộ nội dung trước section header đầu tiên (đặc biệt các dòng Note/Warning). Thử giảm ngưỡng abstain trong prompt để LLM trả lời partial thay vì từ chối hoàn toàn. Kiểm tra lại các câu hỏi có điểm Completeness thấp (q09, q10, gq05, gq07).
