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
llm_model = gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.50 /5 |
| Answer Relevance | 4.50 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 3.20 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> `q01` (SLA ticket P1) - faithfulness = 2/5, completeness = 1/5. Retriever lấy đúng source nhưng answer lại bám nhầm chi tiết "24 giờ viết báo cáo sự cố" thay vì "15 phút phản hồi, 4 giờ resolution".
> `q06` (Escalation P1) - completeness = 2/5. Answer có grounded nhưng thiếu chi tiết cốt lõi là auto-escalate lên Senior Engineer nếu không có phản hồi trong 10 phút.
> `q07` (Approval Matrix) - completeness = 2/5. Hệ thống tìm đúng tài liệu nhưng answer mới nhắc tên cũ "Approval Matrix for System Access", chưa nêu rõ tên hiện tại là `Access Control SOP`.
> `q10` (Refund VIP khẩn cấp) - relevance = 1/5, completeness = 2/5. Prompt abstain khá chặt nên model trả lời "không có thông tin" mà không nối được với quy trình chuẩn hiện hành trong policy.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

Ghi chú:
`inspect_metadata_coverage()` cho thấy `Chunks thiếu effective_date: 0`, nên chưa có bằng chứng lỗi metadata.
`Context Recall = 5.00/5` cho baseline cho thấy expected source hầu như đều được retrieve; vấn đề chính nằm ở bước generate/select hơn là index.

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** `retrieval_mode`: `dense` → `hybrid`  
**Lý do chọn biến này:**
> Chọn hybrid vì corpus có cả câu tự nhiên và keyword/alias chuyên biệt. Từ log chạy `rag_answer.py`, các query như `Approval Matrix` và `CRITICAL` đều là dạng exact term hoặc alias, phù hợp để kiểm tra BM25 + dense fusion. Mục tiêu của variant này là tăng độ ổn định cho các truy vấn có từ khóa đặc thù mà không đổi prompt hoặc thêm rerank.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.50/5 | Chưa có scorecard | Chưa đo |
| Answer Relevance | 4.50/5 | Chưa có scorecard | Chưa đo |
| Context Recall | 5.00/5 | Chưa có scorecard | Chưa đo |
| Completeness | 3.20/5 | Chưa có scorecard | Chưa đo |

**Nhận xét:**
> Từ log `python rag_answer.py`, hybrid cho kết quả tương đương dense ở 3 query demo đã chạy.
> Với query `Approval Matrix để cấp quyền là tài liệu nào?`, hybrid cho câu trả lời rõ hơn một chút: "tài liệu trước đây có tên..." nên sát alias query hơn dense.
> Với query `CRITICAL` và query refund, chưa thấy khác biệt rõ giữa dense và hybrid; output gần như giống nhau.
> Chưa có bằng chứng định lượng để kết luận hybrid cải thiện completeness hay faithfulness trên toàn bộ 10 câu hỏi, vì `eval.py` mới chạy baseline trong log hiện có.

**Kết luận:**
> Chưa thể kết luận Variant 1 tốt hơn baseline theo scorecard vì chưa có lần chạy `run_scorecard()` cho hybrid trong log hiện tại.
> Bằng chứng hiện có chỉ là so sánh định tính trên 3 query demo: hybrid không làm xấu kết quả và có cải thiện nhẹ về diễn đạt ở query alias `Approval Matrix`, nhưng chưa chứng minh được delta trung bình trên 4 metric.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** Không thực hiện  
**Config:**
```
# Không có variant 2 trong phạm vi log hiện tại
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.50 | Chưa có scorecard | N/A | Baseline |
| Answer Relevance | 4.50 | Chưa có scorecard | N/A | Baseline |
| Context Recall | 5.00 | Chưa có scorecard | N/A | Baseline |
| Completeness | 3.20 | Chưa có scorecard | N/A | Baseline |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Retriever thường mang đúng source về, nhưng answer vẫn có thể chọn sai chi tiết hoặc bỏ sót ý quan trọng. Điểm yếu lớn nhất hiện tại là generation/completeness, không phải recall.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Theo cấu trúc code và log demo, retrieval strategy là biến đáng thử nhất cho Sprint 3 vì corpus có nhiều alias và keyword đặc thù. Tuy vậy, trong log hiện tại hybrid mới chỉ cho thấy tín hiệu cải thiện định tính, chưa có số liệu A/B hoàn chỉnh.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Chạy đầy đủ scorecard cho `hybrid`, sau đó thử thêm một biến độc lập như `use_rerank=True` hoặc điều chỉnh prompt để answer bắt buộc nêu đủ "current name / SLA pair / escalation trigger" ở các câu đang thiếu completeness.
