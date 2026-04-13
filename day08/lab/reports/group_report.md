# Group Report — Day 08 (RAG Pipeline)

## 1. Mục tiêu

Nhóm xây dựng RAG pipeline trả lời câu hỏi nội bộ (chính sách, SLA, FAQ) dựa trên 5 tài liệu gốc, đảm bảo grounded (không bịa), có citation, và đo lường được chất lượng qua A/B testing.

## 2. Kiến trúc hệ thống

```
User query → Embedding → ChromaDB search (top-20) → Select top-8 → Abstain guard → Prompt v2 → gpt-4o-mini → Answer + [n] citation
```

- **Indexing**: 5 file → 29 chunk (heading-based, ~400 tokens, overlap 80), metadata gồm source/section/effective_date.
- **Retrieval**: Dense (cosine) là production. Hybrid (dense + BM25 RRF) đã implement nhưng thua dense ở Relevance (3.8 vs 4.2) trên bộ test 10 câu.
- **Generation**: gpt-4o-mini, temperature=0. Prompt v2 gồm 9 rules: grounded, per-fact citation, scope awareness, actionable details.
- **Abstain**: 3 lớp (empty retrieve → weak score < 0.05 → prompt rule).

Chi tiết: `docs/architecture.md`

## 3. Quyết định kỹ thuật chính

### 3.1 Tại sao giữ Dense thay vì Hybrid?

Thử nghiệm A/B ban đầu (dense vs hybrid, cùng k=10, select=3):
- Hybrid thua Relevance (3.8 vs 4.2) và Completeness (4.0 vs 4.2).
- BM25 noise làm loãng context cho câu hỏi tự nhiên.
- Hybrid chỉ có lợi thế ở câu alias/keyword hiếm (gq07 — "Approval Matrix").
- Kết luận: dense ổn định hơn trên bộ 10 câu hiện tại.

### 3.2 Tại sao tăng top_k_select từ 3 lên 8?

Phân tích failure mode baseline:
- gq05 (Zero): thiếu cả section scope lẫn section detail — chỉ 3 chunk không đủ.
- gq09 (Partial): FAQ chunk xếp thứ 4–5, bị loại khỏi top 3.
- gq06 (Partial): chunk hotline xếp thứ 7.

Tăng k_select=8 giải quyết cả 3 trường hợp. Cost trade-off: context dài hơn (~1600 tokens → ~4000 tokens) nhưng gpt-4o-mini xử lý tốt trong window 128k.

### 3.3 Tại sao hạ threshold từ 0.15 xuống 0.05?

gq05 baseline: chunk "contractor" + "Admin Access Level 4" có cosine score ~0.12, bị chặn bởi threshold=0.15 → false abstain. Hạ xuống 0.05 cho phép chunk qua; L3 (prompt rule) vẫn bảo vệ chống hallucination.

### 3.4 Prompt v1 → v2

- Thêm "stay focused" tránh over-generation (gq01 baseline có thêm v2025.3 không liên quan).
- Thêm "scope + applicability" tránh abstain sai cho câu cross-section (gq05).
- Thêm "per-fact citation" thay vì gom hết vào [1].
- Thêm "actionable details" để LLM include URL, ext., hotline (gq09).

## 4. Kết quả benchmark

### Grading questions (10 câu, bộ `grading_questions.json`)

| | Baseline | Variant (production) | Delta |
|---|:---:|:---:|:---:|
| Faithfulness | 4.90 | **5.00** | +0.10 |
| Relevance | 4.20 | **5.00** | +0.80 |
| Context Recall | 4.44 | **4.89** | +0.44 |
| Completeness | 4.10 | **4.70** | +0.60 |
| Full | 5 | **7** | +2 |
| Partial | 4 | 3 | −1 |
| Zero | 1 | **0** | −1 |
| **Raw score** | 69/98 | **83/98** | **+14** |
| **Projected /30** | 21.1 | **25.4** | **+4.3** |
| Hallucination | 0 | 0 | 0 |

Chi tiết per-question: `results/scorecard_baseline.md`, `results/scorecard_variant.md`

### Câu vẫn Partial ở variant

| Câu | Root cause | Giải pháp tiềm năng |
|-----|-----------|---------------------|
| gq02 | LLM gom citation vào [1] dù info từ 2 doc | Tách prompt rule "cross-doc citation" riêng |
| gq04 | Thiếu tên "Điều 5" trong citation | Cải thiện chunk header format |
| gq06 | ext. 9999 nằm rank 7, LLM bỏ qua | Tăng k_select hoặc thêm rerank |

## 5. Phân công nhóm và đóng góp

| Thành viên | Vai trò | Đóng góp chính |
|-----------|---------|----------------|
| Hoàng Kim Trí Thành | Nhóm trưởng | Điều phối, review/merge branch, tối ưu pipeline, xây dựng UI |
| Đặng Đình Tú Anh | Core AI | Harden abstain, citation grounding, A/B log, adversarial test |
| Quách Gia Dược | Retrieval flow | Cải thiện retrieval trace, xử lý abstain |
| Phạm Quốc Dũng | Eval/Scorecard | Edge case eval, scorecard formatting |
| Nguyễn Thành Nam | Documentation | Quick start, troubleshooting guide, tuning explanation |

Chi tiết phân công: `docs/team_task_allocation.md`

## 6. Trạng thái Git

### Branches

| Branch | Trạng thái |
|--------|-----------|
| `fork/main` | Production — đã tổng hợp tất cả |
| `fork/DangDinhTuAnh-2A202600019` | Merged — 3 đợt merge |
| `fork/PhamQuocDung-2A202600490` | Merged |
| `fork/QuachGiaDuoc-2A202600423` | Merged |
| `fork/nam/docs-day08-tasks` | Merged |

### Giai đoạn phát triển

1. **Dựng nền**: API server, ChromaDB index, Next.js UI cơ bản, telemetry framework.
2. **Phân công**: Task allocation file, priority checklist, branch strategy.
3. **Nhập core AI**: Merge branch TuAnh (abstain + citation), Gia Dược (retrieval flow), Quốc Dũng (eval), Nam (docs).
4. **UI/UX**: Panel RAG inspector, streaming SSE, Việt hóa, citation tương tác, test questions.
5. **Tối ưu**: Benchmark 10 câu, tuning k_select/threshold/prompt, đạt 83/98.

## 7. Đối chiếu yêu cầu SCORING.md

| File bắt buộc | Trạng thái |
|---------------|-----------|
| `index.py` | Chạy được, tạo 29 chunk |
| `rag_answer.py` | Chạy được, có citation + abstain |
| `eval.py` | Chạy được end-to-end |
| `data/docs/` | Đủ 5 tài liệu |
| `logs/grading_run.json` | Có, 10 câu, config variant |
| `results/scorecard_baseline.md` | Có, đủ metrics |
| `results/scorecard_variant.md` | Có, đủ metrics + A/B comparison |
| `docs/architecture.md` | Có, diagram + chunking + retrieval config |
| `docs/tuning-log.md` | Có, A/B table + per-question breakdown |
| `reports/group_report.md` | File này |
| `reports/individual/` | Đủ 5 file |
