# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration
**Họ và tên:** Nguyễn Thị Ngọc 
**Vai trò:** MCP Owner & Integration Specialist  
**Mã sinh viên:** 2A202600405

---

### 1. Phần tôi trực tiếp phụ trách (Module/Worker/Contract)

Trong dự án Lab Day 09, tôi chịu trách nhiệm chính về **Sprint 3 (MCP Server)** và việc tích hợp các khả năng mở rộng (external capabilities) vào hệ thống Multi-Agent. Các công việc cụ thể tôi đã thực hiện bao gồm:

- **Xây dựng MCP Server Advanced (+2 bonus)**: Triển khai HTTP Server sử dụng framework **FastAPI** (file `mcp_api.py`). Server đóng vai trò Registry trung tâm, expose các tools qua HTTP endpoint `http://localhost:8000/tools/call`.
- **3 MCP Tools đã implement trong `mcp_server.py`**:
    1. `search_kb` (dòng 138-175): Semantic Search kết nối ChromaDB, dùng model `all-MiniLM-L6-v2` với lazy loading qua `_get_kb_resources()`.
    2. `get_ticket_info` (dòng 200-223): Tra cứu ticket từ `MOCK_TICKETS` và file `tickets_db.json`.
    3. `create_ticket` (dòng 278-308): **Hành động thực** — tạo ticket và lưu vào `tickets_db.json` (khác mock thông thường).
- **Tích hợp Worker**: Sửa `policy_tool.py` (hàm `_call_mcp_tool` dòng 31-60) để gọi MCP qua HTTP POST thay vì import trực tiếp.
- **Temporal Scoping**: Thêm regex `\d{1,2}[/-]\d{1,2}[/-]\d{4}` vào `policy_tool.py` (dòng 110-125) để xử lý ngày tháng, phân biệt policy v3/v4.

### 2. Một quyết định kỹ thuật quan trọng

**Quyết định**: Chuyển đổi từ mô hình In-process Mock sang **FastAPI HTTP Server** cho MCP.

**Lý do chọn**: 
Việc import trực tiếp `chromadb` và `torch` vào mỗi Worker gây lỗi **DLL load failed** trên Windows và tiêu tốn RAM không cần thiết.

**Trade-off Analysis**:
- **Phương án 1 (Mock class)**: Dễ triển khai, không tốn tài nguyên. **Nhược**: Không phản ánh thực tế, khó mở rộng, không đạt bonus.
- **Phương án 2 (FastAPI HTTP Server)**: Tách biệt logic, tối ưu RAM (model load 1 lần), đạt +2 bonus. **Nhược**: Tốn công cấu hình API endpoint.

**Kết quả**: Nhóm chọn FastAPI vì tính module hóa cao và đạt điểm thưởng. Code evidence trong `mcp_api.py` dòng 20-30:
```python
@app.post("/tools/call")
async def call_tool(request: ToolCallRequest):
    result = dispatch_tool(request.tool_name, request.tool_input)
    return result
```

### 3. Một lỗi kỹ thuật đã sửa

**Mô tả lỗi**: Lỗi **DLL load failed** khi chạy `sentence_transformers` trên Windows.

**Nguyên nhân**: Import trực tiếp `chromadb` và `torch` vào Worker process gây conflict DLL khi gọi từ `graph.py`.

**Cách sửa**:
1. **Lazy Loading** (`mcp_server.py` dòng 138-145): Bọc model và collection vào `_get_kb_resources()` với biến toàn cục `_KB_MODEL` để load chỉ khi cần.
2. **Đường dẫn tuyệt đối**: Dùng `os.path.abspath` định vị `chroma_db` chính xác.
3. **Cô lập môi trường**: FastAPI chạy trong process riêng, tránh DLL conflict với `graph.py`.

**Bằng chứng trước/sau**:
- **Trước**: `python graph.py` → Crash: `ImportError: DLL load failed`
- **Sau**: MCP Server chạy độc lập, Worker gọi HTTP thành công, trace ghi `mcp_result` với độ trễ thấp.

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