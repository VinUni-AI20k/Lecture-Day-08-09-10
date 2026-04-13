# AI in Action — Lecture Slides: Day 08 · 09 · 10

> **Course:** AI in Action – Phase 1 (Nền tảng)
> **Topic block:** Từ RAG đến Multi-Agent đến Data Pipeline — xây dựng hệ AI vận hành thực tế

---

## Overview

Repo này hiện là **workspace lab Day 08** (mã nguồn RAG ở root: `src/`, `data/`, `docs/`). **Slide HTML** của cả ba ngày được lưu trong [`archived/`](archived/) để mở trực tiếp trên browser khi học hoặc dạy.

Ba ngày trên lớp tạo thành một **chuỗi bài học** liên tục: cùng một artifact (trợ lý nội bộ cho khối CS + IT Helpdesk) được nâng cấp qua từng ngày — từ RAG có kiểm soát, sang điều phối đa agent, đến tầng data pipeline và observability. Trong repo này, **chỉ có lab Day 08** được đưa ra để làm việc; Day 09 và Day 10 (ở đây) là **slide tham chiếu**, không kèm mã lab trong layout hiện tại.

```
Day 08 ─ RAG grounded          →   Day 09 ─ Supervisor-Workers      →   Day 10 ─ Data + Observe
   Retrieve đúng đoạn               Route + trace + MCP                  Freshness · quality · alert
```

### Cấu trúc repo (tóm tắt)

| Phần | Vị trí |
|------|--------|
| **Frontend (Next.js, Bun)** — UI trợ lý, mock SSE, trace/RAG demo | **[`frontend/`](frontend/)** — chi tiết cài đặt và mô tả dự án: **[`frontend/README.md`](frontend/README.md)** |
| Lab Day 08 (code) | [`src/`](src/) — `index.py`, `rag_answer.py`, `eval.py` |
| Dữ liệu & câu hỏi test | [`data/`](data/) — `docs/`, `test_questions.json` |
| Tài liệu thiết kế / tuning | [`docs/`](docs/) |
| Báo cáo cá nhân (template) | [`reports/individual/`](reports/individual/) |
| Slide Day 08 · 09 · 10 | [`archived/day08/`](archived/day08/), [`archived/day09/`](archived/day09/), [`archived/day10/`](archived/day10/) |

---

## Day 08 — RAG Pipeline

**Slide:** [`archived/day08/lecture-08.html`](archived/day08/lecture-08.html)

**Chi tiết sprint, setup và Definition of Done:** [`archived/day08/README.md`](archived/day08/README.md)

### Vấn đề mở bài
Vector store đã có, nhưng agent vẫn trả lời sai — tại sao?

### Nội dung chính

| Chủ đề | Chi tiết |
|--------|----------|
| **Indexing pipeline** | Chunking đúng, metadata rõ, freshness có kiểm soát |
| **Retrieval strategy** | Dense vs Sparse vs Hybrid; query transformation; top-k & rerank funnel |
| **Grounded prompting** | Inject context đúng cách để model bớt hallucinate |
| **RAG evaluation** | Đo bằng scorecard (faithfulness, relevance, correctness), không bằng cảm giác |

### Hoạt động trong lớp
1. **Error Tree** — phân tích nguyên nhân gốc rễ của RAG failure
2. **Chunking Clinic** — so sánh chiến lược chunk
3. **Retrieval decision map** — chọn chiến lược phù hợp với use case
4. **Prompt Surgery** — sửa grounded prompt thực tế

### Deliverables (lab trong repo này)

- [`src/index.py`](src/index.py) — indexing (preprocess → chunk → embed → store)
- [`src/rag_answer.py`](src/rag_answer.py) — retrieval + grounded answer (+ tuning variant)
- [`src/eval.py`](src/eval.py) — scorecard và so sánh A/B; kết quả markdown (ví dụ `scorecard_baseline.md`) trong `src/results/` khi chạy eval
- [`docs/architecture.md`](docs/architecture.md), [`docs/tuning-log.md`](docs/tuning-log.md)
- [`reports/individual/`](reports/individual/) — báo cáo cá nhân theo template

---

## Day 09 — Multi-Agent & Kết Nối Hệ Thống

**Slide:** [`archived/day09/lecture-09.html`](archived/day09/lecture-09.html)

> **Ghi chú:** Trong repo này chỉ có file slide trong `archived/`. Mã lab multi-agent (nếu có) không nằm trong layout hiện tại.

### Vấn đề mở bài
Một agent giỏi vẫn quá tải khi bài toán phức tạp — khi nào nên tách hệ?

### Nội dung chính

| Chủ đề | Chi tiết |
|--------|----------|
| **Multi-agent patterns** | Supervisor-Workers, Pipeline, Peer-to-peer, Hierarchical |
| **Supervisor-Worker** | Route theo tín hiệu quan sát được (task type, confidence, risk) |
| **Worker contract** | Rõ input · rõ output · rõ lỗi — chuẩn để test và thay thế |
| **MCP architecture** | Agent cắm vào năng lực bên ngoài (tool, API) theo chuẩn chung |
| **A2A vs MCP** | Phân biệt giao việc cho agent khác vs lấy capability từ bên ngoài |
| **LangGraph** | Node, edge, state, route function, HITL checkpoint |
| **Trace & Observability** | Ghi task · route reason · worker IO · answer cuối để debug và học |

### Hoạt động trong lớp
1. **Agent overload map** — xác định điểm single-agent quá tải
2. **Chọn pattern** — so sánh 4 pattern cho 3 use case thực tế
3. **Tách artifact Day 08** — chia RAG agent thành supervisor + workers
4. **Phân biệt MCP với A2A** — hands-on classification

### Deliverables (mục tiêu trên lớp — không có trong repo này)

- `supervisor_agent.py` — router với route logic rõ ràng
- `worker_*.py` — retrieval, policy, synthesis workers
- `trace_log.jsonl` — trace ghi đủ bước cho mỗi run
- `mcp_config.json` — khai báo tool/MCP connection

---

## Day 10 — Data Pipeline & Data Observability

**Slide:** [`archived/day10/lecture-10.html`](archived/day10/lecture-10.html)

> **Ghi chú:** Trong repo này chỉ có file slide trong `archived/`. Mã lab pipeline (nếu có) không nằm trong layout hiện tại.

### Vấn đề mở bài
Data từ database công ty đột nhiên sai — agent hallucinate. Hệ của bạn có biết không?

> *Garbage in → garbage out. Đừng debug model trước khi debug pipeline.*

### Nội dung chính

| Chủ đề | Chi tiết |
|--------|----------|
| **ETL vs ELT** | Transform trước hay sau load — quyết định dựa trên governance, latency, cost |
| **Batch vs Streaming** | Trade-off latency vs complexity; khi nào cần streaming thực sự |
| **Ingestion layer** | CDC, rate limit, backpressure, retry + backoff, DLQ |
| **Data transformation** | Làm sạch PII, chuẩn hoá schema, dedupe, encoding |
| **Data quality as code** | Expectation suite chạy như unit test trong CI/CD |
| **5 pillars of observability** | Freshness · Volume · Distribution · Schema · Lineage |
| **Orchestration** | DAG, dependency, retry, idempotency, SLA alert |
| **Incident triage** | Runbook — detect → isolate → fix → verify → post-mortem |

### Hoạt động trong lớp
1. **ETL hay ELT? Batch hay Streaming?** — phân loại 4 tình huống thực tế
2. **Source map & failure points** — ingestion plan cho DB + API + PDF
3. **Dirty data repair** — sửa dataset có missing, duplicate, wrong format
4. **Incident triage** — xử lý freshness breach theo runbook

### Deliverables (mục tiêu trên lớp — không có trong repo này)

- `etl_pipeline.py` — ingest → clean → validate → embed end-to-end
- `quality/expectations.py` — expectation suite kiểm tra data quality
- `monitoring/freshness_check.py` — freshness + volume monitor
- `before_after_eval.csv` — bằng chứng data quality ảnh hưởng answer quality
- `pipeline_architecture.md` + `data_contract.md` + `runbook.md`

---

## Mạch xuyên suốt 3 ngày

```
                  ┌──────────────────────────────────────────────────────┐
                  │              Trợ lý nội bộ CS + IT Helpdesk          │
                  └──────────────────────────────────────────────────────┘
                            ↑               ↑               ↑
                         Day 08          Day 09          Day 10
                      RAG grounded   Supervisor +    Data pipeline
                      retrieve đúng  workers route   + observability
                      đoạn, đo được  trace rõ,MCP    detect issue
                                     A2A                 sớm
```

Theo chuỗi bài học, mỗi ngày xây trên artifact của ngày trước:

- **Day 08** cung cấp pipeline RAG (trong repo này: code trong [`src/`](src/) + dữ liệu [`data/`](data/)) làm nền retrieval
- **Day 09** (trên lớp) bọc nó vào `retrieval_worker`, thêm `policy_worker`, `synthesis_worker` và supervisor route
- **Day 10** (trên lớp) đảm bảo dữ liệu feeding vào toàn bộ hệ không bị stale, dirty hay missing

---

## Tech Stack

| Layer | Công cụ |
|-------|---------|
| LLM | Claude / GPT-4o |
| Embedding | text-embedding-3-small / BGE |
| Vector store | ChromaDB / Qdrant / pgvector |
| Orchestration | LangGraph / CrewAI |
| MCP | MCP SDK |
| Pipeline | Python ETL / Prefect / Airflow |
| Quality | Great Expectations |
| Monitoring | Custom + Grafana |

---

## How to Use

### Slide (HTML)

Mỗi slide deck là một file HTML độc lập — mở trực tiếp trong browser, không cần server:

```bash
# Linux — ví dụ mở bằng trình duyệt mặc định
xdg-open archived/day08/lecture-08.html
xdg-open archived/day09/lecture-09.html
xdg-open archived/day10/lecture-10.html
```

(trên macOS có thể dùng `open archived/day08/lecture-08.html` tương tự.)

**Điều hướng:**

- `←` / `→` hoặc `Space` — chuyển slide
- `N` — toggle speaker notes
- `Home` / `End` — về đầu / cuối

### Lab Day 08 (Python)

```bash
cp .env.example .env   # điền API key trong .env
pip install -r requirements.txt
python src/index.py
python src/rag_answer.py
python src/eval.py
```

### Frontend (Next.js — thư mục `frontend/`)

Giao diện trợ lý nội bộ (chat, SSE mock, pipeline, HIL email…) dùng **Bun**. Hướng dẫn đầy đủ: **[`frontend/README.md`](frontend/README.md)** (`cp` env, `bun install`, `bun run build`, chạy dev/prod và cổng).

---

*AI in Action · VinUniversity · 2026*
