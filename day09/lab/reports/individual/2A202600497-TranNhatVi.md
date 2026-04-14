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

Quyết định quan trọng nhất của tôi là đồng bộ embedding strategy giữa bước index và bước query retrieval, đồng thời vẫn giữ fallback an toàn trong synthesis/retrieval để pipeline không fail cứng. Trước khi chỉnh, hệ thống chạy được nhưng retrieval thường rỗng do mismatch provider/dimension. Sau khi chỉnh, retrieval ưu tiên Vertex `text-multilingual-embedding-002` giống `build_index.py`, kết quả trace cải thiện rõ về confidence và source coverage.

Tôi cân nhắc hai hướng:

1. Giữ logic cũ, chỉ fallback khi lỗi.
2. Đồng bộ provider/model embedding với index (Vertex) + giữ fallback để không crash.

Tôi chọn hướng 2 vì đây là cách duy nhất để vừa tăng chất lượng retrieval thật, vừa đảm bảo tính ổn định khi chấm trace. Sau khi sửa, `eval_trace.py` chạy 15/15 câu với `avg_confidence=0.739`, `avg_latency_ms=3494`, và top sources không còn rỗng.

Trade-off đã chấp nhận là phụ thuộc nhiều hơn vào môi trường Vertex (SDK + credentials). Tuy nhiên đổi lại là độ chính xác retrieval tăng mạnh và giảm nhu cầu fallback.

Bằng chứng:
- `artifacts/traces/run_20260414_165615.json`: route retrieval trả 3 chunks từ `support/sla-p1-2026.pdf`, confidence 0.76.
- `artifacts/traces/run_20260414_165651.json`: policy route + MCP `search_kb`, trả lời đúng store credit 110%, confidence 0.75.

---

## 3. Tôi đã sửa một lỗi gì?

Lỗi điển hình tôi xử lý trong phiên này là retrieval không dùng được Vertex trong runtime worker, dẫn tới fallback 384 chiều và mismatch với index 768 chiều. Symptom là nhiều trace có `retrieved_chunks=[]`, answer abstain và confidence thấp.

Root cause:
- `scripts/build_index.py` index bằng Vertex `text-multilingual-embedding-002` (768 chiều).
- `workers/retrieval.py` ban đầu không khởi tạo được Vertex (`No module named 'vertexai'`) nên rơi xuống fallback 384 chiều.
- Query embedding và collection embedding không cùng dimension nên Chroma trả lỗi.

Cách sửa tôi thực hiện:
- Cài `google-cloud-aiplatform` để runtime worker dùng được `vertexai`.
- Đồng bộ retrieval đọc `.env` + credentials path và ưu tiên Vertex provider.
- Bổ sung log provider thực tế trong retrieval để xác nhận đang dùng model nào.
- Dọn artifacts cũ, chạy lại full batch để lấy trace sạch.

Before/after:
- Before: nhiều câu retrieval rỗng, confidence ~0.1, source coverage thấp.
- After: `eval_trace.py` chạy 15/15, `avg_confidence=0.739`, `mcp_usage_rate=5/15`, top sources hiển thị đầy đủ.

Tôi xem đây là bug fix quan trọng vì nó biến pipeline từ trạng thái "chạy nhưng trả lời yếu" sang trạng thái có retrieval thật và evidence rõ để chấm điểm.

---

## 4. Tôi tự đánh giá đóng góp của mình

Điểm tôi làm tốt nhất là biến phần worker thành các module có contract rõ, test độc lập được và trace hóa tốt. Tôi cũng phản ứng nhanh khi có lỗi môi trường (API key, encoding console, retrieval backend), ưu tiên giữ pipeline chạy để nhóm không mất dòng dữ liệu cho report.

Điểm tôi chưa tốt là chưa có test tự động kiểm tra provider/dimension ngay từ đầu sprint, nên mất thời gian debug ở cuối. Ngoài ra, tôi chưa tối ưu triệt để route multi-hop để luôn gọi đủ nhánh worker khi câu hỏi đa domain.

Nhóm phụ thuộc vào tôi ở phần worker output và tính nhất quán `worker_io_logs`; nếu phần này lỗi thì route có đúng cũng không ra answer usable. Ngược lại, tôi phụ thuộc vào phần supervisor rule và bộ test/trace để đánh giá nhanh các chỉnh sửa worker có cải thiện thực sự hay không.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Nếu có thêm 2 giờ, tôi sẽ chạy `eval_trace.py --grading` trên bộ `grading_questions.json` để lấy raw score/96 thật, sau đó tinh chỉnh routing cho case multi-hop khó (đặc biệt dạng P1 + access + emergency) dựa trên trace của từng câu gq.

