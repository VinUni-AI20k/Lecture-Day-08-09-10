# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration
**Họ và tên:** Nguyễn Thị Ngọc 
**Vai trò:** MCP Owner & Integration Specialist  
**Mã sinh viên:** 2A202600405

---

### 1. Phần tôi trực tiếp phụ trách (Module/Worker/Contract)

Trong dự án Lab Day 09, tôi chịu trách nhiệm chính về **Sprint 3 (MCP Server)** và việc tích hợp các khả năng mở rộng (external capabilities) vào hệ thống Multi-Agent. Các công việc cụ thể tôi đã thực hiện bao gồm:

- **Xây dựng MCP Server thực tế**: Thay vì chỉ sử dụng một lớp giả lập (mock class) đơn giản, tôi đã nâng cấp hệ thống lên mức **Advanced** bằng cách triển khai một HTTP Server sử dụng framework **FastAPI**. Server này (file `mcp_api.py`) đóng vai trò là một Registry trung tâm, quản lý và expose các công cụ (`tools`) qua giao thức HTTP cho các Worker khác trong hệ thống.
- **Triển khai 3 công cụ (Tools) cốt lõi**:
    1.  `search_kb`: Công cụ tìm kiếm tri thức bằng vector search (Semantic Search). Tôi đã viết logic kết nối trực tiếp với **ChromaDB** và sử dụng model `all-MiniLM-L6-v2` từ thư viện `sentence_transformers` để nhúng (embed) câu hỏi của người dùng và truy vấn dữ liệu chính xác.
    2.  `get_ticket_info`: Công cụ tra cứu thông tin Ticket từ hệ thống Jira (được giả lập dữ liệu JSON).
    3.  `create_ticket`: Công cụ cho phép Agent thực hiện hành động tạo mới một Ticket và lưu trữ thực tế vào database file `tickets_db.json`.
- **Tích hợp Worker và Traceability**: Tôi đã trực tiếp can thiệp vào `policy_tool.py` để thay thế các lệnh gọi database trực tiếp bằng việc gọi qua MCP Client. Đồng thời, tôi thiết lập cấu trúc log Trace (`mcp_tool_called` và `mcp_result`) trong `AgentState` để đáp ứng yêu cầu chấm điểm tự động trong file `SCORING.md`.
- **Xử lý Temporal Scoping**: Tôi đã thêm logic xử lý ngày tháng (regex) vào `policy_tool.py` để phân biệt các phiên bản chính sách hoàn tiền (v3 vs v4) dựa trên ngày đặt hàng của người dùng.

### 2. Một quyết định kỹ thuật quan trọng

**Quyết định**: Chuyển đổi từ mô hình In-process Mock sang **FastAPI HTTP Server** cho MCP.

**Lý do chọn**: 
Ban đầu, hệ thống chỉ yêu cầu một file Python đơn giản để mô phỏng MCP. Tuy nhiên, trong quá trình phát triển, tôi nhận thấy việc import trực tiếp các thư viện nặng như `chromadb` và `torch` (của `sentence_transformers`) vào mọi Worker sẽ làm tăng đáng kể thời gian khởi động của toàn bộ Graph (latency) và tiêu tốn rất nhiều RAM.

Bằng cách tách MCP ra thành một service riêng biệt chạy qua HTTP:
1.  **Tách biệt trách nhiệm (Separation of Concerns)**: Các Worker chỉ cần biết URL của API, không cần quan tâm đến logic phức tạp hay thư viện của ChromaDB.
2.  **Tối ưu hiệu suất**: Model embedding chỉ được load một lần duy nhất khi khởi động API Server. Các Worker gọi tool qua JSON nên cực kỳ nhẹ và nhanh.
3.  **Khả năng mở rộng**: Trong tương lai, chúng ta có thể deploy API Server này lên Cloud độc lập với Agent.
4.  **Điểm thưởng**: Quyết định này giúp nhóm đạt thêm **+2 điểm Bonus** cho hạng mục Sprint 3 Advanced.

### 3. Một lỗi kỹ thuật đã sửa

**Mô tả lỗi**: Lỗi **DLL load failed** khi chạy `sentence_transformers` trên Windows.
Trong quá trình triển khai `tool_search_kb` kết nối trực tiếp với ChromaDB, tôi gặp phải lỗi hệ thống không thể nạp các file DLL của thư viện `torch` hoặc `onnxruntime` khi gọi từ các process con của Graph.

**Cách sửa**:
Tôi đã thực hiện hai thay đổi quan trọng:
1.  **Lazy Loading**: Tôi bọc logic load model và collection vào hàm `_get_kb_resources()` với cơ chế kiểm tra biến toàn cục `_KB_MODEL`. Model chỉ được khởi tạo khi có yêu cầu gọi tool lần đầu tiên.
2.  **Đường dẫn tuyệt đối**: Trên Windows, đường dẫn tương đối thường gây lỗi khi script được chạy từ các thư mục khác nhau (như từ root vs từ `/lab`). Tôi đã sử dụng `os.path.abspath` để định vị chính xác thư mục `chroma_db`.
3.  **Cô lập môi trường**: Việc chuyển sang FastAPI giúp lỗi DLL này không còn ảnh hưởng đến luồng chính của `graph.py`, vì model được load trong một tiến trình (process) hoàn toàn độc lập.

**Bằng chứng**: Trước khi sửa, lệnh `python graph.py` bị crash ngay lập tức. Sau khi sửa và tách service, trace log ghi nhận `mcp_result` trả về thành công 100% với độ trễ thấp.

### 4. Tự đánh giá

**Làm tốt**: 
- Hoàn thành đầy đủ và vượt mức yêu cầu của Sprint 3 (đạt mức Advanced).
- Hệ thống MCP chạy ổn định, có lưu trữ dữ liệu thực tế (`tickets_db.json`).
- Hỗ trợ nhóm tối ưu hóa định dạng Trace để khớp hoàn toàn với Rubric chấm điểm.

**Điểm yếu**: 
- Phần xử lý ngoại lệ (Error handling) khi HTTP Server bị tắt đột ngột vẫn còn ở mức cơ bản (chỉ trả về thông báo lỗi thay vì có cơ chế retry tự động).

**Sự phụ thuộc của nhóm**: Nhóm phụ thuộc vào tôi để cung cấp dữ liệu "Grounding" (thông tin thực tế từ DB và Ticket) cho `synthesis_worker`. Nếu MCP không hoạt động, Agent sẽ rơi vào trạng thái ảo tưởng (hallucinate) hoặc không có dữ liệu để trả lời.

### 5. Nếu có thêm 2 giờ làm việc

Tôi sẽ tập trung vào:
- **Streaming Response**: Cải thiện MCP API để hỗ trợ stream kết quả tìm kiếm, giúp giảm thời gian chờ đợi cảm nhận (perceived latency) của người dùng.
- **Multi-hop Reasoning**: Cải thiện supervisor để có thể gọi MCP nhiều lần trong một lượt (ví dụ: vừa tìm thông tin SLA, vừa kiểm tra quyền truy cập của nhân viên đó) để trả lời các câu hỏi phức tạp hơn như **gq09**.
- **Dashboard Observability**: Xây dựng một giao diện web đơn giản để theo dõi các yêu cầu đang được xử lý bởi MCP Server theo thời gian thực.