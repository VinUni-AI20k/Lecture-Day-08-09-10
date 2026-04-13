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
├── api_server.py         # FastAPI: POST /api/rag cho UI Next.js
├── eval.py               # Sprint 4: Scorecard + A/B Comparison
├── rag-ui/               # Next.js: /chat + panel luồng RAG
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
| Code pipeline | `index.py`, `rag_answer.py`, `eval.py` | Tech Lead |
| Test questions | `data/test_questions.json` (đã có mẫu) | Eval Owner |
| Scorecard | `results/scorecard_baseline.md`, `scorecard_variant.md` | Eval Owner |
| Architecture docs | `docs/architecture.md` | Documentation Owner |
| Tuning log | `docs/tuning-log.md` | Documentation Owner |
| Báo cáo cá nhân | `reports/individual/[ten].md` | Từng người |

---

## Phân vai (Giao ngay phút đầu)

| Vai trò | Trách nhiệm chính | Sprint lead |
|---------|------------------|------------|
| **Tech Lead** | Giữ nhịp sprint, nối code end-to-end | 1, 2 |
| **Retrieval Owner** | Chunking, metadata, retrieval strategy, rerank | 1, 3 |
| **Eval Owner** | Test questions, expected evidence, scorecard, A/B | 3, 4 |
| **Documentation Owner** | architecture.md, tuning-log, báo cáo nhóm | 4 |

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

## Web UI (Next.js) + API (FastAPI)

Giao diện chat và panel “luồng RAG” gọi API trong `api_server.py`.

### 1. Chạy API (terminal 1)

Từ thư mục `lab/`:

```bash
pip install -r requirements.txt
uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
```

- `GET /api/health` — kiểm tra API và số document Chroma.
- `POST /api/rag` — body JSON: `query`, `retrieval_mode` (`dense`|`sparse`|`hybrid`), `use_rerank`, tuỳ chọn `top_k_search` / `top_k_select`. Header `X-Request-ID` (tuỳ chọn) được ghi lại trong `logs/api_access.log` và `extra.request_id` trong `logs/runs.jsonl`.

Biến môi trường (tuỳ chọn, thêm vào `.env`):

- `RAG_CORS_ORIGINS` — danh sách origin CORS, mặc định `http://localhost:3000,http://127.0.0.1:3000`
- `LOG_LEVEL` — mặc định `INFO`

### 2. Chạy UI (terminal 2)

```bash
cd rag-ui
npm install
# Tuỳ chọn nếu API không ở cổng 8000:
# echo NEXT_PUBLIC_RAG_API_URL=http://127.0.0.1:8010 > .env.local
npm run dev
```

Mở [http://localhost:3000](http://localhost:3000) → **Mở chat**. Debug client: `NEXT_PUBLIC_DEBUG_RAG_UI=1` trong `.env.local`.

---

## Tài nguyên tham khảo

- Slide Day 08: `../lecture-08.html`
- ChromaDB docs: https://docs.trychroma.com
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
- Sentence Transformers: https://www.sbert.net
- rank-bm25: https://github.com/dorianbrown/rank_bm25
