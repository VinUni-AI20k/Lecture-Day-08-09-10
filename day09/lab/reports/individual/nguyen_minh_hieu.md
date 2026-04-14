# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Minh Hiếu  
**Mã học viên:** 2A202600180

**Vai trò trong nhóm:** Trace & Docs Owner

**Ngày nộp:** 14/04/2026  

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án lab Day 09 này, tôi chịu trách nhiệm chính về việc xây dựng hệ thống đánh giá hiệu năng (Evaluation) và hoàn thiện toàn bộ bộ hồ sơ kỹ thuật cho nhóm. 

**Module/file tôi chịu trách nhiệm:**
- File chính: `eval_trace.py` - Đây là "trái tim" của hệ thống đánh giá, nơi tôi xử lý việc chạy tự động các câu hỏi kiểm thử và bóc tách dữ liệu.
- Functions tôi implement: `analyze_traces()`, `compare_single_vs_multi()`, và các module tự động tổng hợp metrics từ trace JSON sang `eval_report.json`.
- Phụ trách toàn bộ thư mục `docs/` bao gồm: `system_architecture.md`, `routing_decisions.md`, `single_vs_multi_comparison.md`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Công việc của tôi là tổng hợp code của cả nhóm. Tôi nhận file `graph.py` từ anh Nam (Supervisor Owner) và các worker từ Phúc, Tú Nam, Hữu Hưng để chạy đánh giá. Tôi sử dụng các file trace sinh ra từ code của anh Quân (MCP Owner) để bóc tách thông tin công cụ đã gọi, từ đó viết tài liệu `routing_decisions.md`. Nếu tôi không hoàn thành việc phân tích trace, nhóm sẽ không có số liệu thực tế để so sánh hiệu quả giữa kiến trúc Multi-Agent so với Single Agent của Day 08.

**Bằng chứng:**
Tôi đã trực tiếp viết code tính toán `routing_distribution` và `avg_confidence` trong `eval_trace.py` (dòng 162-231) để chuyển đổi từ hàng chục file log thô sang báo cáo định lượng tóm tắt trong `artifacts/eval_report.json`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** 
Tôi quyết định triển khai cơ chế **Automated Trace Analysis** trong file `eval_trace.py` thay vì kiểm tra thủ công từng file JSON trong thư mục `artifacts/traces/`.

**Lý do:**
Khi làm việc với Multi-Agent, số lượng trace sinh ra rất lớn vì mỗi câu hỏi đi qua nhiều node khác nhau. Nếu kiểm tra thủ công, tôi rất dễ bỏ sót các lỗi logic như Supervisor route nhầm hoặc Worker phản hồi chậm gây thắt nút cổ chai (bottleneck). Việc viết code để tự động bóc tách các trường như `route_reason` và `workers_called` giúp tôi có cái nhìn tổng quát về độ phủ của từng worker và phát hiện nhanh các câu hỏi mà hệ thống chưa tối ưu.

**Trade-off đã chấp nhận:**
Tôi đã phải dành thêm khoảng 3 tiếng ở Sprint 4 để debug logic tính toán trong `eval_trace.py` và xử lý định dạng JSONL cho grading thay vì viết tài liệu ngay lập tức. Điều này làm tăng áp lực thời gian cuối ngày nhưng bù lại, các con số trong `group_report.md` và `single_vs_multi_comparison.md` hoàn toàn chính xác, có bằng chứng định lượng thay vì chỉ là nhận xét cảm tính.

**Bằng chứng từ code:**
Đoạn code tôi dùng để bóc tách lịch sử thực thi của worker (ví dụ minh họa từ `eval_trace.py`):
```python
def analyze_traces(traces_dir):
    # logic duyệt file và tổng hợp metrics
    for fname in trace_files:
        with open(os.path.join(traces_dir, fname), encoding="utf-8") as f:
            t = json.load(f)
            route = t.get("supervisor_route", "unknown")
            routing_counts[route] = routing_counts.get(route, 0) + 1
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `UnicodeEncodeError` khi in các icon đặc biệt trên terminal Windows.

**Symptom:**
Khi chạy `python graph.py` hoặc `eval_trace.py` để sinh dữ liệu trace, script bị crash ngay lập tức tại các dòng `print()` có chứa các icon unicode như `▶`, `✅`, hoặc `⚠️`. Điều này cực kỳ nguy hiểm vì nó làm gián đoạn quá trình đánh giá tự động, khiến nhóm không thể có đủ 15 file trace làm bằng chứng nộp bài.

**Root cause:**
Terminal mặc định của Windows (Command Prompt/PowerShell) trên một số máy thành viên không hỗ trợ mã hóa UTF-8 mặc định cho các ký tự icon này, dẫn đến việc crash script do lỗi mã hóa `cp1252` khi cố gắng in ra các byte không hợp lệ.

**Cách sửa:**
Tôi đã thay đổi toàn bộ các ký tự icon này sang ký tự ASCII tiêu chuẩn hoặc các ký tự unicode an toàn hơn. 
- *Trước:* `print(f"▶ Query: {query}")`
- *Sau:* `print(f" [TASK] Query: {query}")`
Đồng thời, tôi thêm xử lý `encoding="utf-8"` cho tất cả các hàm `open()` và `json.dump()` trong `save_trace()` để đảm bảo file JSON lưu xuống luôn đọc được trên mọi hệ điều hành.

**Bằng chứng trước/sau:**
- Trước: Terminal báo lỗi `'charmap' codec can't encode character '\u25b6'`.
- Sau: Script thực thi mượt mà từ đầu đến cuối, sinh ra đủ bộ trace trong thư mục `artifacts/traces/` mà không bị dừng đột ngột.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi làm tốt ở việc bao quát toàn bộ luồng dữ liệu của hệ thống và chuyển đổi các khái niệm kỹ thuật từ log thô thành tài liệu kiến trúc dễ hiểu cho người đọc. Việc hoàn thiện hệ thống đánh giá tự động đã giúp nhóm tiết kiệm rất nhiều thời gian kiểm thử cuối giờ.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi còn hơi chậm trong việc hiểu sâu về giao thức truyền nhận dữ liệu của `MCP Server` ở Sprint 3, dẫn đến việc phải hỏi anh Quân nhiều lần về cách bóc tách trường `mcp_tools_used` từ `AgentState`.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm phụ thuộc vào tôi để hoàn thành `eval_trace.py` và chuẩn bị các file log. Nếu không có phần phân tích trace này, báo cáo nhóm sẽ thiếu đi các số liệu quan trọng về Latency và Confidence - những yếu tố quyết định 40% điểm số của Lab.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm thời gian, tôi sẽ triển khai cơ chế **LLM-as-a-judge** trong `eval_trace.py`. Hiện tại, chúng ta mới chỉ đánh giá dựa trên `Confidence` (điểm tin cậy của model). Với các câu hỏi phức tạp như `gq09` (multi-doc logic đòi hỏi kết hợp thông tin từ cả Access SOP và SLA), việc dùng một LLM mạnh hơn (như GPT-4o) để chấm điểm `Accuracy` của câu trả lời so với Ground Truth sẽ giúp báo cáo có độ khách quan và chính xác tuyệt đối hơn so với việc kiểm tra bằng mắt.

---
� mình đã xây dựng.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi còn hơi chậm trong việc hiểu sâu về cấu trúc của `MCP Server`. Ở Sprint 3, tôi đã mất khá nhiều thời gian để tìm hiểu cách bóc tách `mcp_tools_used` từ `AgentState`.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm phụ thuộc vào tôi để hoàn thành `eval_trace.py` và chuẩn bị các file log. Nếu không có phần này, nhóm sẽ không thể nộp bài đúng hạn (trước 18:00) với đầy đủ dữ liệu grading.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm thời gian, tôi sẽ thử triển khai **LLM-as-a-judge** trong `eval_trace.py` để chấm điểm Accuracy tự động thay vì chỉ nhìn vào Confidence. Hiện tại, một số câu hỏi phức tạp (multi-hop) vẫn cần kiểm tra tay kết quả để đảm bảo độ chính xác tuyệt đối.

---
