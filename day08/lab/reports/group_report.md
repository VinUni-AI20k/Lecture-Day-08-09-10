# Báo Cáo Nhóm — RAG Pipeline (Day 08 Lab)

**Môn:** AI in Action (AICB-P1)  
**Chủ đề:** RAG Pipeline: Indexing → Retrieval → Generation → Evaluation  
**Ngày nộp:** 2026-04-13  

---

## 1. Giới thiệu

### 1.1 Bối cảnh
Trong bối cảnh doanh nghiệp có nhiều tài liệu nội bộ phân tán (chính sách hoàn tiền, SLA xử lý sự cố, quy trình cấp quyền, FAQ IT, chính sách nhân sự), việc tìm kiếm và truy xuất thông tin chính xác là thách thức lớn. Nhân viên helpdesk thường phải đọc nhiều tài liệu để trả lời một câu hỏi, dẫn đến thời gian phản hồi chậm và nguy cơ trả lời sai.

### 1.2 Mục tiêu
Nhóm xây dựng **trợ lý nội bộ cho khối CS + IT Helpdesk** sử dụng kiến trúc RAG (Retrieval-Augmented Generation):
- **Input**: Câu hỏi tiếng Việt về chính sách, SLA, quy trình
- **Output**: Câu trả lời chính xác, có citation trích nguồn, hoặc "Không đủ dữ liệu" khi thông tin không có trong tài liệu
- **Giải quyết**: Tự động truy xuất đúng đoạn tài liệu liên quan và sinh câu trả lời grounded, giảm thời gian tra cứu từ phút xuống giây

### 1.3 Phạm vi hệ thống
- Index 5 tài liệu nội bộ (tổng ~29 chunks)
- Hỗ trợ 3 chiến lược retrieval: dense, sparse (BM25), hybrid (RRF fusion)
- Evaluation pipeline với 4 metrics: Faithfulness, Relevance, Context Recall, Completeness
- 10 test questions bao gồm easy, medium, hard, và câu hỏi abstain

---

## 2. Phân công công việc

### Thành viên nhóm và vai trò

| Thành viên | Vai trò | Sprint | Nhiệm vụ cụ thể |
|-----------|---------|--------|------------------|
| **Dương Phương Thảo** | Tech Lead + Retrieval | Sprint 1, 2 | Chunking (paragraph-based splitting, intelligent boundary detection); `retrieve_dense()`, `call_llm()`, update prompt RAG pipeline; Test `rag_answer()` với ≥3 câu hỏi |
| **Phạm Thanh Tùng** | Retrieval Owner | Sprint 1, 3 | `get_embedding()` trong `index.py` (Sprint 1); `retrieve_sparse()` trong `rag_answer.py` — implement BM25 search (Sprint 3) |
| **Nguyễn Năng Anh** | Retrieval Owner | Sprint 1, 3 | `build_index()` trong `index.py` — ChromaDB upsert pipeline (Sprint 1); `retrieve_hybrid()` trong `rag_answer.py` — RRF fusion (Sprint 3) |
| **Nguyễn Ngọc Hiếu** | Eval Owner | Sprint 3, 4 | Test questions, expected evidence, scorecard chạy baseline + variant, A/B comparison |
| **Mai Phi Hiếu** | Documentation Owner | Sprint 4 | `architecture.md`, `tuning-log.md`, group report, tài liệu kỹ thuật |

### Phân bố công việc theo Sprint

```
Sprint 1 (60') ─── Build Index ──────────────────────────────────────
  Phạm Thanh Tùng  → get_embedding() (OpenAI text-embedding-3-small)
  Nguyễn Năng Anh  → build_index() (ChromaDB pipeline)
  Dương Phương Thảo → chunk_document() + _split_by_size() (chunking logic)

Sprint 2 (60') ─── Baseline RAG ─────────────────────────────────────
  Dương Phương Thảo → retrieve_dense() + call_llm() + prompt engineering
  Dương Phương Thảo → Test rag_answer() với ≥3 câu hỏi mẫu

Sprint 3 (60') ─── Tuning ───────────────────────────────────────────
  Phạm Thanh Tùng  → retrieve_sparse() (BM25 search)
  Nguyễn Năng Anh  → retrieve_hybrid() (Dense + Sparse + RRF)
  Nguyễn Ngọc Hiếu → Chuẩn bị test questions + evaluation criteria

Sprint 4 (60') ─── Evaluation + Docs ────────────────────────────────
  Nguyễn Ngọc Hiếu → Chạy scorecard baseline + variant, A/B comparison
  Mai Phi Hiếu     → architecture.md, tuning-log.md, group report
```

---

## 3. Mô tả hệ thống

### 3.1 Kiến trúc tổng thể

Hệ thống RAG gồm 3 module chính, tương ứng 3 file Python:

```
┌─────────────────────────────────────────────────────────┐
│                    RAG PIPELINE                          │
│                                                          │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ index.py │ →  │ rag_answer.py│ →  │   eval.py    │   │
│  │ Sprint 1 │    │ Sprint 2+3   │    │  Sprint 4    │   │
│  │          │    │              │    │              │   │
│  │ Preprocess│    │ Retrieve     │    │ Scorecard    │   │
│  │ Chunk    │    │ Rerank       │    │ A/B Compare  │   │
│  │ Embed    │    │ Generate     │    │ Report       │   │
│  │ Store    │    │              │    │              │   │
│  └──────────┘    └──────────────┘    └──────────────┘   │
│       ↓                ↕                    ↑           │
│  ┌──────────┐                                           │
│  │ ChromaDB │ ← Vector Store (cosine similarity)        │
│  └──────────┘                                           │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Module 1: Indexing (`index.py`)

**Mục đích**: Đọc tài liệu → tiền xử lý → chia chunk → embed → lưu vào vector store.

**Các bước xử lý:**

1. **Preprocess** (`preprocess_document()`):
   - Parse metadata từ header: `Source`, `Department`, `Effective Date`, `Access`
   - Tách header khỏi nội dung (dừng khi gặp `===`)
   - Normalize khoảng trắng (max 2 dòng trống liên tiếp)

2. **Chunking** (`chunk_document()` + `_split_by_size()`):
   - **Ưu tiên 1**: Split theo heading `=== Section ===` → mỗi section = 1 đơn vị ngữ nghĩa
   - **Ưu tiên 2**: Nếu section > 1600 ký tự → split tiếp theo paragraph (`\n\n`)
   - **Ưu tiên 3**: Fallback character-based với intelligent boundary detection:
     - Tìm paragraph break (`\n\n`) gần nhất
     - Nếu không có → tìm newline (`\n`)
     - Nếu không có → tìm dấu chấm câu (`. `)
   - **Overlap**: 320 ký tự — giữ paragraph cuối của chunk trước → đầu chunk tiếp
   - Mỗi chunk giữ đầy đủ 5 metadata fields

3. **Embed + Store** (`get_embedding()` + ChromaDB `upsert()`):
   - OpenAI `text-embedding-3-small` (1536 dimensions)
   - ChromaDB PersistentClient, collection `rag_lab`, cosine similarity
   - ID format: `{filename}_{chunk_index}`

### 3.3 Module 2: RAG Answer (`rag_answer.py`)

**Mục đích**: Nhận câu hỏi → truy xuất context → sinh câu trả lời grounded.

**Pipeline chính** (`rag_answer()`):

```
Query → [1. Retrieve] → [2. Rerank/Select] → [3. Build Context] → [4. Generate] → Answer
```

**Chiến lược Retrieval:**

| Strategy | Hàm | Cách hoạt động |
|----------|-----|----------------|
| **Dense** | `retrieve_dense()` | Embed query → ChromaDB cosine search → score = 1 - distance |
| **Sparse** | `retrieve_sparse()` | Load all chunks → BM25Okapi tokenize → score by keyword match |
| **Hybrid** | `retrieve_hybrid()` | Dense + Sparse → RRF fusion (K=60, dense 0.6, sparse 0.4) |

**Prompt Grounding** (4 quy tắc):
1. Evidence-only: Chỉ trả lời từ context
2. Abstain: Thiếu context → "Không đủ dữ liệu"
3. Citation: Gắn `[1]`, `[2]` theo thứ tự chunk
4. Short & clear: Ngắn gọn, rõ ràng

**LLM**: `gpt-4o-mini`, temperature=0, max_tokens=512

### 3.4 Module 3: Evaluation (`eval.py`)

**Mục đích**: Đánh giá chất lượng pipeline theo 4 metrics.

| Metric | Đo gì | Cách tính |
|--------|-------|-----------|
| **Faithfulness** | Answer có bám context không? | Grounding ratio: % từ quan trọng trong answer xuất hiện trong context |
| **Answer Relevance** | Answer có trả lời đúng câu hỏi không? | Query keyword overlap trong answer |
| **Context Recall** | Retriever có mang về đúng source không? | % expected sources được retrieve |
| **Completeness** | Answer có đầy đủ thông tin không? | Jaccard similarity với expected answer |

---

## 4. Demo — Ví dụ Input/Output

### 4.1 Câu hỏi thành công (q05 — IT Helpdesk)

**Input:**
```
Query: "Tài khoản bị khóa sau bao nhiêu lần đăng nhập sai?"
Config: retrieval_mode="dense", top_k_select=3
```

**Output:**
```json
{
  "answer": "Tài khoản bị khóa sau 5 lần đăng nhập sai liên tiếp [1].",
  "sources": ["support/helpdesk-faq.md"],
  "config": {"retrieval_mode": "dense", "top_k_select": 3}
}
```
✅ Answer match 100% expected. Citation `[1]` trỏ đúng source. Faithfulness 5/5.

### 4.2 Câu hỏi abstain đúng (q09 — ERR-403-AUTH)

**Input:**
```
Query: "ERR-403-AUTH là lỗi gì và cách xử lý?"
```

**Output:**
```json
{
  "answer": "Không đủ dữ liệu để trả lời câu hỏi này.",
  "sources": [],
  "config": {"retrieval_mode": "dense"}
}
```
✅ Abstain đúng — ERR-403-AUTH không có trong bất kỳ tài liệu nào. Pipeline không hallucinate.

### 4.3 Câu hỏi thất bại (q07 — Alias query)

**Input:**
```
Query: "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"
```

**Output:**
```json
{
  "answer": "Không đủ dữ liệu để trả lời câu hỏi này.",
  "sources": ["it/access-control-sop.md"]
}
```
❌ **False abstain** — Context đã retrieve đúng `access_control_sop.txt` (trong đó có dòng "Ghi chú: Tài liệu này trước đây có tên Approval Matrix for System Access") nhưng LLM vẫn trả "Không đủ dữ liệu" vì prompt quá nghiêm khắc.

### 4.4 Câu hỏi cross-document (q06 — Escalation P1)

**Input:**
```
Query: "Escalation trong sự cố P1 diễn ra như thế nào?"
```

**Output:**
```
Escalation trong sự cố P1 diễn ra như sau:
1. On-call IT Admin có thể cấp quyền tạm thời (max 24 giờ) sau khi được Tech Lead phê duyệt bằng lời.
2. Sau 24 giờ, phải có ticket chính thức hoặc quyền bị thu hồi tự động.
3. Mọi quyền tạm thời phải được ghi log vào hệ thống Security Audit.

Ngoài ra, trong quy trình xử lý sự cố P1, nếu không có phản hồi trong 10 phút, ticket sẽ tự động escalate lên Senior Engineer [1][2].
```
✅ Trả lời xuất sắc — kết hợp thông tin từ cả SLA doc lẫn Access Control SOP. Multi-document synthesis thành công.

---

## 5. Đánh giá

### 5.1 Kết quả Baseline

| Metric | Score | Đánh giá |
|--------|-------|----------|
| Faithfulness | 4.40/5 | **Tốt** — phần lớn answer grounded trong context |
| Answer Relevance | 5.00/5 | **Xuất sắc** — luôn trả lời đúng trọng tâm câu hỏi |
| Context Recall | 5.00/5 | **Xuất sắc** — retrieval tìm đúng source 100% |
| Completeness | 3.40/5 | **Trung bình** — thiếu chi tiết phụ ở nhiều câu |

### 5.2 Ưu điểm

1. **Indexing chất lượng cao**: Chunking theo heading tự nhiên, metadata đầy đủ 5 fields, không có chunk bị cắt giữa điều khoản. Đây là nền tảng vững chắc cho retrieval.

2. **Retrieval gần như hoàn hảo**: Context Recall 5.00/5 — dense retrieval tìm đúng source cho 100% câu hỏi. Embedding model `text-embedding-3-small` phù hợp tốt với corpus tiếng Việt.

3. **Grounded generation**: Prompt 4 quy tắc hoạt động tốt — answer có citation `[1][2]`, abstain đúng khi không có thông tin (q09).

4. **Multi-document synthesis**: q06 (Escalation P1) kết hợp thông tin từ SLA doc và Access Control SOP thành công.

5. **Code cấu trúc tốt**: Tách biệt rõ ràng indexing / retrieval / generation / evaluation. Hàm `rag_answer()` linh hoạt với parameter `retrieval_mode`, `use_rerank`.

### 5.3 Nhược điểm

1. **Variant crash hoàn toàn**: Thiếu dependency `rank-bm25` → hybrid retrieval không chạy được → không có dữ liệu A/B thực tế. Đây là lỗi nghiêm trọng nhất.

2. **False abstain** (q07, q10): Prompt grounding quá nghiêm khắc khiến LLM abstain khi lẽ ra nên suy luận từ context. q07: context có "Approval Matrix" nhưng LLM không dám map alias. q10: LLM nên trả lời "không có quy trình đặc biệt cho VIP".

3. **Rerank chưa implement**: `rerank()` chỉ return `candidates[:top_k]` (pass-through), nhưng `VARIANT_CONFIG` set `use_rerank=True`. Điều này gây misleading.

4. **BM25 tokenization đơn giản**: `doc.lower().split()` không có stemming, stopword removal, hay xử lý tiếng Việt. Hiệu quả BM25 trên corpus tiếng Việt có thể không tối ưu.

5. **Completeness thấp (3.40/5)**: LLM có xu hướng trả lời ngắn quá, bỏ qua điều kiện kèm theo (q01 thiếu "15 phút phản hồi", q08 thiếu "sau probation").

6. **Evaluation metrics đơn giản**: Dùng keyword matching thay vì LLM-as-Judge → scoring có thể không chính xác cho những câu trả lời paraphrase đúng nhưng dùng từ khác.

---

## 6. Hướng phát triển

### 6.1 Sửa lỗi cấp bách (Short-term)
1. **Cài `rank-bm25`**: `pip install rank-bm25` và chạy lại `eval.py` để có kết quả hybrid thực tế
2. **Implement `rerank()` thực sự**: Dùng cross-encoder `ms-marco-MiniLM-L-6-v2` hoặc LLM-based reranking
3. **Điều chỉnh prompt**: Giảm false abstain bằng cách cho phép LLM suy luận hợp lý từ context

### 6.2 Cải thiện chất lượng (Medium-term)
1. **Vietnamese-aware BM25**: Dùng `underthesea` hoặc `pyvi` để tokenize tiếng Việt thay vì whitespace splitting
2. **LLM-as-Judge**: Implement trong `eval.py` để scoring chính xác hơn
3. **Query expansion**: Implement `transform_query()` để xử lý alias/tên cũ (q07 scenario)
4. **Prompt iteration**: Chỉnh prompt để LLM trả lời đầy đủ hơn các chi tiết phụ

### 6.3 Nâng cấp kiến trúc (Long-term)
1. **Metadata filtering**: Dùng `where` clause trong ChromaDB query để filter theo department, effective_date
2. **Multi-hop reasoning**: Chain-of-thought cho cross-document queries (q06)
3. **Streaming response**: Tích hợp streaming LLM response cho UX tốt hơn
4. **Web UI**: Frontend đơn giản (Streamlit/Gradio) để demo interactive
5. **Feedback loop**: Cho phép user đánh giá answer → cải thiện retrieval ranking

---

*Report prepared by: Mai Phi Hiếu (Documentation Owner)*  
*Date: 2026-04-13*
