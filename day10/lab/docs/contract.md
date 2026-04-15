# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn| Phương thức ingest| Failure mode chính| Metric / alert|
| ----- | -------------| ---------| -----------|
| `data/docs/policy_refund_v4.txt`   | CSV export from DB (doc_id: policy_refund_v4) | `stale_refund_window` (14 ngày vs 7 ngày)         | % flagged; halt if not fixed        |
| `data/docs/sla_p1_2026.txt`        | CSV export (doc_id: sla_p1_2026)              | `duplicate_chunk_text` + `missing_effective_date` | Count dedup'd + quarantine count    |
| `data/docs/it_helpdesk_faq.txt`    | CSV export (doc_id: it_helpdesk_faq)          | `missing_chunk_text`                              | Count quarantined                   |
| `data/docs/hr_leave_policy.txt`    | CSV export (doc_id: hr_leave_policy)          | `stale_hr_policy_effective_date` (< 2026-01-01)   | Count old versions rejected         |
| `data/raw/policy_export_dirty.csv` | Raw CSV export                                | All of above (10 raw records)                     | 6 cleaned + 4 quarantine (Sprint 1) |

---

## 2. Schema cleaned

| Cột            | Kiểu     | Bắt buộc | Ghi chú                                                                            |
| -------------- | -------- | -------- | ---------------------------------------------------------------------------------- |
| chunk_id       | string   | Có       | SHA256 stable ID: `{doc_id}_{seq}_{hash[:16]}` — idempotent embedding              |
| doc_id         | string   | Có       | Allowlist: policy_refund_v4, sla_p1_2026, it_helpdesk_faq, hr_leave_policy         |
| chunk_text     | string   | Có       | Min 8 chars; may include cleanup annotations like `[cleaned: stale_refund_window]` |
| effective_date | date     | Có       | ISO YYYY-MM-DD; normalized from raw (DD/MM/YYYY or ISO)                            |
| exported_at    | datetime | Có       | ISO timestamp of export; audits freshness SLA                                      |

---

## 3. Quy tắc quarantine vs drop

| Reason                           | Action                                               | Chịu trách nhiệm | Approval        |
| -------------------------------- | ---------------------------------------------------- | ---------------- | --------------- |
| `unknown_doc_id`                 | Quarantine → review → add allowlist or delete        | Data team        | Catalog owner   |
| `invalid_effective_date_format`  | Quarantine → source re-export with corrected dates   | Source owner     | Data team QA    |
| `missing_effective_date`         | Quarantine → backfill or exclude from KB             | Data team        | PM              |
| `missing_chunk_text`             | Quarantine → delete from source export               | Source owner     | Data team       |
| `duplicate_chunk_text`           | Auto-dedup'd (keep first, quarantine rest)           | Pipeline         | N/A             |
| `stale_refund_window`            | Auto-fix if `apply_refund_window_fix=True` (default) | Pipeline (auto)  | Billing (audit) |
| `stale_hr_policy_effective_date` | Quarantine → re-publish HR policy v2026+             | HR team          | HR manager      |

**Sprint 1 Results**: 4 quarantine + 1 auto-fix = 5 anomalies / 10 records (50% clean)

---

## 4. Phiên bản & canonical

### Source of Truth (Canonical Documents)

- **policy_refund_v4** (v4, 2026-Q1)
  - File: `data/docs/policy_refund_v4.txt`
  - Policy: 7-day refund window (NOT 14 days from v3)
  - Effective: 2026-02-01+
  - Last sync: 2026-04-10

- **sla_p1_2026** (2026 baseline)
  - File: `data/docs/sla_p1_2026.txt`
  - Policy: P1 = 15 min response + 4h resolution
  - Effective: 2026-01-01+
  - Last sync: 2026-04-05

- **it_helpdesk_faq** (Evergreen)
  - File: `data/docs/it_helpdesk_faq.txt`
  - Status: Active in KB

- **hr_leave_policy** (2026 annual)
  - File: `data/docs/hr_leave_policy.txt`
  - Effective: 2026-01-01+ (reject older)
  - Last sync: 2026-03-15

### Freshness & Publish

- **Measured**: At publish (embed upsert to ChromaDB)
- **SLA**: 24 hours from export timestamp
- **Check**: `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint1.json`
- **Sprint 1**: ⚠️ FAIL (test data exported 2026-04-10, checked 2026-04-15 = 116h > SLA)
  - Expected for demo; production must be fresh

### Raw Input File

- **File**: `data/raw/policy_export_dirty.csv`
- **Format**: `chunk_id, doc_id, chunk_text, effective_date, exported_at`
- **Size**: 1.53 KB (10 rows)
- **Encoding**: UTF-8 (legacy migration artifacts)
- **Processing**: Normalize dates → dedup → validate → fix policy versions → embed to ChromaDB
