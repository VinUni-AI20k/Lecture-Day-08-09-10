# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/raw/policy_export_dirty.csv` (raw export DB policy) | Batch CSV theo từng lần export | Duplicate chunk, thiếu `effective_date`, `doc_id` ngoài allowlist, format ngày không ISO | `raw_records`, `cleaned_records`, `quarantine_records`, tỉ lệ `quarantine_records/raw_records` > 20% thì WARN |
| `data/docs/policy_refund_v4.txt` (canonical refund policy) | File snapshot từ policy repo, đồng bộ theo release | Raw export còn chunk stale (14 ngày) dù canonical là 7 ngày | Expectation `no_stale_refund_window` mức `halt`; `hits_forbidden` trong eval phải bằng 0 |
| `data/docs/hr_leave_policy.txt` (canonical HR leave policy) | File snapshot theo version policy năm | Conflict version 2025 (10 ngày phép) vs 2026 (12 ngày phép) trong cùng lần export | Rule quarantine bản cũ theo `effective_date`; số bản HR cũ bị quarantine theo run |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | … |
| doc_id | string | Có | … |
| chunk_text | string | Có | … |
| effective_date | date | Có | … |
| exported_at | datetime | Có | … |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

- Record vi phạm contract hoặc cần review sẽ vào `artifacts/quarantine/quarantine_<run_id>.csv`.
- Record rỗng `chunk_text` hoặc lỗi parse không thể cứu sẽ bị drop (không publish).
- Quy trình merge lại: Cleaning/Quality owner review quarantine, fix dữ liệu nguồn hoặc override rule, sau đó chạy lại pipeline với run mới.

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?

- Canonical refund: `data/docs/policy_refund_v4.txt` (window hợp lệ: 7 ngày làm việc).
- Canonical HR leave: `data/docs/hr_leave_policy.txt` với cutoff hiệu lực từ 2026-01-01.
- Bất kỳ chunk raw nào trái canonical không được publish vào vector store ở run chuẩn.
