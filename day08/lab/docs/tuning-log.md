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
llm_model = gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.90/5 |
| Relevance | 4.90/5 |
| Context Recall | 4.10/5 |
| Completeness | 4.10/5 |

**Câu hỏi yếu nhất (điểm thấp):**
- **q09 (ERR-403-AUTH)** - Context Recall = 0/5: Dense search không tìm được error code cụ thể, chỉ trả về access-control docs không liên quan.
- **q06 (Escalation P1)** - Context Recall = 2/5: Dense bỏ lỡ escalation steps chi tiết, lấy được section 4 về escalation nhưng không phải P1 escalation.
- **q02 (Refund timeframe)** - Context Recall = 4/5: Thiếu context đầy đủ về điều kiện hoàn tiền.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias (q09: "ERR-403-AUTH" không match semantic)
- [x] Retrieval: Top-k quá ít → thiếu evidence (q06: chỉ 3 chunks lấy được section 4, thiếu P1 escalation steps)
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 13/04/2026  
**Biến thay đổi:** use_rerank  
**Lý do chọn biến này:**
Chọn `use_rerank=True` (hybrid retrieval) vì baseline dense search có 2 lỗi chính:
1. **q09 (ERR-403-AUTH)**: Recall=0 - Dense bỏ lỡ error code cụ thể vì nó không có semantic matching. Cần BM25 keyword search để catch exact codes.
2. **q06 (Escalation P1)**: Recall=2 - Dense chỉ lấy được section 4 (access escalation) không phải P1 escalation. Reranking có thể sắp xếp lại P1 sections lên top.

Giải pháp: Hybrid (dense + BM25) sẽ: 
- BM25 catch "ERR-403", "P1", exact keywords
- Dense catch semantic similarity
- Reranker sắp xếp theo relevance → cải thiện Recall

**Config thay đổi:**
```
retrieval_mode = "hybrid"   
use_rerank = True
use_query_transform =  True,
"transform_strategy": "expansion",
"dense_weight": 0.6,   
"sparse_weight": 0.4,  
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.9/5 | 5/5 | +0.1 |
| Answer Relevance | 4.9/5 | 5/5 | +0.1 |
| Context Recall | 4.1/5 | 3.8/5 | -0.3 |
| Completeness | 4.1/5 | 3.9/5 | -0.2 |

**Nhận xét:**

**Cải thiện:**
- **q02 (Refund timeframe):** Recall 4→5 ✓ - Hybrid search bắt được tất cả 3 sections (Điều 2, 3, 4) và reranker sắp xếp đúng thứ tự → ngữ cảnh đầy đủ hơn.

**Kém hơn (5 câu hỏi bị sụt chất lượng):**
- **q06 (Escalation P1):** Completeness 5→4 - Reranker vẫn không fix được Recall=2 (lấy section 4 access escalation), answer quality giảm.
- **q07 (Approval Matrix):** Recall 5→4, Completeness 5→4 - Reranker sắp xếp nhầm section 2, 4 lên trước section 1 → mất info chính.
- **q08 (Remote work):** Recall 5→4 - Hybrid mất 1 important chunk từ leave-policy.
- **q09 (ERR-403-AUTH):** Vẫn Recall=0, Completeness 4→3  - **Hybrid + rerank KHÔNG fix được error code problem!** Reranker scores tất cả chunks ~0.016 (uniform), không sắp xếp được.
- **q10 (VIP refund):** Completeness 4→1 (catastrophic) - Reranker hoàn toàn sai lệch, answer "Không tìm thấy" thay vì dùng Điều 5.

**Kết luận:**

**Variant 1 KHÔNG tốt hơn baseline.** Thực tế tệ hơn: Recall -0.3, Completeness -0.2.

**Bằng chứng thất bại:**
1. Chỉ cải thiện 1/10 câu (q02), nhưng làm xấu 5/10 câu (q06, q07, q08, q09, q10).
2. **Không fix được vấn đề chính (q09):** Error code "ERR-403-AUTH" vẫn Recall=0. Lý do: Reranker scores tất cả chunks ~0.016 (không phân biệt), BM25 không match được error code cụ thể.
3. Thêm regression: Reranker ranking sai (q07, q08), query expansion tạo noise (q10: Completeness 4→1), uniform scores (~0.016) → reranker không hoạt động.

**Root cause:** Reranker không được fine-tune cho domain này, weights hybrid (dense=0.6, sparse=0.4) không phù hợp.


---

## Tóm tắt học được

**Sprint 4 - Học từ Variant 1 failure:**

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   - **Reranker scores không phân biệt được (tất cả ~0.016)** → Reranker không được fine-tune cho domain, hoặc corpus thiếu explicit structure (error codes, section markers) để reranker nhận diện.
   - **Error code matching problem (q09):** BM25 weight (0.4) không đủ để catch "ERR-403-AUTH" vì corpus không có explicit error code documentation. Cần thêm reference data.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   - **Top-k search (10→3) + reranker:** Hybrid retrieval gây regression do: (1) reranker scores uniform → không sắp xếp được, (2) top-k quá ít (3) → reranker không có candidate tốt để chọn.
   - **Query transform (expansion):** Tạo noise, làm mất focus cho specific questions (q10: Completeness 4→1).
   - **Kết luận:** Dense-only config có quality tốt hơn Hybrid+Rerank cho dataset này (corpus nhỏ, semantic similarity đủ).

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   - **Option A (Retrieval tune):** Tăng top_k_search từ 10→15, điều chỉnh dense/sparse weights → để reranker có thêm candidates tốt.
   - **Option B (Data):** Thêm "Error Code Reference" document với structured data (ERR-403-AUTH = ..., ERR-500 = ...) → BM25 + reranker sẽ match tốt hơn q09.
   - **Option C (Model):** Fine-tune cross-encoder reranker trên domain docs → fix uniform scores (~0.016) problem.
   - **Option D (Chunking):** Tăng chunk_size từ 400→600, giảm overlap (80→50) → mỗi chunk có đủ context để reranker phán đoán tốt hơn (fix q07, q08 regression).
