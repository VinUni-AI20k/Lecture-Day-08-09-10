# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Policy Management System (policy_refund_v4.txt) | CSV export daily | Sync lỗi từ v3 (14 ngày) thay vì v4 (7 ngày); duplicate export | `hits_forbidden` trong eval; `quarantine_records` tăng |
| SLA System (sla_p1_2026.txt) | CSV export daily | Thiếu timestamp; format ngày không chuẩn ISO | `expectation_fail_count`; `cleaned_records` giảm |
| IT Helpdesk (it_helpdesk_faq.txt) | CSV export daily | Format ngày DD/MM/YYYY thay vì ISO YYYY-MM-DD | `quarantine_records` (invalid_date_format) |
| HR System (hr_leave_policy.txt) | API weekly | Xung đột version 2025 (10 ngày) vs 2026 (12 ngày phép) | `quarantine_records` (stale_hr_policy) |
| Access Control (access_control_sop.txt) | CSV export daily | Thiếu metadata; chunk quá ngắn (<8 ký tự) | `expectation_fail` (min_length constraint) |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID ổn định sau clean (thường hash hoặc doc_id + seq). Dùng để upsert idempotent vào vector store. |
| doc_id | string | Có | Khóa logic tài liệu nguồn (vd: policy_refund_v4). Phải nằm trong `allowed_doc_ids`. |
| chunk_text | string | Có | Nội dung chunk. Constraint: min_length=8, không được rỗng hoặc chỉ khoảng trắng. |
| effective_date | date | Có | Ngày hiệu lực của policy/document. Format: ISO YYYY-MM-DD. Dùng để filter version cũ. |
| exported_at | datetime | Có | Timestamp export từ hệ nguồn. Format: ISO 8601. Dùng để tính freshness SLA. |

**Constraints bổ sung:**
- `chunk_text`: min_length=8, không chứa ký tự điều khiển
- `effective_date`: phải >= policy_versioning cutoff date cho từng loại doc
- `doc_id`: phải match regex `^[a-z_0-9]+$` và nằm trong allowlist

---

## 3. Quy tắc quarantine vs drop

### Quarantine (isolate - cần review)
Record bị flag sẽ được ghi vào `artifacts/quarantine/quarantine_<run-id>.csv` với lý do cụ thể:

| Lý do | Hành động | Approval workflow |
|-------|-----------|-------------------|
| `invalid_date_format` | Quarantine 30 ngày | Data Eng Lead review + fix upstream |
| `stale_hr_policy` | Quarantine | HR System sync check |
| `unknown_doc_id` | Quarantine | Cập nhật allowlist hoặc reject |
| `empty_chunk_text` | Quarantine | Kiểm tra export logic |
| `duplicate_chunk` | Quarantine (warn) | Dedupe hoặc merge |

### Drop (không lưu)
- Record có `chunk_id` null hoặc malformed
- Record vi phạm expectation severity="halt" sau khi đã quarantine

### Retention
- Quarantine files: 30 ngày
- Manifest files: 90 ngày
- Cleaned CSV: giữ lại cho audit trail

---

## 4. Phiên bản & canonical

### Source of Truth

| Document | Version hiện tại | File canonical | Effective từ |
|----------|------------------|----------------|--------------|
| Policy Refund | v4 (7 ngày) | `data/docs/policy_refund_v4.txt` | 2026-02-01 |
| SLA P1 | 2026 | `data/docs/sla_p1_2026.txt` | 2026-01-01 |
| IT Helpdesk FAQ | latest | `data/docs/it_helpdesk_faq.txt` | 2026-02-01 |
| HR Leave Policy | 2026 (12 ngày) | `data/docs/hr_leave_policy.txt` | 2026-01-01 |
| Access Control SOP | latest | `data/docs/access_control_sop.txt` | 2026-02-01 |

### Version Deprecation
- **Policy Refund v3** (14 ngày): DEPRECATED - không chấp nhận trong cleaned data
- **HR Leave 2025** (10 ngày): DEPRECATED - chỉ chấp nhận version 2026 (12 ngày)

### Versioning Strategy
- Cutoff date được định nghĩa trong `policy_versioning` section của data contract
- Pipeline tự động quarantine records có `effective_date` < cutoff
- Để tránh hard-code, có thể đọc cutoff từ environment variable (Merit/Distinction)

---

## 5. Quality Rules & Expectations

### Quality Rules (trong cleaning phase)
1. **no_duplicate_chunk_text** (warn): Phát hiện chunk_text trùng lặp
2. **no_stale_refund_window** (halt): Không chấp nhận cửa sổ 14 ngày
3. **no_empty_chunk_text** (halt): Chunk text không được rỗng
4. **valid_doc_id_allowlist** (halt): doc_id phải trong allowlist
5. **effective_date_iso_format** (halt): Ngày phải theo ISO format
6. **hr_policy_version_consistency** (warn): HR policy phải version 2026

### Expectations (validation phase)
- Schema compliance: tất cả required fields phải có
- Data type validation: date/datetime đúng format
- Business rules: refund window = 7 ngày, HR leave = 12 ngày
- Referential integrity: doc_id tồn tại trong canonical sources

---

## 6. Freshness SLA

- **Measured at**: publish (sau khi embed vào vector store)
- **SLA**: 24 giờ từ `exported_at` đến `run_timestamp`
- **Alert channel**: `slack://data-quality-alerts`
- **Recipients**: data-eng@company.com, kb-ops@company.com
- **Status**:
  - PASS: delta < 24h
  - WARN: 24h ≤ delta < 48h
  - FAIL: delta ≥ 48h

---

## 7. Lineage & Traceability

### Upstream
- Policy Management System (database, daily refresh)
- HR System (API, weekly refresh)

### Downstream
- RAG System (Day 08) - vector store consumer
- Multi-agent System (Day 09) - orchestration consumer

### Tracking
- Mỗi run có unique `run_id` (timestamp-based)
- Manifest file lưu metadata: raw_records, cleaned_records, quarantine_records
- Embed snapshot: vector store chỉ chứa chunks từ run gần nhất (prune old IDs)
