# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đỗ Minh Hiếu  
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 14/04/2026  
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

> Mô tả cụ thể module, worker, contract, hoặc phần trace bạn trực tiếp làm.
> Không chỉ nói "tôi làm Sprint X" — nói rõ file nào, function nào, quyết định nào.

**Module/file tôi chịu trách nhiệm:**
- File chính: `graph.py`
- Functions tôi implement: `make_initial_state()`, `supervisor_node()`, `route_decision()`, `human_review_node()`, `build_graph()`, `run_graph()`, `save_trace()`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi chịu trách nhiệm lớp điều phối ở đầu pipeline: nhận `task`, quyết định route, rồi chuyển state sang các worker phía dưới. Phần này nối trực tiếp với retrieval worker, policy worker và synthesis worker vì toàn bộ hệ thống chỉ chạy đúng khi supervisor chọn đúng nhánh. Nếu routing sai, các worker sau đó sẽ làm việc với context không phù hợp hoặc bị gọi sai thứ tự. Tôi cũng thêm `history`, `route_reason`, `risk_high` và `run_id` để trace của team có thể đọc được đường đi của từng câu hỏi.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

Commit `8f54392` (`sprint 1`) cập nhật [graph.py](../../graph.py) với routing logic thực tế. Khi chạy `python graph.py`, tôi thấy trace ghi đúng route_reason như `task contains SLA/ticket/escalation keywords` và `task contains policy/access keywords | risk_high flagged`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tôi chọn routing bằng keyword-based rules trong `supervisor_node()` thay vì gọi LLM để phân loại route.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

Tôi ưu tiên cách này vì Sprint 1 cần một supervisor chạy ổn định, dễ debug và không phụ thuộc API key hay độ ngẫu nhiên của LLM. Bộ câu hỏi của lab chỉ chia thành vài nhóm khá rõ: SLA/ticket/escalation thì đi retrieval, refund/access/policy thì đi policy tool, còn mã lỗi không rõ thì chuyển human review. Với pattern này, keyword routing là đủ tốt và rẻ về latency. Khi chạy thực tế, trace cho thấy ba query mẫu đều route đúng ngay lập tức và không cần thêm bước suy luận phức tạp.

**Trade-off đã chấp nhận:**

Tôi chấp nhận rằng keyword routing kém linh hoạt hơn LLM classification với những câu hỏi mơ hồ. Tuy nhiên, trade-off này hợp lý cho Day 09 vì mục tiêu chính là tách vai rõ ràng và có trace ổn định, không phải tối ưu semantic routing ở mức cao.

**Bằng chứng từ trace/code:**

```
if has_unknown_err_code:
	route = "human_review"
elif has_policy_signal:
	route = "policy_tool_worker"
elif has_retrieval_signal:
	route = "retrieval_worker"

# Trace output:
# Route   : retrieval_worker
# Reason  : task contains SLA/ticket/escalation keywords
# Route   : policy_tool_worker
# Reason  : task contains policy/access keywords | risk_high flagged
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** `run_id` của trace bị trùng khi tôi chạy graph liên tiếp trong cùng một giây.

**Symptom (pipeline làm gì sai?):**

Khi tôi chạy `python graph.py` nhiều lần liên tiếp, trace của các query có thể ghi đè lên cùng một file JSON. Điều này làm mất lịch sử debug và khiến tôi không thể so sánh các lần chạy khác nhau.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Lỗi nằm ở `make_initial_state()` trong [graph.py](../../graph.py): ban đầu `run_id` được tạo theo format đến đơn vị giây, nên hai lần chạy trong cùng một giây sinh ra cùng tên file trace.

**Cách sửa:**

Tôi đổi `run_id` sang format có thêm microseconds (`%f`) để mỗi lần chạy sinh ra một filename duy nhất. Sau khi sửa, trace được lưu tách riêng cho từng query và không còn ghi đè.

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

Trước khi sửa, nhiều lần chạy trong cùng giây có thể lưu cùng tên file. Sau khi sửa, `graph.py` tạo các trace khác nhau như `run_20260414_160508_430558.json`, `run_20260414_160508_430936.json`, `run_20260414_160508_431600.json`. Đây là bằng chứng trực tiếp rằng bug đã được xử lý.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt nhất ở phần thiết kế luồng điều phối rõ ràng và dễ debug. Sprint 1 của tôi không chỉ làm cho `graph.py` chạy được, mà còn làm cho team có trace có ý nghĩa: biết câu nào đi retrieval, câu nào đi policy, câu nào cần human review. Điều đó giúp các sprint sau đỡ phải đoán lỗi nằm ở đâu.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Tôi chưa đẩy mạnh phần worker thực sự, nên `graph.py` hiện vẫn dùng placeholder output ở retrieval/policy/synthesis. Phần này cần người làm Sprint 2 hoàn thiện để hệ thống không chỉ route đúng mà còn trả lời tốt.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Nếu supervisor chưa xong, cả pipeline bị block: retrieval worker không biết khi nào được gọi, policy tool không biết lúc nào cần xử lý policy, và synthesis cũng không có state đúng để tổng hợp. Nói ngắn gọn, route sai thì mọi phần phía sau đều sai.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào worker của các bạn để graph thật sự sinh ra câu trả lời có giá trị. Cụ thể, retrieval worker cần trả chunks đúng contract, policy worker cần trả `policy_result` chuẩn, và synthesis worker cần biến context thành câu trả lời có citation.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Nếu có thêm 2 giờ, tôi sẽ thay placeholder worker wrappers trong `graph.py` bằng call thật tới `workers/retrieval.py`, `workers/policy_tool.py`, và `workers/synthesis.py`, rồi chạy lại `graph.py` để so sánh trace thật với trace placeholder hiện tại. Tôi chọn việc này vì trace hiện nay cho thấy routing đúng, nhưng answer vẫn là placeholder, nghĩa là bottleneck tiếp theo là lớp worker integration chứ không phải supervisor.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
