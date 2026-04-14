# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trịnh Đức Anh  
**Vai trò trong nhóm:** Trace & Docs Owner  
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
- File chính: `day09/lab/eval_trace.py`, `day09/lab/docs/system_architecture.md`, `day09/lab/docs/single_vs_multi_comparison.md`, `day09/lab/docs/routing_decisions.md`
- Functions tôi implement: tôi trực tiếp chạy và dùng kết quả từ `run_test_questions()`, `analyze_traces()`, `compare_single_vs_multi()`, `save_eval_report()` để điền tài liệu.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi là người nhận output từ các bạn phụ trách core pipeline (`graph.py`, `workers/*`, `mcp_server.py`) rồi chuyển thành bằng chứng định lượng cho báo cáo. Cụ thể, sau khi supervisor/worker/mcp chạy được, tôi chạy `python -X utf8 day09/lab/eval_trace.py` để sinh trace và báo cáo tổng hợp, sau đó dùng trace này điền ba tài liệu docs bắt buộc. Nhờ đó, nhóm có một vòng phản hồi rõ ràng: code -> trace -> phát hiện vấn đề -> sửa code -> cập nhật tài liệu. Khi xảy ra lỗi ở nhánh policy (`No module named 'mcp'`), tôi là người phát hiện qua `worker_io_logs` trong trace và phản hồi lại cho bạn phụ trách MCP để fix môi trường.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

- Trace files đã dùng để phân tích: `day09/lab/artifacts/traces/run_20260414_174750_791613.json`, `run_20260414_174756_464141.json`, `run_20260414_174758_278752.json` và bộ gq01-gq10 mới nhất.
- Output đo được tôi đưa vào docs: Day09 `avg_confidence = 0.816`, `avg_latency = 4689ms`, `mcp_usage = 50%`, `abstain_rate = 0/10`.
- Các file docs đã điền dựa trên trace thực tế: `docs/system_architecture.md`, `docs/single_vs_multi_comparison.md`, `docs/routing_decisions.md`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Dùng trace thực tế làm nguồn sự thật duy nhất để điền docs, thay vì suy diễn theo thiết kế kỳ vọng.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

Phải chọn giữa hai cách: (1) mô tả kiến trúc theo “intended design” từ README/contract, hoặc (2) mô tả theo “observed behavior” từ trace chạy thật. Tôi chọn cách (2) vì nó phản ánh đúng chất lượng hệ thống tại thời điểm nộp bài và hỗ trợ debug tốt hơn. Ví dụ, kiến trúc mô tả policy worker có gọi MCP tools, nhưng ở một số run ban đầu trace ghi rõ lỗi dependency (`No module named 'mcp'`) và dẫn tới answer abstain. Nếu tôi chỉ viết theo thiết kế kỳ vọng thì báo cáo đẹp hơn nhưng sai thực tế kỹ thuật.

Khi áp dụng quyết định này, tôi luôn chạy script trước khi ghi số liệu: Day 09 dùng `eval_trace.py`, Day 08 dùng `eval.py`, sau đó mới điền bảng so sánh. Kết quả là tài liệu thể hiện đúng trade-off: Day 09 có observability tốt hơn (route_reason, worker_io_logs), nhưng quality answer chưa tự động vượt Day 08 ở mọi nhóm câu hỏi.

**Trade-off đã chấp nhận:**

Trade-off chấp nhận là báo cáo có thể “xấu” hơn vì phải ghi cả hạn chế (noise nguồn `unknown`, một số câu trả lời chưa đạt rubric), nhưng đổi lại tài liệu trung thực, có giá trị kỹ thuật và giúp nhóm biết cần cải tiến ở đâu.

**Bằng chứng từ trace/code:**

```
{
  "question_id": "gq09",
  "supervisor_route": "policy_tool_worker",
  "route_reason": "access-control signal detected | incident/SLA context also detected | MCP lookup enabled for policy worker | risk_high flagged",
  "workers_called": ["policy_tool_worker", "synthesis_worker"]
}
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** `eval_trace.py` lỗi Unicode trên Windows console khi in emoji, làm tôi không chạy được bộ câu hỏi để lấy metrics.

**Symptom (pipeline làm gì sai?):**

Khi chạy lệnh `python day09/lab/eval_trace.py`, chương trình dừng ngay trước vòng chạy câu hỏi với `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4cb'`. Điều này khiến tôi không thể tạo report và không có dữ liệu để điền docs đúng yêu cầu “phải có số liệu thực tế từ trace”.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Root cause nằm ở lớp runtime/terminal encoding, không phải logic routing hay worker. File `eval_trace.py` có in ký tự emoji (`📋`) trong môi trường Windows cp1252, nên crash trước khi chạy pipeline.

**Cách sửa:**

Tôi sửa theo hướng vận hành: chạy script với UTF-8 mode bằng lệnh `python -X utf8 day09/lab/eval_trace.py`. Sau khi đổi cách chạy, script chạy end-to-end thành công với 10 câu grading và sinh đủ trace/report để phân tích. Ngoài ra, tôi tách thêm một bước kiểm tra metrics từ 10 trace mới nhất để đảm bảo số liệu trong docs nhất quán (`avg_confidence`, `avg_latency`, `abstain_rate`, `mcp_usage`).

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

Trước khi sửa: `UnicodeEncodeError` tại dòng print đầu tiên của `run_test_questions()`.

Sau khi sửa (chạy `-X utf8`): script hoàn tất 10/10 câu, in metrics:
- `avg_confidence = 0.816`
- `avg_latency_ms = 4689`
- `mcp_usage = 5/10 (50%)`
- `abstain_rate = 0/10`

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt nhất ở phần chuẩn hóa bằng chứng kỹ thuật thành tài liệu có thể kiểm chứng. Thay vì điền docs theo cảm tính, tôi luôn gắn kết luận với trace cụ thể và output command. Nhờ đó, ba tài liệu của Sprint 4 không chỉ “đủ form” mà còn có giá trị debug cho nhóm.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Tôi chưa tự động hóa hoàn toàn bước chấm chất lượng answer theo rubric (`grading_criteria`). Hiện nhiều kết luận vẫn phải đọc thủ công từ trace answer, nên tốn thời gian và có độ chủ quan nhất định.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Nếu tôi chưa chạy trace và tổng hợp metrics, nhóm sẽ bị block ở Sprint 4: không điền được docs bắt buộc, không có dữ liệu so sánh Day08/Day09, và khó chứng minh quyết định routing bằng evidence thật.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào các bạn phụ trách worker/MCP để pipeline chạy ổn định. Nếu nhánh `policy_tool_worker` hoặc MCP server lỗi môi trường, dữ liệu trace sẽ lệch và tôi không thể kết luận chính xác về hiệu năng/độ đúng của kiến trúc.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Nếu có thêm 2 giờ, tôi sẽ triển khai một script evaluator cho Day 09 để chấm tự động theo `grading_criteria` (đặc biệt cho gq09 multi-hop). Lý do: trong trace hiện tại, route của gq09 đúng nhưng answer còn nhiễu nguồn; chỉ số confidence chưa đủ để kết luận accuracy. Có evaluator tự động sẽ giúp bảng `single_vs_multi_comparison.md` điền được `multi-hop accuracy` bằng số liệu thật thay vì `N/A`.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
