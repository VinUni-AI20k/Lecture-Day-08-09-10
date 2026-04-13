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
> Hệ thống RAG này được xây dựng để trả lời các câu hỏi nghiệp vụ dựa trên tài liệu nội bộ của công ty. Nó bao gồm 3 pipeline chính: Indexing, Retrieval và Generation. Hệ thống giúp nhân viên tra cứu thông tin nhanh chóng và chính xác từ các tài liệu policy, SOP, FAQ mà không cần tìm thủ công.

---

## 2. Indexing Pipeline (Sprint 1)

### Tài liệu được index
| File | Nguồn | Department | Số chunk |
|------|-------|-----------|---------|
| `policy_refund_v4.txt` | policy/refund-v4.pdf | CS | 5 |
| `sla_p1_2026.txt` | support/sla-p1-2026.pdf | IT | 4 |
| `access_control_sop.txt` | it/access-control-sop.md | IT Security | 6 |
| `it_helpdesk_faq.txt` | support/helpdesk-faq.md | IT | 9 |
| `hr_leave_policy.txt` | hr/leave-policy-2026.pdf | HR | 4 |

### Quyết định chunking
| Tham số | Giá trị | Lý do |
|---------|---------|-------|
| Chunk size | 400 tokens | Nhóm chọn 400 tokens ước lượng (khoảng 1600 ký tự) để giữ trọn ngữ nghĩa của các đoạn policy/SLA vốn hay đi theo cụm điều kiện, ngoại lệ, và quy trình. Nếu nhỏ quá thì dễ vỡ ý, còn lớn quá thì retrieval kém chính xác vì một chunk chứa nhiều nội dung khác nhau; mức này là điểm cân bằng tốt cho bộ tài liệu hiện tại. |
| Overlap | 80 tokens | Nhóm đặt overlap 80 tokens (khoảng 320 ký tự) để giảm mất mát thông tin ở ranh giới chunk, nhất là với danh sách bước và câu có nhiều vế liên tiếp. Mức overlap này đủ nối mạch ngữ cảnh giữa hai chunk mà chưa gây trùng lặp quá nhiều khi truy hồi.
|
| Chunking strategy | Heading-based  | Nhóm dùng chiến lược theo cấu trúc tài liệu: Đầu tiên tách theo heading "=== ... ===" trước, sau đó mới chia nhỏ theo độ dài khi cần; riêng FAQ thì tách theo cặp Q/A để giữ đúng đơn vị hỏi-đáp. Cách này tận dụng format có sẵn trong dữ liệu, giúp chunk rõ nghĩa và tăng độ chính xác retrieval so với cắt theo độ dài thuần túy. |
| Metadata fields | source, section, effective_date, department, access | Phục vụ filter, freshness, citation |

### Embedding model
- **Model**: Paraphrase-multilingual-MiniLM-L12-v2
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
| Strategy | hybrid | Chuyển sang kết hợp Dense và Sparse |
| Top-k search | 10 | Giữ nguyên |
| Top-k select | 3 | Giữ nguyên |
| Rerank | Không | Giữ nguyên |
| Query transform | Không | Giữ nguyên |

**Lý do chọn variant này:**
> Nhóm quyết định lựa chọn Hybrid Search (kết hợp Dense Retrieval bằng Vector và BM25) vì dữ liệu tài liệu (IT Helpdesk, CS) chứa rất nhiều thuật ngữ cứng, mã code riêng (ví dụ: ERR-403, ticket P1) xen lẫn với câu văn tự nhiên. Dense Baseline thu thập theo chuỗi ngữ nghĩa nên dễ bỏ lọt (hoặc hụt điểm) nếu user hỏi mã số chính xác. Hybrid kết hợp BM25 giúp khắc phục khá tốt nhược điểm này.

---

## 4. Generation (Sprint 2)

### Grounded Prompt Template
```
You are a professional IT/CS Helpdesk assistant.
Your task is to answer the user's question based EXCLUSIVELY on the Context provided below.

MANDATORY Rules:
1. ABSTAIN: If the Context does not contain enough information to answer the question, you must reply exactly with: "Not enough data to answer." DO NOT make up information or use outside knowledge.
2. CITATION: Every piece of information you provide must include a citation. Use bracketed numbers like [1], [2] that correspond to the chunk IDs in the Context (e.g., "According to the refund policy [1], the process takes 3 days [2]").
3. Keep your answers short, clear, and direct.

Question: {Nhân viên phải báo trước bao nhiêu ngày để xin nghỉ phép năm? Con số này có giống với số ngày cần giấy tờ khi bị ốm không?}

Context:
[1] {source} | {section} | score={score}
{chunk_text}

[2] ...

Answer: Nhân viên phải báo trước ít nhất 3 ngày làm việc để xin nghỉ phép năm [1]. Con số này không giống với ...

```

### LLM Configuration
| Tham số | Giá trị |
|---------|---------|
| Model | Deepseek Chat |
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

```
mermaid
graph TD
    %% Định dạng phong cách cho các khối
    classDef database fill:#f9f,stroke:#333,stroke-width:2px;
    classDef process fill:#bbf,stroke:#333,stroke-width:1px;
    classDef input fill:#cfc,stroke:#333,stroke-width:1px;
    classDef llm fill:#fca,stroke:#333,stroke-width:2px;

    subgraph "Phase 1: Indexing Pipeline (Sprint 1)"
        R1[Raw Documents <br> PDF, Markdown]:::input --> CH[Document Loader & Chunking <br> Size: 400, Overlap: 80]:::process
        CH --> MT[Attach Metadata <br> source, section...]:::process
        MT --> EM1[Embedding Model <br> MiniLM-L12-v2]:::process
        EM1 -->|Lưu Vector & Text| VDB[(ChromaDB Vector Store)]:::database
    end

    subgraph "Phase 2 & 3: Retrieval & Generation (Sprint 2, 3)"
        UQ[User Query]:::input --> EM2[Embedding Model]:::process
        EM2 -.->|Search Vector| VDB
        UQ -.->|Keyword Search <br>Nếu dùng Hybrid| VDB
        VDB --> T10[Retrieve Top-10 Chunks]:::process
        
        T10 --> RR{Có dùng Rerank?}
        RR -->|Có| CE[Cross-Encoder Reranker]:::process
        RR -->|Không| T3[Lấy Top-3 Chunks]:::process
        CE -->|Tính lại điểm| T3
        
        T3 --> CB[Build Context Block <br> kẹp thêm Citation]:::process
        CB --> PMT[Grounded Prompt]:::llm
        UQ --> PMT
        PMT --> LL[LLM Generation <br> Temperature = 0]:::llm
        LL --> OUT[Grounded Answer <br> kèm trích dẫn nguồn]:::input
    end
```
