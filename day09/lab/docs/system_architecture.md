# System Architecture — Lab Day 09

**Pattern:** Supervisor-Worker + MCP (mock `dispatch_tool`)  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

**Pattern đã chọn:** Supervisor-Worker (orchestrator trong `graph.py`) với ba worker: retrieval, policy/tool (+ MCP), synthesis.

**Lý do chọn thay vì single-agent (Day 08):** Day 08 gom retrieve + generate trong một pipeline khó tách lỗi. Day 09 tách ranh giới: supervisor chỉ routing và trace (`route_reason`); từng worker có contract; policy truy cập KB qua MCP (`search_kb`) thay vì import retrieval trực tiếp.

---

## 2. Sơ đồ Pipeline

```
User question
     │
     ▼
┌──────────────┐
│  Supervisor  │  route_reason, needs_tool, risk_high, retrieval_top_k
└──────┬───────┘
       │
   ┌───┴───────────────────────────────────────────┐
   │                                               │
   ▼                                               ▼
multi_hop ──► retrieval_worker ──► policy_tool_worker ──► synthesis
   │            (Chroma day09_docs)   (MCP search_kb + tools)
   │
   ├──► retrieval_worker ──► synthesis        (SLA/FAQ/HR — evidence + answer)
   │
   └──► policy_tool_worker ──► synthesis      (refund/access — MCP KB + policy)

```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|--------|
| **Nhiệm vụ** | Keyword routing: `multi_hop`, `policy_tool_worker`, `retrieval_worker`; set `needs_tool` cho MCP |
| **Input** | `task` (câu hỏi) |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool`, `retrieval_top_k` |
| **HITL** | `human_review` có thể mở rộng; lab hiện ưu tiên retrieval + abstain cho mã lỗi không có trong docs |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|--------|
| **Embedding** | `sentence-transformers` / `all-MiniLM-L6-v2` (mặc định), fallback OpenAI nếu cấu hình |
| **Vector store** | ChromaDB `day09_docs` tại `day09/lab/chroma_db` (build bằng `python build_index.py`) |
| **Top-k** | `state["retrieval_top_k"]` (mặc định 5–8) |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|--------|
| **MCP** | `search_kb` khi chưa có chunks + `needs_tool`; `get_ticket_info` khi có `ticket`/`p1` |
| **Exception** | Flash Sale, digital product, activated — rule-based + context |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|--------|
| **LLM** | OpenAI hoặc Gemini nếu có API key; nếu không có key → fallback báo lỗi cấu hình (không hallucinate) |
| **Grounding** | Prompt chỉ dùng context + `policy_result` + ticket MCP (nếu có) |

### MCP Server (`mcp_server.py`)

| Tool | Vai trò |
|------|---------|
| `search_kb` | Semantic search qua cùng embedding/Chroma với retrieval |
| `get_ticket_info` | Mock dữ liệu ticket (P1-LATEST) |

---

## 4. Shared State Schema (chính)

| Field | Ý nghĩa |
|-------|---------|
| `supervisor_route` | `retrieval_worker` \| `policy_tool_worker` \| `multi_hop` |
| `route_reason` | Lý do cụ thể (bắt buộc cho chấm điểm Day 09) |
| `retrieved_chunks` / `retrieved_sources` | Evidence |
| `policy_result` | Kết quả policy + optional `ticket_info` |
| `mcp_tools_used` | Danh sách MCP calls (tool, input, output, timestamp) |
| `workers_called` | Chuỗi worker đã chạy (dedupe) |

---

## 5. So với Day 08 (single agent)

| Tiêu chí | Day 08 | Day 09 |
|----------|--------|--------|
| Debug khi sai | Khó định vị bước | Trace: `route_reason` + worker logs |
| Thêm tool | Sửa monolith | Thêm MCP tool + rule supervisor |
| Kiểm tra độc lập | Khó | Mỗi worker chạy `python workers/…` |

---

## 6. Giới hạn

1. Routing keyword-based — có thể mis-classify câu biên; có thể nâng cấp LLM-router sau.
2. Cần API key LLM để đáp án chất lượng production; không có key thì synthesis trả thông báo lỗi.
3. `multi_hop` = retrieval rồi policy; synthesis vẫn một lần LLM — có thể tách thêm bước nếu cần.
