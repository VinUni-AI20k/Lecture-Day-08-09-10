# System Architecture — Lab Day 09

**Nhóm:** Y3  
**Ngày:** 14/4/2026
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**

_________________

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
User Request
     │
     ▼
┌──────────────┐
│  Supervisor  │  ← route_reason, risk_high, needs_tool
└──────┬───────┘
       │
   [route_decision] (LLM)
       │
  ┌────┴────────────────────┐──────────────────────────────────┐
  │                         │                                  |
  ▼                         ▼                                  ▼
Retrieval Worker     Policy Tool Worker                  human_review
  (evidence)           (policy check + MCP)            (pause and wait human approval)
  │                         │                                   |
  └─────────┬───────────────┘───────────────────────────────────┘
            │
            ▼
      Synthesis Worker
        (answer + cite)
            │
            ▼
         Output
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Supervisor Orchestrator |
| **Input** | user's query |
| **Output** | supervisor_route, route_reason, risk_high, needs_tool |
| **Routing logic** | Trả về tên worker tiếp theo dựa vào supervisor_route trong state.|
| **HITL condition** | route == "human_review" |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Truy vấn data từ ChromaDB, trả về chunk và source |
| **Embedding model** | gpt-text-embedding-3-small |
| **Top-k** | 3 |
| **Stateless?** | Yes  |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Kiểm tra policy dựa vào context vào gọi MCP khi cần  |
| **MCP tools gọi** | check_access_permission |
| **Exception cases xử lý** | Flash Sale, Digital product, Sản phẩm đã kích hoạt, Đơn hàng trước 01/02/2026 |

### Synthesis Worker (`workers/synthesis.py`)
**Không làm**

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | ___________________ |
| **Temperature** | ___________________ |
| **Grounding strategy** | ___________________ |
| **Abstain condition** | ___________________ |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | query, top_k | chunks, sources, total_found |
| check_access_permission | access_level, requester_role, is_emergency | can_grant, required_approvers, approver_count, emergency_override, source |
| ___________________ | ___________________ | ___________________ |

---

## 4. Shared State Schema

> Liệt kê các fields trong AgentState và ý nghĩa của từng field.

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| task | str | Câu hỏi đầu vào từ user | supervisor đọc, tất cả workers đọc |
| supervisor_route | str | Worker được chọn (retrieval_worker / policy_tool_worker / human_review) | supervisor ghi, route_decision() đọc |
| route_reason | str | Lý do route (từ LLM hoặc fallback message) | supervisor ghi |
| risk_high | bool | True nếu task có rủi ro cao → cân nhắc HITL | supervisor ghi |
| needs_tool | bool | True nếu cần gọi external tool qua MCP | supervisor ghi, policy_tool đọc |
| hitl_triggered | bool | True nếu HITL node đã được kích hoạt | human_review ghi |
| retrieved_chunks | list | List chunks {text, source, score, metadata} từ ChromaDB | retrieval ghi, policy_tool & synthesis đọc |
| retrieved_sources | list | Danh sách tên file nguồn (unique) | retrieval ghi, synthesis đọc |
| policy_result | dict | Kết quả kiểm tra policy {policy_applies, exceptions_found, source} | policy_tool ghi, synthesis đọc |
| mcp_tools_used | list | Danh sách MCP tool calls {tool, input, output, timestamp} | policy_tool ghi |
| final_answer | str | Câu trả lời cuối có citation | synthesis ghi |
| sources | list | Danh sách nguồn được cite trong answer | synthesis ghi |
| confidence | float | Mức độ tin cậy 0.0–1.0 (tính từ chunk scores và exceptions) | synthesis ghi |
| history | list | Log text từng bước đã qua (debug trace) | tất cả các node append |
| workers_called | list | Danh sách workers đã gọi theo thứ tự | mỗi worker append |
| worker_io_logs | list | Log input/output chi tiết của từng worker | mỗi worker append |
| latency_ms | int | Tổng thời gian xử lý (ms) | graph ghi sau khi hoàn thành |
| run_id | str | ID của run (dạng run_YYYYMMDD_HHMMSS) | make_initial_state() ghi |


## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó — không rõ lỗi ở đâu | Dễ hơn — test từng worker độc lập |
| Thêm capability mới | Phải sửa toàn prompt | Thêm worker/MCP tool riêng |
| Routing visibility | Không có | Có route_reason trong trace |
| Xử lý exception cases | Phụ thuộc prompt engineering | Policy worker có rule-based logic riêng |
| Tích hợp external tools | Hard-code trực tiếp vào pipeline | Qua MCP dispatch_tool() chuẩn hóa |
| Kiểm soát rủi ro | Không có HITL | Có human_review node với risk_high flag |


**Nhóm điền thêm quan sát từ thực tế lab:**

- **LLM Routing (Option B)** linh hoạt hơn keyword matching: Supervisor dùng `gpt-4o-mini` hiểu ngữ nghĩa câu hỏi, không bị sai khi user dùng từ đồng nghĩa.
- **Fallback an toàn:** Nếu LLM Supervisor lỗi (timeout, hết quota), hệ thống tự động về `retrieval_worker` thay vì crash.
- **MCP interface:** Policy worker không gọi ChromaDB trực tiếp mà qua `dispatch_tool()` — khi thay đổi backend, chỉ cần sửa `mcp_server.py`.
- **Confidence-based signal:** Synthesis worker tính confidence từ chunk scores — khi confidence < 0.4, hệ thống biết mình đang trả lời không chắc.


## 6. Giới hạn và điểm cần cải tiến

> Nhóm mô tả những điểm hạn chế của kiến trúc hiện tại.

1. **LLM Supervisor tốn latency và token:** Mỗi request phải gọi thêm 1 LLM call chỉ để route. Với các câu hỏi đơn giản, keyword matching (Option A trong `graph.py:84`) sẽ nhanh và rẻ hơn. Giải pháp: dùng hybrid — keyword matching trước, chỉ fallback sang LLM khi không match rõ ràng.

2. **`get_ticket_info` và `create_ticket` bị comment out:** Hai tools này đã được implement trong `mcp_server.py:162–276` nhưng không có trong `TOOL_REGISTRY`. Policy worker có code gọi `get_ticket_info` (dòng 201) nhưng sẽ nhận error dict thay vì data thực — gây mất thông tin khi xử lý câu hỏi liên quan ticket P1.

3. **Confidence estimation chưa chính xác:** Confidence chỉ tính từ trung bình chunk cosine scores (`synthesis.py:113`) trừ đi exception penalty — không phản ánh đúng chất lượng answer thực tế. Cần dùng LLM-as-Judge hoặc bổ sung signal từ `policy_result` để tránh over-confident khi chunks không thực sự liên quan đến câu hỏi.
