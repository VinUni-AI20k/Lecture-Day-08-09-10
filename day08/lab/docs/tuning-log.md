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
llm_model = Deepseek-chat
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4/5 |
| Answer Relevance | 5/5 |
| Context Recall | 5/5 |
| Completeness | 4.6/5 |

**Câu hỏi yếu nhất (điểm thấp):**
> `q05` (Tài khoản bị khóa sau bao nhiêu lần đăng nhập sai?) - Faithfulness = `1/5`. Baseline nhiều khả năng retrieve đúng FAQ nhưng model trả lời sai con số do chunk chứa nhiều số gần nhau (`5 phút`, `5 lần`, `90 ngày`, `7 ngày`), nên bị nhiễu và không bám chặt vào evidence.
> `q10` (Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?) - Faithfulness = `1/5`. Tài liệu chỉ mô tả quy trình hoàn tiền chuẩn, không có nhánh riêng cho khách VIP; baseline có dấu hiệu suy diễn thêm ngoại lệ không tồn tại thay vì trả lời theo đúng phạm vi context.
> `q09` (ERR-403-AUTH là lỗi gì và cách xử lý?) - Completeness = `3/5`, Faithfulness = `4/5`. Đây là câu hỏi không có đáp án trực tiếp trong docs, nên baseline chưa abstain đủ mạnh: có thể nêu được hướng chung nhưng vẫn thiếu câu trả lời chuẩn kiểu "không đủ dữ liệu" và dễ chen suy đoán ngoài tài liệu.

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
| Faithfulness | 4/5 | 4.2/5 | +0.2 |
| Answer Relevance | 5/5 | 4.8/5 | -0.2 |
| Context Recall | 5/5 | 5/5 | +0 |
| Completeness | 4.6/5 | 4.5/5 | -0.1 |

**Nhận xét:**
> Variant 1 cải thiện rõ nhất ở `q10`: Faithfulness tăng từ `1/5` lên `4/5` trong khi Relevance, Context Recall và Completeness vẫn giữ `5/5`. Điều này phù hợp với giả thuyết ban đầu rằng Hybrid retrieval bắt tốt hơn các mã/keyword cứng, nên câu trả lời bám sát evidence hơn.
> Tuy nhiên, Variant 1 không cải thiện đồng đều trên toàn bộ tập câu hỏi. `q05` có Faithfulness tăng nhẹ (`1/5 -> 2/5`) nhưng Completeness giảm mạnh (`5/5 -> 3/5`), nên tổng thể vẫn kém Baseline. `q06` giảm Relevance (`5/5 -> 4/5`) và `q08` giảm Faithfulness khá rõ (`4/5 -> 2/5`). `q09` có trade-off khi Completeness tăng (`3/5 -> 4/5`) nhưng Relevance giảm (`5/5 -> 4/5`), nên xem như hòa.

**Kết luận:**
> Chưa có đủ bằng chứng để kết luận Variant 1 tốt hơn Baseline, nên chưa nên thay thế cấu hình mặc định ở thời điểm này. Dù Faithfulness trung bình tăng từ `4.0` lên `4.2` (`+0.2`), các chỉ số còn lại lại không tốt hơn: Relevance giảm từ `5.0` xuống `4.8`, Completeness giảm từ `4.6` xuống `4.5`, còn Context Recall giữ nguyên `5.0`.
> Ở mức câu hỏi cụ thể, có `6/10` câu hòa (`q01`, `q02`, `q03`, `q04`, `q07`, `q09`), `3/10` câu Baseline tốt hơn (`q05`, `q06`, `q08`) và chỉ `1/10` câu Variant tốt hơn rõ rệt (`q10`). Kết luận hợp lý là Hybrid retrieval có tiềm năng với nhóm câu hỏi chứa mã/alias, nhưng cần kết hợp thêm rerank hoặc tinh chỉnh `top_k`/metadata trước khi rollout rộng hơn.

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
