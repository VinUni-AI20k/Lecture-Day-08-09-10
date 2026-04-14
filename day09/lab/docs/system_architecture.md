# System Architecture — Lab Day 09

**Nhóm:** 2A202600292-TranDangQuangHuy  
**Ngày:** 2026-04-14  
**Version:** 1.1

---

## 1. Tổng quan kiến trúc

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**

- Tách trách nhiệm rõ: supervisor quyết định route, worker xử lý domain.
- Trace được đầy đủ theo node (route_reason, workers_called, mcp_tools_used).
- Dễ debug hơn: lỗi route, retrieval, policy, synthesis được cô lập theo worker.

---

## 2. Sơ đồ Pipeline

**Sơ đồ thực tế của nhóm:**

```
User Task
   │
   ▼
┌──────────────┐
│  supervisor  │  -> set: supervisor_route, route_reason, needs_tool, risk_high
└──────┬───────┘
       │
   [route_decision]
       │
 ┌─────┼───────────────────────────┐
 ▼     ▼                           ▼
retrieval_worker   policy_tool_worker   human_review
 (workers/retrieval.py) (workers/policy_tool.py) (placeholder HITL)
       └──────────────┬───────────────┘
                      ▼
              synthesis_worker
            (workers/synthesis.py)
                      ▼
              supervisor_audit
        (append mcp_used + latency_ms)
                      ▼
                     END
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân loại task và route tới worker phù hợp |
| **Input** | `task` |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool` |
| **Routing logic** | Keyword/rule-based: SLA/P1 ưu tiên retrieval, refund/access vào policy, mã lỗi mơ hồ vào human_review |
| **HITL condition** | `ERR-*` hoặc tín hiệu rủi ro (`risk_high=True`) |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Retrieve evidence chunks từ KB |
| **Embedding model** | `all-MiniLM-L6-v2` (Sentence-Transformers) |
| **Top-k** | Mặc định 3 (có clamp + fallback) |
| **Stateless?** | Yes |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích policy + gọi MCP tools khi cần |
| **MCP tools gọi** | `search_kb`, `check_access_permission`, `get_ticket_info` (điều kiện) |
| **Exception cases xử lý** | `flash_sale_exception`, `digital_product_exception`, `activated_exception`, temporal note trước 01/02/2026 |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | Groq Chat Completions (`LLM_MODEL`, default `llama-3.1-8b-instant`) |
| **Temperature** | `0.1` |
| **Grounding strategy** | Chỉ tổng hợp từ `retrieved_chunks` + `policy_result`; có enforce citations |
| **Abstain condition** | Nếu không có chunks -> trả "Không đủ thông tin trong tài liệu nội bộ" |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| `search_kb` | `query`, `top_k` | `chunks`, `sources`, `total_found` |
| `get_ticket_info` | `ticket_id` | ticket details |
| `check_access_permission` | `access_level`, `requester_role`, `is_emergency` | `can_grant`, `required_approvers`, `emergency_override`, `notes` |
| `create_ticket` | `priority`, `title`, `description` | ticket mock output (bị safeguard chặn mặc định) |

---

## 4. Shared State Schema

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| `task` | str | Câu hỏi đầu vào | supervisor đọc |
| `supervisor_route` | str | Worker được chọn | supervisor ghi |
| `route_reason` | str | Lý do route + audit `mcp_used` | supervisor ghi |
| `risk_high` | bool | Flag rủi ro | supervisor ghi |
| `needs_tool` | bool | Có cần tool hay không | supervisor ghi |
| `retrieved_chunks` | list | Evidence retrieval | retrieval/policy ghi, synthesis đọc |
| `retrieved_sources` | list | Danh sách nguồn evidence | retrieval/policy ghi, synthesis đọc |
| `policy_result` | dict | Kết quả policy analysis | policy ghi, synthesis đọc |
| `mcp_tools_used` | list | Nhật ký MCP calls | policy ghi, supervisor đọc |
| `final_answer` | str | Câu trả lời cuối | synthesis ghi |
| `sources` | list | Sources được cite | synthesis ghi |
| `confidence` | float | Độ tin cậy | synthesis ghi |
| `hitl_triggered` | bool | Đánh dấu HITL | human_review/synthesis ghi |
| `history` | list | Step-by-step trace | mọi node append |
| `workers_called` | list | Chuỗi worker đã gọi | worker nodes append |
| `latency_ms` | int | Tổng latency run | supervisor_audit ghi |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó định vị bước lỗi | Có `route_reason` + trace theo worker |
| Thêm capability mới | Dễ đụng toàn pipeline | Thêm worker/tool độc lập |
| Routing visibility | Không có route-level trace | Có trong mỗi run |
| MCP integration | Không có lớp chuẩn | Có `mcp_server.py` + guardrails |

**Quan sát từ run thực tế (`sprint4_test_20260414_115500`):**
- Routing distribution: retrieval 9, policy 5, human_review 1.
- MCP usage: 5/15 queries (33.33%).
- Route accuracy theo expected_route test set: 11/15 (73.33%).

---

## 6. Giới hạn và điểm cần cải tiến

1. Multi-hop routing còn yếu: các câu `q13`, `q15` bị ưu tiên retrieval nên route lệch kỳ vọng.
2. Confidence trung bình thấp (`0.295`) và HITL cao (`86.67%`) ở run Sprint 4.
3. Retrieval fallback local đôi khi kéo thêm chunk ít liên quan, ảnh hưởng chất lượng synthesis.
