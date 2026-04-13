# Tuning Log — RAG Pipeline (Day 08 Lab)

> **Nguyên tắc A/B:** Chỉ đổi **MỘT biến** mỗi lần để biết chính xác điều gì tạo ra cải thiện.
> Người quyết định kiến trúc: **Lê Huy Hồng Nhật (Tech Lead)**

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13  
**Config:**
```
retrieval_mode = "dense"
chunking_strategy = "semantic split"
top_k_search = 10
top_k_select = 3
use_rerank = False
threshold = 0.35
llm_model = "gpt-4o-mini"
```

**System Prompt:** Ràng buộc grounding, abstain, citation `[n]`; đã mở rộng (Sprint 4) cho abstain có cấu trúc, đa nguồn, và so sánh phiên bản SLA.

**Scorecard Baseline (test_questions.json — 10 câu mẫu):**

| Metric | Average Score (1–5) | Quy đổi (0–1.0) | Target | Status |
|--------|-------------------|-----------------|--------|--------|
| Faithfulness | 4.60 / 5 | 0.92 | > 0.90 | ✅ |
| Answer Relevance | 4.20 / 5 | 0.84 | > 0.85 | ❌ |
| Context Recall | 4.80 / 5 | 0.96 | > 0.80 | ✅ |
| Completeness | 4.10 / 5 | 0.82 | > 0.80 | ✅ |
| Abstain Accuracy | — | 0.50 | = 1.00 | ❌ |

**Câu hỏi yếu nhất (Baseline Dense):**
- **q09** (ERR-403-AUTH): abstain đúng nhưng Faithfulness/Relevance thấp nếu answer quá ngắn, thiếu gợi ý Helpdesk.
- **q10** (Hoàn tiền VIP): cần trả lời theo chính sách chung + nêu không có quy trình VIP riêng trong tài liệu.

**Giả thuyết nguyên nhân (Error Tree):**
- [x] Retrieval: Dense bỏ lỡ exact keyword (alias "Approval Matrix" → "Access Control SOP")
- [ ] Indexing: Chunking cắt giữa điều khoản
- [x] Generation: Abstain / trả lời theo phạm vi tài liệu chưa đủ chi tiết
- [x] Pipeline: Điểm hybrid (RRF) nhỏ hơn `RELEVANCE_THRESHOLD` → trước đây có thể bị coi là "không có context" dù đã retrieve chunk (đã sửa trong `rag_answer.py`)

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Người thực hiện:** Lê Huy Hồng Nhật (kiến trúc) + Nguyễn Quốc Khánh (hybrid_search)  
**Biến thay đổi DUY NHẤT:** `retrieval_mode`: `"dense"` → `"hybrid"` (Dense + BM25S + RRF k=60)  
**Lý do chọn biến này:**
> Baseline Dense bỏ lỡ các query dùng keyword chính xác và alias. Hybrid giữ Dense (semantic) + BM25 (keyword), RRF tổng hợp rank.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
dense_weight   = 0.6
sparse_weight  = 0.4
RRF_K          = 60
top_k_search   = 10
top_k_select   = 3
```

**Kết quả A/B (test_questions.json — 10 câu mẫu):**

| Metric | Baseline (Dense) | Variant (Hybrid) | Delta | Ghi chú |
|--------|-----------------|-----------------|-------|---------|
| Faithfulness | 4.60/5 (0.92) | 4.20/5 (0.84) | −0.40 | Có thể do thêm chunk nhiễu hoặc judge trên abstain |
| Answer Relevance | 4.20/5 (0.84) | 4.20/5 (0.84) | 0 | Tương đương |
| Context Recall | 4.80/5 (0.96) | 4.80/5 (0.96) | 0 | Tương đương |
| Completeness | 4.10/5 (0.82) | 4.10/5 (0.82) | 0 | Tương đương |

**Một số câu tiêu biểu:** q06 — Hybrid có thể đạt completeness cao hơn khi BM25 bắt đúng section "escalate"; q07 — alias inject giúp HIT tên cũ "Approval Matrix".

**Kết quả A/B (grading_questions.json — 10 câu khó):**

| Metric | Baseline (Dense) | Variant (Hybrid) | Delta |
|--------|-----------------|-----------------|-------|
| Faithfulness | 4.20/5 (0.84) | 4.20/5 (0.84) | 0 |
| Answer Relevance | 4.20/5 (0.84) | 4.20/5 (0.84) | 0 |
| Context Recall | 4.80/5 (0.96) | 4.80/5 (0.96) | 0 |
| Completeness | 3.20/5 (0.64) | 3.10/5 (0.62) | −0.10 |

**Kết luận:**
> **Chọn Hybrid làm default** — ổn định alias/keyword; đồng thời đã sửa lỗi gating: điểm RRF không còn bị so sánh trực tiếp với `threshold` 0.35 (gây abstain sai khi vẫn có chunk). Prompt được bổ sung để cải thiện completeness (đa nguồn, Điều 3, VIP, SLA penalty, HR "3 ngày").

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

1. **Lỗi phổ biến:** Completeness thấp trên câu đa chi tiết — retrieve đúng nhưng generation bỏ sót điều khoản (gq01 so phiên bản, gq08 hai ngữ cảnh "3 ngày"). Abstain / phạm vi: cần trả lời có cấu trúc khi tài liệu không có penalty hoặc không có mã lỗi.

2. **Biến tác động lớn:** Chunking + alias injection + hybrid; sau sửa lỗi threshold vs RRF, hybrid không còn bị "câm" dù đã lấy được Access Control SOP (vd. gq05 contractor / Admin Access).

3. **Hướng tiếp theo:** Tăng `top_k_select` cho câu multi-document; rerank chọn lọc nhiễu sau hybrid; HyDE cho query mơ hỏng.
