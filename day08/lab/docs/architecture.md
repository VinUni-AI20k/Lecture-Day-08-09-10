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
> Nhóm xây một hệ thống RAG chatbot/assistant nội bộ: index tài liệu → truy hồi đoạn liên quan → LLM trả lời có citation.
> Hệ thống dành cho CS team + IT Helpdesk/IT Security/HR (người xử lý ticket và trả lời câu hỏi nội bộ).
> Mục tiêu là trả lời nhanh và nhất quán các câu hỏi về refund policy, SLA P1, quy trình cấp quyền, FAQ dựa trên bằng chứng từ tài liệu, giảm tìm kiếm thủ công và giảm hallucination nhờ grounded + abstain khi thiếu dữ liệu.

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
| Chunk size | 400 tokens | đủ dài để giữ đúng 1 nghiệp vụ trong policy/SOP |
| Overlap | 80 tokens | 80/400 = 20% là mức overlap phổ biến, tránh mất thông tin khi bị cắt giữa 2 chunk |
| Chunking strategy | Heading-based trước sau đó split theo độ dài với overalap | Tài liệu policy/SOPA/SLA đều có cấu trục mục, nên cắt theo heading sẽ giúp mỗi chunk chứa chọn một ý nghiệp vụ, nếu section quá dài thì split theo kích thưóc để vừa ngữ cảnh model và giới hạn token |
| Metadata fields | source, section, effective_date, department, access | Phục vụ filter, freshness, citation |

### Embedding model
- **Model**: chọn theo `EMBEDDING_PROVIDER` trong môi trường chạy (`index.py:get_embedding`)
  - `EMBEDDING_PROVIDER=openai` → OpenAI Embeddings **`text-embedding-3-small`** (cần `OPENAI_API_KEY`)
  - `EMBEDDING_PROVIDER=local` → Sentence Transformers **`paraphrase-multilingual-MiniLM-L12-v2`** (hoặc `LOCAL_EMBEDDING_MODEL` nếu set)
  - Nếu chọn `openai` nhưng thiếu `OPENAI_API_KEY` → code tự fallback sang `local`
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
| Strategy | **Hybrid** (Dense + Sparse/BM25, RRF fusion với \(k=60\)) | đổi từ Dense → Hybrid |
| Top-k search | 10 | giữ nguyên |
| Top-k select | 3 | giữ nguyên |
| Rerank | Không (`use_rerank=False`) | giữ nguyên |
| Query transform | Tắt trong scorecard variant (không gọi `transform_query()` trong pipeline mặc định) | giữ nguyên |

**Lý do chọn variant này:**
> Chọn **Hybrid (Dense + BM25 + RRF)** vì log retrieval cho thấy có những câu mang tính **keyword/alias** (đặc biệt `q07` “Approval Matrix…”) mà BM25 bắt tốt hơn, trong khi các câu mô tả tự nhiên (refund/HR/SLA) vẫn cần dense để bắt ngữ nghĩa.
> Bằng chứng từ `logs/sprint3/retrieval_debug.json`: với query `Approval Matrix…`, cả dense và BM25 đều đưa `it/access-control-sop.md` lên top nhưng từ các góc khác nhau (dense ưu tiên ngữ nghĩa, sparse ưu tiên keyword), nên RRF giúp “đẩy” các chunk đúng nguồn ổn định hơn trong top-k.
> Bằng chứng từ scorecard logs: `logs/grading_run_baseline_dense.json` có **Context Recall = 4.60/5**, còn `logs/grading_run_variant_hybrid.json` tăng lên **5.00/5**; đổi đúng 1 biến (dense → hybrid, `use_rerank=False`) để tuân thủ A/B rule và đo được tác động của retrieval strategy.

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
| Provider + Model | OpenAI Chat Completions (`LLM_PROVIDER=openai`) — `gpt-4o-mini` (`LLM_MODEL`) |
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

Sơ đồ pipeline (Mermaid) phản ánh các nhánh baseline/variant:

```mermaid
graph LR
    A[Raw docs in data/docs/*.txt] --> B[index.py: preprocess + heading chunking]
    B --> C[get_embedding: local ST or OpenAI embeddings]
    C --> D[ChromaDB collection: rag_lab (cosine)]

    Q[User query] --> T{Query transform enabled?}
    T -->|No| R{Retrieval mode}
    T -->|Yes| TQ[transform_query: expansion/decomposition/HyDE] --> R

    R -->|dense| VD[retrieve_dense: vector search]
    R -->|sparse| VS[retrieve_sparse: BM25]
    R -->|hybrid| VH[retrieve_hybrid: RRF(dense+BM25)]

    VD --> P[Candidate pool (top_k_search)]
    VS --> P
    VH --> P

    P --> E{Rerank enabled?}
    E -->|No| S[Select top_k_select]
    E -->|Yes| X[rerank: CrossEncoder] --> S

    S --> H[build_context_block]
    H --> I[build_grounded_prompt]
    I --> J[call_llm]
    J --> K[Answer + sources (citations)]
```
