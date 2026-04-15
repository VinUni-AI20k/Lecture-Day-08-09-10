# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đỗ Minh Khiêm  
**Vai trò trong nhóm:** Trace & Docs Owner + QA Release  
**Ngày nộp:** 2026-04-14  
**Độ dài:** ~650 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong Lab Day 09, tôi đảm nhận vai trò là **Trace & Docs Owner**, phụ trách chính ở Sprint 4. Công việc của tôi tập trung vào việc đảm bảo hệ thống không chỉ chạy được mà còn phải "quan sát được" (observable). 

**Module/file tôi chịu trách nhiệm:**
- **File chính:** `eval_trace.py` — công cụ chạy test tập trung và đánh giá metrics.
- **Docs:** Tôi chịu trách nhiệm hoàn thiện 3 file tài liệu kiến trúc (`system_architecture.md`, `routing_decisions.md`, `single_vs_multi_comparison.md`) và tổng hợp báo cáo nhóm (`group_report.md`).
- **Functions tôi implement:** `run_grading_questions()`, `analyze_traces()` và core logic so sánh trong `compare_single_vs_multi()`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi đóng vai trò là "người kiểm chứng" cuối cùng. Khi Vương (Supervisor Owner) và các bạn Worker hoàn thành pipeline, tôi sẽ sử dụng `eval_trace.py` để đẩy 15 câu hỏi test qua hệ thống. Kết quả trace JSON sinh ra là nguyên liệu đầu vào để tôi phân tích xem routing của Vương có chuẩn không, hay MCP của Văn có thực sự được gọi hiệu quả không.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi quyết định sử dụng định dạng **JSONL (Newline-delimited JSON)** cho file `grading_run.jsonl` thay vì một mảng JSON thông thường, đồng thời bổ sung trường `route_reason` vào mỗi bản ghi logging.

**Lý do:** 
Ban đầu, nhóm định lưu kết quả test vào một file JSON lớn. Tuy nhiên, tôi nhận thấy nếu pipeline gặp lỗi ở câu thứ 10/15 (ví dụ: lỗi LLM rate limit hoặc timeout), việc parse một file JSON dở dang sẽ rất khó khăn. Dùng JSONL cho phép tôi ghi dữ liệu xuống đĩa ngay sau khi mỗi câu hỏi kết thúc. Nếu hệ thống sập giữa chừng, các kết quả trước đó vẫn được bảo toàn. 

Bên cạnh đó, việc ép buộc lưu `route_reason` giúp tôi (với vai trò QA) có thể giải thích được tại sao Supervisor lại chọn nhánh đó mà không cần phải debug lại code của Vương. Điều này cực kỳ quan trọng khi so sánh "Single vs Multi-Agent" vì ta cần bằng chứng định tính về khả năng giải thích (explainability) của hệ thống mới.

**Trade-off đã chấp nhận:**
Việc lưu JSONL khiến việc đọc lại file bằng các tool xem JSON thông thường khó hơn một chút (cần đọc từng dòng), nhưng độ tin cậy của dữ liệu trong quá trình "Grading Run" là ưu tiên số 1 của tôi.

**Bằng chứng từ code:**
```python
# eval_trace.py: L152
with open(output_file, "a", encoding="utf-8") as out:
    out.write(json.dumps(record, ensure_ascii=False) + "\n")
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `analyze_traces` bị crash (ZeroDivisionError) và tính sai latency trung bình khi có một số câu hỏi bị lỗi worker.

**Symptom:** Khi chạy `python eval_trace.py --analyze`, script báo lỗi chia cho 0 hoặc trả về latency là 0ms mặc dù thực tế hệ thống chạy mất vài giây. Điều này xảy ra khi một số trace file chỉ chứa thông báo lỗi mà không có field `latency_ms` hay `confidence`.

**Root cause:** Logic cũ trong `analyze_traces` thực hiện tính tổng latency bằng cách iterate qua list traces nhưng không kiểm tra xem field `latency_ms` có tồn tại và khác `None` hay không. Khi gặp một kết quả lỗi từ Supervisor (không kịp gọi worker), mảng `latencies` bị rỗng.

**Cách sửa:** Tôi đã thêm các bộ lọc check `if lat` và `if conf` trước khi append vào danh sách tính toán, đồng thời thêm kiểm tra độ dài danh sách trước khi thực hiện phép chia trung bình.

**Bằng chứng:**
*Trước khi sửa:*
```python
avg_latency = sum(latencies) / len(traces) # Lỗi nếu trace rỗng hoặc latencies không đủ
```
*Sau khi sửa (eval_trace.py: L225):*
```python
latencies = [t.get("latency_ms") for t in traces if t.get("latency_ms") is not None]
metrics["avg_latency_ms"] = round(sum(latencies) / len(latencies)) if latencies else 0
```

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi nghĩ mình đã làm tốt việc "đóng gói" sản phẩm. Việc thiết kế `eval_trace.py` giúp nhóm tiết kiệm rất nhiều thời gian khi chạy chấm điểm. Tôi cũng là người phát hiện ra việc MCP không được gọi ở một số câu hỏi thông qua việc soi kỹ `mcp_tools_used` trong trace, từ đó giúp Văn sửa kịp logic dispatch.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi chưa dành đủ thời gian để tối ưu hóa code bên trong các worker (Sprint 2), chủ yếu chỉ đứng ở ngoài đọc I/O contract. Điều này khiến tôi mất thời gian lúc đầu để hiểu tại sao confidence của `synthesis_worker` lại thấp.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nếu không có phần script evaluation và report của tôi, nhóm sẽ không có đủ bằng chứng số liệu để nộp bài theo yêu cầu của `SCORING.md`, ngay cả khi code pipeline chạy hoàn hảo.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc hoàn toàn vào Vương (Supervisor) để có cấu trúc State chuẩn và Văn (MCP) để có field `mcp_tools_used` chính xác trong trace.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ xây dựng một dashboard so sánh trực quan (Dùng Streamlit hoặc chỉ đơn giản là vẽ chart bằng Matplotlib) để so sánh Latency vs Accuracy của Day 08 và Day 09. Dựa trên dữ liệu từ câu **gq09** (multi-hop P1), hệ thống đa agent mất thêm 3 giây nhưng độ bao phủ thông tin tốt hơn hẳn; một biểu đồ "Cost per Quality" sẽ chứng minh được giá trị kinh tế của việc refactor sang Multi-agent mà báo cáo chữ chưa lột tả hết được.

---
*Lưu file này tại: `reports/individual/do_minh_khiem.md`*
