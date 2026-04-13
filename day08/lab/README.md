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
| Indexing pipeline với Qdrant & Qwen Embedding | Sprint 1 |
| Baseline RAG với LangChain & Gemini Flash Lite | Sprint 2 |
| Advanced Flow với LangGraph & Hybrid Search | Sprint 3 |
| Monitoring & Eval với LangSmith Scorecard | Sprint 4 |

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
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Tạo file .env
```bash
cp .env.example .env
# Điền GOOGLE_API_KEY, LANGCHAIN_API_KEY (LangSmith)
```

### 3. Test setup
```bash
python index.py    # Xem preview preprocess + chunking (không cần API key)
```

---

## 4 Sprints

### Sprint 1 (60') — Build Index (Qdrant + Qwen)
**File:** `index.py`

**Việc phải làm:**
1. Cài đặt Qdrant Local Mode (hoặc Docker)
2. Implement `get_embedding()` dùng model `Qwen/Qwen3-Embedding-0.6B`
3. Implement `build_index()` — embed và upsert vào **Qdrant**
4. Kiểm tra dữ liệu trong Qdrant Dashboard hoặc `list_points()`

**Definition of Done:**
- [ ] Script chạy được, index đủ 5 tài liệu vào Qdrant
- [ ] Mỗi point (chunk) có đầy đủ metadata: `source`, `section`, `effective_date`
- [ ] Kiểm tra chunk hợp lý, không bị cắt giữa điều khoản

---

### Sprint 2 (60') — Baseline RAG with LangChain
**File:** `rag_answer.py`

**Việc phải làm:**
1. Thiết lập LangChain ChatModel (Gemini Flash Lite Preview)
2. Implement `retrieve_qdrant()` — tìm kiếm similarity trong Qdrant
3. Xây dựng Chain cơ bản: Prompt -> LLM -> OutputParser
4. Test hệ thống với 3+ câu hỏi mẫu

**Definition of Done:**
- [ ] Trả lời đúng "SLA ticket P1?" kèm citation
- [ ] Trả lời "Không đủ dữ liệu" cho câu hỏi không có trong docs
- [ ] Traces xuất hiện trên **LangSmith**

---

### Sprint 3 (60') — Advanced Flow with LangGraph
**File:** `rag_answer.py`

**Việc phải làm:**
1. Thiết lập **LangGraph State Machine** (Nodes: Retrieve, Grade, Generate)
2. Implement **Hybrid Search** trong Qdrant
3. Implement logic "Self-Correction" (nếu context không liên quan -> Re-query)
4. Tích hợp **FastAPI** để expose endpoint

**Definition of Done:**
- [ ] LangGraph chạy đúng luồng logic (Graph visualization)
- [ ] Hybrid search cho kết quả tốt hơn Dense search đơn thuần
- [ ] API endpoint `POST /query` hoạt động

---

### Sprint 4 (60') — Evaluation with LangSmith
**File:** `eval.py`

**Việc phải làm:**
1. Chạy đánh giá tự động trên **LangSmith Dataset**
2. Phân tích scorecard: Faithfulness, Relevancy, Correctness
3. Hoàn thiện tài liệu kiến trúc và báo cáo
4. Demo API và Dashboard LangSmith

**Definition of Done:**
- [ ] Demo chạy hoàn chỉnh từ Index -> Graph -> API
- [ ] LangSmith Dashboard ghi lại đầy đủ Delta giữa các phiên bản
- [ ] Tài liệu giải thích được luồng LangGraph

## Tech Stack (Thống nhất)

| Layer | Công cụ |
|-------|---------|
| LLM | Gemini Flash Lite Preview |
| Embedding | Qwen/Qwen3-Embedding-0.6B (SentenceTransformer) |
| Vector store | Qdrant (Local mode) |
| Orchestration | LangGraph |
| Serving | FastAPI + Uvicorn |
| Monitoring | LangSmith |

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

## Phân vai & Nhiệm vụ cụ thể

| Vai trò | Trách nhiệm chính (Tasks) | Sprint lead |
|---------|---------------------------|------------|
| **Tech Lead** | - Framework LangGraph (State, Nodes, Edges)<br>- API FastAPI & Uvicorn<br>- Tích hợp hệ thống end-to-end | 2, 3 |
| **Retrieval Owner** | - Qdrant setup & Indexing logic<br>- Tích hợp Qwen Embedding model<br>- Hybrid search & Data Preprocessing | 1, 3 |
| **Eval Owner** | - Tích hợp LangSmith (Tracing, Datasets)<br>- Xây dựng Scorecard & Test set<br>- Đánh giá hiệu năng A/B | 2, 4 |
| **Documentation Owner** | - Vẽ Architecture Diagram (LangGraph flow)<br>- Tuning log & Báo cáo tổng kết<br>- Quản lý deliverables | 4 |

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
- Qdrant documentation: https://qdrant.tech/documentation/
- LangChain / LangGraph: https://python.langchain.com/
- LangSmith: https://smith.langchain.com/
- Qwen Embedding: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
