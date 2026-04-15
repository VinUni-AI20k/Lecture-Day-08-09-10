# Lab Day 08 — Full RAG Pipeline

**Môn:** AI in Action (AICB-P1)  
**Chủ đề:** RAG Pipeline: Indexing → Retrieval → Generation → Evaluation  
**Thời gian:** 4 giờ (4 sprints x 60 phút)

---

## Bối cảnh

Nhóm xây dựng **trợ lý nội bộ cho khối CS + IT Helpdesk**: trả lời câu hỏi về chính sách, SLA ticket, quy trình cấp quyền, và FAQ bằng chứng cứ được retrieve có kiểm soát.

**Câu hỏi mẫu hệ thống phải trả lời được:**
- "SLA xử lý ticket P1 là bao lâu?"
- "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?"
- "Ai phải phê duyệt để cấp quyền Level 3?"

---

## Mục tiêu học tập

| Mục tiêu | Sprint liên quan |
|-----------|----------------|
| Build indexing pipeline với metadata | Sprint 1 |
| Build retrieval + grounded answer function | Sprint 2 |
| So sánh dense / hybrid / rerank, chọn và justify variant | Sprint 3 |
| Đánh giá pipeline bằng scorecard, A/B comparison | Sprint 4 |

---

## Cấu trúc repo

```
lab/
├── index.py              # Sprint 1: Preprocess → Chunk → Embed → Store
├── rag_answer.py         # Sprint 2+3: Retrieve → (Rerank) → Generate
├── eval.py               # Sprint 4: Scorecard + A/B Comparison
│
├── data/
│   ├── docs/             # Policy documents để index
│   │   ├── policy_refund_v4.txt
│   │   ├── sla_p1_2026.txt
│   │   ├── access_control_sop.txt
│   │   ├── it_helpdesk_faq.txt
│   │   └── hr_leave_policy.txt
│   └── test_questions.json   # 10 test questions với expected answers
│
├── docs/
│   ├── architecture.md   # Template: mô tả thiết kế pipeline
│   └── tuning-log.md     # Template: ghi lại A/B experiments
│
├── reports/
│   └── individual/
│       └── template.md   # Template báo cáo cá nhân (500-800 từ)
│
├── requirements.txt
└── .env.example
```

---

## Setup

### 1. Cài dependencies
```bash
pip install -r requirements.txt
```

### 2. Tạo file .env
```bash
cp .env.example .env
# Điền OPENAI_API_KEY hoặc GOOGLE_API_KEY
```

### 3. Test setup
```bash
python index.py    # Xem preview preprocess + chunking (không cần API key)
```

---

## 4 Sprints

### Sprint 1 (60') — Build Index
**File:** `index.py`

**Việc phải làm:**
1. Implement `get_embedding()` — chọn OpenAI hoặc Sentence Transformers
2. Implement phần TODO trong `build_index()` — embed và upsert vào ChromaDB
3. Chạy `build_index()` và kiểm tra với `list_chunks()`

**Definition of Done:**
- [ ] Script chạy được, index đủ 5 tài liệu
- [ ] Mỗi chunk có ít nhất 3 metadata fields: `source`, `section`, `effective_date`
- [ ] `list_chunks()` cho thấy chunk hợp lý, không bị cắt giữa điều khoản

---

### Sprint 2 (60') — Baseline Retrieval + Answer
**File:** `rag_answer.py`

**Việc phải làm:**
1. Implement `retrieve_dense()` — query ChromaDB với embedding
2. Implement `call_llm()` — gọi OpenAI hoặc Gemini
3. Test `rag_answer()` với 3+ câu hỏi mẫu

**Definition of Done:**
- [ ] `rag_answer("SLA ticket P1?")` → trả về câu trả lời có citation `[1]`
- [ ] `rag_answer("ERR-403-AUTH")` → trả về "Không đủ dữ liệu" (abstain)
- [ ] Output có `sources` field không rỗng

---

### Sprint 3 (60') — Tuning Tối Thiểu
**File:** `rag_answer.py`

**Chọn 1 trong 3 variants:**

| Variant | Implement | Khi nào chọn |
|---------|-----------|-------------|
| **Hybrid** | `retrieve_sparse()` + `retrieve_hybrid()` | Corpus có cả câu tự nhiên lẫn keyword/mã lỗi |
| **Rerank** | `rerank()` với cross-encoder | Dense search nhiều noise |
| **Query Transform** | `transform_query()` | Query dùng alias, tên cũ |

**Definition of Done:**
- [ ] Variant chạy được end-to-end
- [ ] Có bảng so sánh baseline vs variant (dùng `compare_retrieval_strategies()`)
- [ ] Giải thích được vì sao chọn biến đó (ghi vào `docs/tuning-log.md`)

**A/B Rule:** Chỉ đổi MỘT biến mỗi lần.

---

### Sprint 4 (60') — Evaluation + Docs + Report
**File:** `eval.py`

**Việc phải làm:**
1. Chấm điểm (thủ công hoặc LLM-as-Judge) cho 10 test questions
2. Chạy `run_scorecard(BASELINE_CONFIG)` và `run_scorecard(VARIANT_CONFIG)`
3. Chạy `compare_ab()` để thấy delta
4. Điền vào `docs/architecture.md` và `docs/tuning-log.md`
5. Viết báo cáo cá nhân (500-800 từ/người)

**Definition of Done:**
- [ ] Demo chạy end-to-end: `python index.py && python rag_answer.py && python eval.py`
- [ ] Scorecard baseline và variant đã điền
- [ ] `docs/architecture.md` và `docs/tuning-log.md` hoàn chỉnh
- [ ] Mỗi người có file báo cáo trong `reports/individual/`

---

## Deliverables (Nộp bài)

| Item | File | Owner |
|------|------|-------|
| Indexing pipeline | `index.py` | Indexing Owner |
| Retrieval & Generation | `rag_answer.py` | Retrieval Owner (Dense) + Retrieval Owner (Hybrid/Rerank) |
| Evaluation | `eval.py` | Eval Owner |
| Test questions | `data/test_questions.json` | Eval Owner |
| Scorecard | `results/scorecard_baseline.md`, `scorecard_variant.md` | Eval Owner |
| Architecture docs | `docs/architecture.md` | Documentation Owner |
| Tuning log | `docs/tuning-log.md` | Retrieval Owner (Hybrid/Rerank) + Documentation Owner |
| Báo cáo cá nhân | `reports/individual/[ten].md` | Từng người |

---

## Phân vai (Giao ngay phút đầu)

> **5 người — Retrieval được tách thành 2 vai riêng để đi sâu hơn.**

| Vai trò | Trách nhiệm chính | Sprint lead | File chính |
|---------|------------------|------------|------------|
| **Tech Lead** | Giữ nhịp sprint, `.env` setup, kết nối end-to-end, review PR | 1, 2 | `index.py`, `rag_answer.py` (nối) |
| **Indexing Owner** | `preprocess_document()`, `chunk_document()`, metadata schema, `build_index()`, kiểm tra chunk quality | 1 | `index.py` |
| **Retrieval Owner — Dense & Prompt** | `retrieve_dense()`, `call_llm()`, `build_grounded_prompt()`, baseline `rag_answer()` | 2 | `rag_answer.py` |
| **Retrieval Owner — Hybrid & Rerank** | `retrieve_sparse()` (BM25), `retrieve_hybrid()` (RRF), `rerank()`, so sánh variant vs baseline, ghi `tuning-log.md` | 3 | `rag_answer.py`, `docs/tuning-log.md` |
| **Eval & Docs Owner** | Test questions, expected evidence, `run_scorecard()`, `compare_ab()`, `architecture.md`, báo cáo nhóm | 3, 4 | `eval.py`, `docs/` |

### Chi tiết trách nhiệm từng vai

**Tech Lead**
- Tạo repo, clone, cài `requirements.txt`, kiểm tra `.env` cho cả nhóm
- Chạy smoke test sau mỗi sprint: `python index.py && python rag_answer.py`
- Giải quyết conflict khi merge code giữa Indexing Owner và Retrieval Owner

**Indexing Owner**
- Thiết kế metadata schema: `source`, `section`, `effective_date`, `access`
- Quyết định chiến lược chunk: section-first hay paragraph-first, overlap bao nhiêu
- Kiểm tra output `list_chunks()`: chunk không bị cắt giữa điều khoản
- Đảm bảo dedup trước khi upsert vào ChromaDB

**Retrieval Owner — Dense & Prompt**
- Implement `retrieve_dense()` dùng embedding OpenAI hoặc SentenceTransformer
- Implement `call_llm()` (OpenAI hoặc Gemini)
- Viết và tinh chỉnh `build_grounded_prompt()`: evidence-only, abstain, citation
- Test `rag_answer()` với ≥ 3 câu hỏi mẫu, đảm bảo abstain hoạt động đúng

**Retrieval Owner — Hybrid & Rerank**
- Implement `retrieve_sparse()` dùng BM25Okapi trên toàn corpus
- Implement `retrieve_hybrid()` dùng RRF fusion (dense + sparse)
- Implement `rerank()` — lexical fallback hoặc cross-encoder
- Chạy A/B: so sánh dense vs hybrid, có rerank vs không, ghi delta vào `tuning-log.md`
- Justify lựa chọn variant cuối cùng bằng số liệu scorecard

**Eval & Docs Owner**
- Chuẩn bị `test_questions.json`: 10 câu với `expected_answer` và `expected_sources`
- Implement `run_scorecard()`: 4 metrics (Faithfulness, Relevance, Context Recall, Completeness)
- Implement `compare_ab()`: in bảng delta baseline vs variant
- Điền `docs/architecture.md`: mô tả pipeline, decision choices
- Tổng hợp báo cáo nhóm, nhắc từng người nộp `reports/individual/`

---

## Gợi ý Debug (Error Tree)

Nếu pipeline trả lời sai, kiểm tra lần lượt:

```
1. Indexing?
   → list_chunks() → Chunk có đúng không? Metadata có đủ không?

2. Retrieval?
   → score_context_recall() → Expected source có được retrieve không?
   → Thử thay dense → hybrid nếu query có keyword/alias

3. Generation?
   → score_faithfulness() → Answer có bám context không?
   → Kiểm tra prompt: có "Answer only from context" không?
```

---

## Tài nguyên tham khảo

- Slide Day 08: `../lecture-08.html`
- ChromaDB docs: https://docs.trychroma.com
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
- Sentence Transformers: https://www.sbert.net
- rank-bm25: https://github.com/dorianbrown/rank_bm25
