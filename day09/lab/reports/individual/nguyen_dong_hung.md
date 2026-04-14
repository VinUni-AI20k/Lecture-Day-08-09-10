# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Đông Hưng (2A202600392)  
**Vai trò trong nhóm:** MCP Owner  
**Ngày nộp:** 2026-04-14  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi phụ trách vai trò **MCP Owner** — chịu trách nhiệm triển khai và đảm bảo MCP server hoạt động đúng, cung cấp tool interface cho các worker gọi vào.

**Module/file tôi chịu trách nhiệm:**
- File chính: `mcp_server.py`
- Phần tôi implement: FastAPI HTTP layer (`create_app()`, `serve()`) bọc lên trên 4 tools có sẵn (`search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket`), cung cấp các endpoint `/mcp/tools/list` (GET) và `/mcp/tools/call` (POST) để worker có thể gọi tool qua HTTP thay vì import trực tiếp.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Worker Owner (`policy_tool.py`) gọi MCP tool thông qua `dispatch_tool()` hoặc qua HTTP endpoint mà tôi expose. Supervisor Owner route task có `needs_tool=True` sang `policy_tool_worker`, worker đó sẽ gọi MCP server của tôi để lấy dữ liệu ticket hoặc kiểm tra quyền truy cập.

**Bằng chứng:**
- PR #6 trên GitHub: `Hung-MCP-Owner` branch
- Commit `59459f6` — chỉ chứa duy nhất file `mcp_server.py`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Chọn triển khai **FastAPI HTTP server thật** (bonus +2đ) thay vì chỉ dùng mock in-process.

Ban đầu, tôi tự thêm FastAPI layer với endpoint `/tools/call` ở port 8080. Sau đó team gửi bản `mcp_server.py` chuẩn hóa hơn với `argparse`, `create_app()`, port 8001, và cấu trúc endpoint `/mcp/tools/call` rõ ràng hơn. Tôi đã thay thế phiên bản cũ của mình bằng bản team để đảm bảo tính nhất quán.

**Các lựa chọn thay thế:**
- Option Standard: Dùng `dispatch_tool()` trực tiếp (in-process mock) — không cần HTTP.
- Option Advanced: Triển khai HTTP server bằng FastAPI.

**Lý do chọn HTTP:** Đây là yêu cầu bonus +2đ trong SCORING.md, và việc có HTTP layer giúp mô phỏng chính xác hơn cách MCP protocol hoạt động trong thực tế (client-server qua network).

**Bằng chứng từ test:**

```
# Test HTTP server thành công
PS> Invoke-RestMethod -Uri "http://127.0.0.1:8001/health"
{ "ok": true, "service": "day09-mcp-server", "timestamp": "2026-04-14T15:39:18" }

PS> Invoke-RestMethod -Uri "http://127.0.0.1:8001/mcp/tools/call" -Method Post -Body '{"tool":"get_ticket_info","input":{"ticket_id":"P1-LATEST"}}'
{ "tool": "get_ticket_info", "output": { "ticket_id": "IT-9847", "priority": "P1", "status": "in_progress" } }
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `UnicodeEncodeError` khi chạy `python mcp_server.py` trên Windows — không in được emoji/tiếng Việt ra console.

**Symptom:** Khi chạy `python mcp_server.py` lần đầu, terminal crash ngay ở dòng `print("📋 Available Tools:")` với lỗi:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4cb' in position 0
```

Pipeline không thể chạy được test nào cả.

**Root cause:** Windows sử dụng code page CP1258 (Vietnamese) làm default encoding cho stdout. Python cố encode emoji/Unicode ra CP1258 nhưng code page này không hỗ trợ emoji.

**Cách sửa:** Thêm biến môi trường `PYTHONIOENCODING=utf-8` trước khi chạy script:
```bash
$env:PYTHONIOENCODING='utf-8'; python mcp_server.py
```

Tôi cũng phát hiện lỗi tương tự ở file `eval_trace.py` dòng 192 — hàm `analyze_traces()` mở file JSON trace mà không chỉ định `encoding="utf-8"`, gây crash khi đọc trace chứa tiếng Việt. Đây là lỗi trong code của thành viên khác, tôi đã báo cho team.

**Bằng chứng sau khi sửa:** Toàn bộ 15 test questions và 10 grading questions chạy thành công 100%.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Triển khai FastAPI HTTP server đúng yêu cầu bonus, test kỹ bằng curl thật (không bịa kết quả), và giữ đúng scope — chỉ commit file `mcp_server.py`, không đụng vào code của người khác.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Ban đầu tôi đã sửa cả `policy_tool.py` và `worker_contracts.yaml` — vượt scope MCP Owner. Sau khi team nhắc, tôi phải revert lại. Lần sau cần xác định rõ ranh giới trách nhiệm từ đầu.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nếu MCP server không hoạt động, `policy_tool_worker` sẽ không gọi được `search_kb` hay `get_ticket_info`, dẫn đến thiếu dữ liệu cho câu trả lời.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần Supervisor Owner set `needs_tool=True` trong routing logic và Worker Owner gọi `dispatch_tool()` đúng format để MCP tools được kích hoạt.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ cải thiện `search_kb` tool để trả kết quả chính xác hơn, vì trace câu gq08 cho thấy sources trả về là `policy_refund_v4.txt` và `access_control_sop.txt` — không liên quan đến câu hỏi về quy định đổi mật khẩu (đáng lẽ phải trả `it_helpdesk_faq.txt`). Nguyên nhân có thể do ChromaDB index chưa đủ top_k hoặc embedding model chưa phân biệt tốt giữa các loại chính sách. Tôi sẽ thử tăng `top_k` và thêm metadata filtering theo tên file.

---

