# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Hoàng Quốc Chung - 2A202600070  
**Vai trò trong nhóm:** MCP Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào?

Trong lab Day 09 tôi phụ trách vai trò MCP Owner, nên phần tôi làm tập trung vào Sprint 3: biến lớp tool từ mock function call thành một MCP server thật và nối worker sang client MCP đúng nghĩa. File tôi chịu trách nhiệm chính là `mcp_server.py`, phần tích hợp client trong `workers/policy_tool.py`, và cập nhật contract ở `contracts/worker_contracts.yaml` để phần MCP không còn ở trạng thái TODO. Cụ thể, trong `mcp_server.py` tôi đăng ký các tool `search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket` trên `FastMCP`, đồng thời thêm chế độ chạy stdio server bằng cờ `--stdio-server`. Ở `workers/policy_tool.py`, tôi sửa `_call_mcp_tool()` để dùng `StdioServerParameters`, `stdio_client`, `ClientSession`, sau đó parse `CallToolResult` về dict trace-friendly. Công việc của tôi nối với Supervisor Owner ở chỗ `graph.py` set `needs_tool=True` và ghi `route_reason` có “MCP lookup enabled for policy worker”, rồi nối với Worker Owner ở đầu ra vì `policy_result`, `retrieved_chunks`, `retrieved_sources` và `mcp_*` fields đều phải đủ để synthesis tiếp tục được.

**Module/file tôi chịu trách nhiệm:**
- File chính: `mcp_server.py`, `workers/policy_tool.py`, `contracts/worker_contracts.yaml`
- Functions tôi implement: `run_stdio_server()`, `mcp_search_kb()`, `mcp_get_ticket_info()`, `mcp_check_access_permission()`, `_call_mcp_tool()`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Supervisor quyết định có bật tool hay không; worker policy là nơi thực sự gọi MCP; synthesis dùng kết quả MCP để trả lời grounded. Nếu tôi chưa xong, policy worker chỉ còn cách import mock trực tiếp và nhóm sẽ không đạt option Advanced của Sprint 3.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

Bằng chứng chính là code hiện tại trong `mcp_server.py:214-257` và `workers/policy_tool.py:32-90, 221-279`, cùng contract `contracts/worker_contracts.yaml:224-274`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Tôi chọn dùng MCP server thật qua stdio với `FastMCP` thay vì giữ cách import `dispatch_tool()` trực tiếp trong cùng process.

**Lý do:**

Tôi cân nhắc ba cách. Cách thứ nhất là giữ mock class/fuction call như bản cũ; cách này nhanh nhất nhưng chỉ đạt Standard, không chứng minh được ranh giới client/server. Cách thứ hai là dựng HTTP server bằng FastAPI; cách này đúng tinh thần “external capability” nhưng tốn thêm routing, lifecycle và port management. Cách thứ ba là dùng `mcp` library với stdio transport. Tôi chọn cách thứ ba vì đây là mức Advanced đúng theo README, vẫn là server MCP thật nhưng nhẹ hơn HTTP, không cần port, và phù hợp với bài lab chạy local. Trong code hiện tại, `mcp_server.py` chạy bằng `FastMCP` và đăng ký tool; còn `workers/policy_tool.py` tạo `ClientSession`, `await session.initialize()`, rồi `call_tool()` để lấy dữ liệu tool. Quyết định này cũng giúp trace rõ hơn: ngoài `mcp_tools_used`, state còn có `mcp_tool_called` và `mcp_result`.

**Trade-off đã chấp nhận:**

Trade-off tôi chấp nhận là mỗi lần worker gọi tool sẽ spawn một subprocess MCP server nếu không có session pooling. Cách này rõ ràng và đúng chuẩn giao tiếp, nhưng latency cao hơn cách import trực tiếp. Tôi chấp nhận vì trong Sprint 3 mục tiêu chính là architecture boundary và traceability, chưa phải tối ưu hiệu năng.

**Bằng chứng từ trace/code:**

```text
graph.py:133-143
if has_refund_signal or has_access_signal:
    route = "policy_tool_worker"
    needs_tool = True
    route_reasons.append("MCP lookup enabled for policy worker")

workers/policy_tool.py:56-59
async with ClientSession(read_stream, write_stream) as session:
    await session.initialize()
    result = await session.call_tool(tool_name, tool_input)
```

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** MCP stdio bị treo khi gọi `search_kb`.

**Symptom (pipeline làm gì sai?):**

Khi tôi verify Sprint 3 bằng `.venv`, các tool nhẹ như `get_ticket_info` và `check_access_permission` qua MCP trả được kết quả, nhưng `search_kb` thì treo rất lâu hoặc timeout. Kéo theo đó, `graph.py` ở các query policy có lúc trả confidence rất thấp hoặc answer rỗng vì policy worker không lấy được context từ MCP.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Root cause nằm ở integration giữa MCP stdio và logic search. Bản đầu tiên của tôi cho `search_kb` gọi lại retrieval path có in warning ra stdout khi ChromaDB lỗi. Với stdio transport, stdout là kênh protocol của MCP, nên chỉ cần một dòng warning ngoài JSON-RPC là client có thể bị treo. Ngoài ra, đường search cũ còn kéo theo stack Chroma/embedding không ổn định cho server subprocess.

**Cách sửa:**

Tôi sửa theo hai bước. Thứ nhất, đổi warning ở `workers/retrieval.py` sang `stderr` để không phá protocol stdio. Thứ hai, tôi tách `tool_search_kb()` trong `mcp_server.py` thành lexical KB search tự chứa, đọc trực tiếp `data/docs`, tokenize, score overlap và trả về `chunks/sources/total_found`. Như vậy MCP server không còn phụ thuộc vào Chroma path đang lỗi khi chỉ cần đáp ứng Sprint 3.

**Bằng chứng trước/sau:**
> Trước khi sửa: call MCP `search_kb` bị timeout khi verify qua `.venv`.  
> Sau khi sửa: `_call_mcp_tool('search_kb', {'query': 'refund policy flash sale', 'top_k': 2})` trả được dict có `chunks`, `sources`, `total_found`; trace policy path ghi thêm `mcp_tool_called` và `mcp_result`.

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt ở chỗ giữ ranh giới interface rõ ràng. Tôi không dừng ở mức “có tool”, mà đẩy phần MCP thành một tầng riêng có server, client, trace fields và contract update đi kèm.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Tôi vẫn để chất lượng retrieval-only path chưa đủ tốt cho Sprint 4. Việc chọn lexical fallback giúp MCP ổn định, nhưng chưa giải quyết triệt để chất lượng answer ở các câu chỉ dựa retrieval.

**Nhóm phụ thuộc vào tôi ở đâu?**

Nhóm phụ thuộc vào tôi ở phần tool boundary. Nếu phần này không xong, Sprint 3 chỉ dừng ở mock function call và nhóm không có bonus Advanced.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi phụ thuộc vào Supervisor Owner để route đúng vào `policy_tool_worker`, và phụ thuộc vào Worker Owner ở synthesis để đầu ra cuối cùng tận dụng được `policy_result` cùng `retrieved_chunks`.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Nếu có thêm 2 giờ, tôi sẽ làm đúng một việc: thêm session pooling hoặc server reuse cho MCP client trong `policy_tool.py`. Lý do là trace policy path hiện gọi 2–3 tool liên tiếp (`search_kb`, `check_access_permission`, `get_ticket_info`), nên chi phí spawn MCP server lặp lại đang làm tăng latency không cần thiết. Đây là cải tiến có tác động trực tiếp nhất tới chất lượng đầu ra Sprint 4 vì sẽ giảm thời gian chạy batch và làm trace ổn định hơn.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
