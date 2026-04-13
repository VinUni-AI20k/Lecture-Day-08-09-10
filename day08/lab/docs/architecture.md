# Architecture — RAG Pipeline (Day 08 Lab)

> Template: Điền vào các mục này khi hoàn thành từng sprint.
> Deliverable của Documentation Owner.

## 1. Tổng quan kiến trúc

```
[Raw Docs]
    ↓
[index.py: Preprocess → Chunk → Embed → Store]
    ↓
[ChromaDB Vector Store]
    ↓
[rag_answer.py: Query → Retrieve → Rerank → Generate]
    ↓
[Grounded Answer + Citation]
```

**Mô tả ngắn gọn:**
> Hệ thống này là một pipeline RAG nội bộ giúp tra cứu nhanh các tài liệu policy, SOP, SLA và FAQ cho đội IT, CS, HR.
> Dữ liệu được index thành các chunk có metadata và lưu trong ChromaDB; khi có câu hỏi, hệ thống retrieve (dense/hybrid), có thể rerank, rồi sinh câu trả lời grounded kèm citation nguồn.
> Mục tiêu là giảm thời gian tìm tài liệu, tăng độ chính xác câu trả lời và hạn chế hallucination nhờ chỉ trả lời từ ngữ cảnh đã truy xuất.

### Phân vai (tham chiếu README)

| Vai trò | Tên | Trách nhiệm chính | Sprint lead |
|---------|-----|------------------|------------|
| **Tech Lead** | Tống Tiến Mạnh | Giữ nhịp sprint, nối code end-to-end | 1, 2 |
| **Retrieval Owner** | Nguyễn Minh Hiếu | Chunking, metadata, retrieval strategy, rerank | 1, 3 |
| **Retrieval Owner** | Nguyễn Tùng Lâm | Chunking, metadata, retrieval strategy, rerank | 1, 3 |
| **Eval Owner** | Nguyễn Việt Long | Test questions, expected evidence, scorecard, A/B | 3, 4 |
| **Eval Owner** | Hà Huy Hoàng | Test questions, expected evidence, scorecard, A/B | 3, 4 |
| **Documentation Owner** | Nguyễn Quang Đăng | architecture.md, tuning-log, báo cáo nhóm | 4 |

---

## 2. Indexing Pipeline (Sprint 1)

### Tài liệu được index
| File | Nguồn | Department | Số chunk |
|------|-------|-----------|---------|
| `policy_refund_v4.txt` | policy/refund-v4.pdf | CS | 6 |
| `sla_p1_2026.txt` | support/sla-p1-2026.pdf | IT | 5 |
| `access_control_sop.txt` | it/access-control-sop.md | IT Security | 8 |
| `it_helpdesk_faq.txt` | support/helpdesk-faq.md | IT | 6 |
| `hr_leave_policy.txt` | hr/leave-policy-2026.pdf | HR | 5 |

### Quyết định chunking
| Tham số | Giá trị | Lý do |
|---------|---------|-------|
| Chunk size | 400 tokens (ước lượng theo `CHUNK_SIZE`) | Cân bằng giữa đủ ngữ cảnh và tránh context quá dài khi retrieve nhiều chunk |
| Overlap | 80 tokens (ước lượng theo `CHUNK_OVERLAP`) | Giữ liên tục ngữ nghĩa giữa các chunk liền kề, giảm mất ý ở ranh giới |
| Chunking strategy | Heading-based, fallback paragraph/size split + overlap | Ưu tiên ranh giới tự nhiên theo `=== Section ... ===`, sau đó mới tách theo paragraph/độ dài |
| Metadata fields | source, section, effective_date, department, access | Phục vụ filter, freshness, citation |

### Embedding model
- **Model**: OpenAI-compatible `text-embedding-3-small` (qua `CUSTOM_API_KEY`)
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
| Strategy | Hybrid (Dense + Sparse BM25, RRF `dense_weight=0.6`, `sparse_weight=0.4`) | Đổi từ dense sang hybrid để tăng recall cho query chứa keyword/alias/mã lỗi |
| Top-k search | 10 | Giữ nguyên để so sánh công bằng (A/B chỉ đổi biến chính) |
| Top-k select | 3 | Giữ nguyên để kiểm soát độ dài context |
| Rerank | LLM-based rerank (`use_rerank=True`, model `RERANK_MODEL`) | Thêm bước chọn lại top-3 chunk liên quan nhất sau khi retrieve rộng |
| Query transform | `expansion` / `decomposition` / `hyde` (optional) | Bật theo từng case để tăng recall, mặc định `None` |

**Lý do chọn variant này:**
> Chọn hybrid + rerank vì corpus có cả câu tự nhiên lẫn keyword kỹ thuật (P1/P2, ERR-403, Approval Matrix), nên dense đơn thuần dễ hụt hoặc lẫn noise.
> Hybrid tăng khả năng tìm đúng tài liệu theo cả nghĩa và từ khóa; rerank giúp chỉ giữ các chunk liên quan nhất trước khi generate để giảm hallucination.

---

## 4. Generation (Sprint 2)

### Grounded Prompt Template
```
Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

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
| Model | `LLM_MODEL` (default: `openai-gpt-4o`, đọc từ biến môi trường) |
| API key | `SHOPAIKEY_API_KEY` |
| Base URL | `https://api.shopaikey.com/v1` |
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

> TODO: Vẽ sơ đồ pipeline nếu có thời gian. Có thể dùng Mermaid hoặc drawio.

```mermaid
graph LR
    A[User Query] --> B[Query Embedding]
    B --> C[ChromaDB Vector Search]
    C --> D[Top-10 Candidates]
    D --> E{Rerank?}
    E -->|Yes| F[Cross-Encoder]
    E -->|No| G[Top-3 Select]
    F --> G
    G --> H[Build Context Block]
    H --> I[Grounded Prompt]
    I --> J[LLM]
    J --> K[Answer + Citation]
```
