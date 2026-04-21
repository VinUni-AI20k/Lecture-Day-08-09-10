# Data contract — Lab Day 10

> Synced with `contracts/data_contract.yaml`.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|---|---|---|---|
| CSV export từ DB (`data/raw/policy_export_dirty.csv`) | Batch CSV load — `load_raw_csv()` trong `transform/cleaning_rules.py` | Schema drift (cột đổi tên / thiếu cột), encoding lỗi, `effective_date` sai định dạng | `quarantine_records > 0`; `raw_records = 0` nếu file không tồn tại; `invalid_effective_date_format` trong quarantine CSV |
| Policy docs TXT/PDF (`data/docs/*.txt`) | Direct file read (Day 08 `index.py`) | OCR noise tạo ký tự rác, chunk rỗng sau parse, BOM prefix | `chunk_text_too_short_after_strip` quarantine spike; `missing_chunk_text` trong quarantine |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `chunk_id` | string | Có | Hash xác định theo công thức hiện tại: `sha256(doc_id\|chunk_text\|seq)[:16]`. Giá trị chỉ ổn định khi thứ tự ingest / kết quả quarantine không đổi; nếu `seq` dịch chuyển giữa các lần chạy thì `chunk_id` cũng sẽ đổi. |
| `doc_id` | string | Có | Phải thuộc `ALLOWED_DOC_IDS` trong `cleaning_rules.py` và `contracts/data_contract.yaml` |
| `chunk_text` | string | Có | Tối thiểu 8 ký tự (warn), tối đa 2000 ký tự (warn E7) |
| `effective_date` | date (YYYY-MM-DD) | Có | Chuẩn hoá từ DD/MM/YYYY hoặc YYYY/MM/DD; rỗng hoặc không parse được → quarantine |
| `exported_at` | datetime (ISO 8601) | Có | Dùng bởi `freshness_check.py` để tính `age_hours` so với SLA |

---

## 3. Quy tắc quarantine vs drop

Mọi row bị loại đều ghi vào `artifacts/quarantine/quarantine_<run_id>.csv` kèm cột `reason`. Không có silent drop.

| Reason | Hành động | Ai review |
|---|---|---|
| `unknown_doc_id` | Quarantine — export catalog sai, không embed | Data Eng kiểm tra nguồn |
| `missing_effective_date` | Quarantine — không embed cho đến khi SME điền ngày | AI Eng / SME |
| `invalid_effective_date_format` | Quarantine — parser không nhận ra format | Data Eng sửa parser hoặc nguồn |
| `stale_hr_policy_effective_date` | Quarantine — bản HR cũ trước 2026-01-01 | AI Eng xác nhận version mới |
| `missing_chunk_text` | Quarantine — không có nội dung để embed | Data Eng kiểm tra nguồn |
| `chunk_text_too_short_after_strip` | Quarantine — nội dung quá ngắn (< 8 ký tự) sau khi strip BOM/control chars; bắt stub rows như "N/A", "---" hoặc nội dung bị collapse | Data Eng kiểm tra nguồn / OCR output |
| `duplicate_chunk_text` | Quarantine — giữ bản đầu, loại bản trùng | Tự động, không cần review |

Row trong quarantine **không** được embed. Để re-ingest, sửa nguồn và chạy lại `etl_pipeline.py run` với `run_id` mới.

---

## 4. Phiên bản & canonical

| doc_id | Canonical source | Version hiện hành | Ghi chú |
|---|---|---|---|
| `policy_refund_v4` | `data/docs/policy_refund_v4.txt` | v4 | Cửa sổ hoàn tiền = **7 ngày** làm việc; bản cũ v3 ghi 14 ngày — Rule 6 fix khi ingest |
| `sla_p1_2026` | `data/docs/sla_p1_2026.txt` | 2026 | P1 SLA phản hồi đầu = 15 phút |
| `it_helpdesk_faq` | `data/docs/it_helpdesk_faq.txt` | — | Tài khoản khóa sau 5 lần sai |
| `hr_leave_policy` | `data/docs/hr_leave_policy.txt` | 2026 | Phép năm = **12 ngày** (< 3 năm KN); bản 2025 ghi 10 ngày — quarantine bởi Rule 3 |
