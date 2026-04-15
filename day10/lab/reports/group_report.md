# Báo cáo nhóm - Lab Day 10

**Tên nhóm:** Team Day10-CS-IT  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|---|---|---|
| Nam | Ingestion Owner | nam@example.com |
| Cao | Cleaning / Quality Owner | cao@example.com |
| Tuấn | Embed Owner | tuan@example.com |
| Ly | Monitoring / Docs Owner | ly@example.com |

**Ngày nộp:** 2026-04-15  
**Repo:** `day10/lab`

## 1. Pipeline tổng quan

Nhóm triển khai pipeline một lệnh từ ingest đến publish: đọc raw CSV, áp dụng cleaning rules, chạy expectation suite, rồi upsert vào Chroma theo `chunk_id`. Mỗi run tạo đầy đủ log, quarantine CSV, cleaned CSV và manifest để quan sát chất lượng dữ liệu theo run boundary. Run chính nộp bài là `sprint4-final`; run inject để chứng minh suy giảm chất lượng là `sprint3-inject`.

Lệnh chạy chuẩn:

`python etl_pipeline.py run --run-id sprint4-final`

Trong log có các key bắt buộc: `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`, các dòng `expectation[...]`, `embed_upsert`, `manifest_written`, `freshness_ingest`, `freshness_publish`.

## 2. Cleaning & expectation

Nhóm giữ baseline và bổ sung rule/expectation có tác động đo được.

### 2a. metric_impact (anti-trivial)

| Rule / Expectation mới | Trước (inject) | Sau (clean) | Chứng cứ |
|---|---|---|---|
| `topic_keyword_mismatch` (rule) | 1 row quarantine | 0 row quarantine | `artifacts/quarantine/quarantine_sprint3-inject.csv` |
| `invalid_exported_at_format` (rule) | 1 row quarantine | 0 row quarantine | `artifacts/quarantine/quarantine_sprint3-inject.csv` |
| `effective_date_after_exported_at` (rule) | 1 row quarantine | 0 row quarantine | `artifacts/quarantine/quarantine_sprint3-inject.csv` |
| `exported_at_iso_utc` (expectation halt) | pass sau clean; inject sinh `WARN` boundary ingest do ts lỗi | pass ở run sạch | `artifacts/logs/run_sprint3-inject.log`, `manifest_sprint3-inject.json` |
| `effective_not_after_exported` (expectation halt) | dữ liệu vi phạm bị quarantine từ inject | pass ở run sạch | `quarantine_sprint3-inject.csv`, `run_sprint4-final.log` |

Expectation fail có chủ đích:
- `expectation[refund_no_stale_14d_window] FAIL (halt)` xuất hiện ở `run_sprint3-inject.log` khi dùng `--no-refund-fix --skip-validate`.

## 3. Before / after retrieval ảnh hưởng agent

Kịch bản inject:
- Raw file `data/raw/policy_export_inject.csv` chứa off-topic row, timestamp sai format, effective_date vượt exported_at và dòng policy refund 14 ngày.
- Chạy:  
`python etl_pipeline.py run --run-id sprint3-inject --raw data/raw/policy_export_inject.csv --no-refund-fix --skip-validate`

Kết quả định lượng:
- `after_inject_bad.csv`: `q_refund_window` có `hits_forbidden=yes`; `q_leave_version` có `contains_expected=no` và `top1_doc_expected=no`.
- `before_after_eval.csv` (state clean): cả 4 câu đều `contains_expected=yes`, `hits_forbidden=no`; riêng `q_leave_version` có `top1_doc_expected=yes`.

Điều này cho thấy dữ liệu bẩn làm retrieval suy giảm rõ ràng và pipeline clean + validate khôi phục chất lượng.

## 4. Freshness & monitoring

Nhóm áp dụng monitor 2 boundary:
- `freshness_ingest` dùng `latest_raw_exported_at`
- `freshness_publish` dùng `latest_cleaned_exported_at`

Trên sample dataset, cả hai đều `FAIL` vì timestamp nguồn (2026-04-10) cũ hơn SLA 24h tại thời điểm run. Đây là hành vi đúng cho bài lab vì mô phỏng stale upstream snapshot, được ghi rõ trong runbook.

## 5. Liên hệ Day 09

Sau embed, collection `day10_kb` trở thành nguồn retrieval đã qua clean/validate cho flow Day 09. Nhóm tách collection khỏi Day 09 mặc định để tránh lẫn vector cũ trong giai đoạn demo inject, đồng thời vẫn dùng chung Chroma path để dễ tích hợp khi chuyển sang run sạch.

## 6. Rủi ro còn lại & việc chưa làm

- Chưa thêm GE/pydantic validator ngoài expectation hiện tại.
- Chưa tăng bộ eval lên >4 câu theo từng slice lỗi.
- Freshness hiện chỉ dựa trên timestamp trong manifest, chưa lấy watermark trực tiếp từ DB/API.
