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
> Nhóm xây một chatbot RAG để trả lời câu hỏi từ tài liệu nội bộ kèm citation. Hệ thống giúp người dùng tìm thông tin nhanh, chính xác và đáng tin cậy.

---

## 2. Indexing Pipeline (Sprint 1)

### Tài liệu được index
| File | Nguồn | Department | Số chunk |
|------|-------|-----------|---------|
| `policy_refund_v4.txt` | policy/refund-v4.pdf | CS | 6 |
| `sla_p1_2026.txt` | support/sla-p1-2026.pdf | IT | 6 |
| `access_control_sop.txt` | it/access-control-sop.md | IT Security | 7 |
| `it_helpdesk_faq.txt` | support/helpdesk-faq.md | IT | 12 |
| `hr_leave_policy.txt` | hr/leave-policy-2026.pdf | HR | 5 |

### Quyết định chunking
| Tham số | Giá trị | Lý do |
|---------|---------|-------|
| Chunk size | 400 tokens | Common practice |
| Overlap | 80 tokens | Preserve context |
| Chunking strategy | Mỗi file chunking 1 kiểu khác nhau (chi tiết trong README)| Mỗi tài liệu có 1 kiểu bố trí dữ liệu khác nhau và sẽ có cách chunk tối ưu khác nhau |
| Metadata fields | doc_id, chunk_id, section_title, department, effective_date, prev_chunk_id, next_chunk_id, aliases, char_count | Phục vụ filter, freshness, citation |

### Embedding model
- **Model**: OpenAI text-embedding-3-small 
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
| Strategy | hybrid | Có |
| Top-k search | 10 | Không |
| Top-k select | 3 | Không |
| Rerank | Không | Không |
| Query transform | decomposition | Có |

**Lý do chọn variant này:**
> Chọn hybrid retrieval vì corpus chứa cả văn bản tự nhiên lẫn từ khóa/ thuật ngữ đặc thù, giúp kết hợp ưu điểm của semantic và keyword matching để tăng recall. Áp dụng query decomposition để tách câu hỏi phức tạp thành các truy vấn nhỏ, cải thiện độ chính xác khi retrieve thông tin liên quan, đặc biệt khi cần truy vấn từ nhiều hơn 2 file khác nhau.

---

## 4. Generation (Sprint 2)

### Grounded Prompt Template
```
Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know and do not make up information, suggest user to contact support.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

Question: {query}

Context:
{context_block}

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

> Sơ đồ pipeline (mermaid)

```mermaid
flowchart TD
    subgraph OFFLINE["OFFLINE — Index Pipeline"]
        direction LR
        DOC["Raw Documents\n5 source files"] --> PRE
        PRE["Preprocess\nParse metadata header\nNormalize text"] --> CHUNK
        CHUNK["Chunk\nSplit by section heading\nApply size + overlap"] --> EMBED
        EMBED["Embed\nget_embedding()\nper chunk"] --> STORE
        STORE[("Vector Store\nChromaDB\nvector + metadata")]
    end

    subgraph ONLINE["ONLINE — Query Pipeline"]
        direction TB
        QUERY(["User Query"]) --> PROBE

        PROBE["Probe Retrieve\ntop-k=6 dense search\nto inspect result diversity"]

        PROBE --> SCORE{"Unique sources\nin top-4 results >= 2?"}

        SCORE -->|"No — single doc"| RETRIEVE
        SCORE -->|"Yes — multi-doc"| DECOMP

        DECOMP["Query Decomposition\nLLM splits into 2-3\nsingle-doc sub-questions"] --> MULTI_RET

        MULTI_RET["Retrieve per sub-question\nindependently"] --> MERGE

        RETRIEVE["Retrieve\ndense or hybrid\nRRF fusion if hybrid"] --> RERANK

        MERGE["Deduplicate + Merge\nunique chunks across sources"] --> RERANK

        RERANK["Select top-k\ntop_k_search=10\ndown-select to top_k_select=3"]

        RERANK --> ABSTAIN{"max similarity score\n< threshold?"}

        ABSTAIN -->|"Insufficient context"| ABSTAIN_OUT["Abstain\nReturn: not found\nin available documents"]
        ABSTAIN -->|"Context available"| PROMPT

        PROMPT["Build Grounded Prompt\nEvidence-only constraint\nCite sources by index\ntemperature=0"] --> LLM

        LLM["LLM Generate\ncall_llm()"] --> OUT

        OUT(["Structured Output\nanswer + sources + chunks_used"])
    end

    subgraph EVAL["EVAL — Scorecard Pipeline"]
        direction LR
        TQ["test_questions.json\nquestion + expected_answer\n+ expected_sources"] --> SC
        SC["run_scorecard()\nbaseline config\nvariant config"] --> METRICS
        METRICS["Score 4 Metrics\nFaithfulness\nAnswer Relevance\nContext Recall\nCompleteness"] --> AB
        AB["compare_ab()\ndelta per metric\nper-question breakdown"] --> CARD
        CARD["scorecard_baseline.md\nscorecard_variant.md\nlogs/grading_run.json"]
    end

    STORE -->|"embedding search"| PROBE
    STORE -->|"embedding search"| RETRIEVE
    STORE -->|"embedding search"| MULTI_RET
    OUT --> SC

    style OFFLINE fill:#dbeafe,stroke:#3b82f6
    style ONLINE fill:#dcfce7,stroke:#22c55e
    style EVAL fill:#ede9fe,stroke:#8b5cf6
    style ABSTAIN_OUT fill:#fee2e2,stroke:#ef4444
    style DECOMP fill:#fce7f3,stroke:#ec4899
    style MULTI_RET fill:#fce7f3,stroke:#ec4899
    style MERGE fill:#fce7f3,stroke:#ec4899
    style SCORE fill:#fef9c3,stroke:#eab308
    style ABSTAIN fill:#fef9c3,stroke:#eab308
```
