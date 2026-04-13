# Architecture — RAG Pipeline (Day 08 Lab)

## 1. Tổng quan kiến trúc

```
[Raw policy/SOP/FAQ docs]
    ↓
[index.py]
    Preprocess → Extract metadata → Chunk → Embed
    ↓
[ChromaDB Persistent Vector Store]
    Stores: chunk text + embedding + metadata
    ↓
[rag_answer.py]
    User query → Retrieve dense/hybrid → Select top chunks → Build grounded prompt
    ↓
[LLM]
    Generate answer from retrieved context only
    ↓
[Grounded Answer + Citation + Sources]
```

**Mô tả ngắn gọn:**
Nhóm xây dựng một hệ thống RAG nội bộ để hỗ trợ CS, IT Helpdesk, HR và IT Security tra cứu nhanh các tài liệu chính sách, SLA, quy trình cấp quyền và FAQ. Hệ thống index tài liệu thành các chunk có metadata, lưu embedding trong ChromaDB, sau đó retrieve các chunk liên quan để LLM trả lời ngắn gọn kèm citation. Mục tiêu là giảm việc tìm kiếm thủ công trong nhiều tài liệu và hạn chế hallucination bằng cách bắt buộc câu trả lời dựa trên context đã retrieve.

---

## 2. Indexing Pipeline (Sprint 1)

### Tài liệu được index
| File | Nguồn | Department | Số chunk |
|------|-------|-----------|---------|
| `policy_refund_v4.txt` | policy/refund-v4.pdf | CS | 6 |
| `sla_p1_2026.txt` | support/sla-p1-2026.pdf | IT | 5 |
| `access_control_sop.txt` | it/access-control-sop.md | IT Security | 7 |
| `it_helpdesk_faq.txt` | support/helpdesk-faq.md | IT | 6 |
| `hr_leave_policy.txt` | hr/leave-policy-2026.pdf | HR | 5 |

### Quyết định chunking
| Tham số | Giá trị | Lý do |
|---------|---------|-------|
| Chunk size | 500 tokens | Được cấu hình trong code để tối ưu cho văn bản quy định, chính sách, SOP; khi split thực tế code quy đổi xấp xỉ 500 * 4 = 2000 ký tự. |
| Overlap | 100 tokens | Giữ lại ngữ cảnh giữa các chunk liền kề, đủ để bao trọn điều kiện, ngoại lệ, hoặc câu nối tiếp nhau; code quy đổi xấp xỉ 100 * 4 = 400 ký tự. |
| Chunking strategy | Heading-based + paragraph/natural-boundary fallback | Code ưu tiên split theo heading dạng === ... ===; nếu section quá dài thì split tiếp theo ranh giới tự nhiên như đoạn văn, dòng mới, dấu chấm, khoảng trắng. |
| Metadata fields | source, section, effective_date, department, access | Phục vụ filter, freshness, citation |

### Embedding model
- **Model**: paraphrase-multilingual-MiniLM-L12-v2
- **Vector store**: ChromaDB (PersistentClient)
- **Similarity metric**: Cosine

---

## 3. Retrieval Pipeline (Sprint 2 + 3)

### Baseline (Sprint 2)
| Tham số | Giá trị |
|---------|---------|
| Strategy | Dense (embedding similarity) |
| Top-k search | 10 |
| Top-k select | 3 |
| Rerank | Không |

### Variant (Sprint 3)
| Tham số | Giá trị | Thay đổi so với baseline |
|---------|---------|------------------------|
| Strategy | hybrid | Baseline dùng dense; variant đổi sang hybrid, kết hợp dense retrieval và sparse/BM25 bằng Reciprocal Rank Fusion. |
| Top-k search | 10 | Giữ nguyên |
| Top-k select | 3 | Giữ nguyên |
| Rerank | Không | Giữ nguyên |
| Query transform | Không | Giữ nguyên |

**Lý do chọn variant này:**
> Chọn hybrid vì corpus có cả văn bản tự nhiên như policy, SOP, quy trình, FAQ và các keyword/tên chuyên ngành cần match chính xác như SLA, P1, Level 3, ERR-403, Approval Matrix, Access Control SOP. Dense retrieval giúp tìm theo nghĩa khi câu hỏi được diễn đạt khác tài liệu, còn sparse/BM25 giúp bắt đúng keyword, mã lỗi, cấp quyền, tên hệ thống hoặc thuật ngữ cụ thể. Hybrid RRF kết hợp hai loại tín hiệu này nên phù hợp để tune retrieval mà không cần thay đổi embedding model hay prompt."

---

## 4. Generation (Sprint 2)

### Grounded Prompt Template
```
Answer only from the retrieved context below.
If the context is insufficient, say you do not know.
Cite the source field when possible.
Keep your answer short, clear, and factual.

Question: {query}

Context:
[1] {source} | {section} | score={score}
{chunk_text}

[2] ...

Answer:
```

### LLM Configuration
| Tham số | Giá trị |
|---------|---------|
| Model | gpt-4o-mini |
| Temperature | 0 (để output ổn định cho eval) |
| Max tokens | 512 |

---

## 5. Failure Mode Checklist

> Dùng khi debug — kiểm tra lần lượt: index → retrieval → generation

| Failure Mode | Triệu chứng | Cách kiểm tra |
|-------------|-------------|---------------|
| Index lỗi | Retrieve về docs cũ / sai version | `inspect_metadata_coverage()` trong index.py |
| Chunking tệ | Chunk cắt giữa điều khoản | `list_chunks()` và đọc text preview |
| Retrieval lỗi | Không tìm được expected source | `score_context_recall()` trong eval.py |
| Generation lỗi | Answer không grounded / bịa | `score_faithfulness()` trong eval.py |
| Token overload | Context quá dài → lost in the middle | Kiểm tra độ dài context_block |

---

## 6. Diagram (tùy chọn)

Sơ đồ dưới đây mô tả hai luồng retrieval đã dùng trong evaluation: baseline dense và variant hybrid.

```mermaid
flowchart LR
    A[User Query] --> B{Retrieval mode}

    B -->|Baseline: dense| C[Query embedding]
    C --> D[ChromaDB vector search<br/>cosine similarity]
    D --> E[Top-k search = 10]

    B -->|Variant: hybrid| F[Query embedding]
    B -->|Variant: hybrid| G[BM25 keyword search]
    F --> H[Dense results]
    G --> I[Sparse results]
    H --> J[Reciprocal Rank Fusion<br/>dense weight 0.6<br/>sparse weight 0.4]
    I --> J
    J --> K[Top-k search = 10]

    E --> L[Top-k select = 3<br/>no rerank]
    K --> L
    L --> M[Build context block<br/>numbered citations]
    M --> N[Grounded prompt]
    N --> O[LLM: gpt-4o-mini<br/>temperature 0]
    O --> P[Answer + citations + sources]
```
