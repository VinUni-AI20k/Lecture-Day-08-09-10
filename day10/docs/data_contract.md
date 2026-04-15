# Data Contract & Source Map — Sprint 1 Ingest

**Sprint**: 1 (Ingest & Schema)  
**Date**: 2026-04-15  
**Owner Team**: Lab Day 10 — AI2026  

---

## Overview

Describes the data contract for the KB chunk export pipeline. Maps 4 canonical document sources into cleaned chunks, with defined failure modes and quality metrics.

---

## Canonical Sources

### Source 1: Policy Refund v4
- **Path**: `data/docs/policy_refund_v4.txt`
- **Doc ID**: `policy_refund_v4`
- **Version Baseline**: v4 (2026-Q1)
- **Effective Date Range**: 2026-02-01 to present
- **Responsibility**: Billing & Refunds team
- **Freshness SLA**: 24 hours
- **Last Updated**: 2026-04-10

#### Failure Modes & Metrics:
| Failure Mode                    | Description                                                         | Metric            | Impact                                                                          |
| ------------------------------- | ------------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------- |
| `stale_refund_window`           | Legacy export contains "14 ngày làm việc" (should be 7 days per v4) | % of rows flagged | Halts pipeline if not fixed; corrected in Sprint 1 by `apply_refund_window_fix` |
| `invalid_effective_date_format` | Date not YYYY-MM-DD or DD/MM/YYYY                                   | Count quarantined | Affects SLA accuracy & reporting compliance                                     |
| `missing_chunk_text`            | Empty chunk_text field                                              | Count quarantined | Loss of policy content; user queries fail silently                              |

---

### Source 2: SLA P1 2026
- **Path**: `data/docs/sla_p1_2026.txt`
- **Doc ID**: `sla_p1_2026`
- **Version Baseline**: 2026 update
- **Effective Date Range**: 2026-01-01 to present
- **Responsibility**: IT Operations team
- **Freshness SLA**: 24 hours
- **Last Updated**: 2026-04-05

#### Failure Modes & Metrics:
| Failure Mode             | Description                                                     | Metric            | Impact                                                                 |
| ------------------------ | --------------------------------------------------------------- | ----------------- | ---------------------------------------------------------------------- |
| `duplicate_chunk_text`   | Same SLA text appears multiple times (format migration residue) | % of rows dedup'd | Inflates index size; wastes embedding budget; pollutes top-k retrieval |
| `missing_effective_date` | Chunk lacking effective_date field                              | Count quarantined | Cannot filter by date range; breaks temporal queries                   |
| `unknown_doc_id`         | Export includes id not in allowed_doc_ids allowlist             | Count rejected    | Indicates catalog drift or unauthorized source injection               |

---

## Additional Sources (Baseline)

### Source 3: IT Helpdesk FAQ
- **Path**: `data/docs/it_helpdesk_faq.txt`
- **Doc ID**: `it_helpdesk_faq`
- **Status**: Active in cleaned exports

### Source 4: HR Leave Policy
- **Path**: `data/docs/hr_leave_policy.txt`
- **Doc ID**: `hr_leave_policy`
- **Status**: Active in cleaned exports
- **Note**: Records with `effective_date < 2026-01-01` quarantined (prevents serving stale HR guidance)

---

## Schema (Cleaned Output)

| Field            | Type         | Required | Validation                 | Purpose                                                 |
| ---------------- | ------------ | -------- | -------------------------- | ------------------------------------------------------- |
| `chunk_id`       | string       | ✓        | Unique per run; hash-based | Stable idempotent ID for embeddings & dedup             |
| `doc_id`         | string       | ✓        | One of 4 allowed IDs       | Source document identifier                              |
| `chunk_text`     | string       | ✓        | Length ≥ 8 chars           | Content served to LLM (may include cleanup annotations) |
| `effective_date` | ISO date     | ✓        | YYYY-MM-DD                 | Temporal filtering; SLA & policy version binding        |
| `exported_at`    | ISO datetime | ✓        | YYYY-MM-DDTHH:MM:SSZ       | Export audit trail; freshness tracking                  |

---

## Quarantine Reason Codes

| Code                             | Count (Sprint 1) | Example Record                                 | Action                                                      | Owner        |
| -------------------------------- | ---------------- | ---------------------------------------------- | ----------------------------------------------------------- | ------------ |
| `unknown_doc_id`                 | **1**            | Row 9: `legacy_catalog_xyz_zzz`                | Investigate catalog drift; add to allowlist if authorized   | Data team    |
| `invalid_effective_date_format`  | 0                | —                                              | Re-export from source with corrected dates                  | Source owner |
| `missing_effective_date`         | **1**            | Row 5: `policy_refund_v4` (empty date)         | Manual backfill or exclude from KB                          | Data team    |
| `missing_chunk_text`             | 0                | —                                              | Delete malformed records from source export                 | Source owner |
| `duplicate_chunk_text`           | **1**            | Row 2: `policy_refund_v4` (dedup'd)            | None (automatically dedup'd)                                | N/A          |
| `stale_hr_policy_effective_date` | **1**            | Row 7: `hr_leave_policy` (2025-01-01 < cutoff) | Review HR policy version; re-publish with 2026-01-01+ dates | HR team      |

---

## Quality Rules & Expectations

1. **no_duplicate_chunk_text**: Warn if duplicates found (auto-resolved by dedup)
   - Sprint 1 Result: **1 duplicate removed** (Row 2, policy_refund_v4)

2. **no_stale_refund_window**: Halt on "14 ngày" in policy_refund_v4 — expectation suite blocks pub unless `--skip-validate` or fix applied
   - Sprint 1 Result: **✅ Fixed & validated** (Row 1 corrected: "14 ngày" → "7 ngày")

3. **min_chunk_length**: Warn if any chunk < 8 characters (likely noise)
   - Sprint 1 Result: **✅ All cleaned records ≥ 8 chars** (0 violations)

### Sprint 1 Cleaned Records (6 total)
| Seq | Doc ID           | Chunk Preview                                         | Status    |
| --- | ---------------- | ----------------------------------------------------- | --------- |
| 1   | policy_refund_v4 | "Yêu cầu được gửi trong vòng 7 ngày..."               | ✅ Cleaned |
| 2   | policy_refund_v4 | "Yêu cầu hoàn tiền... [cleaned: stale_refund_window]" | ✅ Fixed   |
| 3   | sla_p1_2026      | "Ticket P1 có SLA phản hồi ban đầu 15 phút..."        | ✅ Cleaned |
| 4   | it_helpdesk_faq  | "Tài khoản bị khóa sau 5 lần..."                      | ✅ Cleaned |
| 5   | hr_leave_policy  | "Nhân viên dưới 3 năm kinh nghiệm được 12 ngày..."    | ✅ Cleaned |
| 6   | it_helpdesk_faq  | "FAQ bổ sung: đổi mật khẩu..."                        | ✅ Cleaned |

---

## Freshness & Monitoring

- **Measured At**: `publish` (after embed upsert to Chroma)
- **SLA**: 24 hours from export timestamp  
- **Alert**: Log to stdout + manifest JSON
- **Status**: Check via `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint1.json`

---

## Sprint 1 Results & Validation

### Execution Summary
- **Run ID**: `sprint1`
- **Timestamp**: 2026-04-15T04:56:28.402273+00:00
- **Raw Input**: 10 records from `data/raw/policy_export_dirty.csv`
- **Duration**: < 5 seconds

### Processing Results
✅ **cleaned_records**: 6  
✅ **quarantine_records**: 4  
✅ **Total Accounted**: 10 (100%)

### Quality Gate Status
```
✅ expectation[min_one_row]                      PASS (halt)
✅ expectation[no_empty_doc_id]                  PASS (halt) :: count=0
✅ expectation[refund_no_stale_14d_window]       PASS (halt) :: violations=0
✅ expectation[chunk_min_length_8]               PASS (warn) :: short_chunks=0
✅ expectation[effective_date_iso_yyyy_mm_dd]    PASS (halt) :: non_iso_rows=0
✅ expectation[hr_leave_no_stale_10d_annual]     PASS (halt) :: violations=0
```

### Artifacts Generated
- ✅ Cleaned CSV: `artifacts/cleaned/cleaned_sprint1.csv` (6 data rows)
- ✅ Quarantine CSV: `artifacts/quarantine/quarantine_sprint1.csv` (4 data rows)
- ✅ Manifest JSON: `artifacts/manifests/manifest_sprint1.json`
- ✅ Log File: `artifacts/logs/run_sprint1.log`
- ✅ Embeddings: 6 vectors upserted to `day10_kb` collection

### Failure Mode Analysis

| Failure Mode                     | Count | Resolution                                          | Recommendation                                      |
| -------------------------------- | ----- | --------------------------------------------------- | --------------------------------------------------- |
| `unknown_doc_id`                 | 1     | Quarantined (Row 9: `legacy_catalog_xyz_zzz`)       | Add to allowed list if authorized; otherwise delete |
| `missing_effective_date`         | 1     | Quarantined (Row 5: `policy_refund_v4`)             | Backfill date or exclude                            |
| `duplicate_chunk_text`           | 1     | Quarantined (Row 2: `policy_refund_v4`)             | Auto-dedup'd; no action needed                      |
| `stale_hr_policy_effective_date` | 1     | Quarantined (Row 7: `hr_leave_policy @ 2025-01-01`) | Re-publish with 2026-01-01+ version                 |
| `stale_refund_window`            | 1     | **Fixed** (Row 1: "14 ngày" → "7 ngày")             | Annotation: `[cleaned: stale_refund_window]`        |

**Summary**: 4 records removed for quality, 1 record fixed by policy enforcement, 6 records published to KB.

---

## DoD Sign-Off (Sprint 1)

- ✅ Source map filled with ≥2 canonical sources
- ✅ Failure modes documented for both sources
- ✅ Metrics defined (% flagged, count quarantined, etc.)
- ✅ Pipeline executed: `python etl_pipeline.py run --run-id sprint1`
- ✅ Log contains: `run_id`, `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`
- ✅ All quality expectations passed (zero halts)
- ✅ Manifest & CSV artifacts generated
