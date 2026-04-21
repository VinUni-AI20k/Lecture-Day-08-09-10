# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Tiến Huy Hoàng  
**Vai trò trong nhóm:** Trace & Docs Owner  
**Ngày nộp:** 2026-04-14  
**Độ dài:** ~620 từ

---

## 1. Tôi phụ trách phần nào?

Trong Day 09, tôi phụ trách phần trace/evaluation và hệ thống tài liệu nộp bài. Trọng tâm của tôi là đảm bảo pipeline có dữ liệu quan sát được, có thể kiểm chứng theo rubric, và docs phản ánh đúng trạng thái code chạy thật. Các file tôi trực tiếp làm gồm `eval_trace.py` (luồng chạy test/grading và phân tích trace), `docs/system_architecture.md`, `docs/routing_decisions.md`, `docs/single_vs_multi_comparison.md`, và `reports/group_report.md`.

Ở `eval_trace.py`, tôi tập trung vào tính ổn định khi chạy batch (ghi JSONL, tránh crash, có thông tin route/confidence/latency). Ở docs/report, tôi chịu trách nhiệm chuyển dữ liệu trace thành nội dung có bằng chứng, bám đúng rubric trong `SCORING.md`. Công việc của tôi kết nối trực tiếp với Supervisor/Worker Owner: nếu routing và answer đã chạy nhưng trace hoặc docs không nhất quán thì nhóm vẫn mất điểm.

**Bằng chứng:**
- File liên quan: `eval_trace.py`, `docs/*.md`, `reports/group_report.md`
- Trace/evidence: `artifacts/grading_run.jsonl`, `artifacts/day09_scoring.json`, `artifacts/eval_report.json`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

Quyết định kỹ thuật quan trọng nhất của tôi là chọn chuẩn hóa toàn bộ đánh giá dựa trên **trace-first workflow**: mọi claim trong docs/report phải truy ngược được về trace hoặc file scoring, thay vì viết theo cảm tính. Tôi cân nhắc hai cách:

1. Viết docs theo mô tả high-level, cập nhật thủ công theo trí nhớ.
2. Dựa trace làm nguồn sự thật (source of truth), rồi map ngược về tài liệu.

Tôi chọn cách 2 vì Day09 chấm rất nặng phần evidence. Cách này giúp giảm mâu thuẫn giữa code và report, đặc biệt ở phần route decision, tool usage, và grading summary. Khi có thay đổi trong pipeline, tôi chỉ cần chạy lại `eval_trace.py --grading` và đối chiếu file output để cập nhật docs/report nhất quán.

Trade-off là mất thêm thời gian ở khâu tổng hợp và kiểm tra chéo, nhưng đổi lại tính audit tốt hơn: giảng viên có thể mở đúng file trace/scoring để xác minh từng nhận định.

**Bằng chứng từ trace/code:**
- `artifacts/grading_run.jsonl` có đủ các field bắt buộc: `supervisor_route`, `route_reason`, `workers_called`, `mcp_tools_used`, `confidence`.
- `artifacts/day09_scoring.json` cho số liệu chấm cuối: `raw_total=92/96`, `group_score_30=28.75`.
- `reports/group_report.md` đã tham chiếu trực tiếp hai file trên trong mục kết quả grading.

---

## 3. Tôi đã sửa một lỗi gì?

Lỗi tôi xử lý là dữ liệu báo cáo nhóm bị lệch trạng thái thực tế sau nhiều vòng chạy grading. Cụ thể, có thời điểm report vẫn giữ nội dung cũ (điểm cũ, nhận định cũ) dù trace/scoring đã đổi. Đây là lỗi nguy hiểm vì có thể bị đánh giá là claim không khớp evidence.

**Symptom:**
- Report có số liệu không đồng bộ với file chấm mới.
- Một số câu mô tả chưa phản ánh đúng kết quả run mới nhất.

**Root cause:**
- Quy trình cập nhật docs/report chưa khóa nguồn dữ liệu chuẩn.
- Chưa có bước “đối chiếu cuối” giữa `grading_run.jsonl`, `day09_scoring.json`, và report.

**Cách sửa:**
- Chốt quy ước: chỉ lấy số cuối từ file scoring Day09.
- Cập nhật report theo evidence mới nhất và bổ sung đường dẫn file chứng minh.
- Rà soát checklist trước nộp để tránh câu chữ không khớp trạng thái code/trace.

**Before/after evidence:**
- Trước: report có nguy cơ mismatch sau các lần rerun.
- Sau: `reports/group_report.md` đồng bộ với `artifacts/day09_scoring.json` và `artifacts/grading_run.jsonl`.

Tôi coi đây là bug fix thuộc lớp “process quality”: không đổi thuật toán, nhưng giảm rủi ro mất điểm do thiếu nhất quán giữa thực thi và tài liệu.

---

## 4. Tôi tự đánh giá đóng góp của mình

Điểm tôi làm tốt nhất là giữ được kỷ luật evidence: mọi phần trong docs/report đều truy được về file trace hoặc scoring cụ thể. Tôi cũng làm tốt ở việc tổng hợp dữ liệu kỹ thuật thành nội dung dễ chấm, giúp nhóm tiết kiệm thời gian ở giai đoạn hoàn thiện báo cáo.

Điểm tôi chưa tốt là chưa tự động hóa hoàn toàn khâu “sync report từ artifact”, nên vẫn cần kiểm tra tay trước khi chốt nộp. Nếu có nhiều vòng thay đổi liên tiếp, việc cập nhật thủ công vẫn dễ sót.

Nhóm phụ thuộc vào tôi ở phần đóng gói đầu ra nộp bài: dù code chạy tốt, nếu docs/report không bám trace thì rủi ro mất điểm cao. Ngược lại, tôi phụ thuộc vào Supervisor/Worker/MCP Owner để có output kỹ thuật ổn định trước khi tôi tổng hợp.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Nếu có thêm 2 giờ, tôi sẽ viết một script nhỏ tự động sinh bảng “trace-to-report” từ `grading_run.jsonl` + `day09_scoring.json` (route distribution, câu full/partial, raw/96, quy đổi /30). Mục tiêu là giảm thao tác tay khi cập nhật report và loại bỏ hoàn toàn rủi ro lệch số liệu giữa artifacts và tài liệu nộp.

