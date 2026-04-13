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
| Faithfulness | 4.60 /5 |
| Answer Relevance | 4.50 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 4.00 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
- q07 (Approval Matrix) — Completeness = 2/5: dense retrieve đúng source `access_control_sop` nhưng model không nêu được tên tài liệu cụ thể "Access Control SOP" trong câu trả lời.
- q09 (ERR-403-AUTH) — Faithfulness = 2/5, Relevance = 3/5: không có doc nào chứa mã lỗi này, nhưng model đoán "lỗi liên quan đến xác thực" thay vì abstain hoàn toàn.
- q10 (Hoàn tiền VIP) — Relevance = 2/5, Completeness = 3/5: model trả lời đúng hướng nhưng không trích dẫn rõ nguồn và thiếu thông tin về thời gian xử lý.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding — model không abstain đúng cách (q09), không cite tên tài liệu (q07)
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** `retrieval_mode = "dense"` → `retrieval_mode = "hybrid"`  
**Lý do chọn biến này:**
> Giả thuyết từ Error Tree: dense bỏ lỡ exact keyword/alias ở q07 và q09. Corpus có cả ngôn ngữ tự nhiên (policy, HR) lẫn tên riêng/mã lỗi (ERR-403, Approval Matrix). Kỳ vọng BM25 khớp exact term giúp tăng Context Recall và Completeness cho hai câu này. Chi phí thấp, không thay đổi generation layer — biến an toàn nhất để thử.

**Config thay đổi:**
```
retrieval_mode = "hybrid"   # dense_weight=0.6, sparse_weight=0.4, RRF K=60
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.60 /5 | 4.60 /5 | 0 |
| Answer Relevance | 4.50 /5 | 4.30 /5 | −0.20 |
| Context Recall | 5.00 /5 | 5.00 /5 | 0 |
| Completeness | 4.00 /5 | 3.90 /5 | −0.10 |

**Nhận xét:**
> Variant 1 (hybrid + rerank) có kết quả **hỗn hợp** — tổng thể tốn 0.30 điểm nhưng có những cải thiện cục bộ:
> - q06 (Escalation P1): **Cải thiện** từ 4 → 5 completeness! Hybrid retrieval + rerank lấy được context đầy đủ hơn về escalation workflow.
> - q09 (ERR-403-AUTH): **Tệ hơn** từ 3 → 1 completeness. Variant hybrid/rerank làm model hoàn toàn abstain "Tôi không biết" thay vì partial answer — này LLM-as-Judge đánh giá không tốt.
> - q07 (Approval Matrix): Cả hai config đều không cite tên tài liệu (completeness = 2) — vấn đề không phải retrieval mà generation.
> Context Recall = 5.0 ở cả hai: hybrid không thêm được source nào có giá trị, chỉ thay đổi ranking/context quality.

**Kết luận:**
> Variant 1 giảm 0.30 điểm tổng hợp (Relevance −0.20, Completeness −0.10; Faithfulness không đổi). Hybrid retrieval **có lợi cho q06** nhưng **có hại cho q09**. Trên balance, chưa xứng đáng thay thế baseline vì:
> 1. Cải thiện tại q06 không bù được hại tại q09 + q10
> 2. Faithfulness giữ nguyên (4.60), nhưng Relevance giảm (4.50 → 4.30) → model trả lời ít relevant hơn
> 3. Với corpus nhỏ (~29 chunks), dense embedding đã đủ tốt. BM25 giới hạn (không hiểu semantic, chỉ exact keyword) không giúp ích.

---

## Variant 2

**Biến thay đổi:** `query_transform = None` → `query_transform = "expansion"` (giữ `retrieval_mode = "dense"`)  
**Config:**
```
retrieval_mode = "dense"       # giữ nguyên như baseline
query_transform = "expansion"  # LLM sinh 2-3 alias/paraphrase, retrieve từng cái, merge dedup
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.60 | 4.40 | 4.40 | Baseline |
| Answer Relevance | 4.60 | 4.40 | 4.20 | Baseline |
| Context Recall | 5.00 | 5.00 | 5.00 | Tie |
| Completeness | 3.90 | 3.40 | 3.20 | Baseline |

> Nhận xét Variant 2: expansion làm giảm thêm so với Variant 1. Sub-queries loãng context: q01 (SLA P1) bị giảm Completeness từ 5 → 2 vì các sub-queries "Thời gian phản hồi P1" kéo về chunk khác, model bỏ sót "15 phút phản hồi ban đầu". q06 tiếp tục bị ảnh hưởng tương tự Variant 1. q09 vẫn không có doc nên model abstain. Expansion phù hợp hơn với corpus lớn và query thực sự dùng alias không có trong doc.

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Generation failure, không phải retrieval failure. Context Recall = 5.0 trên cả 3 strategies — dense đã retrieve đúng source cho hầu hết câu. Vấn đề thực sự: model không abstain đúng cách khi context mơ hồ (q09), và không cite tên tài liệu cụ thể dù chunk có thông tin (q07). Cần cải thiện grounded prompt, không cần thay đổi retrieval.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Không có biến retrieval nào giúp cải thiện — baseline dense là tốt nhất. Biến thực sự có tác động là chất lượng prompt generation: instruction abstain ("nếu không có trong tài liệu, nói rõ không tìm thấy") và instruction cite tên tài liệu cụ thể. Đây là bài học quan trọng: không nên tuning retrieval khi lỗi thực sự nằm ở generation.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Tập trung vào generation layer: (1) Sửa grounded prompt — thêm instruction ép model cite tên tài liệu đầy đủ, giải quyết q07. (2) Thêm câu instruction abstain rõ ràng hơn: "Nếu câu trả lời không được đề cập trực tiếp trong tài liệu, trả lời: Không tìm thấy thông tin trong tài liệu nội bộ." để fix q09. (3) Tăng `top_k_select` từ 3 → 5 cho q06 — câu escalation cần nhiều chunk để cover đủ các bước. That's all for the architecture
