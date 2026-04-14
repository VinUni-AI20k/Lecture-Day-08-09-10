# System Architecture — Lab Day 09

**Nhóm:** ___________  
**Ngày:** 2026-04-14  
**Version:** 1.1

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker

**Mô tả ngắn hệ thống của nhóm:**

Hệ thống Day 09 của nhóm dùng một `supervisor` để phân tích câu hỏi đầu vào và gắn các tín hiệu điều phối vào shared state, gồm `supervisor_route`, `route_reason`, `risk_high`, và `needs_tool`. Từ đó graph route sang đúng một worker xử lý chính: `retrieval_worker`, `policy_tool_worker`, hoặc `human_review`. Sau bước worker chính, pipeline luôn đi vào `synthesis_worker` để tạo câu trả lời cuối, trích nguồn và gán confidence.

Thành phần chính hiện tại:

- `graph.py`: supervisor orchestrator và LangGraph state machine
- `workers/retrieval.py`: lấy evidence từ ChromaDB
- `workers/policy_tool.py`: phân tích policy/access rule và gọi MCP tools khi cần
- `workers/synthesis.py`: tổng hợp answer grounded từ context
- `mcp_server.py`: mock MCP server với các tools `search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket`

**Lý do chọn pattern này (thay vì single agent):**

- Tách trách nhiệm rõ giữa điều phối, retrieval, policy/tool calling và synthesis nên dễ debug hơn khi pipeline trả lời sai.
- Có thể test từng worker độc lập theo contract thay vì dồn toàn bộ logic vào một prompt lớn.
- Trace dễ đọc hơn vì mỗi run đều có `route_reason`, `workers_called`, `worker_io_logs`, `mcp_tools_used`.
- Dễ mở rộng thêm worker hoặc MCP capability mới mà không phải sửa lại toàn bộ hệ thống trả lời.

---

## 2. Sơ đồ Pipeline

> Vẽ sơ đồ pipeline dưới dạng text, Mermaid diagram, hoặc ASCII art.
> Yêu cầu tối thiểu: thể hiện rõ luồng từ input → supervisor → workers → output.

**Ví dụ (ASCII art):**

```
User Request
     │
     ▼
┌──────────────┐
│  Supervisor  │  ← route_reason, risk_high, needs_tool
└──────┬───────┘
       │
   [route_decision]
       │
  ┌────┴────────────────────┐
  │                         │
  ▼                         ▼
Retrieval Worker     Policy Tool Worker
  (evidence)           (policy check + MCP)
  │                         │
  └─────────┬───────────────┘
            │
            ▼
      Synthesis Worker
        (answer + cite)
            │
            ▼
         Output
```

**Sơ đồ thực tế của nhóm:**

```
User Query
    │
    ▼
┌──────────────────────────────┐
│ Supervisor (graph.py)        │
│ - đọc task                   │
│ - set supervisor_route       │
│ - set route_reason           │
│ - set risk_high / needs_tool │
└──────────────┬───────────────┘
               │
               ▼
         [route_decision]
               │
   ┌───────────┼───────────────────────┐
   │           │                       │
   ▼           ▼                       ▼
retrieval   policy_tool            human_review
worker      worker                 (HITL placeholder)
   │           │                       │
   │           │                       └──────► retrieval_worker
   │           │
   │           ├─ phân tích domain policy/access
   │           ├─ nếu chưa có chunks và needs_tool=True:
   │           │    gọi MCP search_kb
   │           ├─ nếu là access:
   │           │    gọi check_access_permission
   │           └─ nếu là incident_access:
   │                gọi get_ticket_info
   │
   └───────────────────────┬───────────────────────┘
                           │
                           ▼
                 synthesis_worker
                 - build context
                 - trả final_answer
                 - cite sources
                 - estimate confidence
                           │
                           ▼
         Final Answer + Sources + Confidence + Trace
```

**Lưu ý để đọc đúng sơ đồ hiện tại:**

- Graph runtime hiện tại không có các node riêng kiểu `PolicyDomain`, `IncidentSupportDomain`, `ITHelpdeskDomain`.
- `policy_tool_worker` có thể tự gọi `search_kb` qua MCP nếu chưa nhận được `retrieved_chunks`, nên retrieval không phải lúc nào cũng chạy trước policy.
- `human_review` hiện là placeholder auto-approve trong lab mode; sau khi trigger sẽ chuyển tiếp sang `retrieval_worker`.

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
| ---------- | ----- |
| **Nhiệm vụ** | Phân tích task đầu vào và quyết định worker chính cho run hiện tại. Supervisor không tự trả lời câu hỏi nghiệp vụ. |
| **Input** | `task` từ user query và shared `AgentState` |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool` |
| **Routing logic** | Query chứa `refund`, `flash sale`, `license`, `access`, `level 3`, `approval`, `security` → route `policy_tool_worker`; query chứa `P1`, `SLA`, `ticket`, `escalation`, `incident`, `on-call` → route `retrieval_worker`; query chứa `ERR-` → route `human_review`; nếu không match gì → fallback `retrieval_worker`. |
| **HITL condition** | Hiện tại trigger trực tiếp khi task chứa `ERR-`. Các tín hiệu `risk_high` khác mới được log vào state chứ chưa route sang HITL tự động. |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
| ---------- | ----- |
| **Nhiệm vụ** | Lấy evidence từ ChromaDB và ghi vào `retrieved_chunks`, `retrieved_sources`. |
| **Retrieval mode** | Hỗ trợ `dense`, `sparse`, `hybrid`; mặc định để `auto` rồi chọn theo query. |
| **Embedding strategy** | Nếu có `OPENAI_API_KEY` thì dùng `text-embedding-3-small`; nếu không có thì fallback `all-MiniLM-L6-v2`; cuối cùng mới fallback random embedding cho môi trường test. |
| **Top-k** | Mặc định `3` (`DEFAULT_TOP_K = 3`) |
| **Stateless?** | Yes |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
| ---------- | ----- |
| **Nhiệm vụ** | Phân tích policy/rule cho các nhóm câu hỏi refund, access, incident-access; ghi `policy_result` và `mcp_tools_used`. |
| **Input chính** | `task`, `retrieved_chunks`, `needs_tool`, `risk_high` |
| **Domain xử lý** | `refund`, `access`, `incident_access`, `unknown` |
| **MCP tools gọi** | `search_kb`, `get_ticket_info`, `check_access_permission` |
| **Cách hoạt động** | Nếu chưa có chunks và `needs_tool=True` thì worker tự gọi `search_kb`; sau đó detect domain lại nếu cần. Với access domain, worker parse access level rồi gọi `check_access_permission`. Với incident-access, worker gọi thêm `get_ticket_info`. |
| **Exception cases xử lý** | `flash_sale_exception`, `digital_product_exception`, `activated_exception`, và `policy_version_note` cho các case temporal scoping trước `01/02/2026`. |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
| ---------- | ----- |
| **Nhiệm vụ** | Tổng hợp answer cuối từ `retrieved_chunks` và `policy_result`, sau đó ghi `final_answer`, `sources`, `confidence`. |
| **LLM model** | Mặc định `gpt-4o-mini`; fallback `gemini-2.5-flash` nếu dùng Google API; nếu không gọi được model thì fallback template answer. |
| **Temperature** | `0.1` ở nhánh OpenAI |
| **Grounding strategy** | Build context từ chunks + policy analysis + tool findings, rồi prompt model chỉ trả lời dựa trên context và có citation. |
| **Abstain condition** | Nếu context thiếu hoặc policy worker báo lỗi thì trả lời theo hướng `Không đủ thông tin trong tài liệu nội bộ` và hạ confidence. |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
| ---- | ----- | ------ |
| `search_kb` | `query`, `top_k` | `chunks`, `sources`, `total_found` |
| `get_ticket_info` | `ticket_id` | ticket details từ mock database |
| `check_access_permission` | `access_level`, `requester_role`, `is_emergency` | `can_grant`, `required_approvers`, `emergency_override`, `notes` |
| `create_ticket` | `priority`, `title`, `description` | mock `ticket_id`, `url`, `created_at` |

---

## 4. Shared State Schema

> Liệt kê các fields trong AgentState và ý nghĩa của từng field.

| Field | Type | Mô tả | Ai đọc/ghi |
| ----- | ---- | ----- | ---------- |
| `task` | `str` | Câu hỏi đầu vào | supervisor đọc |
| `supervisor_route` | `str` | Worker được supervisor chọn | supervisor ghi, graph đọc |
| `route_reason` | `str` | Lý do route | supervisor ghi, trace/eval đọc |
| `risk_high` | `bool` | Cờ đánh dấu query có rủi ro cao | supervisor ghi, policy/human_review đọc |
| `needs_tool` | `bool` | Cho biết run này có thể cần MCP tools | supervisor ghi, policy_tool đọc |
| `hitl_triggered` | `bool` | Cho biết pipeline đã đi qua human review chưa | human_review ghi, eval/trace đọc |
| `retrieved_chunks` | `list` | Evidence từ retrieval hoặc từ MCP `search_kb` | retrieval/policy_tool ghi, synthesis đọc |
| `retrieved_sources` | `list` | Nguồn lấy được từ retrieval | retrieval/policy_tool ghi, synthesis/eval đọc |
| `policy_result` | `dict` | Kết quả kiểm tra policy/tool analysis | policy_tool ghi, synthesis đọc |
| `mcp_tools_used` | `list` | Danh sách tool calls đã thực hiện | policy_tool ghi, eval đọc |
| `worker_io_logs` | `list` | Log input/output/error của từng worker | retrieval/policy_tool/synthesis ghi |
| `error` | `dict \| null` | Lỗi pipeline ở mức node nếu có | graph ghi, eval đọc |
| `final_answer` | `str` | Câu trả lời cuối | synthesis ghi |
| `sources` | `list` | Nguồn cuối cùng được cite trong answer | synthesis ghi |
| `confidence` | `float` | Mức tin cậy của answer | synthesis ghi |
| `history` | `list` | Nhật ký text theo từng bước trong graph | supervisor và mọi worker ghi |
| `workers_called` | `list` | Danh sách worker/node đã được gọi trong run | worker/node ghi, eval đọc |
| `latency_ms` | `int hoặc null` | Thời gian chạy toàn pipeline | graph ghi, eval đọc |
| `run_id` | `str` | ID duy nhất của mỗi run | graph ghi, `save_trace` đọc |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
| -------- | --------------------- | -------------------------- |
| Debug khi sai | Khó biết lỗi nằm ở retrieval, policy hay generation | Dễ hơn vì trace tách theo từng worker |
| Thêm capability mới | Phải nhồi thêm logic vào một prompt hoặc một flow duy nhất | Có thể thêm worker hoặc MCP tool riêng |
| Routing visibility | Hầu như không có quyết định route rõ ràng | Có `supervisor_route`, `route_reason`, `workers_called` trong trace |
| Tool calling | Dễ bị trộn lẫn với logic trả lời | Tập trung trong `policy_tool_worker`, dễ quan sát hơn |

**Nhóm điền thêm quan sát từ thực tế lab:**

- Với các câu access/policy, route sang `policy_tool_worker` giúp nhìn rõ worker đã gọi tool nào và vì sao.
- Với các câu incident/SLA đơn giản, đi thẳng `retrieval_worker -> synthesis_worker` cho pipeline ngắn và dễ đọc.
- Human review hiện mới là placeholder nên supervisor-worker pattern đã rõ, nhưng HITL thực sự vẫn còn là phần cần hoàn thiện thêm.

---

## 6. Giới hạn và điểm cần cải tiến

> Nhóm mô tả những điểm hạn chế của kiến trúc hiện tại.

1. Kiến trúc runtime hiện tại còn đơn giản; graph mới route sang một worker chính rồi synthesis, chưa có domain nodes riêng như một số sơ đồ mở rộng.
2. `policy_tool_worker` có thể tự gọi `search_kb`, nên ranh giới giữa retrieval và policy chưa thật sự tách bạch hoàn toàn.
3. `human_review` mới là auto-approve placeholder trong lab mode, chưa có cơ chế pause/resume với human input thật.
