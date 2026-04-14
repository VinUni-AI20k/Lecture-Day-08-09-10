# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Phạm Quốc Dũng  
**Vai trò trong nhóm:** MCP Owner  
**Ngày nộp:** 2026-04-14  
**Độ dài:** ~640 từ  
**Kết quả đối chiếu team_task_allocation:** Đã hoàn thành nhiệm vụ được giao (2/2 file owner + 4/4 MCP tools)

---

## 1. Tôi phụ trách phần nào? (100-150 từ)

Trong Day09, tôi phụ trách đúng 2 file owner trong phân công: `day09/lab/mcp_server.py` và `day09/lab/workers/retrieval.py`. Ở `mcp_server.py`, tôi xây dựng lớp MCP mock gồm `TOOL_SCHEMAS`, `list_tools()`, `dispatch_tool()` và 4 tool chính: `search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket`. Ở `retrieval.py`, tôi chốt luồng retrieve dense từ ChromaDB và trả về đúng contract (`retrieved_chunks`, `retrieved_sources`, `worker_io_logs`). Phần của tôi là điểm giao giữa supervisor/policy với data backend.

**Module/file tôi chịu trách nhiệm:**
- File chính: `day09/lab/mcp_server.py`, `day09/lab/workers/retrieval.py`
- Functions tôi implement/chốt contract: `list_tools`, `dispatch_tool`, `_validate_tool_input`, `tool_search_kb`, `tool_get_ticket_info`, `tool_check_access_permission`, `tool_create_ticket`, `retrieve_dense`, `run`

**Bằng chứng thực thi:**
- Chạy `python workers/retrieval.py`: retrieve được 3/3 query test với source đúng domain.
- Chạy `python mcp_server.py`: show đủ 4 tools và test được các luồng `search_kb`, `get_ticket_info`, `check_access_permission`, unknown tool.
- Chạy `python -m pytest tests/test_mcp_server.py -q`: 11 passed; full suite `python -m pytest -q`: 19 passed.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150-200 từ)

**Quyết định:** Tôi chọn mock MCP in-process bằng `dispatch_tool()` + schema validation, thay vì dùng HTTP MCP server trong scope lab 4 giờ.

Lý do là bài cần ưu tiên tính ổn định và tốc độ test. Nếu worker gọi trực tiếp function thì sẽ hard-code và khó mở rộng. Nếu dùng HTTP server ngay sẽ tốn effort cho endpoint, auth, timeout, retry, trong khi nhóm đang cần chốt route và quality answer. Cách in-process vẫn giữ interface MCP (`tools/list`, `tools/call`) nên dễ nâng cấp sau, đồng thời dễ viết test contract nhanh. Hiệu quả thấy rõ ở chỗ policy worker gọi tool theo intent mà không cần biết implementation bên dưới, và test có thể monkeypatch tool để kiểm tra từng nhánh.

**Trade-off đã chấp nhận:**
- Chưa cover lỗi mạng (timeout, retry, circuit-breaker).
- Chưa mô phỏng deployment tách process.

**Bằng chứng từ code:**

```python
validation_error = _validate_tool_input(tool_name, tool_input)
if validation_error:
    return validation_error

try:
    result = tool_fn(**tool_input)
    ...
except TypeError as e:
    return {"error": f"Invalid input for tool '{tool_name}': {e}", ...}
```

---

## 3. Tôi đã sửa một lỗi gì? (150-200 từ)

**Lỗi:** Drift contract input giữa schema và runtime ở MCP boundary.

**Triệu chứng:** Input sai kiểu dữ liệu không được chặn nhất quán tại boundary, gây hành vi mơ hồ khi worker bên trên gọi MCP. Ví dụ `top_k` theo schema là integer, nhưng client gửi string thì cần bị reject sớm với lỗi rõ ràng.

**Nguyên nhân gốc:** Dispatch layer thiếu gate validation tập trung, nên mỗi tool "tự vệ" theo cách riêng (ép kiểu, default, hoặc fail). Kết quả là contract MCP không nghiêm và khó debug.

**Cách sửa:** Tôi thêm `_matches_schema_type` + `_validate_tool_input` trong `dispatch_tool` để check `required`, `type`, `enum`, trả về error dict có cấu trúc (`missing_required`, `type_errors`, `enum_errors`, kèm `schema`). Tôi cũng bổ sung thông điệp unknown tool kèm danh sách tools có sẵn.

**Bằng chứng trước/sau:**
- Sau khi fix, command:
	`dispatch_tool('search_kb', {'query': 'SLA', 'top_k': '2'})`
	trả về: `type_errors: ["field 'top_k' expected 'integer' but got 'str'"]`.
- Sau khi fix, command:
	`dispatch_tool('unknown_tool', {})`
	trả về error kèm available tools.
- Regression test xác nhận: `tests/test_mcp_server.py` pass 11/11, có case `test_search_kb_top_k_type_validation` và `test_dispatch_unknown_tool_returns_error`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100-150 từ)

Điểm tôi làm tốt nhất là chốt được boundary contract rõ ràng cho MCP tools và giữ output format ổn định để worker khác dùng an toàn. Việc tách `TOOL_SCHEMAS` + `dispatch_tool` + test contract giúp nhóm debug nhanh, đặc biệt khi policy worker gọi tool theo intent. Điểm chưa tốt là reliability vẫn ở mức mock: chưa có timeout/retry và metrics chi tiết theo từng tool call. Nhóm phụ thuộc vào tôi ở chỗ boundary MCP; nếu boundary mơ hồ thì policy worker dễ routing sai và synthesis thiếu evidence.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thêm timeout + retry metadata + standardized error code cho mỗi tool call, ưu tiên implement ngay trong `dispatch_tool` và log vào `mcp_tools_used`. Lý do: trong `artifacts/eval_report.json`, tỉ lệ dùng MCP là 6/15 (40%), nghĩa là đường MCP đã được sử dụng thường xuyên; khi có lỗi tool thì cần telemetry chi tiết hơn để truy vết nhanh worker nào fail và fail theo loại nào.
