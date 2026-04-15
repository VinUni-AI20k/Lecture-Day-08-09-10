# System Architecture — Lab Day 09

**Nhóm:** Team 62  
**Ngày:** 2026-04-14  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**

Hệ thống Day 08 dùng một RAG pipeline duy nhất xử lý toàn bộ: retrieve → policy check → generate. Khi trả lời sai, không thể xác định lỗi nằm ở bước nào. Day 09 tách thành các worker độc lập với vai trò rõ ràng: Supervisor ra quyết định routing, từng Worker xử lý domain riêng, Synthesis tổng hợp cuối. Mỗi worker có thể test độc lập và trace ghi lại toàn bộ luồng.

---

## 2. Sơ đồ Pipeline

```
User Request (task)
        │
        ▼
┌───────────────────┐
│    Supervisor     │  graph.py
│  route_decision() │  → supervisor_route
│                   │  → route_reason ("MCP enabled/disabled")
│                   │  → risk_high, needs_tool
└────────┬──────────┘
         │
    [conditional routing]
         │
   ┌─────┴──────────────────────┐
   │             │              │
   ▼             ▼              ▼
Retrieval    Policy Tool    Human Review
 Worker       Worker         (HITL)
retrieval.py  policy_tool.py
   │             │
   │         [MCP calls]
   │         search_kb()
   │         check_access_permission()
   │         get_ticket_info()
   │             │
   └─────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  Synthesis   │  synthesis.py
  │   Worker     │  → final_answer (với citation [1][2])
  │              │  → confidence score
  └──────┬───────┘
         │
         ▼
      Output (AgentState)
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích task, quyết định route, KHÔNG tự trả lời domain |
| **Input** | `task` (câu hỏi từ user) |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool` |
| **Routing logic** | Keyword matching: policy/access keywords → policy_tool_worker; SLA/ticket keywords → retrieval_worker; error code + risk → human_review |
| **HITL condition** | `error_code_pattern` (ERR-xxx) + `risk_keywords` (khẩn cấp, emergency) |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Embed query, query ChromaDB, trả về top-k chunks có evidence |
| **Embedding model** | `sentence-transformers/all-MiniLM-L6-v2` (offline, không cần API key) |
| **Top-k** | 3 (mặc định, cấu hình qua `retrieval_top_k` trong state) |
| **Stateless?** | Yes — không giữ state giữa các lần gọi |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Kiểm tra policy exception, gọi MCP tools khi `needs_tool=True` |
| **MCP tools gọi** | `search_kb` (luôn gọi khi needs_tool), `check_access_permission` (khi có access/quyền keyword), `get_ticket_info` (khi có ticket/P1 keyword) |
| **Exception cases xử lý** | Flash Sale, digital product/license key, sản phẩm đã kích hoạt, temporal scoping (policy v3 vs v4 theo ngày đặt hàng) |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | `gpt-4o-mini` (OpenAI) hoặc `gemini-1.5-flash` (Google), cấu hình qua `.env` |
| **Temperature** | 0 — deterministic để consistency |
| **Grounding strategy** | Chỉ dùng evidence từ `retrieved_chunks` và `policy_result` trong state; không dùng prior knowledge |
| **Abstain condition** | Khi không có chunks hoặc confidence < threshold → nêu rõ "không đủ thông tin" |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| `search_kb` | `query`, `top_k=3` | `chunks`, `sources`, `total_found` |
| `get_ticket_info` | `ticket_id` | ticket details (priority, status, assignee, SLA deadline) |
| `check_access_permission` | `access_level`, `requester_role`, `is_emergency` | `can_grant`, `required_approvers`, `emergency_override` |
| `create_ticket` | `priority`, `title`, `description` | `ticket_id`, `url`, `created_at` (MOCK) |

---

## 4. Shared State Schema

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| `task` | str | Câu hỏi đầu vào | supervisor đọc |
| `supervisor_route` | str | Worker được chọn | supervisor ghi |
| `route_reason` | str | Lý do route + MCP enabled/disabled | supervisor ghi |
| `risk_high` | bool | True nếu task có risk cao | supervisor ghi |
| `needs_tool` | bool | True nếu cần gọi MCP | supervisor ghi |
| `hitl_triggered` | bool | True nếu HITL đã kích hoạt | human_review ghi |
| `retrieved_chunks` | list | Evidence từ retrieval | retrieval ghi, synthesis đọc |
| `retrieved_sources` | list | Danh sách tài liệu nguồn | retrieval ghi, synthesis đọc |
| `policy_result` | dict | Kết quả policy check + exceptions | policy_tool ghi, synthesis đọc |
| `mcp_tools_used` | list | Tool calls (tool, input, output, timestamp) | policy_tool ghi |
| `final_answer` | str | Câu trả lời cuối với citation | synthesis ghi |
| `confidence` | float | Mức tin cậy 0.0–1.0 | synthesis ghi |
| `workers_called` | list | Thứ tự workers đã chạy | mỗi worker append |
| `history` | list | Log chi tiết từng bước | mỗi node append |
| `latency_ms` | int | Tổng thời gian xử lý | graph ghi |
| `run_id` | str | ID định danh run | graph ghi |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)
| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó — không rõ lỗi ở retrieval hay generation | Dễ — test từng worker độc lập, trace ghi từng bước |
| Thêm capability mới | Phải sửa toàn prompt | Thêm MCP tool trong `mcp_server.py` |
| Routing visibility | Không có | `route_reason` rõ ràng trong mọi trace |
| Xử lý edge case | Hard-code trong prompt | Policy worker tách riêng, dễ cập nhật rule |
| Extensibility | Phải re-prompt khi domain mới | Thêm worker mới, không ảnh hưởng worker cũ |

**Quan sát từ thực tế lab:**  
Câu hỏi `gq09` (P1 lúc 2am + cấp quyền Level 2 cho contractor) cần cross-document: SLA P1 từ `sla_p1_2026.txt` và access control từ `access_control_sop.txt`. Single agent Day 08 không có cơ chế nào để ưu tiên retrieve cả hai. Day 09 với `policy_tool_worker` + MCP `search_kb` có thể retrieve từ cả hai nguồn và gọi `check_access_permission` bổ sung.

---

## 6. Giới hạn và điểm cần cải tiến

1. **Routing bằng keyword**: Dễ sai với câu hỏi mơ hồ (ví dụ: "quy trình xử lý lỗi" có thể là SLA hoặc access control). LLM classifier sẽ tốt hơn nhưng tốn thêm 1 LLM call.
2. **Confidence hard-code**: Synthesis worker tính confidence dựa trên heuristic, không phải LLM-as-judge thực sự. Kết quả không ổn định.
3. **Không có retry logic**: Nếu 1 worker fail, pipeline không tự retry với strategy khác.
**Bối cảnh vấn đề:** `policy_tool_worker_node` trong `graph.py` tự gọi `retrieval_run` trước khi chạy policy_tool để đảm bảo có evidence. Kết quả: khi `policy_tool.py` chạy, `retrieved_chunks` đã có sẵn → điều kiện ban đầu `if not chunks and needs_tool` không bao giờ trigger MCP. Trace ghi `mcp_tools_used: []` dù route là policy và `needs_tool=True`.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Giữ `if not chunks and needs_tool` | Không gọi MCP nếu đã có đủ evidence | MCP không bao giờ được gọi trong thực tế — vi phạm Sprint 3 DoD |
| Đổi sang `if needs_tool` (luôn gọi MCP) | MCP luôn được gọi khi supervisor quyết định cần tool | Gọi thêm 1 search_kb dù đã có chunks — hơi redundant |
| Bỏ retrieval trước, để policy_tool tự gọi MCP search_kb | MCP là nguồn duy nhất — clean architecture | Phải sửa graph.py của Sprint 1 — rủi ro break |

**Phương án đã chọn:** Đổi sang `if needs_tool` — luôn gọi MCP khi supervisor set `needs_tool=True`. Lý do: Sprint 3 yêu cầu trace ghi `mcp_tool_called` thực tế; `needs_tool=True` là tín hiệu từ supervisor rằng MCP cần được dùng — policy_tool phải tôn trọng quyết định đó. Gọi thêm 1 `search_kb` chấp nhận được vì kết quả có thể bổ sung chunk mới.

**Bằng chứng từ trace/code:**
```json
// Sau fix — run mới:
{
  "supervisor_route": "policy_tool_worker",
  "route_reason": "task contains policy/access keywords: hoàn tiền, flash sale | MCP enabled: search_kb + check_access_permission",
  "needs_tool": true,
  "mcp_tools_used": [
    {
      "tool": "search_kb",
      "input": {"query": "Khách hàng Flash Sale yêu cầu hoàn tiền...", "top_k": 3},
      "output": {"chunks": [...], "sources": ["policy_refund_v4.txt"], "total_found": 3},
      "timestamp": "2026-04-14T..."
    }
  ]
}
```

---

## 3. Kết quả grading questions

> *Phần này sẽ được cập nhật sau khi `grading_questions.json` được public lúc 17:00 và pipeline chạy xong.*

**Tổng điểm raw ước tính:** ___ / 96

**Câu pipeline xử lý tốt nhất (dự đoán dựa trên test_questions):**
- **gq01** (P1 lúc 22:47 — ai nhận thông báo): Pipeline route đúng `retrieval_worker`, retrieve từ `sla_p1_2026.txt`, answer có escalation timeline và notification channels.
- **gq04** (store credit %): Fact đơn giản từ 1 doc — retrieval đủ, confidence cao.

**Câu pipeline có thể gặp khó:**
- **gq07** (mức phạt tài chính vi phạm SLA P1): Thông tin không có trong 5 tài liệu → pipeline nên abstain. Nếu synthesis hallucinate sẽ bị penalty −5 điểm.