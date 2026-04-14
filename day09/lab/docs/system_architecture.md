# System Architecture — Lab Day 09

**Nhóm:** 67  
**Ngày:** 14/04/2026  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**
Giúp chia tách rõ ràng logic phân loại (Routing), tra cứu (Retrieval) và công cụ (Tools). Cho phép kiểm tra rủi ro (HITL) độc lập trước khi thực thi nhằm tránh ảo giác và sai lệch quy trình nội bộ khắt khe.

---

## 2. Sơ đồ Pipeline

**Sơ đồ thực tế của nhóm:**

```
User Request
     │
     ▼
┌──────────────┐
│  Supervisor  │  ← Kiểm tra Keyword: "hoàn tiền", "refund", "err-", "P1"...
└──────┬───────┘
       │
   [route_decision] (if/else)
       │
  ┌────┼───────────────────────────┐
  │    │                           │
  ▼    ▼                           ▼
Human Review (HITL)         Policy Tool Worker
  │                              (gọi MCP search_kb, get_ticket_info)
  │                                │
  └─────────┬──────────────────────┘
            │
            ▼ (Nếu default route hoặc sau khi duyệt)
     Retrieval Worker
        (query ChromaDB)
            │
            ▼
      Synthesis Worker
        (answer + cites)
            │
            ▼
         Output
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Nhận task, phân tích từ khóa và điều hướng đến Worker tương ứng. Đánh giá rủi ro (`risk_high`). |
| **Input** | `state["task"]` |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool` |
| **Routing logic** | Rule-based (Keyword matching). Nhận diện "hoàn tiền, cấp quyền..." → `policy_tool_worker`. Gặp "err-" → `human_review`. Phần còn lại chuyển default `retrieval_worker`. |
| **HITL condition** | Trigger nếu string chứa `"err-"` VÀ rơi vào keyword thuộc `risk_keywords`. |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Embed câu hỏi và search ChromaDB để lấy chunks. |
| **Embedding model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Top-k** | Default 3 |
| **Stateless?** | Yes |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Kiểm tra Policy exception bằng IF/ELSE và gọi MCP Tools phụ trợ thông tin thực tế. |
| **MCP tools gọi** | `search_kb`, `get_ticket_info` |
| **Exception cases xử lý** | Flash Sale, License key/Digital product, Sản phẩm đã kích hoạt. |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | `gpt-4o-mini` hoặc `gemini-1.5-flash` |
| **Temperature** | 0.1 (để bám sát Ground truth) |
| **Grounding strategy** | Cấu trúc Context gồm `[Nguồn] + Text`. Bắt buộc cite nguồn ở cuối câu bằng `[source]`. |
| **Abstain condition** | Khi context rỗng hoặc không liên quan ngữ nghĩa. Tự bắt keyword "Không đủ thông tin" để hạ confidence = 0.3. |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | query, top_k | chunks, sources, total_found |
| get_ticket_info | ticket_id | ticket details (từ MOCK_TICKETS dict) |
| check_access_permission | access_level, requester_role | can_grant, required_approvers, emergency_override |
| create_ticket | priority, title, description | ticket_id, url (lưu vào tickets_db.json) |

---

## 4. Shared State Schema

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| task | str | Câu hỏi đầu vào | supervisor đọc |
| supervisor_route | str | Worker được chọn | supervisor ghi |
| route_reason | str | Lý do route | supervisor ghi |
| retrieved_chunks | list | Evidence từ retrieval | retrieval ghi, synthesis đọc |
| policy_result | dict | Kết quả kiểm tra policy | policy_tool ghi, synthesis đọc |
| mcp_tools_used | list | Tool calls đã thực hiện | policy_tool ghi, synthesis đọc |
| final_answer | str | Câu trả lời cuối | synthesis ghi |
| confidence | float | Mức tin cậy (0.0 - 1.0) | synthesis ghi |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó — không rõ lỗi ở khâu VectorDB hay Prompt | Dễ hơn — test từng worker thông qua `worker_io_logs` |
| Thêm capability mới | Phải sửa toàn prompt | Chỉ việc đăng ký tool vào `mcp_server` và báo Policy Worker |
| Routing visibility | Không có | Có log `route_reason` thể hiện rule nào được trigger |

**Nhóm điền thêm quan sát từ thực tế lab:**
Policy_tool_worker khi kết nối MCP là điểm mạnh xuất sắc: Nó tự động detect ra truy vấn chứa ticket ID khẩn cấp, từ chối policy vì đó là Flash Sale một cách minh bạch qua mảng `exceptions_found` thay vì ép LLM phải tự dò dẫm text như Day 08.

---

## 6. Giới hạn và điểm cần cải tiến

1. Logic Router trong `graph.py` hiện dùng if-else keyword tĩnh, dễ bị miss match các từ khóa không liệt kê sẵn.
2. `policy_tool_worker` implement hard-code các luật exception cho bài toán Hoàn tiền trực tiếp bằng code Python thay vì suy luận động thông qua LLM.
3. Node cấu trúc bằng code Python thuần (Option A), chưa tận dụng được tính năng Snapshot trạng thái StateGraph của LangGraph.
