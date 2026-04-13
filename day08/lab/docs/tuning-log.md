# Tuning Log — RAG Pipeline (Day 08 Lab)

> A/B so sánh: **baseline** = dense, không rerank · **variant** = hybrid (RRF) + cross-encoder rerank.  
> Điểm số chi tiết: chạy `python eval.py` (cần `OPENAI_API_KEY`) và xem `results/scorecard_*.md`.

---

## Baseline (Sprint 2)

**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens (ước lượng)
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini (temperature=0)
```

**Quan sát nhanh (qualitative):**
- Dense ổn với câu hỏi diễn đạt gần văn bản gốc (SLA P1, hoàn tiền 7 ngày).
- Dễ hụt khi query dùng **từ khóa hiếm** hoặc **alias** (ví dụ “Approval Matrix”): embedding có thể không đứng đầu đúng chunk ghi chú đổi tên tài liệu.

**Scorecard Baseline:** xem file `results/scorecard_baseline.md` sau khi chạy eval.

---

## Variant 1 (Sprint 3)

**Biến đổi chính:** `retrieval_mode = "hybrid"` (dense + BM25, RRF) và `use_rerank = True` (cross-encoder).

**Lý do:**
- Corpus trộn **tiếng Việt tự nhiên** và **ký hiệu/keyword** (P1, Level 3, ERR-403, Flash Sale) → BM25 bổ sung recall cho từ hiếm.
- **RRF** hợp nhất thứ hạng dense và sparse mà không cần scale score thủ công.
- **Rerank** giảm nhiễu khi top-10 vẫn lẫn chunk liên quan mức độ thấp.

**Config:**
```
retrieval_mode = "hybrid"
top_k_search = 10
top_k_select = 3
use_rerank = True
cross_encoder = cross-encoder/ms-marco-MiniLM-L-6-v2
```

**Scorecard Variant:** `results/scorecard_variant.md`

**Kết luận (cần khớp với số liệu eval):**
- Kỳ vọng: **context recall** và **relevance** cao hơn ở câu có alias/keyword; chi phí tính toán tăng (BM25 + cross-encoder trên CPU/GPU).

---

## Bảng so sánh metrics (điền từ `compare_ab` / scorecard)

| Metric | Baseline | Variant | Delta |
|--------|----------|---------|-------|
| Faithfulness | _xem scorecard_ | _xem scorecard_ | _chạy eval_ |
| Answer Relevance | _xem scorecard_ | _xem scorecard_ | _chạy eval_ |
| Context Recall | _xem scorecard_ | _xem scorecard_ | _chạy eval_ |
| Completeness | _xem scorecard_ | _xem scorecard_ | _chạy eval_ |

---

## Tóm tắt học được

1. **Lỗi phổ biến:** retrieval sai đoạn → LLM vẫn trả lời “hợp lý” nhưng hallucinate; cần prompt abstain + judge faithfulness.
2. **Biến tác động lớn:** chiến lược retrieval (dense vs hybrid) và chất lượng chunk/metadata.
3. **Hướng tiếp:** query expansion có kiểm soát cho alias; hoặc metadata filter theo `department` nếu có routing chủ đề.
