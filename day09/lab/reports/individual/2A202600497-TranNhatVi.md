# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Nhật Vĩ
**Vai trò trong nhóm:** Worker Owner (Retrieval + Policy + Synthesis)  
**Ngày nộp:** 2026-04-14  
**Độ dài:** ~650 từ

---

## 1. Tôi phụ trách phần nào?

Trong Day 09, tôi phụ trách chính cụm worker và tích hợp thực thi thật vào pipeline. Cụ thể, tôi chịu trách nhiệm các file `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py` và tham gia chỉnh `graph.py` để bỏ placeholder, gọi trực tiếp `run()` của worker. Ở `retrieval.py`, tôi triển khai luồng lấy embedding, query ChromaDB, trả `retrieved_chunks` và `retrieved_sources`, đồng thời ghi `worker_io_logs` để trace được input/output theo contract. Ở `policy_tool.py`, tôi duy trì rule-based exception cho hoàn tiền (Flash Sale, digital product, activated product) và bổ sung nhánh gọi MCP tool cho access control (`check_access_permission`) ngoài `search_kb`/`get_ticket_info`. Ở `synthesis.py`, tôi triển khai synthesis có grounding, confidence scoring và fallback deterministic để không hallucinate khi không gọi được model.

Công việc của tôi kết nối trực tiếp với Supervisor Owner: supervisor quyết định route và worker của tôi là nơi xử lý domain logic thật. Nếu worker không ổn, trace vẫn có route nhưng answer không usable. Bằng chứng chính là các trace mới trong `artifacts/traces/` có `workers_called`, `worker_io_logs`, `mcp_tools_used` và log lỗi/đầu ra chi tiết theo từng worker.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

Quyết định quan trọng nhất của tôi là chuyển từ route đơn sang route multi-hop có điều kiện cho các câu hỏi giao thoa domain (SLA + access/policy). Trước khi chỉnh, nhiều câu đi vào một nhánh duy nhất nên answer thiếu một nửa yêu cầu của đề. Sau khi chỉnh, với task chứa cả tín hiệu retrieval và policy, graph chạy retrieval trước rồi mới policy để synthesis có đủ evidence từ cả hai phía.

Tôi cân nhắc hai hướng:

1. Giữ route đơn theo keyword mạnh nhất (đơn giản, nhanh).
2. Thêm nhánh multi-hop có điều kiện (phức tạp hơn nhưng bao phủ tốt câu đa domain).

Tôi chọn hướng 2 vì rubric Day09 có nhóm câu multi-hop nặng điểm và yêu cầu câu trả lời tổng hợp đủ hai quy trình. Khi đi theo multi-hop, trace thể hiện rõ chain `retrieval_worker -> policy_tool_worker -> synthesis_worker`, nhờ đó vừa tăng độ đầy đủ nội dung vừa dễ audit.

Trade-off đã chấp nhận là latency tăng nhẹ ở câu phức tạp do gọi nhiều worker hơn, nhưng đổi lại giảm rủi ro partial/zero ở các câu yêu cầu cross-doc.

Bằng chứng:
- `artifacts/grading_run.jsonl`: ở các câu multi-hop, `workers_called` có đủ retrieval + policy + synthesis và answer nêu đủ 2 domain.
- `artifacts/day09_scoring.json`: nhóm câu multi-hop đạt mức full theo rubric; tổng raw đạt `92/96`.

---

## 3. Tôi đã sửa một lỗi gì?

Lỗi điển hình tôi xử lý trong phiên này là câu trả lời dạng “tóm tắt chunk” quá chung, chưa bám intent nghiệp vụ của từng nhóm câu hỏi. Hệ quả là cùng có evidence nhưng câu trả lời thiếu quyết định cuối cùng (kết luận có/không), hoặc thiếu cấu trúc cần thiết cho các tình huống exception và cross-domain.

Root cause:
- `synthesis.py` ban đầu ưu tiên câu trả lời generic, chưa có lớp xử lý theo intent (abstain, exception, multi-hop, access approval).
- Với các câu cần kết luận dứt khoát, output dài và lan man làm người đọc khó verify nhanh.

Cách sửa tôi thực hiện:
- Bổ sung lớp rule-based tổng quát trong `synthesis.py` theo intent nghiệp vụ, không phụ thuộc vào ID câu hỏi cụ thể.
- Giữ nguyên nguyên tắc grounded + citation nhưng chuẩn hóa format câu trả lời theo hướng ngắn, rõ, có kết luận.
- Chạy lại `eval_trace.py --grading` và đối chiếu kết quả trong `day09_scoring.json`.

Before/after:
- Before: nhiều câu bị partial/zero ở rubric dù có source.
- After: các câu thuộc nhóm SLA, policy exception, access control và multi-hop ổn định hơn; tổng raw đạt `92/96`.

Tôi xem đây là bug fix quan trọng vì chuyển hệ thống từ “có evidence nhưng trả lời chưa đúng cách chấm” sang “đúng cả nội dung lẫn format rubric”.

---

## 4. Tôi tự đánh giá đóng góp của mình

Điểm tôi làm tốt nhất là biến phần worker thành các module có contract rõ, test độc lập được và trace hóa tốt. Tôi cũng phản ứng nhanh khi có lỗi môi trường (API key, encoding console, retrieval backend), ưu tiên giữ pipeline chạy để nhóm không mất dòng dữ liệu cho report.

Điểm tôi chưa tốt là chưa có test tự động kiểm tra provider/dimension ngay từ đầu sprint, nên mất thời gian debug ở cuối. Ngoài ra, tôi chưa tối ưu triệt để route multi-hop để luôn gọi đủ nhánh worker khi câu hỏi đa domain.

Nhóm phụ thuộc vào tôi ở phần worker output và tính nhất quán `worker_io_logs`; nếu phần này lỗi thì route có đúng cũng không ra answer usable. Ngược lại, tôi phụ thuộc vào phần supervisor rule và bộ test/trace để đánh giá nhanh các chỉnh sửa worker có cải thiện thực sự hay không.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Nếu có thêm 2 giờ tôi sẽ bổ sung bộ regression test theo nhóm intent (SLA, exception policy, access control, FAQ) để đảm bảo mỗi lần chỉnh worker/synthesis không làm giảm độ đúng nghiệp vụ. Đồng thời tôi sẽ tách riêng lớp “answer policy” thành module nhỏ có test unit để tránh việc logic trả lời bị phân tán và khó bảo trì.

