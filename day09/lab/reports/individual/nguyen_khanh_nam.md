# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Khánh Nam  
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 15/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án Lab Day 09, tôi đảm nhận vai trò Supervisor Owner, chịu trách nhiệm chính về thiết kế và triển khai file `graph.py` — trung tâm điều phối toàn bộ pipeline multi-agent. Tôi trực tiếp viết các function quan trọng như `supervisor_node()`, `route_decision()`, và kết nối các worker (retrieval, policy_tool, synthesis) thành một graph hoàn chỉnh. Tôi cũng là người quyết định và implement logic routing dựa trên keyword, risk flag, và multi-hop reasoning, đảm bảo mọi task đều được route đúng worker, đồng thời trace lại đầy đủ `route_reason`, `risk_high` cho từng truy vấn. Công việc của tôi là nền tảng để các worker hoạt động đúng contract, giúp nhóm dễ dàng kiểm thử và debug pipeline. 

**Bằng chứng:**
- File: `day09/lab/graph.py` (commit `50acbbc` ngày 2026-04-14)
- Function: `supervisor_node`, `route_decision` (được mở rộng với multi-hop, risk flag, unknown error pattern)
- Trace log: route_reason luôn rõ ràng, không còn giá trị "unknown"

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi chọn mở rộng routing logic trong `supervisor_node()` từ keyword-based đơn giản sang mô hình kết hợp nhiều tiêu chí: keyword, risk trigger, multi-hop, và nhận diện lỗi không rõ (unknown error code). Thay vì chỉ match 1 chiều, tôi bổ sung các danh sách `policy_keywords`, `retrieval_keywords`, và kiểm tra pattern `err-` để tự động route sang human review khi gặp lỗi lạ. Đặc biệt, tôi đề xuất và implement nhận diện multi-hop (task chứa đồng thời keyword cấp quyền và SLA) để route qua cả retrieval và policy worker, tăng khả năng trả lời đúng cho các câu hỏi phức tạp.

**Lý do:**
- Keyword-based routing đơn giản nhưng dễ miss các edge case (multi-hop, lỗi lạ)
- Việc bổ sung risk flag giúp trace rõ các truy vấn nguy hiểm, hỗ trợ đánh giá hiệu năng
- Multi-hop reasoning là yêu cầu mới của Day 09, nếu không có sẽ fail các câu như gq09

**Bằng chứng:**
- Đoạn code mở rộng trong `supervisor_node` (commit `50acbbc`):
```python
policy_keywords = ["hoàn tiền", "refund", ...]
retrieval_keywords = ["p1", "sla", ...]
unknown_error_pattern = re.search(r"\\berr-[a-z0-9\\-]+\\b", task)
...
if unknown_error_pattern:
    route = "human_review"
    ...
elif is_multi_hop:
    route = "policy_tool_worker"
    ...
```
- Trace grading log: route_reason="multi-hop: access control + SLA context" cho gq09

**Trade-off đã chấp nhận:**
- Routing logic phức tạp hơn, cần nhiều test case để tránh bug
- Độ trễ tăng nhẹ do kiểm tra nhiều điều kiện, nhưng đổi lại trace rõ ràng và pipeline linh hoạt hơn

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Route fallback về retrieval_worker khi supervisor_route bị thiếu hoặc không hợp lệ, dẫn đến trace thiếu thông tin hoặc pipeline trả lời sai worker.

**Cách phát hiện:** Khi chạy thử nghiệm với các câu hỏi có nội dung lạ hoặc thiếu keyword, tôi nhận thấy trace log ghi supervisor_route="retrieval_worker" ngay cả khi task đáng lẽ phải chuyển sang human_review hoặc policy_tool_worker. Điều này làm giảm tính explainable của pipeline và có thể khiến nhóm mất điểm trace.

**Cách khắc phục:** Tôi đã sửa hàm `route_decision()` để kiểm tra chặt chẽ giá trị supervisor_route, nếu thiếu hoặc không hợp lệ sẽ raise exception thay vì fallback silent. Điều này giúp phát hiện bug sớm, trace rõ lỗi, và đảm bảo mọi route đều được quyết định minh bạch.

**Bằng chứng:**
- File: `day09/lab/graph.py`, function `route_decision()`
- Đoạn code:
```python
if not route:
    raise ValueError("[route_decision] supervisor_route is empty — supervisor_node chưa chạy hoặc state bị corrupt.")
if route not in VALID_ROUTES:
    raise ValueError(f"[route_decision] unknown route: '{route}'. Expected one of {VALID_ROUTES}.")
```
- Trace grading log: không còn trường hợp supervisor_route="retrieval_worker" khi task không hợp lệ

---

## 4. Tôi học được gì từ bài này? (100–150 từ)

Qua bài lab này, tôi nhận ra tầm quan trọng của việc thiết kế pipeline rõ ràng, trace được mọi quyết định routing và lý do. Việc chuyển từ pipeline monolith sang supervisor-worker giúp nhóm dễ dàng debug, kiểm thử từng thành phần, và mở rộng cho các use case phức tạp như multi-hop hoặc abstain. Tôi cũng học được cách phối hợp với các thành viên khác để chuẩn hóa contract, đảm bảo input/output giữa các worker luôn nhất quán. Cuối cùng, tôi rút ra bài học về việc log đầy đủ mọi quyết định, giúp nhóm dễ dàng đối chiếu trace với kết quả grading và nâng cao điểm số nhóm.
