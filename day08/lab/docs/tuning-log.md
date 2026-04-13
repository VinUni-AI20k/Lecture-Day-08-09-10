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

**Quan sát từ `grading_questions.json` (config `variant_hybrid`):**
> Đã chạy đủ 10 câu và xuất `logs/grading_run.json` lúc khoảng `2026-04-13T17:52`. Hybrid cho thấy lợi thế rõ ở truy vấn cross-document và emergency path: `gq06` trả về khá đầy đủ quy trình cấp quyền tạm thời trong sự cố P1; `gq03`, `gq08`, `gq10` cũng bám đúng policy tương đối tốt.
> Các lỗi còn lại chủ yếu là completeness hơn là recall: `gq02` thiếu VPN bắt buộc và Cisco AnyConnect; `gq04` thiếu ý "store credit là tùy chọn"; `gq09` thiếu kênh đổi mật khẩu; `gq07` abstain đúng hướng nhưng mới dừng ở "Tôi không biết", chưa nói rõ là tài liệu không có thông tin này.
> `gq05` là câu fail lớn nhất: answer nhầm approver, thời gian xử lý và bỏ mất training bắt buộc của `Admin Access (Level 4)`, cho thấy model vẫn dễ chọn sai chi tiết dù retrieve có chứa đúng source `it/access-control-sop.md`.

**Nhận xét:**
> Từ log `python rag_answer.py`, hybrid cho kết quả tương đương dense ở các query demo đơn giản và có cải thiện nhẹ về diễn đạt ở query alias `Approval Matrix`.
> Từ `grading_run.json`, hybrid thực sự hữu ích cho câu hỏi cần nhiều nguồn hoặc keyword rõ như `gq02`, `gq06`, `gq10`, vì output cho thấy hệ thống giữ được đúng source chính.
> Tuy vậy, hybrid không tự giải quyết được lỗi generation: khi candidate có nhiều chi tiết gần nhau, model vẫn có thể chọn nhầm hoặc rút gọn quá mức như ở `gq05` và `gq09`.
> Nói ngắn gọn: hybrid cải thiện khả năng retrieve evidence phù hợp, nhưng bottleneck lớn nhất sau tuning vẫn là completeness ở bước answer synthesis.

**Kết luận:**
> Chưa thể kết luận Variant 1 tốt hơn baseline bằng số liệu A/B đầy đủ vì nhóm mới có `scorecard_baseline.md` và `grading_run.json`, chưa có `scorecard_variant.md`.
> Tuy nhiên, dựa trên log grading hiện có, variant `hybrid` là hướng đúng: nó xử lý tốt hơn các câu cần exact term hoặc nhiều nguồn như `gq02`, `gq06`, `gq10`, đồng thời vẫn abstain an toàn ở `gq07`.
> Bằng chứng quan trọng nhất từ toàn bộ kết quả hiện có là: retrieval/recall đã khá tốt, còn phần cần cải thiện tiếp theo là answer synthesis và rerank để tránh thiếu ý hoặc chọn sai chi tiết trong cùng một tài liệu.

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
   > Retriever thường mang đúng source về, nhưng answer vẫn có thể chọn sai chi tiết hoặc bỏ sót ý quan trọng. Từ cả baseline scorecard lẫn grading log, điểm yếu lớn nhất hiện tại là generation/completeness, không phải recall.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Retrieval strategy là biến có tác động nhìn thấy rõ nhất ở giai đoạn tuning vì corpus có nhiều alias, keyword và câu hỏi cross-document. Hybrid giúp giữ evidence đúng tốt hơn, nhưng để kéo chất lượng tổng thể lên nữa thì biến tiếp theo nên là rerank hoặc prompt stricter cho completeness.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Chạy đầy đủ `scorecard_variant.md` cho `hybrid`, sau đó thử một biến độc lập như `use_rerank=True` hoặc prompt template bắt buộc liệt kê đủ các ý chính khi câu hỏi là multi-part. Hai mục tiêu ưu tiên là sửa `gq05` và tăng completeness cho `gq02`, `gq04`, `gq09`.
