# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Bùi Văn Đạt 
**Vai trò trong nhóm:** Trace & Docs Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi chịu trách nhiệm chính cho Sprint 4 evaluation và trace analysis của Lab Day 09, bao gồm sửa lỗi `eval_trace.py`, hoàn thiện quy trình chạy test questions và grading questions, và kiểm tra trace output để báo cáo chất lượng pipeline.

**Module/file tôi chịu trách nhiệm:**
- File chính: `eval_trace.py`, `graph.py`, `workers/retrieval.py`
- Functions tôi implement: `run_test_questions`, `run_grading_questions`, `analyze_traces`, `save_trace`, `run_graph`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi làm việc trực tiếp với phần supervisor routing trong `graph.py` và phần retrieval/policy worker để đảm bảo trace có đủ metadata. Kết quả của tôi hỗ trợ nhóm đánh giá độ chính xác route và nguồn evidence cho `Synthesis` và `MCP` owner.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

- File: `day09/lab/eval_trace.py`
- File: `day09/lab/graph.py`
- File: `day09/lab/workers/retrieval.py`
- Kết quả trace: `artifacts/traces/*.json`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi chọn giữ nguyên routing rule-based trong supervisor và tập trung vào trace metadata thay vì đưa router sang mô hình LLM cho Sprint 4.

**Lý do:**

Trong Sprint 4, mục tiêu chính của tôi là đánh giá pipeline và so sánh trace giữa Day 08 và Day 09. Nếu chuyển router sang LLM, tôi sẽ mất thời gian debug một luồng mới và khó so sánh trực tiếp. Rule-based routing cũng đã cho phép tôi ghi rõ `supervisor_route`, `route_reason`, `needs_tool` và `risk_high` trong mỗi trace, tạo điều kiện cho phần `analyze_traces()`.

**Trade-off đã chấp nhận:**

Tôi chấp nhận rằng rule-based routing có thể kém linh hoạt hơn LLM khi câu hỏi có từ ngữ đa dạng, nhưng đổi lại nó giúp trace ổn định và dễ kiểm tra. Do đó, đánh giá chất lượng Sprint 4 tập trung vào trace coverage và khả năng debug, thay vì độ bao phủ ngôn ngữ hoàn hảo.

**Bằng chứng từ trace/code:**

```text
[supervisor] route=policy_tool_worker needs_tool=True risk_high=True reason=access-control signal detected | incident/SLA context also detected | MCP lookup enabled for policy worker
```

Trace `gq09` thể hiện rõ route reason và worker sequence, cho thấy quyết định kỹ thuật này giúp phân tích chính xác từng trường hợp.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Mặc định `eval_trace.py` dùng `grading_questions.json` làm test file, nên khi chạy test questions vẫn lấy nhầm bộ grading.

**Symptom (pipeline làm gì sai?):**

Khi chạy `python eval_trace.py` đơn thuần, pipeline chỉ chạy bộ grading questions thay vì file `test_questions.json` như yêu cầu Sprint 4 ban đầu. Điều này làm report đánh giá test không đúng dataset và trace không phản ánh đúng quy trình test cơ bản.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Lỗi nằm ở logic cấu hình file đầu vào trong `eval_trace.py`, thuộc phần trace/evaluation workflow chứ không phải worker. `DEFAULT_TEST_FILE` được đặt nhầm thành `data/grading_questions.json`.

**Cách sửa:**

Tôi sửa `DEFAULT_TEST_FILE` thành `data/test_questions.json` trong `eval_trace.py`, đồng thời thêm tính năng resolve đường dẫn tương đối để bảo đảm script chạy ổn định từ thư mục `day09/lab`.

**Bằng chứng trước/sau:**

- Trước: `eval_trace.py` chạy 15 câu grading khi dùng lệnh mặc định.
- Sau: `eval_trace.py` chạy đúng 15 câu trong `test_questions.json`, tạo trace `artifacts/traces/*.json` và báo cáo metrics hợp lệ.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt nhất ở việc xác định và sửa lỗi cấu hình chạy test trong `eval_trace.py`, cũng như hoàn thiện trace analysis để nhóm có thể so sánh Day 08 vs Day 09. Tôi giữ đầu bài Sprint 4 tập trung vào evaluation pipeline thay vì lan man vào phần docs.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Điểm tôi còn yếu là chưa kịp test kỹ toàn bộ phần retrieval với OpenAI/Chroma vì môi trường venv có vấn đề dependency. Tôi có thể cải thiện bằng cách triển khai thêm kiểm tra environment và cài đặt package cụ thể trước khi chạy pipeline.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Nhóm phụ thuộc vào tôi ở phần `eval_trace.py` và phân tích trace. Nếu tôi chưa hoàn thành, nhóm sẽ không có báo cáo Sprint 4 rõ ràng và không thể đánh giá đúng routing hoặc source coverage.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào thành viên `Supervisor Owner` và `Retrieval Worker Owner` để đảm bảo `graph.py` và `workers/retrieval.py` tạo trace chính xác. Tôi cũng cần `MCP Owner` xác nhận các trace call tool đủ rõ và `Synthesis Owner` xác nhận output answer được ghi `final_answer` đúng format.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm 2 giờ, tôi sẽ bổ sung kiểm tra environment và dependency cho `eval_trace.py`, cụ thể là tự động xác định xem `openai`/`sentence-transformers` có hoạt động hay không trước khi chạy retrieval. Lý do: trace gq07 cho thấy fallback random embeddings làm mất nguồn evidence, nên một kiểm tra dependency sớm sẽ giúp nhóm tránh chạy grading với kết quả không đáng tin cậy.
*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
