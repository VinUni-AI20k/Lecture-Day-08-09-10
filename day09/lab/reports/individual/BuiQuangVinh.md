# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Bùi Quang Vinh  
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 2026-04-14  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? 

Tôi phụ trách phần core orchestrator của hệ multi-agent, cụ thể là file `lab/graph.py`, đồng thời hoàn thiện tài liệu mô tả kiến trúc trong `lab/docs/system_architecture.md` để phản ánh đúng trạng thái repo sau khi graph được nối với worker thật. Ở `graph.py`, tôi triển khai `AgentState`, `make_initial_state()`, `supervisor_node()`, `route_decision()`, `human_review_node()`, ba wrapper worker, cùng `build_graph()`, `run_graph()` và `save_trace()`. Ở `system_architecture.md`, tôi viết lại các phần về pipeline thực tế, shared state, vai trò từng thành phần, observability và giới hạn hiện tại của repo. Công việc của tôi là lớp nền cho cả nhóm, vì nếu graph và tài liệu kiến trúc không đúng thì worker vẫn có thể chạy riêng lẻ nhưng toàn hệ sẽ không có flow tích hợp rõ ràng và cũng không có chuẩn chung để debug.

**Module/file tôi chịu trách nhiệm:**
- File chính: `lab/graph.py`, `lab/docs/system_architecture.md`
- Functions tôi implement: `AgentState`, `make_initial_state`, `supervisor_node`, `route_decision`, `human_review_node`, `retrieval_worker_node`, `policy_tool_worker_node`, `synthesis_worker_node`, `build_graph`, `run_graph`, `save_trace`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Graph của tôi là điểm giao giữa user input và ba worker. Tôi phải bảo đảm state vào/ra đúng contract để retrieval, policy_tool và synthesis của các thành viên khác cắm vào mà không cần sửa lại orchestration.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

Bằng chứng trực tiếp là `lab/graph.py`, `lab/docs/system_architecture.md` và các trace như `lab/artifacts/traces/run_20260414_160019.json`, `lab/artifacts/traces/run_20260414_160036.json`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? 

**Quyết định:** Tôi chọn để Supervisor dùng heuristic keyword-based routing và ghi lại lý do route thành `route_reason`, thay vì dùng thêm một LLM riêng để classify task.

**Lý do:**

Tôi chọn cách này vì Day 09 của repo nhấn mạnh tính minh bạch của orchestration hơn là tối đa hóa “độ thông minh” của một router. Nếu tôi dùng LLM classifier, route có thể linh hoạt hơn nhưng sẽ khó giải thích tại sao một câu được đưa sang `retrieval_worker` hay `policy_tool_worker`, nhất là khi nhóm phải debug nhanh trong lab. Với heuristic routing, logic nằm lộ rõ trong `graph.py`: câu có access/approval/refund decision đi sang policy, câu có SLA/ticket/FAQ/HR đi retrieval, câu có error code kèm manual-review signal mới vào human review. Tôi cũng dùng thêm các cờ `needs_tool` và `risk_high` để tách quyết định điều phối khỏi xử lý domain của worker.

**Trade-off đã chấp nhận:**

Trade-off là routing hiện tại phụ thuộc keyword nên chưa bao phủ tốt các câu hỏi diễn đạt quá tự do. Tuy nhiên tôi chấp nhận điều đó vì đổi lại trace đọc được ngay, dễ so với kiến trúc đã mô tả trong `system_architecture.md`, và đủ ổn định để cả nhóm tích hợp song song.

**Bằng chứng từ trace/code:**

```python
if access_matches:
    route = "policy_tool_worker"
    needs_tool = True
elif refund_base_matches and (refund_decision_matches or temporal_policy or "duoc khong" in task):
    route = "policy_tool_worker"
    needs_tool = True
elif retrieval_matches:
    route = "retrieval_worker"
```

```text
run_20260414_160019.json
route_reason = "refund decision/exception routing via ['hoan tien', 'flash sale', 'duoc khong']"

run_20260414_160036.json
route_reason = "access-control routing via ['cap quyen', 'level 3'] | policy route overrides retrieval signals ['p1'] | cross-domain query detected | risk_high=True from ['khan cap', 'p1']"
```

---

## 3. Tôi đã sửa một lỗi gì? 

**Lỗi:** `UnicodeEncodeError` khi chạy manual smoke test trong `graph.py` trên Windows console.

**Symptom (pipeline làm gì sai?):**

Sau khi tôi hoàn thành flow `supervisor -> worker -> synthesis`, lệnh `python graph.py` vẫn có lúc dừng giữa chừng ở phần in kết quả ra màn hình. Graph đã chạy gần xong, state đã có `final_answer`, nhưng chương trình vẫn fail nếu câu trả lời chứa tiếng Việt.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Root cause không nằm ở routing hay worker contract mà nằm ở phần manual test của `graph.py`. Console mặc định của Windows dùng `cp1252`, trong khi output từ synthesis hoặc fallback error có ký tự Unicode tiếng Việt, nên `print()` bị lỗi encode. Đây là lỗi tầng orchestration/debugging vì làm hỏng smoke test dù bản thân state đã hợp lệ.

**Cách sửa:**

Tôi thêm `_console_text()` để chuẩn hóa text theo encoding hiện tại của stdout với `errors="replace"`, đồng thời reconfigure `sys.stdout` sang UTF-8 trong block `if __name__ == "__main__":`. Sau đó tôi bọc các giá trị như `query`, `route_reason`, `workers_called`, `final_answer` trước khi in ra console.

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

Trước khi sửa:

```text
UnicodeEncodeError: 'charmap' codec can't encode character '\u1ec3'
```

Sau khi sửa:

```text
> Query: Khach hang Flash Sale yeu cau hoan tien vi san pham loi - duoc khong?
Route      : policy_tool_worker
Workers    : ['policy_tool_worker', 'retrieval_worker', 'synthesis_worker']
Trace saved: ./artifacts/traces/run_20260414_160019.json
Graph smoke test complete.
```

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt nhất ở việc tạo ra một lớp orchestrator đủ rõ để các phần khác cắm vào mà không chồng chéo trách nhiệm, đồng thời tài liệu hóa lại kiến trúc để repo và docs không bị lệch nhau. Phần `system_architecture.md` tôi viết lại cũng giúp chứng minh repo đang chạy theo flow nào thật, thay vì chỉ mô tả ý tưởng ban đầu.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Tôi vẫn chưa biến routing thành một cơ chế được đo định lượng trên toàn bộ tập câu hỏi. Ngoài ra `human_review_node()` hiện mới là placeholder auto-approve chứ chưa phải HITL thật.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Nếu tôi chưa xong `graph.py`, nhóm sẽ bị block ở phần tích hợp end-to-end. Nếu tôi chưa cập nhật `system_architecture.md`, nhóm sẽ thiếu tài liệu chuẩn để đối chiếu contract và giải thích kiến trúc khi nộp bài.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào các worker owner ở chỗ họ phải giữ đúng contract state và output. Tôi cũng phụ thuộc vào dữ liệu/index và MCP implementation để graph chạy ra answer thực tế tốt hơn, thay vì chỉ đúng flow.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? 

Nếu có thêm 2 giờ, tôi sẽ bổ sung một bước đo routing accuracy cho Supervisor dựa trên `data/test_questions.json` và ghi kết quả tổng hợp vào trace hoặc `eval_report`. Lý do là tôi đã hoàn thành được graph và tài liệu kiến trúc, nhưng hiện mới chỉ có bằng chứng theo từng trace đơn lẻ như `run_20260414_160019.json`; tôi chưa có một con số tổng thể để chứng minh Supervisor route đúng bao nhiêu phần trăm trên toàn bộ bộ câu hỏi.

---

