# Data contract - Lab Day 10

Tài liệu này phản chiếu `contracts/data_contract.yaml` và cách nhóm áp dụng trong code.

## 1. Source map

| Nguồn | Ingest | Failure mode chính | Metric / alert |
|---|---|---|---|
| `data/raw/policy_export_dirty.csv` | Batch CSV read (`load_raw_csv`) | duplicate, missing date, legacy doc_id | `raw_records`, `quarantine_records` |
| `data/raw/policy_export_inject.csv` | Inject test cho Sprint 3 | invalid `exported_at`, off-topic chunk, future effective date | expectation fail + reason breakdown |
| `data/docs/*.txt` (canonical) | Mapping doc_id trong contract | content drift giữa export và canonical | retrieval eval (`hits_forbidden`) |

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `chunk_id` | string | Có | Hash ổn định phục vụ upsert |
| `doc_id` | string | Có | Thuộc allowlist contract |
| `chunk_text` | string | Có | min length >= 8 |
| `effective_date` | date | Có | Chuẩn hoá `YYYY-MM-DD` |
| `exported_at` | datetime UTC | Có | Chuẩn hoá `YYYY-MM-DDTHH:MM:SSZ` |

## 3. Quarantine vs drop

- Mọi bản ghi vi phạm rule không bị xóa im lặng, mà được chuyển vào `artifacts/quarantine/*.csv` với cột `reason`.
- Các `reason` chính đã dùng: `duplicate_chunk_text`, `missing_effective_date`, `stale_hr_policy_effective_date`, `unknown_doc_id`, `topic_keyword_mismatch`, `invalid_exported_at_format`, `effective_date_after_exported_at`, `missing_chunk_text`.
- Chỉ cleaned dataset mới được publish vào vector store.

## 4. Versioning và canonical

- HR cutoff không hard-code trong code: lấy từ `policy_versioning.hr_leave_min_effective_date` (có thể override env `HR_LEAVE_MIN_EFFECTIVE_DATE`).
- Refund window không hard-code: lấy từ `policy_versioning.refund_window_days` (có thể override env `REFUND_WINDOW_DAYS`).
- Topic guard theo `doc_topic_keywords` trong contract để bắt off-topic rows khi ingest.

## 5. Owner và SLA

- Owner team: `day10-data-platform`.
- Alert channel: `#day10-data-observability`.
- Freshness check chạy 2 boundary:
  - `latest_raw_exported_at` (ingest boundary)
  - `latest_cleaned_exported_at` (publish boundary)
