# Technical Breakdown — Lab Day 09

**Nhóm:** 4 - E402  
**Ngày:** 2026-04-14  
**Version:** 1.0

---

## 1. Tổng quan

Day 09 xây dựng hệ thống **Supervisor-Worker** multi-agent RAG, thay thế single-agent pipeline của Day 08. Pipeline
gồm các bước: index building → hybrid retrieval → supervisor routing → worker execution → synthesis. Tài liệu này
mô tả từng bước, giải thích các lựa chọn thuật toán và lý do thay đổi so với Day 08.

---

## 2. Index Building

### 2.1 Nguồn tài liệu

Tài liệu KB được đặt tại `kb/` (JSON hoặc text). Mỗi document được chunk với `chunk_size=512`, `overlap=64`.

### 2.2 Embedding model

| Priority | Model                                      | Ghi chú                              |
|----------|--------------------------------------------|--------------------------------------|
| 1        | Vertex AI `text-multilingual-embedding-002` | Tiếng Việt chất lượng cao hơn        |
| 2        | OpenAI `text-embedding-3-small`            | Fallback khi Vertex AI không có sẵn  |

**Lý do chọn multilingual model:** KB chứa nội dung tiếng Việt. `text-embedding-3-small` (English-tuned) sẽ có
representation quality thấp hơn cho Vietnamese text.

### 2.3 Vector store

ChromaDB (local persistent, `chroma_db/`). Tên collection: `kb_chunks`.  
Mỗi chunk được lưu kèm metadata: `source` (tên file), `chunk_index`, `total_chunks`.

**Lưu ý:** `chroma_db/` bị liệt vào `.gitignore` — phải chạy lại indexing script trước khi dùng pipeline.

### 2.4 BM25 sparse index

BM25 index được build in-memory từ toàn bộ corpus mỗi khi `retrieval.py` được import. Tokenizer: whitespace +
lowercase. Index không được persist ra disk — rebuild tự động mỗi lần khởi động.

---

## 3. Retrieval — Dense, Sparse, Hybrid

### 3.1 Dense retrieval

```
query  →  embedding model  →  query_vector
query_vector  →  ChromaDB cosine similarity  →  top-k chunks (với score)
```

### 3.2 Sparse retrieval (BM25)

```
query  →  tokenize  →  BM25.get_scores(tokenized_query)
scores  →  rank  →  top-k chunks (chỉ dùng index rank, không có similarity score 0–1)
```

### 3.3 Hybrid RRF (Reciprocal Rank Fusion)

Kết hợp kết quả dense và BM25 bằng RRF với `k=60`:

```
rrf_score(d) = weight_dense / (k + rank_dense(d))
             + weight_sparse / (k + rank_sparse(d))

weight_dense  = 0.6
weight_sparse = 0.4
k             = 60  (RRF smoothing constant)
```

Kết quả: top-`top_k` chunks theo `rrf_score` (mặc định `top_k=5`, configurable qua `state["retrieval_top_k"]`).

**Lý do chọn Hybrid thay vì Dense-only:**  
Dense search giỏi semantic similarity nhưng kém với exact term matching (e.g., tên SLA tier, mã lỗi). BM25 bù đắp
cho điểm yếu này. Kết quả hybrid recall cao hơn trên câu hỏi kỹ thuật cụ thể.

---

## 4. Supervisor Routing Logic

Supervisor (`graph.py → supervisor_node`) sử dụng **keyword matching + regex** để phân loại task:

```
task (str)
  │
  ├─ re.search(r'err-\d+', task, re.IGNORECASE)
  │     → route = "human_review"
  │       risk_high = True
  │
  ├─ any(kw in task_lower for kw in POLICY_KEYWORDS)
  │     POLICY_KEYWORDS = ["hoàn tiền", "đổi trả", "flash sale", "bảo hành",
  │                        "sản phẩm kích hoạt", "digital", "cấp quyền",
  │                        "quyền truy cập", "level"]
  │     → route = "policy_tool_worker"
  │       needs_tool = True  (nếu có "quyền truy cập" hoặc "ticket")
  │
  └─ default
        → route = "retrieval_worker"
          route_reason = "default route"
```

`route_reason` luôn được ghi vào state — bắt buộc non-empty để đảm bảo trace đầy đủ.

**Giới hạn:** Keyword matching không hiểu ngữ nghĩa. Câu "Khách hàng hoàn tiền khi nào?" route đúng, nhưng
"Quy trình xử lý phàn nàn" có thể bị miss nếu không chứa keyword chính xác. Cải tiến đề xuất: LLM intent
classifier cho supervisor.

---

## 5. Workers

### 5.1 Retrieval Worker (`workers/retrieval.py`)

1. Đọc `state["task"]` và `state.get("retrieval_top_k", 3)`
2. Gọi `retrieve_hybrid(query, top_k)` → list of `{text, source, score, metadata}`
3. Ghi `state["retrieved_chunks"]`, `state["retrieved_sources"]`
4. Append `"retrieval_worker"` vào `state["workers_called"]`

### 5.2 Policy Tool Worker (`workers/policy_tool.py`)

1. Kiểm tra exception rules (flash sale, digital product, activated product)
2. Nếu `state["needs_tool"] == True`:
   - Gọi `mcp_server.dispatch_tool("get_ticket_info", ...)` nếu task chứa ticket ID
   - Gọi `mcp_server.dispatch_tool("check_access_permission", ...)` nếu task chứa "level" / access keywords
   - Gọi `mcp_server.dispatch_tool("search_kb", ...)` nếu không có chunks
3. Ghi `state["policy_result"]`, `state["mcp_tools_used"]`
4. Nếu không có `retrieved_chunks` sau bước 2: delegate sang `retrieval_worker`

### 5.3 Human Review Node (`graph.py → human_review_node`)

Triggered khi supervisor route = `"human_review"` (ERR-\d+ pattern):
- Auto-approve với confidence 0.30
- `final_answer = "Mã lỗi {code} cần được xem xét thủ công..."`
- Không gọi retrieval hay synthesis
- `hitl_triggered = True`

### 5.4 Synthesis Worker (`workers/synthesis.py`)

1. `_build_context()`: ghép chunks thành context có đánh số `[1]...[n]`, thêm policy exceptions, thêm MCP tool outputs
   với label `Source: [mcp:{tool_name}]`
2. `_calculate_confidence()`: tính từ RRF scores (penalty 0.05/exception; clamp [0.1, 0.95])
3. Gọi `gpt-4o-mini` (temperature=0) với system prompt cấm kiến thức ngoài
4. Abstain nếu `retrieved_chunks == []` → `"Không đủ thông tin trong tài liệu nội bộ"`
5. Ghi `state["final_answer"]`, `state["sources"]`, `state["confidence"]`

---

## 6. MCP Server (`mcp_server.py`)

In-process mock server, không có HTTP boundary. `dispatch_tool()` là entry point:

| Tool                      | Input params                                        | Output                                               |
|---------------------------|-----------------------------------------------------|------------------------------------------------------|
| `search_kb`               | `query: str, top_k: int = 3`                        | `{chunks, sources, total_found}` — hybrid retrieval  |
| `get_ticket_info`         | `ticket_id: str`                                    | ticket details + SLA deadline + notifications_sent   |
| `check_access_permission` | `access_level, requester_role, is_emergency=False`  | `{can_grant, required_approvers, emergency_override}` |
| `create_ticket`           | `priority, title, description`                      | `{ticket_id, url, created_at}` — mock only           |

`dispatch_tool()` không bao giờ raise exception — lỗi trả về dưới dạng `{"error": "..."}`.

**Lưu ý về `search_kb`:** Tool này sử dụng `retrieve_hybrid()` (dense + BM25 via RRF), không phải semantic-only search.

---

## 7. State Schema

```python
AgentState = TypedDict("AgentState", {
    "task":              str,    # câu hỏi đầu vào
    "run_id":            str,    # run_YYYYMMDD_HHMMSS
    "supervisor_route":  str,    # worker được chọn
    "route_reason":      str,    # lý do route — non-empty
    "risk_high":         bool,   # emergency / ERR-\d+
    "needs_tool":        bool,   # MCP tool cần thiết
    "hitl_triggered":    bool,   # human review đã chạy
    "retrieved_chunks":  list,   # [{text, source, score, metadata}]
    "retrieved_sources": list,   # unique source filenames
    "retrieval_top_k":   int,    # configurable, default=5
    "policy_result":     dict,   # {policy_applies, exceptions_found, ...}
    "mcp_tools_used":    list,   # [{tool, input, output, timestamp}]
    "final_answer":      str,    # grounded answer với [source] citation
    "sources":           list,   # sources cited
    "confidence":        float,  # 0.1–0.95
    "workers_called":    list,   # thứ tự workers thực thi
    "history":           list,   # event log
    "latency_ms":        int,    # wall-clock time toàn run
})
```

---

## 8. Rationale — Các lựa chọn thuật toán

| Quyết định                              | Lựa chọn                       | Lý do                                                                             |
|-----------------------------------------|--------------------------------|-----------------------------------------------------------------------------------|
| Retrieval mode                          | Hybrid RRF (dense 0.6 + BM25 0.4) | Kết hợp semantic và exact-term matching; recall cao hơn dense-only trên KB tiếng Việt |
| LLM model cho synthesis                 | `gpt-4o-mini`, temperature=0   | Deterministic output; đủ capability cho Vietnamese instruction-following           |
| Supervisor strategy                     | Keyword match + regex          | Đơn giản, nhanh, không tốn LLM call cho routing; đủ cho 15 câu test              |
| top_k mặc định                          | 5 (nâng từ 3 của Day 08)       | Recall cải thiện trên multi-hop questions; synthesis vẫn handle được              |
| MCP server in-process                   | Mock Python functions          | Không cần network setup; đủ để demo tool-calling pattern                          |
| Abstain condition                       | `retrieved_chunks == []`       | Ngăn hallucination khi không có evidence; confidence = 0.0 khi abstain           |
| Human-in-the-loop trigger               | `re.search(r'err-\d+', task)`  | Unknown error codes cần human judgment; pattern đơn giản, không FP trong test set |

---

## 9. Tài liệu liên quan

- [`system_architecture.md`](system_architecture.md) — sơ đồ pipeline và bảng state schema đầy đủ
- [`routing_decisions.md`](routing_decisions.md) — log 15 routing decisions từ eval run
- [`single_vs_multi_comparison.md`](single_vs_multi_comparison.md) — so sánh Day 08 vs Day 09
- [`../artifacts/eval_report.json`](../artifacts/eval_report.json) — summary statistics
- [`../artifacts/scorecard_day09_grading.md`](../artifacts/scorecard_day09_grading.md) — per-question grading
