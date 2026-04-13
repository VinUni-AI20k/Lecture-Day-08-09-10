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

Nhóm phát triển một hệ thống RAG nội bộ giúp tra cứu và trả lời tự động các câu hỏi về chính sách, quy trình vận hành và hỗ trợ nội bộ công ty. Hệ thống hiện tích hợp 5 tài liệu thuộc các lĩnh vực IT Security, HR, IT Support và Customer Service, nhằm hỗ trợ nhân viên và các bộ phận liên quan tra cứu thông tin chính xác, nhanh chóng và luôn dựa trên tài liệu chính thức.

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

| Tham số              | Giá trị          | Lý do |
|----------------------|------------------|-------|
| Chunk size           | 400 tokens       | Đủ lớn để chứa một phần nội dung logic (1–2 điều khoản hoặc 1 section nhỏ), nhưng vẫn ngắn gọn để giữ độ chính xác khi retrieve và tránh vượt giới hạn context của LLM. |
| Overlap              | 80 tokens        | Đảm bảo ngữ cảnh chuyển tiếp giữa các chunk, giảm tình trạng cắt ngang câu hoặc ý quan trọng, đặc biệt hữu ích khi chunking theo section. |
| Chunking strategy    | Heading-based + Paragraph fallback | Ưu tiên tách theo heading tự nhiên (`=== Section ... ===` hoặc `=== Phần ... ===`) để giữ cấu trúc tài liệu, sau đó mới split theo paragraph và kích thước nếu section quá dài. Giúp chunk có ý nghĩa rõ ràng và dễ citation hơn. |
| Metadata fields      | source, section, department, effective_date, access | Phục vụ filter theo bộ phận (department), kiểm tra độ mới (effective_date), kiểm soát quyền truy cập (access), và hỗ trợ citation chính xác khi trả lời người dùng. |

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
| Strategy | Hybrid (Dense + Sparse) | Đổi từ Dense sang Hybrid |
| Top-k search | 10 | Giữ nguyên |
| Top-k select | 3 | Giữ nguyên |
| Rerank | Cross-encoder | Thêm bước Rerank |
| Query transform | Không | Giữ nguyên |

**Lý do chọn variant này:**
> Chọn Hybrid kết hợp Rerank (Cross-encoder) để cải thiện độ chính xác (relevance) của kết quả truy xuất, đặc biệt đối với các câu hỏi chứa keyword cụ thể, thuật ngữ hoặc tên riêng (như mã lỗi, access level). Dense search giỏi bắt ý nghĩa ngữ cảnh nhưng có thể bỏ lỡ keyword chính xác, nên bù đắp bằng Sparse (BM25). Sau đó, dùng Cross-encoder để rerank các chunk top-10 giúp tinh chọn ra 3 chunk phù hợp nhất đưa vào ngữ cảnh, thay vì chỉ dựa vào similarity score mặc định. Kết quả thực tế cho thấy điểm Relevance trung bình đã cải thiện từ 4.20 (Baseline) lên 4.40 (Variant).

---

## 4. Generation (Sprint 2)

### Grounded Prompt Template
```
Answer only from the retrieved context below.
If the context contains enough information:
- Provide a short, clear, factual answer.
- Cite the source field (in brackets like [1]) when possible.

If the context does NOT contain enough information:
- DO NOT guess or fabricate.
- Instead, respond in a helpful way:
  + State that you could not find the answer in the provided context.
  + Suggest 1-2 concrete next steps (e.g., refine keywords, search broader documents, contact relevant department).
  + Optionally suggest related keywords or what information is missing.

Additional rules:
- Respond in the same language as the question.
- If there is conflict between documents, list all conflicting sources and point out where they differ.
- Do not infer information not explicitly stated in the context.

Question: {query}

Context:
{context_block}
```

### LLM Configuration
| Tham số | Giá trị |
|---------|---------|
| Model | gpt-4o-mini |
| Temperature | 0 (để output ổn định cho eval) |
| Max tokens | 512 |

---

## 5. Failure Mode Checklist

> Dùng khi debug — kiểm tra lần lượt theo thứ tự: **index → retrieval → generation**

| # | Failure Mode | Triệu chứng | Nguyên nhân thường gặp | Cách kiểm tra / Fix |
|---|-------------|-------------|----------------------|---------------------|
| 1 | **Index lỗi / outdated** | Retrieve về nội dung cũ hoặc thiếu tài liệu | Quên chạy lại `build_index()` sau khi sửa docs | Chạy `inspect_metadata_coverage()` trong `index.py`, kiểm tra `effective_date` |
| 2 | **Chunking tệ** | Chunk cắt giữa điều khoản, thiếu ngữ cảnh | `CHUNK_SIZE` quá nhỏ hoặc split không theo heading | Chạy `list_chunks()`, đọc text preview từng chunk |
| 3 | **Metadata source sai** | `source` log ra tên file `.txt` thay vì tên tài liệu gốc | File `.txt` thiếu dòng `Source: ...` ở header | Kiểm tra 5 dòng đầu của mỗi file trong `data/docs/` |
| 4 | **Context Recall thấp** | Đúng câu hỏi nhưng source sai / không retrieve được expected doc | Dense search yếu với exact term (mã lỗi, tên riêng) | Xem `score_context_recall()` trong `eval.py`; thử chuyển sang hybrid |
| 5 | **Faithfulness thấp** | Answer chứa thông tin không có trong context | LLM dùng prior knowledge ngoài retrieved chunks | Xem `score_faithfulness()` trong `eval.py`; kiểm tra prompt có đủ constraint không |
| 6 | **Completeness thấp** | Answer đúng nhưng thiếu số liệu / điều kiện / ngoại lệ | Prompt có `"short"` khiến LLM tóm tắt quá mức | Kiểm tra prompt trong `build_grounded_prompt()`; bỏ instruction về độ ngắn |
| 7 | **Abstain sai** | Câu không có trong docs nhưng LLM vẫn trả lời | Retriever tìm được chunk liên quan xa, LLM đoán thêm | Kiểm tra score của candidates; thêm score threshold filter |
| 8 | **Token overload** | Answer bị cắt giữa chừng hoặc context bị truncate | `top_k_select` quá cao, chunk quá dài | Giảm `TOP_K_SELECT`, kiểm tra độ dài `context_block` trước khi gửi LLM |

---

## 6. Sơ đồ Pipeline tổng thể

Sơ đồ thể hiện luồng truy vấn nâng cao sử dụng Hybrid Search (kết hợp Dense và Sparse) tiếp nối bởi Cross-encoder Reranking, định hình theo kiến trúc ưu tú nhất (Variant 1) của hệ thống:

```mermaid
graph TD
    %% User Input
    Q([User Query]) --> SPLIT{Hybrid Search}

    %% Hybrid Retrieval Flow
    SPLIT -->|Dense (Ngữ nghĩa)| DE[Query Embedding]
    SPLIT -->|Sparse (Từ khóa)| SP[BM25 Tokenization]
    
    DE --> VDB[(ChromaDB Vector Store)]
    SP --> BMDB[(BM25 Keyword Index)]
    
    VDB --> DS[Dense Candidates]
    BMDB --> SS[Sparse Candidates]
    
    DS --> RRF[Reciprocal Rank Fusion]
    SS --> RRF
    
    RRF --> TOP10[Top-10 Candidates]
    
    %% Reranking & Selection Flow
    TOP10 --> RR{Cross-Encoder Rerank}
    Q -.-> RR
    RR -->|Re-score pairs| R[Ranked Candidates]
    R --> T3[Select Top-3 Chunks]
    
    %% Generation Flow
    T3 --> CB[Build Context Block]
    CB --> GP[Grounded Prompt]
    Q -.-> GP
    
    GP --> LLM[[LLM: gpt-4o-mini]]
    LLM --> ANS([Answer + Citations])
    
    %% Styling
    classDef io fill:#f0f4fa,stroke:#0055ff,stroke-width:2px;
    classDef process fill:#fff,stroke:#333,stroke-width:1px;
    classDef db fill:#f9f2e7,stroke:#e69000,stroke-width:2px;
    classDef llm fill:#e6f9ec,stroke:#00ab41,stroke-width:2px;

    class Q,ANS io;
    class VDB,BMDB db;
    class LLM llm;
    class DE,SP,DS,SS,RRF,TOP10,RR,R,T3,CB,GP process;
```
