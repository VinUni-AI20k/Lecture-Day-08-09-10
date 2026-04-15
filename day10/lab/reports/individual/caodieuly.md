# Báo cáo cá nhân - Ly

**Họ và tên:** Cao Diệu Ly  
**Vai trò:** Monitoring / Docs Owner  
**Ngày nộp:** 2026-04-15

## 1. Tôi phụ trách phần nào?

Tôi phụ trách lớp monitoring và tài liệu vận hành: `monitoring/freshness_check.py`, `docs/runbook.md`, `docs/pipeline_architecture.md`, `docs/data_contract.md`, `docs/quality_report.md`, và tổng hợp `reports/group_report.md`.

Tôi làm việc với Nam để chuẩn hóa các trường manifest phục vụ quan sát theo boundary, làm việc với Cao để diễn giải các reason quarantine/expectation theo ngôn ngữ vận hành, và làm việc với Tuấn để đưa chỉ số retrieval vào quality evidence.

Mục tiêu của tôi là bảo đảm khi giảng viên đọc report có thể lần theo toàn bộ chuỗi bằng chứng từ log -> manifest -> quarantine -> eval mà không cần đoán.

## 2. Một quyết định kỹ thuật

Tôi chọn monitor freshness theo hai boundary thay vì một điểm:
- `ingest` từ `latest_raw_exported_at`
- `publish` từ `latest_cleaned_exported_at`

Lý do: một boundary duy nhất không đủ để phân biệt lỗi upstream data stale và lỗi publish trễ. Với hai boundary, ta biết vấn đề ở nguồn hay ở pipeline.  
Trong code, tôi dùng `timestamp_field` trong `check_manifest_freshness()` để kiểm tra từng field rõ ràng, và ghi log riêng `freshness_ingest`, `freshness_publish`.

Đây cũng là điểm cộng Distinction theo rubric (freshness đo 2 boundary có bằng chứng log).

## 3. Một lỗi/anomaly đã xử lý

Anomaly tôi theo dõi là inject timestamp sai format (`2026/04/10 08:00:00`), khiến boundary ingest không parse được.  
Kỳ vọng là không trả `PASS/FAIL` giả mà phải trả `WARN` với reason cụ thể.  
Kết quả thực tế:
- `manifest_sprint3-inject.json` giữ nguyên timestamp inject.
- Log có `freshness_ingest=WARN {"reason":"no_timestamp_in_manifest","field":"latest_raw_exported_at"}`.

Điều này quan trọng vì team có thể phân biệt:
- lỗi stale thật (`FAIL` do quá SLA),
- lỗi dữ liệu timestamp malformed (`WARN` cần sửa format trước).

## 4. Bằng chứng trước/sau

Run inject `sprint3-inject`:
- `freshness_publish=FAIL` (dữ liệu cũ hơn SLA),
- `freshness_ingest=WARN` (timestamp malformed),
- eval xấu ở `after_inject_bad.csv`.

Run clean `sprint4-final`:
- `freshness_ingest=FAIL`, `freshness_publish=FAIL` nhất quán với snapshot lab cũ,
- eval sạch ở `before_after_eval.csv`,
- grading pass đủ 3 câu ở `grading_run.jsonl`.

Từ góc nhìn monitoring, trạng thái hiện tại "pipeline khỏe nhưng nguồn stale" được diễn giải rõ và nhất quán giữa runbook, quality report và manifest.

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ thêm một bảng timeline trong report tự động trích từ nhiều manifest gần nhất để so sánh trend freshness theo thời gian (age_hours theo run). Điều này giúp phát hiện drift của upstream mà không cần đọc từng file JSON thủ công.