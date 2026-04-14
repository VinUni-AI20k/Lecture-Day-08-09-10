# System Architecture — Lab Day 09

**Nhóm:** A20C1E402G4  
**Ngày:** 2026-04-14  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

**Pattern đã chọn:** Supervisor-Worker (Pure Python, không dùng LangGraph)

**Lý do chọn pattern này (thay vì single agent):**  
Day 08 dùng single-agent RAG: mọi câu hỏi đều đi qua cùng một luồng retrieve→synthesize. Không có routing visibility, không test worker độc lập được, và completeness score thấp (3.00/5) trên câu multi-hop. Supervisor-Worker giải quyết: supervisor quyết định route, mỗi worker giữ một domain skill, trace ghi `route_reason` cho mọi câu → dễ debug và extend.

---

## 2. Sơ đồ Pipeline

```
User Input (task: str)
        │
        ▼
┌───────────────────────────────────┐
│         supervisor_node           │
│  keyword match + ERR-\d+ regex    │
│  → sets route, route_reason,      │
│    risk_high, needs_tool          │
└───────────────┬───────────────────┘
                │ route_decision()
     ┌──────────┼─────────────────────┐
     ▼          ▼                     ▼
retrieval   policy_tool_worker    human_review
_worker     (Flash Sale, Level N,  (ERR-\d+
            license, access)       unknown code)
     │          │                     │
     │          │   ┌─────────────────┘
     │          │   ▼ auto-approve → retrieval
     │          │
     │          ├──[needs_tool=True]──▶  mcp_server.py
     │          │                         search_kb
     │          │                         get_ticket_info
     │          │                         check_access_permission
     │          │
     │          └──[no chunks yet]──▶ retrieval_worker
     │
     └──────────────────┐
                        ▼
               synthesis_worker_node
               gpt-4o-mini, temperature=0
               grounded prompt, cite [source]
               abstain if no evidence
                        │
                        ▼
                   AgentState
            final_answer, sources,
            confidence, latency_ms,
            workers_called, history,
            mcp_tools_used, route_reason
                        │
                        ▼
              artifacts/traces/{run_id}.json
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân loại task, quyết định route, đánh giá risk — KHÔNG tự trả lời domain |
| **Input** | `task: str` từ `AgentState` |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool` |
| **Routing logic** | Policy keywords → `policy_tool_worker`; `ERR-\d+` regex → `human_review`; default → `retrieval_worker` |
| **HITL condition** | `re.search(r'err-\d+', task)` — unknown error code triggers human review |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Tìm evidence chunks từ ChromaDB bằng hybrid search |
| **Embedding model** | Vertex AI `text-multilingual-embedding-002` (fallback: OpenAI `text-embedding-3-small`) |
| **Retrieval mode** | Hybrid RRF: dense (weight 0.6) + BM25 sparse (weight 0.4), k=60 |
| **Top-k** | 3 (configurable) |
| **Stateless?** | Yes — BM25 index cached in-memory, không ghi state ngoài contract |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Rule-based exception detection + MCP tool calls khi cần external context |
| **MCP tools gọi** | `search_kb` (fallback KB), `get_ticket_info` (P1/ticket context), `check_access_permission` (Level N emergency) |
| **Exception cases** | `flash_sale_exception`, `digital_product_exception`, `activated_exception` |
| **MCP trigger** | `needs_tool=True` (set bởi supervisor khi task chứa policy/access keywords) |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | OpenAI `gpt-4o-mini` |
| **Temperature** | 0 (fully deterministic) |
| **Grounding strategy** | System prompt cấm dùng kiến thức ngoài; mỗi câu phải cite `[source_filename]` |
| **Abstain condition** | `retrieved_chunks = []` → trả về "Không đủ thông tin trong tài liệu nội bộ" |
| **Confidence** | Normalised từ RRF scores; penalty 0.05/exception; clamp [0.1, 0.95] |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output | Ghi chú |
|------|-------|--------|---------|
| `search_kb` | `query, top_k=3` | `{chunks, sources, total_found}` | Dùng retrieval hybrid |
| `get_ticket_info` | `ticket_id` | ticket details + `sla_deadline`, `notifications_sent` | Mock Jira DB |
| `check_access_permission` | `access_level, requester_role, is_emergency=False` | `{can_grant, required_approvers, emergency_override, notes}` | Access Control SOP rules |
| `create_ticket` | `priority, title, description` | `{ticket_id, url, created_at}` | Mock only, không persist |

`dispatch_tool()` không bao giờ raise exception — lỗi trả về dưới dạng `{error: ...}`.

---

## 4. Shared State Schema

| Field | Type | Mô tả | Ai ghi |
|-------|------|-------|--------|
| `task` | str | Câu hỏi đầu vào | caller |
| `supervisor_route` | str | Worker được chọn | supervisor |
| `route_reason` | str | Lý do route — bắt buộc non-empty | supervisor |
| `risk_high` | bool | True khi emergency/ERR-\d+ | supervisor |
| `needs_tool` | bool | True khi policy keywords → MCP | supervisor |
| `hitl_triggered` | bool | True khi human_review node chạy | human_review |
| `retrieved_chunks` | list | `[{text, source, score, metadata}]` | retrieval |
| `retrieved_sources` | list | Unique source filenames | retrieval |
| `policy_result` | dict | `{policy_applies, exceptions_found, ...}` | policy_tool |
| `mcp_tools_used` | list | `[{tool, input, output, timestamp}]` | policy_tool |
| `final_answer` | str | Grounded answer với `[source]` citation | synthesis |
| `sources` | list | Sources cited | synthesis |
| `confidence` | float | 0.1–0.95 | synthesis |
| `workers_called` | list | Thứ tự workers thực thi | mỗi worker |
| `history` | list | Event log | mỗi node |
| `latency_ms` | int | Wall-clock time toàn run | build_graph |
| `run_id` | str | `run_YYYYMMDD_HHMMSS` | make_initial_state |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Không có trace → đọc toàn bộ code | `route_reason` + `worker_io_logs` → biết ngay lỗi ở worker nào |
| Thêm capability mới | Phải sửa toàn prompt + retrieval logic | Thêm MCP tool + 1 route rule trong supervisor |
| Routing visibility | Không có — mọi câu đều đi cùng đường | Có `route_reason` trong mọi trace |
| Test độc lập | Không thể test retrieval riêng | `uv run python workers/retrieval.py` test được ngay |
| Multi-hop queries | Một lần retrieve, synthesis tổng hợp một mình | Policy worker + retrieval worker cùng cung cấp evidence cho synthesis |
| Completeness (Day 08 score) | 4.29 (dense) / 3.00 (hybrid) | Kỳ vọng > 3.00 nhờ policy worker bổ sung exception context |

**Quan sát thực tế từ lab:**  
Câu q09 (ERR-403-AUTH) — single agent sẽ retrieve rồi hallucinate một giải thích lỗi. Day 09 routing đúng vào `human_review` → abstain với confidence 0.30, không hallucinate số liệu nào.

---

## 6. Giới hạn và điểm cần cải tiến

1. **Supervisor dùng keyword matching** — không hiểu ngữ nghĩa. Câu "Khách hàng hoàn tiền" chứa "hoàn tiền" → route policy_tool, nhưng đây có thể chỉ là câu retrieval đơn giản. Cải tiến: dùng LLM intent classifier cho supervisor.
2. **policy_tool chỉ check rule-based exceptions** — không đọc được policy text phức tạp. Câu q12 (temporal scoping, đơn 31/01) trả lời sai vì không có policy v3 trong docs. Cải tiến: thêm temporal scoping logic hoặc LLM analysis trong policy_tool.
3. **MCP server là in-process mock** — không có real HTTP server, không test được network boundary. Cải tiến: implement FastAPI + `mcp` library cho bonus +2 points.
