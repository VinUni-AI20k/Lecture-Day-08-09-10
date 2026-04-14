# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Bình Minh
**Vai trò trong nhóm:** MCP Owner (Tích hợp MCP - External Capability)
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `mcp_server.py`, `workers/policy_tool.py`
- Functions tôi implement:
  - Hàm `_call_mcp_tool` (trong policy_tool.py) gửi request qua protocol REST (HTTP) đến MCP API.
  - Các endpoints FastAPI để expose `list_tools` và `dispatch_tool` (trong mcp_server.py).

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi tạo ra Endpoint chuẩn mực giúp Worker của Hoàng (Worker 1) và Quang Minh (Worker 2/3) có thể gọi external capabilities (ví dụ tra cứu KB hoặc fetch thông tin ticket). Đầu ra (output) JSON từ MCP server được parse và chuyển ngược về cho Policy Worker để tổng hợp dữ liệu. Điều này đảm bảo external API call chuẩn như yêu cầu của kiến trúc.

**Bằng chứng:**
- Thiết lập REST Client trong `_call_mcp_tool()`.
- Thêm uvicorn API vào phần main của `mcp_server.py`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Sử dụng FastAPI thay vì gọi class cục bộ, và kèm logic try-except fallback thông minh trong `_call_mcp_tool()`.

**Lý do:**
Yêu cầu của dự án khuyến khích sử dụng một external capability (Bonus Sprint 3 Advanced). Ban đầu tôi cân nhắc dùng chính thư viện MCP protocol. Tuy nhiên, để đảm bảo nhóm có thể test local dễ dàng không gặp nhiều dependency phức tạp (đồng thời tận dụng FastAPI để expose endpoints chuẩn web REST), tôi dùng httpx gọi qua server HTTP. Quyết định tiếp theo là: Nếu server chưa bật (đặc biệt trong lúc hệ thống chấm điểm tự động khởi chạy), worker sẽ tự động catch lỗi connection và import cục bộ (local override mock).

**Trade-off đã chấp nhận:**
Việc gọi HTTP sẽ làm tăng latency so với gọi class cục bộ (~2ms → ~20ms tuỳ thiết lập local) và có nguy cơ timeout. Bù lại, cấu trúc này là distributed service đúng nghĩa, tái lập y hệt kịch bản agent gọi API bên ngoài thay vì gọi local module trong 1 monolithic app.

**Bằng chứng từ trace/code:**
```python
# Ví dụ logic tự động fallback trong _call_mcp_tool:
try:
    response = httpx.post(SERVER_URL, json=payload, timeout=2.0)
    response.raise_for_status()
    ...
except Exception as e:
    # Tránh làm rớt hệ thống, import local mcp_server
    from mcp_server import dispatch_tool
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `ModuleNotFoundError: No module named 'mcp_server'` trong fallback block khi Worker chạy qua đồ thị graph ở một thư mục path khác (như từ thư mục root).

**Symptom:**
Khi pipeline cố gắng gọi `_call_mcp_tool` và server FastAPI chưa được bật, exception HTTP đẩy code vào luồng fallback cục bộ. Tuy nhiên, import `mcp_server` thất bại do file worker nằm sâu trong thư mục `workers/`, dẫn tới worker bị sập hoàn toàn và AgentState report module lỗi thay vì ra policy kết quả.

**Root cause:** Python resolver không tự động hiểu được thư mục parent (day09/lab/) khi script chạy context bên trong `workers/policy_tool.py` hoặc khi file test được gọi.

**Cách sửa:**
Tôi đã chỉnh sửa đường dẫn bằng `sys.path.insert` một cách an toàn bên trong block except để đăng ký cha của directory hiện hành, giúp import thành công `mcp_server.py`.

**Bằng chứng trước/sau:**
Trước khi sửa:
```
File "workers/policy_tool.py", line 60, in _call_mcp_tool
  from mcp_server import dispatch_tool
ModuleNotFoundError: No module named 'mcp_server'
```

Sau khi sửa:
```python
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp_server import dispatch_tool
```
(Worker vượt qua được lỗi và hoàn thành mock response.)

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Khả năng tư duy đảm bảo độ ổn định (fault-tolerance). Không chỉ làm theo yêu cầu tạo API bên ngoài, tôi còn lường trước tình huống server không bật và viết fallback mechanism rất chắc chắn.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Chưa setup streaming protocols hoặc websockets cho MCP mà mới chỉ dùng request/response REST phổ thông.

**Nhóm phụ thuộc vào tôi ở đâu?**
Các worker (như policy hay retrieval tool) sẽ bị kẹt không thể có evidence từ tool ngoài nếu luồng MCP client của tôi lỗi, dẫn đến hệ thống bị sập ngay khâu gather chứng cớ.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần Vinh (Supervisor) gửi tín hiệu `needs_tool=True` khi cần thì code mới được kích hoạt, đồng thời cần Quang Minh (Worker 2/3) parse cái object `output` JSON mà API của tôi return để sinh câu trả lời LLM.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ tích hợp chính thức thư viện `mcp` SDK (Model Context Protocol). Trực tiếp cài đặt `from mcp.server.fastmcp import FastMCP` chuẩn spec của ngành thay vì viết proxy bằng FastAPI đơn thuần. Bằng chứng là hiện tại file code mới đang định nghĩa Schema tương đồng với chuẩn JSON của protocol, nếu dùng thư viện gốc thì tính mở rộng sẽ cao hơn và plug được vào các MCP client khác (như Claude Desktop / Cursor) dễ dàng hơn rất nhiều.
