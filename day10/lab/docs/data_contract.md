# Data contract — Lab Day 10

**Nhóm:** C401-Y3  
**Cập nhật:** 2026-04-15  
**Đồng bộ từ:** `contracts/data_contract.yaml` (version 1.0)

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Policy/SLA DB | CSV export qua batch script | Stale policy version (14 vs 7 ngày refund); sai format date | `refund_no_stale_14d_window` (halt); `effective_date_iso_yyyy_mm_dd` (halt) |
| HR System | CSV export qua batch script | Policy version conflict (10 vs 12 ngày phép); xung đột effective_date | `hr_leave_no_stale_10d_annual` (halt); quarantine nếu `effective_date < 2026-01-01` |
| Helpdesk KB | CSV export (sporadic updates) | Missing chunk_text; unknown doc_id; chunk quá dài | `chunk_min_length_8` (warn); `all_doc_ids_in_allowlist` (halt); Rule C max 800 chars |
| Tất cả nguồn | CSV batch | Thiếu `exported_at` (không truy vết freshness) | `exported_at_not_empty` (halt); Rule B quarantine |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ràng buộc | Ghi chú |
|-----|------|----------|-----------|---------|
| `chunk_id` | string | Có | SHA-256 stable | Dùng để upsert và prune vector store; ổn định qua nhiều run |
| `doc_id` | string | Có | Thuộc allowlist | 4 doc_id hợp lệ: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy` |
| `chunk_text` | string | Có | ≥ 8 chars, ≤ 800 chars | Chuẩn hoá, đã fix stale refund window và loại migration marker |
| `effective_date` | date | Có | Định dạng `YYYY-MM-DD` | Non-ISO (vd `01/02/2026`) được chuẩn hoá; không parse được → quarantine |
| `exported_at` | datetime | Có | ISO datetime | Timestamp xuất bản raw; dùng để tính `latest_exported_at` và freshness SLA |

---

## 3. Quy tắc quarantine

| Reason | Mô tả | Severity |
|--------|-------|----------|
| `unknown_doc_id` | `doc_id` không thuộc allowlist — export lạ hoặc catalog chưa cập nhật | halt-equivalent (quarantine) |
| `missing_or_invalid_exported_at` | Thiếu hoặc sai định dạng `exported_at` — không thể truy vết freshness | halt-equivalent |
| `missing_effective_date` | `effective_date` rỗng | halt-equivalent |
| `invalid_effective_date_format` | Không parse được sang `YYYY-MM-DD` sau khi thử `DD/MM/YYYY` | halt-equivalent |
| `stale_hr_policy_effective_date` | HR leave policy với `effective_date < 2026-01-01` (bản 2025 cũ) | halt-equivalent |
| `missing_chunk_text` | `chunk_text` rỗng sau strip | halt-equivalent |
| `chunk_text_too_long_N_chars` | `chunk_text` dài hơn 800 ký tự (splitter lỗi) — Rule C | halt-equivalent |
| `duplicate_chunk_text` | Nội dung chunk trùng lặp sau chuẩn hoá lowercase | warn-equivalent |
| `internal_migration_note` | Chunk chứa marker nội bộ: `(ghi chú:`, `[lỗi migration]`, `[draft]`, `[wip]` — Rule A | halt-equivalent |

> Quarantine lưu tại `artifacts/quarantine/quarantine_<run_id>.csv` để audit và approval.  
> Nếu cần publish lại, team data phải xác nhận source raw trước khi cập nhật rule hoặc allowlist.

---

## 4. Phiên bản & canonical

| Canonical path | `doc_id` | Source of truth |
|---------------|----------|-----------------|
| `data/docs/policy_refund_v4.txt` | `policy_refund_v4` | Cửa sổ hoàn tiền **7 ngày** làm việc (v4, không phải v3 14 ngày) |
| `data/docs/hr_leave_policy.txt` | `hr_leave_policy` | Chính sách nghỉ phép **2026**: 12 ngày; quarantine bản 2025 (10 ngày) |
| `data/docs/sla_p1_2026.txt` | `sla_p1_2026` | SLA P1: phản hồi 15 phút, resolution 4 giờ |
| `data/docs/it_helpdesk_faq.txt` | `it_helpdesk_faq` | FAQ Helpdesk: khóa tài khoản sau 5 lần sai, đổi mật khẩu portal |

---

## 5. Freshness SLA

| Trường đo | Giá trị | Ghi chú |
|----------|---------|---------|
| `measured_at` | `publish` | Đo tại thời điểm hoàn tất embed |
| `sla_hours` | 24 | Configurable qua env `FRESHNESS_SLA_HOURS` |
| `alert_channel` | `__TODO__` | Chưa có webhook thực — ghi log + manifest |

**Kết quả sprint2:** `freshness_check=FAIL` — `age_hours=117.4h` > SLA 24h.  
Raw export mẫu có `exported_at=2026-04-10T08:00:00`, cũ hơn 5 ngày tính từ lúc chạy.  
> Cần batch export mới từ source hoặc nâng SLA_HOURS cho môi trường dev/test.

---

## 6. Allowlist doc_id

```yaml
allowed_doc_ids:
  - policy_refund_v4
  - sla_p1_2026
  - it_helpdesk_faq
  - hr_leave_policy
```

Thêm doc mới → cập nhật đồng thời `ALLOWED_DOC_IDS` trong `transform/cleaning_rules.py`, `_ALLOWED` trong `quality/expectations.py`, và file YAML này.
