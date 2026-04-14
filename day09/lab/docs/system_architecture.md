# System Architecture — Lab Day 09

**Nhóm:** C401-B4  
**Ngày:** 14/04/2026  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):** Nhóm chọn pattern Supervisor-Worker vì:
- Hệ thống có nhiều nhiệm vụ khác nhau: phân loại câu hỏi, truy xuất chunk liên quan, kiểm tra policy/tool nếu cần, rồi mới tổng hợp câu trả lời.
- Supervisor-Worker giúp tách rõ trách nhiệm:
    + Supervisor quyết định route
    + Retrieval worker lấy evidence
    + Policy/tool worker xử lý rule hoặc gọi MCP
    + Synthesis worker viết câu trả lời cuối
- So với single agent, Supervisor-Worker giúp tách trách nhiệm, dễ debug, dễ đánh giá từng bước, và thuận tiện mở rộng thêm worker hoặc MCP tool trong tương lai.

_________________

---

## 2. Sơ đồ Pipeline

> Vẽ sơ đồ pipeline dưới dạng text, Mermaid diagram, hoặc ASCII art.
> Yêu cầu tối thiểu: thể hiện rõ luồng từ input → supervisor → workers → output.

**Sơ đồ thực tế của nhóm:**

```
User Request
     │
     ▼
┌─────────────────────────────┐
│         Supervisor          │  ← route_reason, risk_high, needs_tool
└─────────────┬───────────────┘
              │
        [route_decision]
              │
     ┌────────┴─────────┌─────────────────────┐
     │                  │                     │
     ▼                  ▼                     ▼
┌──────────┐ ┌────────────────────┐ ┌──────────────────┐
│Retrieval │ │ Policy Tool Worker │ │   Human Review   │
│ Worker   │ │ (policy check +    │ │ (HITL placeholder│
│(evidence)│ │ MCP tool calls)    │ │  → auto approve) │
└────┬─────┘ └─────────┬──────────┘ └────────┬─────────┘
     │                 │                     │
     │                 │ nếu chưa có chunk   │
     │                 ▼                     │
     │           ┌─────────────────┐         │
     │           │Retrieval Worker │◄────────┘
     │           │   (evidence)    │
     │           └───────┬─────────┘
     └───────────────────|
                         ▼
              ┌────────────────────┐
              │  Synthesis Worker  │
              │   (answer + cite)  │
              └─────────┬──────────┘
                        │
                        ▼
                     Output
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích câu hỏi đầu vào, quyết định route sang worker phù hợp, gắn cờ risk_high, needs_tool, và điều phối luồng xử lý toàn graph. |
| **Input** | task từ user và AgentState hiện tại. |
| **Output** | supervisor_route, route_reason, risk_high, needs_tool |
| **Routing logic** | Nếu task chứa từ khóa rủi ro như cấp quyền tạm thời, ciso, bảo mật, khẩn cấp, emergency, err-, không rõ thì route sang human_review; nếu chứa từ khóa IT support như p1, p2, sla, incident, password, vpn, license, spam, reset thì route sang retrieval_worker; nếu chứa từ khóa policy như nghỉ phép, hoàn tiền, refund, flash sale, cấp quyền, access, level 1/2/3/4 thì route sang policy_tool_worker; còn lại mặc định là retrieval_worker. |
| **HITL condition** | Kích hoạt khi task có dấu hiệu rủi ro cao, khẩn cấp, liên quan bảo mật, hoặc có mã lỗi/thiếu ngữ cảnh không rõ; khi đó route sang human_review và đặt risk_high = True. Trong lab hiện tại node này auto-approve rồi quay về retrieval. |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Nhận câu hỏi, tạo embedding cho query, truy vấn ChromaDB, và trả về retrieved_chunks cùng retrieved_sources. |
| **Embedding model** | gemini-embedding-2-preview |
| **Top-k** | Mặc định 3 (DEFAULT_TOP_K = 3), có thể lấy từ state["retrieval_top_k"] nếu được truyền vào. |
| **Stateless?** | Yes. Worker chỉ đọc task/top_k từ state và ghi kết quả retrieval trở lại state, không giữ memory nội bộ giữa các lần chạy. |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích policy dựa trên task và retrieved_chunks, gọi MCP tools khi cần, cập nhật policy_result và mcp_tools_used vào state. |
| **MCP tools gọi** | search_kb khi needs_tool=True và chưa có chunks; get_ticket_info khi task có chứa ticket, p1, hoặc jira. Phần MCP client gọi thông qua dispatch_tool() trong mcp_server.py. |
| **Exception cases xử lý** | Có rule-based check cho các ngoại lệ policy gồm: Flash Sale không được hoàn tiền, sản phẩm kỹ thuật số / license key / subscription không được hoàn tiền, sản phẩm đã kích hoạt / đã đăng ký / đã sử dụng không được hoàn tiền; ngoài ra còn gắn policy_version_note nếu đơn hàng trước 01/02/2026 vì khi đó áp dụng policy v3 không có trong docs hiện tại. Worker cũng bắt lỗi MCP call fail và policy check fail. |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | gemini-2.5-flash |
| **Temperature** | 0.1 |
| **Grounding strategy** | Xây context từ retrieved_chunks và policy_result, sau đó prompt LLM với rule nghiêm ngặt: chỉ trả lời dựa trên context, không dùng kiến thức ngoài, phải nêu exceptions rõ ràng và trích dẫn nguồn ở cuối các ý quan trọng. sources được lấy từ danh sách source trong chunks. |
| **Abstain condition** | Nếu không có context đủ mạnh thì system prompt yêu cầu trả lời: “Không đủ thông tin trong tài liệu nội bộ”. Ngoài ra nếu không có chunks thì confidence bị hạ rất thấp; nếu không gọi được LLM thì trả về thông báo lỗi synthesis thay vì bịa nội dung. |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | query, top_k (optional) | chunks, sources, total_found |
| get_ticket_info | ticket_id | ticket_id, priority, status, assignee, created_at, sla_deadline |
| check_access_permission | access_level, requester_role, is_emergency (optional) | can_grant, required_approvers, approver_count, emergency_override, notes, source |
| create_ticket | priority, title, description (optional) | ticket_id, priority, title, description, status, created_at, url |

---

## 4. Shared State Schema

> Liệt kê các fields trong AgentState và ý nghĩa của từng field.

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| task | str | Câu hỏi đầu vào | supervisor đọc |
| supervisor_route | str | Worker được chọn | supervisor ghi |
| route_reason | str | Lý do route | supervisor ghi |
| retrieved_chunks | list | Evidence từ retrieval | retrieval ghi, synthesis đọc |
| policy_result | dict | Kết quả kiểm tra policy | policy_tool ghi, synthesis đọc |
| mcp_tools_used | list | Tool calls đã thực hiện | policy_tool ghi |
| final_answer | str | Câu trả lời cuối | synthesis ghi |
| confidence | float | Mức tin cậy | synthesis ghi |
| risk_high | bool | Đánh dấu yêu cầu có rủi ro cao (security, emergency, lỗi không rõ) | supervisor ghi, human_review đọc |
| needs_tool | bool | Có cần gọi MCP/tool hay không | supervisor ghi, policy_tool đọc |
| hitl_triggered | bool | Đã kích hoạt Human-in-the-loop hay chưa | human_review ghi |
| retrieved_sources | list | Danh sách nguồn tài liệu từ retrieval | retrieval ghi, synthesis đọc |
| sources | list | Nguồn được trích dẫn trong câu trả lời cuối | synthesis ghi |
| history | list | Log toàn bộ các bước xử lý trong pipeline | worker ghi |
| workers_called | list | Danh sách các worker đã được gọi trong run | worker ghi |
| latency_ms | int | Thời gian xử lý toàn pipeline (ms) | graph ghi |
| run_id | str | ID của phiên chạy để trace/debug | graph ghi |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó — không rõ lỗi ở đâu | Dễ hơn — test từng worker độc lập |
| Thêm capability mới | Phải sửa toàn prompt | Thêm worker/MCP tool riêng |
| Routing visibility | Không có | Có route_reason trong trace |
| Kiểm soát hallucination | Khó kiểm soát | Tốt hơn — synthesis bám evidence từ retrieval |
| Mở rộng hệ thống | Khó scale | Dễ mở rộng theo từng worker/module |

**Nhóm điền thêm quan sát từ thực tế lab:**

- Supervisor-Worker giúp debug dễ hơn vì có thể kiểm tra riêng từng bước như retrieval (có lấy đúng chunk không), policy (có áp dụng đúng rule không), và synthesis (có bám context không). Khi câu trả lời sai, nhóm dễ xác định lỗi nằm ở bước nào. Tuy nhiên, pipeline phức tạp hơn so với single agent và cần quản lý state cẩn thận để tránh mất dữ liệu giữa các bước.

---

## 6. Giới hạn và điểm cần cải tiến

> Nhóm mô tả những điểm hạn chế của kiến trúc hiện tại.

1. Chất lượng retrieval phụ thuộc mạnh vào chunking và embedding model; nếu chunk không tốt hoặc embedding không phù hợp thì dễ bỏ sót thông tin quan trọng hoặc lấy sai context.
2. Routing logic của Supervisor hiện đang dựa trên keyword (rule-based), chưa đủ thông minh để xử lý các câu hỏi phức tạp hoặc đa ý, dễ dẫn đến route sai worker.
3. Pipeline hiện tại chưa tối ưu về hiệu năng và độ phức tạp; các bước xử lý tuần tự (retrieval → policy → synthesis) có thể gây tăng latency và chưa có cơ chế re-ranking hoặc caching để cải thiện tốc độ và độ chính xác.
