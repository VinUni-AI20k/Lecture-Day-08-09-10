# Báo Cáo Cá Nhân — Lab Day 09

**Họ và tên:** Nguyễn Việt Quang
**Vai trò:** Toàn bộ công đoạn Code Pipeline & Trace Docs Owner
**Ngày nộp:** 14/04/2026

---

## 1. Phần tôi phụ trách

Trong phiên bản Day 09 này, tôi phụ trách xuyên suốt các quy trình bao gồm việc nâng cấp luồng **Supervisor**, triển khai hệ thống ngoại lệ của **Policy Tool Worker** và hoàn thiện khâu Tracing **Sprint 4**. Cụ thể tôi đã:
- **Supervisor & Routing:** Code cấu trúc Router trong `graph.py` xử lý các Flag bẫy kiểm duyệt như cờ `risk_high` nếu người dùng nhắc đến mã "err-" và tự động ngắt kết nối chuyển sang máy thủ công `human_review_node`.
- **Worker Contracts:** Cấu hình Rule-based cứng trong `analyze_policy()` ở `policy_tool.py`. Worker này được cài đặt rẽ nhánh để bắt các Edge Cases như: Đơn hàng Flash Sale, Đơn mua thẻ License Key Kỹ thuật số, hoặc Đơn đã được mở Activiated. 
- **Tracing:** Export thành công biểu đồ metric ra `eval_report.json` với tỷ lệ routing chính xác cho 15 câu test nội bộ và 10 câu chấm thi Grading.

---

## 2. Quyết định kỹ thuật thiết yếu

**Quyết định:** Chặn (Hard-code) logic Exception Rule trong Policy Worker thay cho prompt bằng LLM.

**Lý do chọn:** Đối với quy trình Đổi & Trả cực kỳ nhạy cảm liên quan đến dòng tiền Doanh nghiệp. Nếu để 1 mình Model tự do đọc Chunk Vector rồi suy luận ngoại lệ, tôi nhận thấy LLM đôi lúc "quên" (Ignored) các điều kiện như "Flash Sale không nhận Hoàn hàng". Việc tôi gán chặt mảng Check Exception bằng Python (kiểm tra có chữ "flash sale" trong Document -> Tự động bắn thông báo lỗi cứng) nhằm cấm triệt để Model phạm quyền. Việc này khiến tính Grounding trở nên hoàn hảo tại `q10` (Flash sale - Yêu cầu hoàn tiền). Sự đánh đổi ở đây là Code Python có Hard Code nên sẽ khó cập nhật tự động khi Policy file rẽ sang một tệp mới không có Keyword cũ.

---

## 3. Lỗi đã mắc phải và cách khắc phục

**Lỗi mắc phải:** `UnicodeDecodeError` khi Script tính Metrics `eval_trace.py` cố xuất các dòng thống kê (có in chứa Icon như ⚠️ hoặc 🎯) lên môi trường Terminal PowerShell của Windows. Lỗi này làm treo toàn bộ luồng tạo JSON.

**Khắc phục & Bằng chứng:**
Tôi trực tiếp can thiệp và ép việc đọc/mở tệp lên thư viện chuẩn của Python luôn dùng cơ chế mã hóa `encoding="utf-8"`.
`with open(questions_file, encoding="utf-8") as f:`
Đồng thời phải tạo ra Script chạy đi qua biến môi trường để Bypass lỗi hệ thống:
`$env:PYTHONIOENCODING="utf-8"; python eval_trace.py`
Ngay lập tức, Log chạy 10 câu Grading xuất xưởng mềm mượt ra `artifacts/grading_run.jsonl`.

---

## 4. Đánh giá sự nghiệp cá nhân

- **Mặt làm tốt:** Xây dựng thành công bộ máy Tracing mạnh mẽ không bị Crack (Không câu nào báo Error Out of Logic). Rõ ràng và tường minh ở `mcp_tools_used` cho Routing. 
- **Mặt chưa tốt:** Cấu trúc Router `Supervisor` làm quá thô, còn dùng if-string. Node `Retrieval` chưa cài đặt phương án tái nạp Sparse/BM25 hay Reranker.
- Sự phụ thuộc: Toàn bộ Artifacts sinh lời và số liệu Group Report phụ thuộc vào Output của quá trình chạy Evaluate trong Sprint này.

---

## 5. Cải tiến nếu có thêm thời gian

Từ thực tế của file Trace JSON (`artifacts/traces/run...q01.json`), nhiều câu hỏi bị đẩy thẳng vào luồng `default route` vì các Rule-based không đủ phủ rào hết Ngữ nghia Tiếng Việt của người dùng. Nếu có thêm 2h, tôi sẽ cắm cổng gọi API `client.chat.completions.create()` bằng OpenAI gpt-4o-mini tích hợp JSON Schema (Structured Output) ngay tại vị trí Supervisor Node để LLM làm Routing Classification Classifier phân loại Intent tự nhiên (Natural Intent), nhắm tới đập tan điểm mù của Regex truyền thống.
