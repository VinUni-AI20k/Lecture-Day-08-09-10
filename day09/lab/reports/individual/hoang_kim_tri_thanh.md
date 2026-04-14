# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Hoàng Kim Trí Thành  
**Vai trò trong nhóm:** Synthesis + Eval Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài:** ~700 từ

---

## 1. Tôi phụ trách phần nào?

Trong Day 09, tôi phụ trách chính hai file: `day09/lab/workers/synthesis.py` và `day09/lab/eval_trace.py`.

Ở `synthesis.py`, công việc của tôi là lớp tổng hợp cuối: biến context từ retrieval/policy thành câu trả lời có thể chấm được, có nguồn và có confidence. Tôi tập trung vào ba điểm: (1) grounded answer (chỉ dùng context trong state), (2) tránh hallucination bằng abstain khi thiếu bằng chứng, (3) trả về output ổn định để trace được.

Ở `eval_trace.py`, tôi hoàn thiện flow chạy test và grading: chạy batch câu hỏi, lưu trace, phân tích metrics (`routing_distribution`, `avg_confidence`, `avg_latency_ms`, `mcp_usage_rate`) và xuất report so sánh Day 08 vs Day 09.

Công việc của tôi kết nối trực tiếp với phần của retrieval/policy owners: nếu retrieval trả context sai hoặc thiếu thì synthesis sẽ rớt chất lượng. Vì vậy tôi phải đọc trace thường xuyên và phản hồi ngược để điều chỉnh route/retrieval.

**Bằng chứng:** artifact trong `day09/lab/artifacts/` và các lệnh chạy `python day09/lab/eval_trace.py`, `--analyze`, `--compare`, `--grading`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** siết grounded prompt + abstain cứng trong synthesis, thay vì cố trả lời “đủ ý” khi context yếu.

Ban đầu, pipeline có xu hướng để model tổng hợp khá tự do. Điều này làm tăng rủi ro thêm thông tin ngoài tài liệu, đặc biệt với câu policy/SLA có nhiều con số. Tôi chọn chiến lược thận trọng hơn: nếu context không đủ thì trả lời rõ là không đủ thông tin, thay vì đoán.

Lý do tôi chọn cách này là vì rubric Day 09 phạt hallucination rất nặng (penalty), trong khi câu trả lời abstain đúng vẫn được chấm điểm cao ở câu kiểu gq07. Tôi cũng giữ `confidence` phụ thuộc vào chất lượng chunk và độ đầy đủ context, không hard-code cao để “đẹp số”.

**Trade-off:** câu trả lời có thể ngắn hơn và bớt “mượt”, nhưng tăng độ an toàn chấm điểm và giúp trace trung thực hơn với dữ liệu thực có.

**Bằng chứng từ trace:** record gq07 trong `artifacts/grading_run.jsonl` abstain đúng và vẫn giữ đủ `supervisor_route`, `route_reason`, `workers_called`.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** `eval_trace.py` từng fail khi phân tích trace trên Windows do encoding mismatch.

**Symptom:** pipeline chạy xong câu hỏi nhưng `python day09/lab/eval_trace.py --analyze` báo `UnicodeDecodeError`, khiến nhóm không lấy được metrics để điền docs và so sánh Day 08/Day 09.

**Root cause:** file trace được ghi UTF-8 nhưng đoạn đọc trace dùng encoding mặc định hệ điều hành (cp1252), nên đụng ký tự Unicode là lỗi.

**Cách sửa:** chuẩn hóa phần đọc trace sang `encoding=\"utf-8\"` và rà lại flow output report để tránh crash giữa chừng.

Sau fix, các lệnh `--analyze` và `--compare` chạy ổn định, tạo được `artifacts/eval_report.json` với đủ các trường metrics.

**Bằng chứng trước/sau:** trước fix có lỗi decode trong terminal; sau fix report xuất đầy đủ `total_traces`, `routing_distribution`, `avg_confidence`, `avg_latency_ms`, `mcp_usage_rate`.

---

## 4. Tôi tự đánh giá đóng góp của mình

Điểm tôi làm tốt nhất là giữ được “khả năng chấm được” cho pipeline: không chỉ trả lời đúng mà còn có trace, metrics và report nhất quán để cả nhóm debug và viết tài liệu.

Điểm tôi chưa tốt là chưa khóa triệt để các câu policy/multi-hop nhạy cảm (đặc biệt gq09) để đạt Full ổn định ở mọi lần chạy; vẫn còn phụ thuộc vào chất lượng retrieval và cách synthesis gom ý trong từng run.

Nhóm phụ thuộc vào tôi ở phần eval/synthesis cuối: nếu output hoặc trace không ổn, phần docs/report bị block ngay. Tôi phụ thuộc vào retrieval/policy owners để đảm bảo context đầu vào cho synthesis đủ đúng và đủ rộng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ tối ưu riêng case gq09 bằng cách thêm post-check deterministic trong synthesis cho câu multi-hop P1 + Level 2 access: bắt buộc xác nhận đủ bộ kênh thông báo SLA (Slack, email, PagerDuty) và điều kiện emergency Level 2 (cần Line Manager + IT Admin on-call, không cần IT Security). Tôi chọn việc này vì trace hiện tại cho thấy gq09 là câu còn rủi ro partial dù đa số câu khác đã ổn định.
