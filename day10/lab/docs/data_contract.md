# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/raw/policy_export_dirty.csv` — Export DB nội bộ (policy_refund_v4, sla_p1_2026) | Batch CSV export từ hệ thống quản lý chính sách, lên lịch mỗi 24h | **Stale window bug**: chunk `policy_refund_v4` chứa cửa sổ 14 ngày (lệch v4 = 7 ngày) do migration nhầm từ v3; chunk rỗng (`chunk_text` empty); ngày `effective_date` dưới dạng DD/MM/YYYY thay vì ISO-8601 | `no_stale_refund_window` (severity=halt) → pipeline dừng; `row_quarantine_rate > 30%` → alert Slack #data-ops; freshness SLA 24h |
| `data/docs/hr_leave_policy.txt` — Tài liệu HR policy (hr_leave_policy) | Ingest thủ công từ file text nội bộ, được đưa vào CSV export qua script sync | **Version conflict**: tồn tại đồng thời bản HR 2025 (10 ngày phép) và HR 2026 (12 ngày phép) trong cùng một export; effective_date < 2026-01-01 bị giữ lại nhầm | `duplicate_chunk_text` trên cùng `doc_id` (severity=warn); `hr_leave_min_effective_date` check: mọi chunk `hr_leave_policy` phải có `effective_date >= 2026-01-01`; bản cũ bị quarantine |
| `data/docs/it_helpdesk_faq.txt` — IT Helpdesk FAQ (it_helpdesk_faq) | Ingest thủ công từ file text, xuất qua batch export | **Định dạng ngày sai**: `effective_date` = `01/02/2026` (DD/MM/YYYY) thay vì `2026-02-01`; dẫn đến parse error khi validate schema | `date_format_error_count` — số bản ghi có `effective_date` không hợp lệ; bản lỗi bị quarantine; alert nếu `date_format_error_count > 0` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID ổn định sau clean — thường là số thứ tự hoặc hash dạng `doc_id + seq`; dùng làm primary key khi upsert vào ChromaDB |
| doc_id | string | Có | Khóa logic tài liệu nguồn (vd `policy_refund_v4`, `hr_leave_policy`); phải nằm trong `allowed_doc_ids` của `data_contract.yaml` — nếu không → quarantine |
| chunk_text | string | Có | Nội dung văn bản của chunk sau clean; tối thiểu 8 ký tự (expectation `chunk_min_length_8`, severity=warn); chunk rỗng hoặc quá ngắn → quarantine |
| effective_date | date (ISO-8601 `YYYY-MM-DD`) | Có | Ngày hiệu lực của tài liệu nguồn; phải đúng format ISO-8601 sau clean (expectation `effective_date_iso_yyyy_mm_dd`, severity=halt); bản ghi sai format (vd `01/02/2026`) → quarantine trước khi clean |
| exported_at | datetime (ISO-8601) | Có | Timestamp lúc record được export từ hệ thống nguồn; dùng để tính freshness SLA (mặc định 24h); giá trị `max(exported_at)` trong cleaned run được ghi vào manifest |

---

## 3. Quy tắc quarantine vs drop

| Điều kiện | Hành động | Nơi lưu | Người approve merge lại |
|-----------|-----------|---------|------------------------|
| `chunk_text` rỗng hoặc quá ngắn (< 8 ký tự) | Quarantine (không drop hẳn) | `artifacts/quarantine/quarantine_<run_id>.csv` | Data Owner (nhóm Data Ops) review thủ công |
| `doc_id` không nằm trong `allowed_doc_ids` (vd `legacy_catalog_xyz_zzz`) | Quarantine | `artifacts/quarantine/quarantine_<run_id>.csv` | Cần có yêu cầu chính thức mở rộng allowlist trong `data_contract.yaml` |
| `chunk_text` chứa cửa sổ refund 14 ngày (stale) và `apply_refund_window_fix=True` | Tự động fix → cleaned | `artifacts/cleaned/` | Không cần — rule xác định rõ trong `cleaning_rules.py` |
| `effective_date` không parse được (sai format) | Quarantine | `artifacts/quarantine/quarantine_<run_id>.csv` | Data Engineer kiểm tra nguồn, fix format rồi re-ingest |
| Duplicate `chunk_text` trong cùng `doc_id` | Warn (không quarantine) — expectation `no_duplicate_chunk_text` severity=warn | Log warning trong `artifacts/logs/` | Không bắt buộc approve; team tự review |

---

## 4. Phiên bản & canonical

- **Source of truth cho policy refund**: `data/docs/policy_refund_v4.txt` — cửa sổ hoàn tiền **7 ngày làm việc** (version 4, `effective_date=2026-02-01`). Mọi chunk trong `policy_refund_v4` chứa "14 ngày" đều bị coi là lỗi migration từ v3 và phải được fix/quarantine.
- **Source of truth cho HR leave policy**: `data/docs/hr_leave_policy.txt` bản `effective_date >= 2026-01-01` (12 ngày phép). Bản 2025 (10 ngày phép) là outdated và bị quarantine.
- **Versioning**: `policy_versioning.hr_leave_min_effective_date = "2026-01-01"` được định nghĩa trong `contracts/data_contract.yaml` — không hard-code trong code.
- **Canonical doc_id list**: xem `allowed_doc_ids` trong `contracts/data_contract.yaml`. Thêm nguồn mới phải cập nhật đồng thời `cleaning_rules.py` và contract này.
