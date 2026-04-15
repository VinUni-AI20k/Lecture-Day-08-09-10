# Data contract — Lab Day 10

> Đồng bộ với `contracts/data_contract.yaml`. Mọi thay đổi schema hay SLA cần cập nhật cả 2 file.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Policy DB export (System A) | CSV batch hàng ngày (`data/raw/policy_export_dirty.csv`) | Duplicate chunk_text; ngày hiệu lực sai format (dd/MM/yyyy); doc_id catalog cũ; chunk "lỗi migration" | `quarantine_records` > 0 → alert `#data-quality` |
| HR system sync (System B) | CSV batch (chèn vào export chung) | Bản HR cũ (effective_date < 2026-01-01) conflict với bản 12 ngày phép | expectation `hr_leave_no_stale_10d_annual` FAIL → halt |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | SHA-256 16 ký tự của `doc_id\|chunk_text\|seq`; ổn định theo nội dung |
| doc_id | string | Có | Phải thuộc `ALLOWED_DOC_IDS`; map sang file canonical |
| chunk_text | string | Có | Sau collapse whitespace; không rỗng; không chứa "lỗi migration" |
| effective_date | date (YYYY-MM-DD) | Có | Normalize từ dd/MM/yyyy; HR ≥ 2026-01-01; SLA ≥ 2026-01-01 |
| exported_at | datetime (ISO) | Có | Dùng cho freshness SLA — do source system ghi |

---

## 3. Quy tắc quarantine vs drop

Record bị **quarantine** (không drop vĩnh viễn) vào `artifacts/quarantine/quarantine_<run_id>.csv` kèm cột `reason`:

| Reason | Ý nghĩa | Ai approve merge lại |
|--------|---------|----------------------|
| `unknown_doc_id` | doc_id ngoài allowlist | Cleaning Owner sau khi xác nhận catalog |
| `missing_effective_date` | effective_date rỗng | Source system owner |
| `invalid_effective_date_format` | format không parse được | Source system owner |
| `stale_hr_policy_effective_date` | HR chunk trước 2026-01-01 | HR system owner |
| `stale_sla_effective_date` | SLA chunk trước 2026-01-01 | SLA owner |
| `missing_chunk_text` | chunk_text rỗng | Source DB admin |
| `migration_error_marker_detected` | chunk chứa "lỗi migration" | Pipeline engineer |
| `duplicate_chunk_text` | nội dung trùng bản trước | Tự động — không cần approve |

**Drop vĩnh viễn** không được dùng — quarantine file là audit trail.

---

## 4. Phiên bản & canonical

| doc_id | Canonical source | Version hiện hành | SLA freshness |
|--------|-----------------|-------------------|---------------|
| `policy_refund_v4` | `data/docs/policy_refund_v4.txt` | v4 (cửa sổ 7 ngày) | 24h |
| `sla_p1_2026` | `data/docs/sla_p1_2026.txt` | 2026 (P1 = 15 phút) | 24h |
| `it_helpdesk_faq` | `data/docs/it_helpdesk_faq.txt` | 2026-02-01 | 24h |
| `hr_leave_policy` | `data/docs/hr_leave_policy.txt` | 2026 (12 ngày phép) | 24h |

Source of truth cho **policy refund**: `data/docs/policy_refund_v4.txt` — v4 quy định 7 ngày làm việc. Bất kỳ chunk nào chứa "14 ngày làm việc" là bản v3 lỗi migration → phải bị quarantine.
