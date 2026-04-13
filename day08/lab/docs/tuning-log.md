# Tuning Log — RAG Pipeline (Day 08 Lab)

---

## Baseline (Sprint 2)

**Ngày:** 13/4/2026  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 500 tokens
overlap = 100 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.5 /5 |
| Answer Relevance | 4.2 /5 |
| Context Recall | 5 /5 |
| Completeness | 3.8 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
- q09 (ERR-403-AUTH là lỗi gì và cách xử lý?) - Faithfulness = 1, Relevance = 1, Completeness = 1. Baseline trả lời "Tôi không biết", cho thấy retrieved context không có đủ evidence hoặc dữ liệu không chứa thông tin này.
- q10 (Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?) - Relevance = 1, Completeness = 2. Model abstain đúng theo context, nhưng câu trả lời chưa giải quyết được nhu cầu người dùng vì tài liệu không có quy trình VIP/khẩn cấp.
- q07 (Approval Matrix để cấp quyền hệ thống là tài liệu nào?) - Completeness = 2. Câu trả lời đúng nguồn nhưng còn thiếu thông tin rõ ràng rằng tài liệu hiện tại là Access Control SOP và có ghi chú từng được gọi là "Approval Matrix for System Access".

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 13/4/2026  
**Biến thay đổi:** Chuyển sang hybrid  
**Lý do chọn biến này:**
> Chọn hybrid vì corpus có cả ngôn ngữ tự nhiên (policy, SOP, FAQ) lẫn keyword/tên chuyên ngành cần match chính xác như SLA, P1, Level 3, ERR-403, Approval Matrix. Baseline dense đạt điểm trung bình tốt nhưng vẫn yếu ở các câu cần alias hoặc exact keyword như q07 và q09. Hybrid kết hợp dense retrieval với BM25/sparse retrieval bằng Reciprocal Rank Fusion, kỳ vọng tăng khả năng bắt đúng keyword mà vẫn giữ được tìm kiếm theo nghĩa.

**Config thay đổi:**
```
retrieval_mode = "hybrid"   
top_k_search = 10
top_k_select = 3
use_rerank = False
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.50/5 | 4.50/5 | 0.00 |
| Answer Relevance | 4.20/5 | 4.20/5 | 0.00 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.80/5 | 3.80/5 | 0.00 |

**Nhận xét:**
Variant hybrid không làm thay đổi điểm trung bình so với baseline. Các câu q01, q02, q03, q05, q06, q08 vẫn đạt điểm tối đa. q03 có citation đổi từ [2] ở baseline sang [1] ở hybrid, cho thấy thứ tự chunk liên quan tốt hơn, nhưng điểm đánh giá vẫn giữ nguyên.

Các câu yếu vẫn chưa cải thiện:
- q04 giữ Faithfulness = 4 và Completeness = 3 vì câu trả lời còn thiếu/không đầy đủ chi tiết ngoại lệ hoàn tiền cho sản phẩm kỹ thuật số.
- q07 giữ Completeness = 2 vì câu trả lời còn thiếu chi tiết alias "Approval Matrix for System Access".
- q09 vẫn thất bại với "Tôi không biết" vì context không có đủ thông tin về ERR-403-AUTH hoặc retrieval chưa tìm được evidence liên quan.
- q10 vẫn Relevance = 1 và Completeness = 2 vì tài liệu không có thông tin về quy trình hoàn tiền khẩn cấp cho khách hàng VIP.

**Kết luận:**
Variant 1 chưa tốt hơn baseline theo scorecard tổng thể. Tất cả metric trung bình đều bằng nhau: Faithfulness 4.50, Relevance 4.20, Context Recall 5.00, Completeness 3.80.

Tuy vậy, hybrid vẫn là hướng hợp lý để giữ làm variant vì nó thay đổi retrieval theo đúng đặc điểm corpus: văn bản chính sách cần semantic search, còn mã lỗi/tên chuyên ngành cần keyword search. Kết quả hiện tại cho thấy vấn đề còn lại có thể nằm ở dữ liệu thiếu evidence, câu trả lời chưa đủ chi tiết, hoặc cần query transform/rerank thay vì chỉ đổi retrieval sang hybrid.

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
   > Lỗi phổ biến nhất không phải là không retrieve được tài liệu đúng, mà là retrieve đúng source nhưng câu trả lời chưa đầy đủ hoặc chưa abstain tốt khi context thiếu. Nói cách khác, nút thắt nằm ở evidence selection và generation grounding hơn là ở indexing cơ bản.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Việc đổi từ dense sang hybrid không tạo cải thiện tích cực. Biến có khả năng tác động lớn hơn ở vòng sau nhiều khả năng là rerank hoặc prompt grounding/abstain, vì đây mới là nơi ảnh hưởng trực tiếp đến completeness và faithfulness ở các câu khó.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Nhóm sẽ thử một pipeline dạng dense retrieve → rerank → top-3 select → grounded answer. Đồng thời cần siết prompt theo hướng: chỉ trả lời khi ít nhất một chunk chứa evidence trực tiếp; nếu không đủ evidence thì phải trả lời “Không đủ dữ liệu”.
