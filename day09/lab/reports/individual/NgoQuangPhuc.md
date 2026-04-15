# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Ngô Quang Phúc  
**Vai trò trong nhóm:** Group Lead (QA/Integration/Documentation Owner)  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `eval_trace.py` (Sprint 4 — Trace Evaluation & Comparison)
- Functions tôi implement: `run_test_questions()`, `run_grading_questions()`, `analyze_traces()`, `compare_single_vs_multi()`, `save_trace()`
- Tài liệu: `reports/group_report.md`, `docs/system_architecture.md`, `docs/routing_decisions.md`, `docs/single_vs_multi_comparison.md`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi là trưởng nhóm QA/Integration, chịu trách nhiệm chạy pipeline trên test/grading questions, phân tích trace từ tất cả workers (Supervisor, Retrieval, Policy Tool, Synthesis), và so sánh kết quả Day 08 vs Day 09. Phần này là "integration layer" — nếu eval_trace.py không chạy được hoặc trace không đầy đủ, nhóm không thể xác nhận Definition of Done. Tôi cũng soạn thảo group report bằng cách tổng hợp bằng chứng từ trace thực tế (latency, routing accuracy, confidence scores) thay vì mô tả chung chung.

**Bằng chứng:**

Bằng chứng nằm trong `eval_trace.py` (365 dòng), `artifacts/grading_run.jsonl` (10 trace entries), và `reports/group_report.md` (175 dòng). Grading run cho thấy 10/10 questions processed, 100% routing accuracy, avg latency 5,056ms.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Thiết kế trace format chuẩn với 15 fields bắt buộc (id, question, answer, sources, supervisor_route, route_reason, workers_called, mcp_tools_used, confidence, hitl_triggered, latency_ms, timestamp, v.v.) thay vì log tự do.

**Lý do:**

Lúc đầu, mỗi worker có thể log output khác nhau, làm khó so sánh và phân tích. Tôi chọn định nghĩa schema trace chuẩn để: (1) đảm bảo tất cả trace có đủ thông tin để debug, (2) cho phép tính toán metrics nhất quán (avg latency, routing accuracy, confidence distribution), (3) hỗ trợ so sánh Day 08 vs Day 09 bằng cách chuẩn hóa output format.

**Trade-off đã chấp nhận:**

Trade-off là phải enforce schema này trên tất cả workers (Supervisor, Retrieval, Policy Tool, Synthesis), làm code phức tạp hơn. Nhưng đổi lại, trace trở thành "single source of truth" cho QA, giảm rủi ro miss bug, và tăng tốc độ debug khi ghép nhóm.

**Bằng chứng từ trace:**

```json
{
  "id": "gq10",
  "question": "Khách hàng mua sản phẩm trong chương trình Flash Sale...",
  "answer": "Khách hàng không được hoàn tiền...",
  "sources": [],
  "supervisor_route": "policy_tool_worker",
  "route_reason": "refund decision/exception routing via ['hoan tien', 'flash sale']",
  "workers_called": ["policy_tool_worker", "retrieval_worker", "synthesis_worker"],
  "mcp_tools_used": ["search_kb"],
  "confidence": 0.1,
  "latency_ms": 6525,
  "timestamp": "2026-04-14T21:18:04.873658"
}
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** API key 401 error khi chạy grading questions — OpenAI API không nhận key từ .env file.

**Symptom:**

Khi chạy `python eval_trace.py --grading`, synthesis_worker gọi OpenAI API nhưng nhận lỗi `401 Unauthorized: Invalid authentication credentials`. Pipeline dừng giữa chừng, không thể hoàn tất 10 grading questions.

**Root cause:**

Lỗi nằm ở lớp environment variable loading. Các file (eval_trace.py, graph.py, workers/synthesis.py, workers/policy_tool.py, workers/retrieval.py) không gọi `load_dotenv()` hoặc gọi mà không set `override=True`, nên Python không load API key từ .env file mà dùng system environment (rỗng).

**Cách sửa:**

Tôi thêm `load_dotenv(override=True)` ở đầu tất cả 5 files trên. Dòng này đảm bảo .env file được load và override system variables. Sau khi sửa, grading run hoàn tất 10/10 questions với latency trung bình 5,056ms.

**Bằng chứng trước/sau:**

Trước: `401 Unauthorized: Invalid authentication credentials` → script dừng.  
Sau: 10/10 questions processed, `artifacts/grading_run.jsonl` có 10 trace entries, exit code 0.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt ở việc "thiết kế trace schema chuẩn" và "chạy integration test toàn hệ thống". Nhờ vậy, nhóm có bằng chứng cụ thể (latency, routing accuracy, confidence) để xác nhận Definition of Done, thay vì chỉ "code chạy được".

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Hiện tại tôi chưa implement automated regression testing — nếu ai sửa code, tôi phải chạy lại eval_trace.py thủ công. Tôi cũng chưa thêm performance profiling chi tiết (breakdown latency từng worker).

**Nhóm phụ thuộc vào tôi ở đâu?**

Nếu eval_trace.py không chạy được, nhóm không thể xác nhận pipeline hoạt động đúng. Nếu trace không đầy đủ, không thể debug khi ghép nhóm.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi phụ thuộc vào Vinh (Supervisor), Hoàng (Retrieval), Quang Minh (Synthesis/Policy), B. Minh (MCP) để implement workers đúng contract. Tôi cũng phụ thuộc vào Việt (Tracing) để cập nhật worker_contracts.yaml.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm 2 cải tiến: (1) Automated regression test — mỗi lần code thay đổi, tự động chạy eval_trace.py và so sánh metrics với baseline, alert nếu latency tăng >20% hoặc routing accuracy giảm. (2) Performance profiling — breakdown latency từng worker (Supervisor: Xms, Retrieval: Yms, Synthesis: Zms) để phát hiện bottleneck. Với 2 tính năng này, nhóm sẽ debug nhanh hơn và tránh regression.

---
