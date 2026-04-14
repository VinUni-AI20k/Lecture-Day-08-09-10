# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Đức Anh - 2A202600146
**Vai trò trong nhóm:** MCP Owner (Sprint 3 Lead)  
**Ngày nộp:** 2026-04-14  

---

## 1. Tôi phụ trách phần nào?

Tôi phụ trách phần **MCP Server và tích hợp tool vào Policy Tool Worker** để hệ multi-agent có thể gọi external capability mà không phải hard-code vào core graph. Mục tiêu của tôi là: (1) `mcp_server.py` có ít nhất 2 tools chạy được, (2) `workers/policy_tool.py` gọi MCP tool khi cần, và (3) trace ghi nhận đầy đủ `mcp_tools_used` để phục vụ đánh giá Sprint 3/4 và debug.

**Module/file tôi chịu trách nhiệm:**
- File chính: `day09/lab/mcp_server.py` (mock MCP server + tool dispatch)
- File tích hợp MCP: `day09/lab/workers/policy_tool.py` (client wrapper `_call_mcp_tool()`)

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Supervisor (Member 1) quyết định `needs_tool=True` và route sang `policy_tool_worker`. Retrieval (Member 2) có thể cung cấp chunks trước, còn phần của tôi giúp policy worker **gọi MCP** để bổ sung thông tin (ví dụ ticket info) hoặc search KB khi thiếu context. Synthesis (Member 3) tổng hợp câu trả lời cuối, còn phần MCP của tôi đảm bảo tool-call được log để trace/debug.

**Bằng chứng:**
- `workers/policy_tool.py` có `_call_mcp_tool()` gọi `mcp_server.dispatch_tool()` (mock in-process) và append vào `state["mcp_tools_used"]`.
- Kết quả tổng hợp có trường `mcp_usage_rate` trong `day09/lab/artifacts/eval_report.json`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Tôi chọn **triển khai MCP theo mode “mock in-process” trước (Standard)** thay vì dựng HTTP MCP server thật ngay (Advanced).

**Lý do:**
Trong thời gian lab 4 giờ, mục tiêu chấm điểm Sprint 3 yêu cầu “có ít nhất 2 tools và được gọi thực tế trong trace”. Cách mock in-process (import `dispatch_tool` từ `mcp_server.py`) giúp:
- Ít phụ thuộc môi trường (không cần mở port, không cần cấu hình server URL).
- Debug nhanh (stack trace trực tiếp trong cùng process).
- Dễ đảm bảo trace có `mcp_tools_used` đúng format.

**Trade-off đã chấp nhận:**
Hy sinh tính “realistic deployment” của MCP (HTTP server) và không lấy được bonus Advanced (+2). Tuy nhiên, giải pháp này đủ để đạt full credit phần MCP integration nếu tool calls xuất hiện trong trace.

**Bằng chứng từ trace/code:**

```text
workers/policy_tool.py
  if not chunks and needs_tool:
      mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
      state["mcp_tools_used"].append(mcp_result)

  if needs_tool and any(kw in task.lower() for kw in ["ticket", "p1", "jira"]):
      mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
      state["mcp_tools_used"].append(mcp_result)
```

Và từ `day09/lab/artifacts/eval_report.json` (sau khi chạy `python eval_trace.py`) có `mcp_usage_rate: 7/100 (7%)`, chứng minh MCP tool call đã xuất hiện trong trace.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** `UnicodeEncodeError` khi chạy test/trace liên quan đến MCP và policy worker trên Windows terminal (encoding cp1252), làm các script test crash trước khi ghi trace đầy đủ.

**Symptom (pipeline làm gì sai?):**
- `python workers/policy_tool.py` crash khi in ký tự “▶” trong phần standalone test
- Một số print output (tiếng Việt có dấu) trong synthesis/policy context cũng có thể làm crash, gây mất log và khó kiểm chứng `mcp_tools_used`.

**Root cause:**
`sys.stdout` đang dùng encoding mặc định của console (cp1252) nên không thể encode nhiều ký tự Unicode.

**Cách sửa:**
Tôi thêm cấu hình `sys.stdout.reconfigure(encoding="utf-8")` (khi có) vào các file worker có in output liên quan đến MCP/policy:
- `day09/lab/workers/policy_tool.py`
- `day09/lab/workers/synthesis.py` (để in câu trả lời tiếng Việt không crash)

Ngoài ra, khi cần smoke-test MCP nhanh trong CLI, tôi dùng `python -X utf8 -c "...dispatch_tool..."` để đảm bảo output UTF-8.

**Bằng chứng trước/sau:**
- Trước: `python workers/policy_tool.py` báo `UnicodeEncodeError ... can't encode character '\u25b6'`
- Sau: `python workers/policy_tool.py` chạy hết standalone test; và `python eval_trace.py` chạy xong tạo `artifacts/eval_report.json` có `mcp_usage_rate` > 0.

---

## 4. Tôi tự đánh giá đóng góp của mình 

**Tôi làm tốt nhất ở điểm nào?**
Tôi làm tốt nhất ở việc đảm bảo phần MCP “có thật trong hệ thống” theo tiêu chí chấm: tool call được thực hiện và được log vào trace (`mcp_tools_used`). Tôi cũng ưu tiên cách làm ít rủi ro (mock in-process) để kịp tiến độ Sprint 3 và vẫn tạo được evidence cho Sprint 4.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Chất lượng tool `search_kb` trong smoke test có lúc trả `sources` rỗng, và policy worker còn phụ thuộc vào `LLM_PROVIDER` khiến `analyze_policy()` có thể trả về text thay vì dict (khó dùng downstream). Nếu có thêm thời gian, tôi sẽ chuẩn hóa kiểu dữ liệu trả về để contract luôn ổn định.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm phụ thuộc vào tôi ở Sprint 3: nếu MCP chưa chạy/không được gọi, nhóm sẽ mất điểm ở tiêu chí “MCP server có ít nhất 2 tools implement và được gọi từ worker” và trace thiếu `mcp_tools_used`.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần supervisor route đúng các case cần tool (`needs_tool=True`) và policy worker được gọi trong graph; đồng thời retrieval/synthesis cần sử dụng thông tin tool trả về để trả lời tốt các câu multi-hop (đặc biệt gq09).

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ cải thiện tool `search_kb` trong `mcp_server.py` để luôn trả về `sources` và top chunks ổn định (không rỗng trong các query policy phổ biến như “refund flash sale”). Lý do: trace hiện cho thấy MCP được gọi nhưng KB search chưa đóng góp rõ rệt; nếu `search_kb` trả evidence tốt hơn, policy worker sẽ giảm “over-abstain” ở các câu hard và giúp gq09 multi-hop đạt điểm cao hơn.

---
