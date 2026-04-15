# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration
# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Kiều Đức Lâm  
**Vai trò trong nhóm:** MCP Owner / Trace & Docs Owner  
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

Ở Sprint 4, tôi chịu trách nhiệm chính về mảng Quan sát (Observability) và Đánh giá (Evaluation) của toàn bộ hệ thống. Nhiệm vụ của tôi là đảm bảo mọi bước đi của các Agent đều được ghi nhận (trace) chính xác và có thể định lượng được hiệu quả so với hệ thống cũ.


**Module/file tôi chịu trách nhiệm:**
- File chính: `eval_trace.py` và các file tài liệu trong `docs/`.
- Functions tôi implement: Tôi đã xây dựng hàm `run_test_questions` để tự động hóa việc đẩy 15 câu hỏi qua Graph, hàm `analyze_traces` để tính toán các chỉ số kỹ thuật, và `compare_single_vs_multi` để thực hiện phép so sánh đối chiếu với kết quả từ Lab Day 08.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi là người nhận đầu ra cuối cùng từ Supervisor Owner và Worker Owner. Nếu các bạn ấy không ghi log vào `history` hoặc không tuân thủ `AgentState` schema, hệ thống đánh giá của tôi sẽ không thể trích xuất được dữ liệu. Sau khi tôi tổng hợp được các chỉ số về Latency và Accuracy, tôi sẽ cung cấp dữ liệu đó cho cả nhóm để hoàn thiện báo cáo chung.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

commit: update eval_trace

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)



**Quyết định:** Tôi chọn phương pháp **Differential Evaluation** (Đánh giá vi phân) khi so sánh hệ thống Single-Agent (Day 08) và Multi-Agent (Day 09).



**Lý do:**

Thay vì chỉ nhìn vào điểm số chính xác cuối cùng, tôi quyết định tập trung vào việc đo lường "Độ minh bạch của quá trình suy luận" (Routing Visibility). 



**Bằng chứng từ trace/code:**
for t in traces:
    # Lấy worker được chọn bởi Supervisor để đo độ chính xác của logic điều hướng
    route = t.get("supervisor_route", "unknown")
    routing_counts[route] = routing_counts.get(route, 0) + 1
    
    # Đo mức độ tin cậy của Agent tại thời điểm đưa ra câu trả lời
    conf = t.get("confidence", 0)
    confidences.append(conf)
# Xuất ra các chỉ số giúp so sánh chi tiết với Day 08
metrics = {
    "routing_distribution": routing_counts,
    "avg_confidence": sum(confidences) / len(confidences),
    "mcp_usage_rate": mcp_calls
}


## 3. Tôi đã sửa một lỗi gì? (150–200 từ)



**Lỗi:** Sai lệch dữ liệu Latency (thời gian phản hồi) trong báo cáo so sánh.


**Symptom (pipeline làm gì sai?):**

Ban đầu, khi chạy `python eval_trace.py`, thời gian latency của hệ thống Multi-Agent trả về cực kỳ thấp (chỉ ~10-20ms), trong khi thực tế mỗi lần gọi LLM phải mất 1-2 giây. Điều này dẫn đến biểu đồ so sánh cho thấy Day 09 nhanh gấp 100 lần Day 08, một kết quả vô lý.


**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Lỗi nằm ở cách tính thời gian trong hàm `build_graph` của `graph.py`. Do sơ suất khi tích hợp, biến `start_time` được khởi tạo bên trong mỗi Node thay vì khởi tạo một lần duy nhất lúc bắt đầu Graph. Kết quả là latency ghi nhận chỉ là thời gian chạy của Node cuối cùng (Synthesis) chứ không phải tổng thời gian của toàn pipeline.

**Cách sửa:**

Tôi đã trực tiếp can thiệp vào `graph.py` để đặt lại timer ở cấp độ cao nhất của hàm `run`. Tôi sử dụng thư mục `time` để đo khoảng cách từ lúc Supervisor nhận yêu cầu đến khi Synthesis hoàn tất, đảm bảo tính cả thời gian gọi tool qua MCP Server.


**Bằng chứng trước/sau:**
- **Trước:** Traces ghi nhận `latency_ms: 15` cho mọi câu hỏi.
- **Sau:** Latency dao động từ `2500ms` đến `3500ms`, phản ánh đúng thực tế của hệ thống agentic (Bằng chứng: file `artifacts/eval_report.json` sau khi sửa).

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Tôi có khả năng phân tích dữ liệu từ trace rất chi tiết. Việc tôi xây dựng được bộ format JSON đồng nhất cho cả nhóm đã giúp việc debug trở nên nhanh chóng hơn. Khi pipeline trả lời sai, tôi là người chỉ ra chính xác lỗi nằm ở bước Routing hay bước Retrieval dựa trên log.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Tôi còn hơi lúng túng trong việc sử dụng script để tự động hóa việc so sánh Accuracy. Hiện tại tôi vẫn phải ngồi chấm tay xem câu nào đúng, câu nào sai trước khi điền vào bảng so sánh vì chưa kịp viết script "LLM Judge".

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Cả nhóm phụ thuộc vào tôi để biết được hệ thống mới có thực sự tốt hơn hệ thống cũ hay không. Nếu không có phần Eval của tôi, nhóm sẽ không có số liệu để điền vào file `single_vs_multi_comparison.md`.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Cả nhóm phụ thuộc vào tôi để biết được hệ thống mới có thực sự tốt hơn hệ thống cũ hay không. Nếu không có phần Eval của tôi, nhóm sẽ không có số liệu để điền vào file `single_vs_multi_comparison.md`.


## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm 2 giờ, tôi sẽ triển khai tính năng **Automated Scorecard** sử dụng một LLM mạnh hơn (như GPT-4o) để làm giám khảo chấm điểm tự động cho 15 câu test. Hiện tại việc so sánh Accuracy đang tốn nhiều thời gian thủ công; nếu tự động hóa được bước này, nhóm sẽ có thêm thời gian để tinh chỉnh Prompts cho từng Worker.


*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
