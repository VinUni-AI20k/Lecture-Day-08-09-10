# System Architecture — Lab Day 09

**Nhóm:** C401-A4 
**Ngày:** 14/4/2026
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**

Tách rõ quyết định điều phối (supervisor) khỏi xử lý nghiệp vụ (workers) giúp trace được lý do route qua `route_reason`, debug theo từng worker độc lập, và mở rộng capability (thêm worker/tool) mà không phải sửa toàn bộ prompt như mô hình single-agent.

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
    |
    v
Supervisor (graph.py)
  - set supervisor_route, route_reason, risk_high, needs_tool
    |
    v
route_decision()
  |------------------------|
  |                        |
  v                        v
retrieval_worker       policy_tool_worker
  |                      |  \
  |                      |   +--(needs_tool)--> MCP: search_kb / check_access_permission / get_ticket_info
  |                      |
  +-----------> synthesis_worker <-----------+
                        |
                        v
            final_answer + confidence + sources

Nhánh HITL:
Supervisor -> human_review (placeholder) -> retrieval_worker -> synthesis_worker
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích task, xác định route phù hợp và gắn metadata routing để worker downstream xử lý. |
| **Input** | `task` (str) từ user, `history` (list, optional). |
| **Output** | supervisor_route, route_reason, risk_high, needs_tool |
| **Routing logic** | Từ khóa refund/access -> `policy_tool_worker`; từ khóa SLA/P1/ticket/escalation -> `retrieval_worker`; mã lỗi `ERR-` + rủi ro cao -> `human_review`; còn lại mặc định `retrieval_worker`. |
| **HITL condition** | Nếu route là `human_review` (placeholder node) hoặc khi synthesis trả confidence thấp (`< 0.4`) thì bật `hitl_triggered`. |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Retrieve evidence từ KB (ưu tiên ChromaDB dense retrieval, fallback lexical search trên `data/docs`). |
| **Embedding model** | `all-MiniLM-L6-v2` (SentenceTransformers, local) hoặc fallback `text-embedding-3-small` (OpenAI). |
| **Top-k** | Mặc định `3` (đọc từ `top_k` hoặc `retrieval_top_k` trong state). |
| **Stateless?** | Yes |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích policy rule/exception dựa trên context và gọi MCP tool khi `needs_tool=True`. |
| **MCP tools gọi** | `search_kb`, `check_access_permission`, `get_ticket_info` (theo signal của task). |
| **Exception cases xử lý** | Flash Sale, digital product/license/subscription, sản phẩm đã kích hoạt, và temporal note cho đơn trước `01/02/2026` (không đủ docs v3). |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | `gpt-4o-mini` (OpenAI); nếu không có API key dùng deterministic fallback. |
| **Temperature** | `0.1` |
| **Grounding strategy** | Build context từ `retrieved_chunks` + `policy_result`, chỉ trả lời theo evidence, kèm citation nguồn `[source]`. |
| **Abstain condition** | Không có chunks/evidence hoặc có `policy_version_note` thiếu dữ liệu -> trả "Không đủ thông tin trong tài liệu nội bộ". |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | query, top_k | chunks, sources |
| get_ticket_info | ticket_id | ticket details |
| check_access_permission | access_level, requester_role | can_grant, approvers |
| create_ticket | priority, title, description | ticket_id, url, created_at |

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
| risk_high | bool | Cờ cảnh báo mức rủi ro cao của task | supervisor ghi, route/hitl đọc |
| needs_tool | bool | Có cần gọi MCP tools hay không | supervisor ghi, policy_tool đọc |
| retrieved_sources | list[str] | Danh sách nguồn evidence unique | retrieval/policy_tool ghi, synthesis đọc |
| workers_called | list[str] | Sequence worker đã chạy | mọi worker ghi append, trace đọc |
| worker_io_logs | list[dict] | Log input/output/error từng worker | mọi worker ghi append, debug đọc |
| mcp_tool_called | list[str] | Tên MCP tools đã gọi | policy_tool ghi, trace đọc |
| mcp_result | list[dict] | Kết quả trả về từ MCP theo từng call | policy_tool ghi, synthesis/debug đọc |
| hitl_triggered | bool | Cờ yêu cầu/đã kích hoạt HITL | supervisor/human/synthesis ghi |
| sources | list[str] | Sources của câu trả lời cuối | synthesis ghi |
| retrieval_top_k | int | Cấu hình số chunk retrieve | graph init ghi, retrieval đọc |
| latency_ms | int | Thời gian xử lý end-to-end | graph ghi sau invoke |
| run_id, timestamp | str | Định danh run và thời điểm chạy trace | graph init ghi |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó — không rõ lỗi ở đâu | Dễ hơn — test từng worker độc lập |
| Thêm capability mới | Phải sửa toàn prompt | Thêm worker/MCP tool riêng |
| Routing visibility | Không có | Có route_reason trong trace |
| Khả năng cô lập lỗi phụ thuộc | Lỗi thư viện/tool thường làm fail toàn pipeline | Lỗi tập trung theo worker (vd `policy_tool_worker` lỗi `No module named 'mcp'` vẫn trace được rõ) |

**Nhóm điền thêm quan sát từ thực tế lab:**

Với 3 query mẫu chạy ngày 14/4/2026: query SLA route đúng qua `retrieval_worker` và trả lời có source với confidence `0.95`; 2 query policy/access route đúng qua `policy_tool_worker` nhưng fail do thiếu dependency `mcp`, vì vậy synthesis buộc abstain (confidence `0.1`). Điều này cho thấy kiến trúc multi-agent giúp xác định chính xác lỗi nằm ở integration layer thay vì retrieval/synthesis.

---

## 6. Giới hạn và điểm cần cải tiến

> Nhóm mô tả những điểm hạn chế của kiến trúc hiện tại.

1. `policy_tool_worker` phụ thuộc thư viện `mcp`; khi môi trường thiếu package này thì nhánh policy thất bại và trả abstain.
2. Routing hiện tại dựa trên keyword heuristic, chưa có classifier/LLM router nên dễ miss các câu diễn đạt gián tiếp.
3. `human_review` mới là placeholder, chưa có HITL interrupt thực sự (chưa có bước chờ/phê duyệt thủ công trong runtime).
**TrinhDucAnh**