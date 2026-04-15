# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| **Policy Export CSV** | File-based batch export từ policy management system | • Duplicate records<br>• Missing exported_at<br>• Invalid effective_date format<br>• Stale version (HR 10 days vs 12 days) | • `quarantine_records` > threshold<br>• `freshness_check=FAIL`<br>• `expectation[hr_leave_no_stale_10d_annual] FAIL` |
| **Document Repository** | Manual upload / Git sync từ `data/docs/` | • Unknown doc_id (không trong allowlist)<br>• Empty chunk_text<br>• BOM characters (\ufeff) | • `quarantine_records` reason=unknown_doc_id<br>• `cleaning_bom_stripped` > 0<br>• `expectation[no_empty_doc_id] FAIL` |

**Allowlist doc_id:** `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Stable hash: `{doc_id}_{seq}_{sha256[:16]}` — đảm bảo idempotent upsert |
| doc_id | string | Có | Phải thuộc allowlist; dùng để route policy type |
| chunk_text | string | Có | Min 20 chars (rule 7); không chứa BOM; không duplicate |
| effective_date | date (YYYY-MM-DD) | Có | ISO format; HR policy phải >= 2026-01-01 |
| exported_at | datetime (ISO) | Có | Dùng cho freshness check; SLA 24h default |

**Validation rules:**
- `chunk_text`: >= 20 chars (warn), >= 8 chars (halt)
- `effective_date`: ISO YYYY-MM-DD format (halt)
- `exported_at`: không rỗng (warn)
- `doc_id`: trong allowlist (quarantine nếu không)

---

## 3. Quy tắc quarantine vs drop

**Quarantine reasons:**
- `unknown_doc_id`: doc_id không trong allowlist → cần review catalog
- `missing_effective_date` / `invalid_effective_date_format`: không parse được ngày
- `stale_hr_policy_effective_date`: HR policy < 2026-01-01 (conflict version)
- `missing_chunk_text`: text rỗng
- `short_chunk`: < 20 chars
- `missing_exported_at`: không có timestamp export
- `duplicate_chunk_text`: trùng nội dung (giữ bản đầu)

**Workflow:**
1. Record quarantine → ghi vào `artifacts/quarantine/quarantine_<run_id>.csv`
2. Data owner review reason
3. Nếu hợp lệ: fix nguồn + rerun pipeline
4. Nếu không hợp lệ: bỏ qua (không merge)

**Drop vs Quarantine:**
- Quarantine: có thể recover (vd: fix format ngày)
- Drop: không recover (vd: duplicate — chỉ giữ 1 bản)

---

## 4. Phiên bản & canonical

**Source of truth:**
- **Policy refund:** `data/docs/policy_refund_v4.txt` — version 4 (7 ngày làm việc)
  - Stale version: 14 ngày làm việc → fix bằng cleaning rule
  - Expectation: `refund_no_stale_14d_window` (halt)
  
- **HR leave policy:** `data/docs/hr_leave_policy.txt` — version 2026 (12 ngày phép năm)
  - Stale version: 10 ngày phép năm → quarantine nếu effective_date < 2026-01-01
  - Expectation: `hr_leave_no_stale_10d_annual` (halt)

**Version control:**
- `effective_date` dùng để phân biệt version
- Chỉ giữ version mới nhất trong cleaned (version cũ → quarantine)
- Nếu cần multi-version: thêm cột `version` vào schema

**Owner:**
- Policy refund: Product team
- HR leave: HR team
- SLA: Operations team
- IT helpdesk: IT support team
