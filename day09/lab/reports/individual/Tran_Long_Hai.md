# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Long Hải
**Vai trò trong nhóm:** Trace & Docs Owner (Sprint 4)
**Ngày nộp:** 14/04/2026
**Độ dài:** ~800 từ

---

## 1. Tôi phụ trách phần nào? (200–250 từ)

Trong dự án Day 09 về tối ưu hóa hệ trợ lý thông minh CS + IT Helpdesk, tôi đảm nhận vai trò **Trace & Docs Owner**, phụ trách toàn bộ Sprint 4 — giai đoạn đánh giá và tài liệu hóa hệ thống. Đây là một vị trí mang tính chiến lược vì kết quả của tôi chính là bằng chứng xác thực nhất cho hiệu quả của việc chuyển đổi từ mô hình Single-Agent sang Multi-Agent.

**Phạm vi công việc cụ thể của tôi bao gồm:**
- **Phát triển và tối ưu hóa bộ công cụ đánh giá (`eval_trace.py`)**: Tôi không chỉ cài đặt các hàm mặc định mà còn mở rộng chúng để có thể xử lý các tập dữ liệu lớn, trích xuất metrics tự động từ hàng chục tệp JSON trace. Tôi đã xây dựng các logic tính toán độ tin cậy, độ trễ và tỷ lệ phân bổ routing để cung cấp cái nhìn định lượng chính xác nhất cho nhóm.
- **Xây dựng hệ thống tài liệu so sánh**: Tôi chịu trách nhiệm chính cho file `single_vs_multi_comparison.md`, nơi tôi phải thu thập dữ liệu thô (raw data) từ Day 08 lab và đối chiếu với dữ liệu mới. Tôi cũng hoàn thiện `system_architecture.md` để mô tả lại kiến trúc mà nhóm đã thống nhất.
- **Xử lý tính tương thích hệ thống**: Do nhóm làm việc trên nhiều hệ điều hành khác nhau, tôi đã chủ động can thiệp vào các module I/O để đảm bảo script đánh giá hoạt động trơn tru trên cả Windows, Linux và macOS, đặc biệt là xử lý các vấn đề về bảng mã tiếng Việt.

Công việc của tôi kết nối trực tiếp với kết quả của Supervisor Owner và Worker Owners. Tôi lấy đầu ra là các tệp `traces` của họ để biến chúng thành những thông tin có ý nghĩa quản trị và đánh giá.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (200–250 từ)

**Quyết định: Thiết lập cơ chế "Global UTF-8 Encoding Enforcement" và Tái cấu trúc logic tính toán trung bình có kiểm soát (Null-safe Analysis).**

**Quyết định là gì?**
Tôi đã quyết định cấu hình lại toàn bộ luồng xuất chuẩn (`sys.stdout`) của Python sang UTF-8 và áp dụng tham số `encoding="utf-8"` cho tất cả các thao tác đọc ghi file JSON. Đồng thời, tôi thay đổi cách tính toán metrics từ dạng mảng thuần túy sang dạng kiểm tra điều kiện an toàn (`if-exists` checks).

**Tại sao tôi chọn cách này?**
Lý do xuất phát từ một vấn đề thực tế: Terminal của Windows (CMD/PowerShell) thường gặp lỗi crash khi gặp các ký tự đặc biệt hoặc biểu tượng trạng thái (emoji) thường dùng trong báo cáo. Việc ép bảng mã giúp hệ thống hoạt động ổn định mọi lúc mọi nơi. Hơn nữa, trong quá trình phát triển, sẽ có những lúc pipeline bị lỗi ở giữa chừng, dẫn đến các mảng dữ liệu trống. Bản gốc của script sẽ bị lỗi `ZeroDivisionError` làm dừng toàn bộ quá trình evaluation. Quyết định "Null-safe" của tôi đảm bảo script vẫn chạy hết 100% câu hỏi và chỉ ra chính xác câu nào bị lỗi thay vì crash toàn bộ script.

**Bằng chứng hiệu quả:**
Nhờ quyết định này, nhóm đã có thể chạy evaluation liên tục 15 câu hỏi và xuất báo cáo đẹp mắt với các icon 📊, ✅ ngay trên terminal Windows mà không gặp bất kỳ lỗi gián đoạn nào. Điều này giúp cả nhóm tiết kiệm ít nhất 30 phút mỗi lần cần chạy lại test để kiểm tra logic routing.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi: `UnicodeDecodeError` khi parse kết quả từ đồng đội và lỗi sai lệch metrics khi so sánh với Day 08.**

**Symptom:**
Khi tôi bắt đầu chạy `eval_trace.py --analyze`, script báo lỗi không thể đọc được các ký tự tại byte `0x81`. Điều này xảy ra ngay khi script cố gắng load nội dung có tiếng Việt từ các file trace JSON. Ngoài ra, chỉ số latency ban đầu hiển thị bằng 0 một cách vô lý do logic làm tròn chưa chính xác.

**Root cause:**
Nguyên nhân nằm ở việc mở file không chỉ định encoding trên môi trường Windows (mặc định Windows dùng `cp1252`). Đồng thời, tham số đo thời gian (`time.time()`) trả về đơn vị giây, khi nhân 1000 để ra miligiây và ép kiểu integer đã làm mất đi độ chính xác ở các worker xử lý quá nhanh.

**Cách sửa:**
- Tôi đã cập nhật lệnh mở file: `with open(path, encoding="utf-8") as f:`.
- Tôi đã thiết lập script đo lường "Grading Run" chính thức, kích hoạt toàn bộ luồng gọi LLM và Vector DB.

**Bằng chứng trước/sau:**
Trước khi sửa, script crash ngay câu hỏi đầu tiên. Sau khi sửa, script chạy mượt mà qua toàn bộ 15 câu hỏi, tính toán được `avg_confidence: 0.75` và xuất ra file `eval_report.json` hoàn chỉnh cho nhóm.

---

## 4. Tôi tự đánh giá đóng góp của mình (150–200 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi tin rằng đóng góp lớn nhất của mình là khả năng tạo ra sự **minh bạch (Observability)** cho dự án. Việc tôi tỉ mỉ trong việc thiết kế định dạng trace giúp cả nhóm có thể nhìn thấy lỗi ở đâu ngay lập tức. Tôi cũng hoàn thành phần tài liệu vượt mức mong đợi, biến các con số thô thành các phân tích có giá trị so sánh cao.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi nhận thấy mình hơi "cầu toàn" trong việc chỉnh sửa script đánh giá, đôi khi dành quá nhiều thời gian để format terminal thay vì tập trung sâu hơn vào việc đề xuất các logic routing tối ưu cho Supervisor Owner.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nếu không có phần Sprint 4 của tôi, nhóm sẽ không thể chứng minh được là Day 09 tốt hơn Day 08 như thế nào. Tôi là người cung cấp "số liệu thực tế" — thứ quan trọng nhất để giảng viên chấm điểm cho toàn bộ nhóm. Nếu tôi chưa xong, báo cáo của mọi thành viên khác đều sẽ thiếu đi phần bằng chứng trace.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm thời gian, tôi sẽ xây dựng **Automated Regression Testing**. Tôi sẽ viết script để mỗi khi Supervisor Owner thay đổi một dòng code routing, hệ thống sẽ tự động chạy lại 15 câu hỏi test và đưa ra cảnh báo nếu độ chính xác giảm xuống hoặc latency tăng đột ngột. Điều này sẽ giúp nhóm hoàn toàn yên tâm khi thực hiện các thay đổi (Refactoring) ở phút chót.

---

*Lưu file cá nhân: reports/individual/Tran_Long_Hai.md*
