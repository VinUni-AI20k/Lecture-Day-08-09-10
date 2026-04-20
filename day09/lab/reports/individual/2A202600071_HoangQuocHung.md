# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Hoàng Quốc Hùng
**Vai trò trong nhóm:** MCP Owner  
**Ngày nộp:** 14-04-2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi phụ trách việc triển khai và quản lý hệ thống Model Context Protocol (MCP) — hệ thống đóng vai trò như một giao thức kết nối (protocol) cho phép các worker agent của nhóm truy cập vào các công cụ và dữ liệu bên ngoài một cách tiêu chuẩn hóa.

**Module/file tôi chịu trách nhiệm:**
- File chính: `day09/lab/mcp_server.py`.
- Functions tôi implement: `dispatch_tool`, `list_tools`, `tool_search_kb`, `tool_get_ticket_info`, `tool_check_access_permission`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi xây dựng các API (Tools) cho các worker khác gọi. Tôi cung cấp tool `search_kb` cho Hải và Tuấn Anh để họ có thể lấy dữ liệu từ ChromaDB của Day 08. Ngoài ra, tôi phối hợp với Tuấn Anh để tích hợp tool `get_ticket_info` cho worker kiểm tra chính sách. Công việc của tôi giúp giảm bớt sự phụ thuộc lẫn nhau giữa các worker bằng cách trừu tượng hóa (abstract) các thao tác xử lý dữ liệu thông qua giao thức MCP.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
Tôi đã hoàn thiện hàm `tool_search_kb` để trỏ trực tiếp vào logic của `retrieval_worker.retrieve_dense`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Triển khai mô hình "In-Process Mock Server" thay vì xây dựng một MCP HTTP Server độc lập hoàn chỉnh trong lab này.

**Lý do:**
Việc xây dựng một HTTP server sử dụng thư viện `mcp` chính thức (mcp-python-sdk) sẽ đòi hỏi việc cài đặt thêm nhiều dependency (FastAPI, uvicorn) và cấu hình cổng mạng phức tạp, điều này làm tăng rủi ro lỗi trong thời gian lab giới hạn. Tôi đã chọn cách triển khai `dispatch_tool` đơn giản trực tiếp bằng Python. Cách này vẫn giữ đúng tinh thần của MCP là tách biệt giữa mô tả tool (Schema) và triển khai thực tế (Implementation), đồng thời giúp latency cực thấp (~1ms).

**Trade-off đã chấp nhận:**
Hệ thống sẽ không thể mở rộng để được gọi từ các agent chạy bên ngoài môi trường hiện tại. Tuy nhiên, cho mục tiêu hoàn thành các Sprint của lab, đây là giải pháp nhanh chóng và hiệu quả nhất.

**Bằng chứng từ trace/code:**
```python
# snippet từ mcp_server.py
def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Tool '{tool_name}' không tồn tại..."}
    # Gọi hàm thực thi tool trực tiếp từ registry
    tool_fn = TOOL_REGISTRY[tool_name]
    return tool_fn(**tool_input)
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Module `workers.retrieval` không thể được tìm thấy khi gọi tool `search_kb` từ `mcp_server.py`.

**Symptom (pipeline làm gì sai?):**
Khi chạy `python mcp_server.py` để test độc lập, tool `search_kb` trả về lỗi: `ModuleNotFoundError: No module named 'workers'`.

**Root cause:**
Do cấu trúc thư mục của lab, `mcp_server.py` nằm ở thư mục root của lab, còn file `retrieval.py` nằm trong folder `workers`. Khi thực thi file `mcp_server.py`, Python không tự động thêm thư mục hiện hành vào `sys.path` để tìm được module con theo kiểu tương đối.

**Cách sửa:**
Tôi đã thêm đoạn code xử lý path linh hoạt ngay trong hàm `tool_search_kb`:
```python
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
from workers.retrieval import retrieve_dense
```

**Bằng chứng trước/sau:**
- Trước: `{"error": "Failed to search KB: No module named 'workers'..."}`
- Sau: Trả về kết quả chunks từ ChromaDB thành công.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã chuẩn hóa được các `TOOL_SCHEMAS`, giúp cho các worker agent có thể biết trước input/output của tool cần gọi, rất giống với quy chuẩn của OpenAI Function Calling.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi chưa triển khai đầy đủ các tool phức tạp như `create_ticket` (hiện tại mới chỉ là in log console), nếu làm được việc này sẽ giúp hệ thống thực sự có khả năng thực hiện hành động (Action) thay vì chỉ đọc thông tin.

**Nhóm phụ thuộc vào tôi ở đâu?**
Tôi là cầu nối giữa code và dữ liệu. Nếu `dispatch_tool` của tôi bị lỗi, toàn bộ khả năng gọi tool của agent sẽ bị tê liệt.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào code của Hải để thực thi logic tìm kiếm trong `search_kb`.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ nâng cấp MCP Server lên giao thức HTTP sử dụng thư viện `mcp-python-sdk`. Trace của câu gq13 cho thấy hệ thống cần lấy thêm dữ liệu từ các ticket thật, việc có một HTTP server riêng sẽ giúp mô phỏng đúng môi trường IT Helpdesk thực tế hơn.

---
*Lưu file này với tên: `reports/individual/E.md`*
