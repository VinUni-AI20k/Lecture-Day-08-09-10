# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Quách Gia Được  
**Vai trò trong nhóm:** Worker Owner (policy_tool_worker) + phụ trách test policy/multi-hop  
**Ngày nộp:** 14/04/2026  
**Độ dài:** ~700 từ

---

## 1. Tôi phụ trách phần nào? (100-150 từ)

Trong Day 09, tôi phụ trách trực tiếp hai phần chính: triển khai policy worker trong file day09/lab/workers/policy_tool.py và cập nhật bộ câu hỏi kiểm thử trong day09/lab/data/test_questions.json. Ở policy worker, tôi làm ba việc: hoàn thiện logic phát hiện ngoại lệ hoàn tiền (Flash Sale, sản phẩm số, sản phẩm đã kích hoạt), xử lý temporal scoping giữa policy v3 và v4 theo mốc 01/02/2026, và hoàn thiện luồng gọi MCP kèm logging để trace rõ ràng hơn. Ở test questions, tôi cập nhật expected_route cho các câu đa bước để đồng nhất với routing hiện tại của supervisor. Phần việc của tôi phụ thuộc vào MCP/retrieval và routing graph để đầu vào nhất quán.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150-200 từ)

**Quyết định:** Tôi chọn mô hình gọi MCP theo intent, kèm một điểm ghi nhận chung cho trace (_record_mcp_call), thay vì gọi trực tiếp từng tool ở nhiều vị trí rời rạc.

Lý do chính là nếu gọi tool theo kiểu “thấy từ khóa là gọi hết” thì số lần gọi tăng nhanh, trace bị nhiễu và khó debug. Nếu viết rời từng đoạn gọi tool thì cấu trúc mcp_tools_used và history dễ lệch format. Tôi chọn giải pháp trung gian: supervisor giữ routing đơn giản, policy worker gọi đúng tool theo ngữ cảnh, và mọi lần gọi đều qua một điểm ghi log chung.

Trade-off tôi chấp nhận là cách làm theo keyword/intent có thể chưa phủ hết mọi biến thể ngôn ngữ hiếm. Đổi lại, hệ thống dễ test, dễ quan sát, và khi lỗi thì xác định nhanh lỗi nằm ở tool nào.

---

## 3. Tôi đã sửa một lỗi gì? (150-200 từ)

**Lỗi:** Khi chạy policy_tool ở chế độ standalone từ thư mục gốc workspace, các lệnh gọi MCP bị lỗi import module.

**Biểu hiện:** Pipeline không dừng hẳn nhưng các tool trong trace đều báo lỗi, làm phần trace MCP không đạt yêu cầu vì không có dữ liệu tool thực tế.

**Nguyên nhân gốc:** Đường dẫn import mcp_server phụ thuộc vào thư mục chạy lệnh. Chạy từ day09/lab thì được, chạy từ root repo thì Python path không chứa day09/lab.

**Cách sửa:** Tôi thêm fallback xử lý đường dẫn trong hàm gọi MCP: nếu import thất bại thì tự thêm day09/lab vào sys.path rồi import lại dispatch_tool. Đồng thời chuẩn hóa bắt lỗi tool-level để trace vẫn giữ format thống nhất.

**Kết quả sau sửa:** Case needs_tool cho tình huống access + ticket đã gọi đủ get_ticket_info, check_access_permission, create_ticket và không còn lỗi import.

---

## 4. Tôi tự đánh giá đóng góp của mình (100-150 từ)

Điểm tôi làm tốt là chia nhỏ công việc theo từng lớp: refactor helper trước, harden ngoại lệ sau, rồi mới chốt temporal scoping và MCP flow. Cách làm này giúp thay đổi dễ review, dễ test lại và giảm rủi ro khi tích hợp.

Điểm tôi chưa tốt là còn phụ thuộc vào tiến độ tích hợp của các bạn khác. Có thời điểm tôi phải chờ routing hoặc MCP ổn định rồi mới chốt tiếp. Nhóm phụ thuộc vào tôi ở độ đúng của policy worker và expected route cho các câu policy/multi-hop; nếu lệch thì trace và kết quả chấm sẽ sai.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm 2 giờ, tôi sẽ bổ sung bộ test policy theo hướng table-driven và thêm tiêu chí confidence cho các tình huống temporal/multi-hop. Lý do là các câu khó như q12, q13, q15 đã đúng route nhưng vẫn có thể sai khi người dùng đổi cách diễn đạt. Mục tiêu của tôi là tăng độ ổn định bằng nhiều biến thể câu hỏi và đo tỉ lệ sai theo từng nhóm điều kiện.
