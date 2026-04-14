# Group Report — Lab Day 08: RAG Pipeline

**Nhóm:** C401-C5
**Thành viên & vai trò:**

| Thành viên       | Vai trò chính                           | Deliverable tiêu biểu                                                                       |
| ---------------- | --------------------------------------- | ------------------------------------------------------------------------------------------- |
| Nam Khánh Nam    | Retrieval Owner (Sprint 1 base)         | `index.py` (chunking skeleton, metadata extraction), grounded prompt refine                 |
| Lê Hữu Hùng      | Tech Lead (Sprint 2)                    | Baseline `rag_answer.py` (retrieve_dense, call_llm), Sprint 2 wiring                        |
| Lê Tú Nam        | Retrieval Owner (Sprint 3 testing)      | Thử nghiệm các variant, phân tích `compare_retrieval_strategies`                            |
| Nguyễn Minh Hiếu | Documentation Owner (Sprint 2–4)        | `architecture.md`, `tuning-log.md`, phân tích ablation                                      |
| Đỗ Minh Phúc     | Tech Lead + Eval Owner (Sprint 1, 3, 4) | Paragraph-aware chunking, rerank cross-encoder,`ablation.py`, `run_grading.py`, grading run |

**Ngày nộp:** 13/04/2026
**Pipeline config cuối cùng cho grading:** `Dense + Rerank` (Variant 1)

---

## 1. Vấn đề & bối cảnh

Nhóm xây trợ lý nội bộ CS + IT Helpdesk trả lời câu hỏi về SLA, chính sách hoàn tiền, cấp quyền truy cập, FAQ IT, quy định nghỉ phép — chỉ dựa trên 5 tài liệu nội bộ (`data/docs/`). Yêu cầu cốt lõi: **grounded** (không bịa), **cite nguồn**, **abstain** khi thiếu evidence.

**Corpus:** 5 documents → **29 chunks** (paragraph-aware, `CHUNK_SIZE=400 tokens`, `overlap=80`). Metadata mỗi chunk: `source`, `section`, `department`, `effective_date`, `access`.

| File                     | Department  | Số chunk |
| ------------------------ | ----------- | -------- |
| `policy_refund_v4.txt`   | CS          | 6        |
| `sla_p1_2026.txt`        | IT          | 5        |
| `access_control_sop.txt` | IT Security | 7        |
| `it_helpdesk_faq.txt`    | IT          | 6        |
| `hr_leave_policy.txt`    | HR          | 5        |

**Embedding:** `paraphrase-multilingual-MiniLM-L12-v2` (Sentence Transformers, cosine). **Vector store:** ChromaDB PersistentClient. **LLM:** `gpt-4o-mini` (temperature=0, max_tokens=512).

---

## 2. Kiến trúc pipeline

```
User Query
   │
   ├─► (Sprint 3: Rerank enabled) Dense retrieve top-10 from ChromaDB
   │                        (embed: paraphrase-multilingual-MiniLM-L12-v2,
   │                                   │  cosine similarity, 29 chunks)
   │                                   ▼
   │                        Cross-Encoder rerank (ms-marco-MiniLM-L-6-v2)
   │                                   │
   │                                   ▼
   │                               Top-3 chunks
   │                                   │
   ▼                                   ▼
build_grounded_prompt  ◄───────── context block (source · section · effective_date)
   │
   ▼
gpt-4o-mini (temperature=0, max_tokens=512)
   │
   ▼
Answer + [citation] + sources[]
```

**Biến duy nhất đổi so với baseline:** `use_rerank: False → True`. Mọi tham số khác giữ nguyên (xem [tuning-log.md](../docs/tuning-log.md)).

---

## 3. Quyết định kỹ thuật chính (team-level)

| #   | Quyết định                                                                     | Lý do (bằng chứng)                                                                                                                                      |
| --- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Paragraph-aware chunking** thay vì fixed-size                                | Corpus có heading `=== Section ===` rõ + điều khoản theo đoạn — cắt fixed-size làm mất ngữ cảnh điều khoản. Sau khi đổi, Context Recall đạt 5.00 stable |
| 2   | **Temperature = 0** cho LLM                                                    | Scorecard cần reproducible;`gpt-4o-mini` temp=0 cho output ổn định ±0.1 điểm giữa các lần chạy                                                          |
| 3   | **Variant 1 (Dense+Rerank)** cho grading, không phải V3 (Hybrid+Rerank)        | V3 thực tế kém hơn V1: Faithfulness 4.10 vs 4.30, Relevance 4.30 vs 4.50. Stacking kỹ thuật ≠ cải thiện                                                 |
| 4   | **Không dùng Hybrid (V2)** dù được lecture đề cập                              | BM25 `text.lower().split()` không tokenize được tiếng Việt + corpus 29 chunk quá nhỏ → sparse nhiễu kéo Completeness −0.20                              |
| 5   | **LLM-as-Judge** (`gpt-4o-mini` + `response_format=json_object`) cho 4 metrics | Tiết kiệm thời gian chấm thủ công 10 câu × 4 metric × 2 config = 80 điểm; đạt bonus +2                                                                  |

---

## 4. Kết quả thực nghiệm

### 4.1 A/B ablation (đúng luật 1 biến)

| Metric           | Baseline (Dense) | V1 (Rerank)      | V2 (Hybrid)  | V3 (Hybrid+Rerank) |
| ---------------- | ---------------- | ---------------- | ------------ | ------------------ |
| Faithfulness     | 4.10             | **4.30 (+0.20)** | 4.20 (+0.10) | 4.10 (0.00)        |
| Answer Relevance | 4.30             | **4.50 (+0.20)** | 4.20 (−0.10) | 4.30 (0.00)        |
| Context Recall   | 5.00             | 5.00             | 5.00         | 5.00               |
| Completeness     | 4.10             | 4.00 (−0.10)     | 3.80 (−0.30) | 4.00 (−0.10)       |

**Kết luận:** Rerank là biến đòn bẩy duy nhất. Hybrid phản tác dụng trên corpus nhỏ tiếng Việt.

### 4.2 Per-question delta (Baseline → Variant 1)

Cải thiện rõ ở câu bị noise trong top-3: **q07** (Faithful 3→4), **q09** (Faithful 1→3, Relevance 1→4 — model abstain mềm hơn, gợi ý next step).
Giảm nhẹ ở **q04** (Faithful 4→3): rerank loại mất chunk nói về digital license exception, đây là trade-off đã document.
**q10** (VIP refund) vẫn yếu (Relevance 1/5) — thông tin thật sự không có trong docs.

### 4.3 Grading run (17:00–18:00)

- `logs/grading_run.json`: đủ 10 câu, timestamp hợp lệ, dùng Variant 1.
- **gq07 abstain đúng chuẩn** (`sources: []`, đề xuất liên hệ HR/IT Security) — không bịa penalty.
- **gq05** cũng abstain khi thiếu evidence về contractor Admin Access.
- Không phát hiện hallucination trong 10 câu grading.

---

## 5. Hạn chế đã nhận diện

1. **Corpus quá nhỏ (29 chunks)** làm Hybrid retrieval không có lợi thế — kết luận này **không generalize** cho production corpus lớn.
2. **BM25 tokenizer ngây thơ** (`.split()`) — không xử lý từ ghép, dấu tiếng Việt.
3. **Completeness không cải thiện được** bằng rerank: các câu cần synthesis nhiều exception (q04 license, q10 VIP) vẫn yếu vì evidence bị phân tán qua nhiều chunk.
4. **LLM-as-Judge dao động ±0.10** giữa các lần chạy — cần chạy nhiều lần và lấy trung bình nếu delta nhỏ hơn 0.1.
5. **Không có score threshold cho abstain** — model vẫn tiêu token gọi LLM cả khi top-1 similarity < 0.35.

---

## 6. Bài học nhóm

1. **A/B rule một biến không phải formality** — V3 Hybrid+Rerank lẽ ra phải cộng dồn lợi ích, nhưng kết quả thực đo cho thấy **ngược lại**. Nếu nhóm bật cả hai từ đầu mà không ablation, chúng ta sẽ chọn V3 và mất ~0.2 Faithfulness + 0.2 Relevance so với V1.
2. **Context Recall cao ≠ Answer tốt.** Baseline đạt Recall 5.00 nhưng Faithfulness chỉ 4.10 — vấn đề nằm ở selection/ranking bên trong top-3, không phải retriever. Rerank fix được đúng điểm đó.
3. **Grounded prompt làm được việc của threshold** cho các câu abstain (q07, q09) — model không bịa mà còn gợi ý next step. Instruction "DO NOT guess. Instead suggest next steps" quan trọng ngang với instruction "cite source".
4. **Debug trước khi tuning.** Bug `UnboundLocalError` trong `retrieve_sparse` che hết kết quả Hybrid cho đến khi commit `c418202` fix. Nếu không fix, số đo V2/V3 sẽ sai.

---

## 7. Hướng mở rộng (nếu có thêm 1 giờ)

Ưu tiên theo points-per-effort:

1. **Score-threshold early-abstain** (< 0.35): −15% LLM cost, không ảnh hưởng Faithfulness.
2. **Tokenizer tiếng Việt cho BM25** (`pyvi` / `underthesea`) + mở rộng corpus: để đánh giá lại Hybrid trong điều kiện fair.
3. **Query transform HyDE** cho câu mơ hồ kiểu q10 (VIP refund): sinh hypothetical answer trước khi embed, kỳ vọng nâng Relevance q10 từ 1 → 3.
4. **Metadata enrichment**: trích xuất mã lỗi / alias (như `ERR-403-AUTH`) vào trường metadata riêng để sparse match chính xác với câu kiểu q09.

---

## 8. Checklist nộp bài

- [x] `index.py`, `rag_answer.py`, `eval.py`, `ablation.py`, `run_grading.py` — chạy end-to-end
- [x] `data/docs/` (5 tài liệu), `data/test_questions.json`
- [x] `logs/grading_run.json` — 10 câu, timestamp hợp lệ
- [x] `results/scorecard_baseline.md`, `scorecard_variant.md`, `ab_comparison.csv`, `ab_A_hybrid.csv`, `ab_B_rerank.csv`
- [x] `docs/architecture.md`, `docs/tuning-log.md`
- [x] `reports/group_report.md` (file này)
- [x] `reports/individual/*.md` — mỗi thành viên 1 file

---

_Commit evidence: `a5fd62a` (sprint1 index), `0f8e045`/`a16e6c5` (sprint2 baseline), `b2ee29b` (rerank + paragraph chunking + grading runner), `c418202` (fix retrieve_sparse + ablation), `8dc0f63`/`09459da` (architecture + tuning-log), `afa3826` (grading run)._
