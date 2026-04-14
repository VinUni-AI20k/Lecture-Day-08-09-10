# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Vũ Minh Quân
**Vai trò trong nhóm:** Trace & Docs Owner
**Ngày nộp:** 14/04/2026
**Độ dài:** 500-800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án Lab Day 09, tôi đảm nhận vai trò **Trace & Docs Owner**, chịu trách nhiệm chính về việc đo lường hiệu năng và hệ thống hóa tài liệu kỹ thuật. Công việc cụ thể của tôi tập trung vào việc hiện thực hóa file [eval_trace.py] để tự động hóa quá trình chạy 15 câu hỏi test và các câu hỏi chấm điểm (grading questions).

Tôi đã thiết kế các hàm cốt lõi như `run_grading_questions` để thực thi pipeline và lưu trữ dưới dạng JSONL, cùng với hàm `analyze_traces` để tính toán các chỉ số KPI quan trọng như: tỷ lệ phân bổ định tuyến (routing distribution), thời gian phản hồi trung bình (average latency), và độ tin cậy của câu trả lời (confidence score). Ngoài ra, tôi phối hợp với Supervisor Owner để triển khai cơ chế `save_trace` trong [graph.py] giúp ghi lại toàn bộ lịch sử suy luận của Agent.

Công việc của tôi đóng vai trò là "trọng tài" và "người quan sát", cung cấp phản hồi định lượng cho các thành viên khác (Worker Owners) biết được những thay đổi trong prompt hoặc logic của họ có thực sự cải thiện hệ thống hay không.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Thiết kế cơ chế **Comparison Benchmark tự động** giữa Day 08 và Day 09 ngay trong code thay vì so sánh thủ công.

**Lý do:** Khi làm việc với kiến trúc Multi-Agent, độ phức tạp của hệ thống tăng vọt. Nếu chỉ nhìn vào từng file trace riêng lẻ, nhóm sẽ không biết được liệu việc chuyển sang Supervisor-Worker có thực sự xứng đáng với cái giá phải trả là độ trễ (latency) tăng cao hay không. Tôi đã quyết định viết hàm `compare_single_vs_multi` trong `eval_trace.py`. Hàm này không chỉ đọc dữ liệu hiện tại mà còn nạp baseline từ kết quả Lab 08 để tạo ra một file báo cáo so sánh [eval_report.json].

Các lựa chọn thay thế là so sánh bằng bảng Excel thủ công, nhưng cách đó rất dễ sai sót và không cập nhật kịp thời khi nhóm thay đổi Worker logic ở những phút cuối. Bằng việc chọn cách code hóa benchmark, tôi đã giúp nhóm nhìn thấy ngay sự chênh lệch: Multi-hop Accuracy tăng từ 40% lên 80%, dù đánh đổi bằng việc latency tăng từ 2s lên 21s.

**Bằng chứng từ trace/code:**
Trong `eval_trace.py` (line 238-279), tôi đã cấu trúc dictionary comparison với các trường `accuracy_delta` và `mcp_benefit` để phục vụ trực tiếp cho báo cáo nhóm.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Hệ thống gặp lỗi hiển thị và lưu trữ **Unicode Encoding** trên môi trường Windows.

**Symptom:** Khi chạy pipeline với các câu hỏi tiếng Việt có dấu (như "hoàn tiền", "khẩn cấp"), file trace JSON được tạo ra chứa các ký tự lỗi (với định dạng `\uXXXX`) hoặc file report bị lỗi font khi mở bằng các trình soạn thảo text thông thường. Điều này khiến việc review trace để tìm nguyên nhân sai định tuyến trở nên cực kỳ khó khăn.

**Root cause:** Mặc định hàm `open()` trong Python trên Windows sử dụng encoding CP1252 (ANSI), trong khi dữ liệu từ LLM và file JSON yêu cầu chuẩn UTF-8. Đồng thời, `json.dump` theo mặc định sẽ escape các ký tự non-ASCII.

**Cách sửa:** Tôi đã rà soát toàn bộ các điểm ghi file trong hệ thống. Tại `graph.py` (line 276) và `eval_trace.py` (line 112, 152, 290), tôi đã ép kiểu encoding bằng cách thêm tham số `encoding="utf-8"` vào hàm `open()` và thiết lập `ensure_ascii=False` trong hàm `json.dump()`.

**Bằng chứng trước/sau:**
- **Trước:** `"task": "SLA x\u1eed l\u00fd ticket P1 là bao l\u00e2u?"`
- **Sau:** `"task": "SLA xử lý ticket P1 là bao lâu?"` (Dữ liệu hiển thị rõ ràng trong [grading_run.jsonl]).

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã hoàn thành tốt việc xây dựng bộ khung đánh giá tự động. Thay vì đợi đến cuối ngày mới viết báo cáo, tôi đã chuẩn bị sẵn các script tính toán metrics ngay từ Sprint 1, giúp nhóm có dữ liệu liên tục để tối ưu hóa.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi chưa dành đủ thời gian để tối ưu hóa logic `analyze_traces`. Hiện tại nó chỉ mới đếm được số lượng route, chưa phân tích sâu được sự tương quan giữa các top sources và mức độ chính xác của câu trả lời.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm phụ thuộc vào tôi để có file `grading_run.jsonl` chuẩn xác để nộp bài. Nếu script của tôi bị bug, toàn bộ kết quả làm việc của 4 thành viên khác sẽ không có bằng chứng để chấm điểm.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc hoàn toàn vào cấu trúc `AgentState` mà Supervisor Owner và Worker Owners thống nhất. Nếu họ thay đổi tên field (ví dụ đổi `retrieved_sources` thành `sources`) mà không báo trước, các hàm evaluation của tôi sẽ trả về giá trị None/Error.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm thời gian, tôi sẽ xây dựng một **Trace Visualization Dashboard** đơn giản bằng Streamlit. Dựa trên kết quả từ `eval_report.json`, việc nhìn vào những con số thô như "Latency 21s" rất khó để nhận diện điểm nghẽn. Một dashboard trực quan hóa dòng thời gian (Gantt chart) cho từng node trong graph sẽ giúp nhóm xác định chính xác bộ phận nào (thường là bước embedding local) đang gây chậm hệ thống để có phương án optimize tốt hơn.

---

