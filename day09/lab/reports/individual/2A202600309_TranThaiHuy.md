# Báo cáo cá nhân — Trần Thái Huy

**MSSV:** 2A202600309  
**Vai trò:** MCP Owner (Sprint 3)  
**Ngày nộp:** 2026-04-14  

## 1. Tôi phụ trách phần nào?

Trong lab Day 09, tôi phụ trách phần **MCP layer**: mô phỏng một “tool provider” thống nhất để các worker (đặc biệt là `policy_tool_worker`) có thể gọi tool theo một chuẩn chung thay vì hard-code từng API. File tôi chịu trách nhiệm chính là `day09/lab/mcp_server.py`, gồm `TOOL_SCHEMAS` (schema discovery/contract) và `dispatch_tool()/list_tools()` (entrypoint gọi tool).

Phần của tôi kết nối trực tiếp với bạn Hải (Policy Tool Worker) thông qua `day09/lab/workers/policy_tool.py`, nơi worker gọi `dispatch_tool()` và ghi trace vào `state["mcp_tools_used"]`. Đồng thời nó cũng hỗ trợ Long (Trace & Eval Owner) vì trace cần ghi rõ tool đã gọi và kết quả trả về.

**Bằng chứng:** tôi ghi lại các thay đổi và lệnh smoke test trong `.agent/mcp_server_standard_update_2026-04-14.md`, và cập nhật trực tiếp vào `day09/lab/mcp_server.py`.

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Tôi chọn hoàn thiện MCP theo **mức Standard (in-process mock)**, giữ interface ổn định qua `dispatch_tool()` và `TOOL_SCHEMAS`, thay vì dựng MCP server thật (HTTP/FastAPI) ngay trong lab.

**Lý do:** Sprint 3 ưu tiên “có tool + trace rõ ràng” hơn là transport. In-process mock giảm rủi ro setup (deps/port/server nền), nhưng vẫn giữ được ý chính: worker chỉ gọi `dispatch_tool`, có discovery qua `list_tools()`, và có thể thay đổi implementation của tool mà không sửa code gọi.

**Trade-off đã chấp nhận:** Không kiểm chứng được “transport-level MCP” (stdio/HTTP). Tuy nhiên, trong phạm vi bài lab này, phần quan trọng là chuẩn hóa I/O và trace, nên trade-off này hợp lý.

**Bằng chứng từ code:** Tôi thêm wrapper `MCPServer` để match ví dụ trong phân công và giữ tương thích với worker đang dùng `dispatch_tool()`:
```python
class MCPServer:
    def list_tools(self) -> list:
        return list_tools()
    def dispatch_tool(self, tool_name: str, tool_input: dict) -> dict:
        return dispatch_tool(tool_name, tool_input)
```

## 3. Tôi đã sửa một lỗi gì?

**Lỗi 1 (contract/schema mismatch):** Contract MCP trong `day09/lab/contracts/worker_contracts.yaml` yêu cầu `get_ticket_info` output có `notifications_sent` và `check_access_permission` output có `notes`, nhưng schema trong `TOOL_SCHEMAS` thiếu hai field này. Điều này gây lệch giữa “schema discovery” và output thực tế (data mock đã có `notifications_sent`, tool access đã trả `notes`).

**Cách sửa:** Bổ sung 2 field vào `TOOL_SCHEMAS` để schema phản ánh đúng output thực tế và đúng contract.

**Lỗi 2 (tool call input không hợp lệ):** Nếu client gọi sai kiểu input hoặc thiếu required field, trước đây tool có thể ném `TypeError` hoặc trả lỗi không nhất quán. Contract yêu cầu `dispatch_tool()` **không được raise** ra ngoài.

**Cách sửa:** Tôi thêm validate tối thiểu trong `dispatch_tool()`:
- `tool_input` phải là dict
- fill default theo schema (vd `top_k=3`)
- check required theo schema và trả error dict rõ ràng

**Bằng chứng sau khi sửa (output thực tế):**
```json
{"error":"Missing required fields for tool 'get_ticket_info': ['ticket_id']"}
```
Ngoài ra, gọi sai kiểu input cũng trả về error dict thay vì crash:
```json
{"error":"Invalid input for tool 'search_kb': tool_input must be a dict"}
```

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?** Tôi làm rõ ranh giới “client gọi tool” và “tool provider” bằng một interface thống nhất (`dispatch_tool`, `list_tools`) và schema rõ ràng. Việc thêm `MCPServer` wrapper cũng giúp tài liệu/phân công khớp với code thực tế, giảm hiểu nhầm khi team demo.

**Tôi làm chưa tốt ở điểm nào?** Tôi chưa giúp team validate end-to-end bằng retrieval thật do dependency chưa được cài đầy đủ (khi chạy demo `search_kb` có fallback mock). Đây là vấn đề setup, nhưng ảnh hưởng trải nghiệm test.

**Nhóm phụ thuộc vào tôi ở đâu?** Nếu MCP layer không ổn định hoặc schema lệch contract, `policy_tool_worker` sẽ khó log tool call đúng và trace thiếu thông tin, ảnh hưởng trực tiếp tiêu chí chấm Sprint 3.

**Phần tôi phụ thuộc vào thành viên khác:** Tôi phụ thuộc vào phần Policy Tool Worker (bạn Hải) để gọi thêm đúng tool trong các câu multi-hop (vd access permission), và phụ thuộc vào phần setup dependency để `search_kb` retrieve thật thay vì mock.

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thêm một “contract test” nhỏ cho MCP: chạy `list_tools()` và gọi lần lượt 4 tools với input hợp lệ/không hợp lệ, rồi assert output luôn là dict và `dispatch_tool()` không bao giờ raise. Mục tiêu là khóa tiêu chí “Không được raise exception ra ngoài dispatch_tool()”, tránh `eval_trace.py` crash khi chạy batch.
