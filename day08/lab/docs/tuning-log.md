# Tuning Log - RAG Pipeline (Day 08 Lab)

> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13
**Config:**

```
retrieval_mode = "dense"
chunk_size     = 400 tokens (≈ 1600 chars)
overlap        = 80 tokens  (≈ 320 chars)
top_k_search   = 10
top_k_select   = 3
use_rerank     = False
llm_model      = gemini-2.5-flash (Vertex AI, temperature=0, max_tokens=1024)
embedding      = text-multilingual-embedding-002 (Vertex AI, 768-dim)
```

**Scorecard Baseline:**

| Metric           | Average Score |
|------------------|---------------|
| Faithfulness     | 4.60 /5       |
| Answer Relevance | 5.00 /5       |
| Context Recall   | 5.00 /5       |
| Completeness     | 4.29 /5       |

**Câu hỏi yếu nhất:**

- **q01, q08** (Completeness=3) - trả lời đúng fact cốt lõi nhưng thiếu chi tiết phụ (q01: chỉ nêu 4 giờ, không đề cập
  thêm SLA response time; q08: thiếu điều kiện sau probation)
- **q07** (Faithfulness=1) - model tự thêm đường dẫn file `it/access-control-sop.md` vào câu trả lời mà thông tin đó
  không rõ ràng trong retrieved chunks $\rightarrow$ hallucination nhẹ

**Giả thuyết nguyên nhân (Error Tree):**

- [x] Generation: Model thêm thông tin ngoài context (q07 Faithfulness=1)
- [x] Generation: Thiếu chi tiết phụ trong câu trả lời (q01, q08 Completeness=3)
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Indexing: Chunking cắt giữa điều khoản

---

## Variant 1 - Hybrid Retrieval (Sprint 3)

**Ngày:** 2026-04-13
**Biến thay đổi:** `retrieval_mode` dense $\rightarrow$ hybrid (Dense + BM25 via RRF)
**Lý do chọn biến này:**
Corpus có cả ngôn ngữ tự nhiên (policy, HR) lẫn exact term (P1, ERR-403, Level 3, SLA). Giả thuyết: BM25 sẽ giúp recall
tốt hơn cho các query có keyword chính xác, trong khi dense giữ được semantic matching cho query dùng alias.

**Config thay đổi:**

```
retrieval_mode = "hybrid"   # dense_weight=0.6, sparse_weight=0.4 (default, chưa tune)
# Tất cả tham số khác giữ nguyên
```

**Scorecard Variant 1:**

| Metric           | Baseline | Variant 1 | Delta     |
|------------------|----------|-----------|-----------|
| Faithfulness     | 4.60 /5  | 5.00 /5   | **+0.40** |
| Answer Relevance | 5.00 /5  | 4.50 /5   | **-0.50** |
| Context Recall   | 5.00 /5  | 5.00 /5   | 0.00      |
| Completeness     | 4.29 /5  | 3.14 /5   | **-1.14** |

**Per-question:**

| Câu | Baseline F/R/Rc/C | Variant F/R/Rc/C    | Better?  |
|-----|-------------------|---------------------|----------|
| q01 | 5/5/5/3           | 5/5/5/3             | Tie      |
| q02 | 5/5/5/5           | 5/5/5/3             | Baseline |
| q03 | 5/5/5/None        | 5/5/5/5             | Variant  |
| q04 | 5/5/5/None        | 5/5/5/None          | Tie      |
| q05 | 5/5/5/5           | 5/5/5/5             | Tie      |
| q06 | 5/5/5/5           | 5/None/5/1          | Baseline |
| q07 | 1/5/5/5           | 5/1/5/1             | Baseline |
| q08 | 5/5/5/3           | 5/5/5/None          | Baseline |
| q09 | 5/None/None/None  | None/None/None/None | Baseline |
| q10 | 5/5/5/4           | 5/5/5/4             | Tie      |

**Nhận xét:**

Hybrid tốt hơn baseline ở:

- **Faithfulness** (+0.40): Dense baseline hallucinate đường dẫn file ở q07 (Faithful=1). Hybrid tránh được điều này.

Hybrid kém hơn baseline ở:

- **q07 (Approval Matrix)** - Đây là failure mode điển hình nhất. BM25 cho "Approval Matrix" điểm 0 (không khớp keyword
  nào trong corpus tiếng Việt), kéo các chunk nhiễu vào top-3, đẩy chunk đúng ra ngoài. Model abstain dù Recall=5 (
  source đúng được retrieve). Dense xử lý tốt hơn vì semantic search hiểu "Approval Matrix" ≈ "ma trận phê duyệt".

- **q06 (Escalation P1)** - BM25 khớp keyword "P1" và "on-call" trong `access-control-sop.md` (emergency access
  section), đưa chunk sai vào top-3. Model trả lời về cấp quyền tạm thời thay vì escalation process. Relevance=None,
  Completeness=1.

- **q02 (Completeness 5$\rightarrow$3)** - Dense baseline giữ được "7 ngày **làm việc**" (working days), hybrid mất chi
  tiết "làm việc".

**Kết luận:**
Hybrid **không tốt hơn baseline** trên test set này. Nguyên nhân chính:

1. BM25 tokenizer dùng `.lower().split()` - không có Vietnamese tokenizer $\rightarrow$ nhiễu cao
2. Corpus nhỏ (29 chunks) và chủ yếu tiếng Việt $\rightarrow$ BM25 yếu, dense đủ mạnh
3. `top_k_select=3` quá chặt - một chunk BM25 nhiễu đủ để đẩy chunk đúng ra ngoài
4. `sparse_weight=0.4` chưa được tune - có thể giảm xuống 0.2 để cải thiện

**Config tốt nhất cho grading: `retrieval_mode="dense"`, `use_rerank=False`**

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   Completeness thấp ở các câu hỏi multi-part: model trả lời đúng fact chính nhưng bỏ sót chi tiết phụ (điều kiện, ngoại
   lệ, số ngày cụ thể). Lỗi nằm ở generation (context đủ, nhưng prompt không ép model liệt kê đầy đủ).

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   `retrieval_mode` - việc đổi sang hybrid gây regression rõ rệt (-1.14 completeness). BM25 tokenizer chất lượng thấp
   trên tiếng Việt là bottleneck.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   Giảm `sparse_weight` từ 0.4 xuống 0.2 và đo lại, hoặc dùng Vietnamese tokenizer (`underthesea`) cho BM25 để cải thiện
   keyword matching. Ngoài ra, tune prompt để ép model liệt kê đủ chi tiết (cải thiện Completeness).
