# Sprint 1 Completion Report — ETL Ingest & Schema

**Date**: 2026-04-15  
**Duration**: ~60 minutes  
**Status**: ✅ **COMPLETE**  

---

## Objectives Met

### ✅ 1. Data Ingestion
- **Raw Data Source**: `data/raw/policy_export_dirty.csv`
- **Records Ingested**: 10
- **Format**: CSV with columns: `chunk_id`, `doc_id`, `chunk_text`, `effective_date`, `exported_at`
- **Encoding**: UTF-8 (with legacy migration artifacts)

### ✅ 2. Source Map & Data Contract
- **File Created**: `docs/data_contract.md`
- **Coverage**: 4 canonical document sources mapped
  - `policy_refund_v4` (v4 from 2026-Q1)
  - `sla_p1_2026` (2026 baseline)
  - `it_helpdesk_faq` (active)
  - `hr_leave_policy` (active for 2026+)

#### Failure Modes Documented:
| Failure Mode                     | Count          | Owner        |
| -------------------------------- | -------------- | ------------ |
| `unknown_doc_id`                 | —              | Data team    |
| `invalid_effective_date_format`  | —              | Source owner |
| `missing_effective_date`         | —              | Data team    |
| `missing_chunk_text`             | —              | Source owner |
| `duplicate_chunk_text`           | auto-dedup     | N/A          |
| `stale_hr_policy_effective_date` | —              | HR team      |
| `stale_refund_window`            | fixed in clean | Billing team |

#### Metrics Defined:
- Quarantine reason codes
- Quality expectations (6 rules)
- Freshness SLA: 24 hours
- Min chunk length: 8 characters

### ✅ 3. ETL Pipeline Execution

#### Command Run:
```bash
python etl_pipeline.py run --run-id sprint1
```

#### Results:

| Metric               | Value                            | Status |
| -------------------- | -------------------------------- | ------ |
| `run_id`             | sprint1                          | ✅      |
| `raw_records`        | 10                               | ✅      |
| `cleaned_records`    | 6                                | ✅      |
| `quarantine_records` | 4                                | ✅      |
| `run_timestamp`      | 2026-04-15T04:56:28.402273+00:00 | ✅      |

### ✅ 4. Quality Expectations — All Passed

```
expectation[min_one_row]                      OK (halt) :: cleaned_rows=6
expectation[no_empty_doc_id]                  OK (halt) :: empty_doc_id_count=0
expectation[refund_no_stale_14d_window]       OK (halt) :: violations=0
expectation[chunk_min_length_8]               OK (warn) :: short_chunks=0
expectation[effective_date_iso_yyyy_mm_dd]    OK (halt) :: non_iso_rows=0
expectation[hr_leave_no_stale_10d_annual]     OK (halt) :: violations=0
```

✅ **No Hard Halt** — All critical expectations passed.

### ✅ 5. Artifacts Generated

| Artifact           | Path                                          | Status                            |
| ------------------ | --------------------------------------------- | --------------------------------- |
| **Log File**       | `artifacts/logs/run_sprint1.log`              | ✅                                 |
| **Cleaned CSV**    | `artifacts/cleaned/cleaned_sprint1.csv`       | ✅ (7 lines: 1 header + 6 records) |
| **Quarantine CSV** | `artifacts/quarantine/quarantine_sprint1.csv` | ✅ (5 lines: 1 header + 4 records) |
| **Manifest JSON**  | `artifacts/manifests/manifest_sprint1.json`   | ✅                                 |
| **Embeddings**     | ChromaDB collection `day10_kb`                | ✅ (6 vectors upserted)            |

### ✅ 6. Freshness Check

```
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 116.941, "sla_hours": 24.0}
```

**Note**: FAIL is expected for Sprint 1 test data (exported 5 days ago). In production, **FRESH** export required before publish.

---

## Cleaning Operations Summary

### Records Processed:
- **Input**: 10 raw records
- **Output**: 6 cleaned + 4 quarantine = 10 ✓ (100% accounted for)

### Transformations Applied:

1. **Refund Policy Fix**: Policy refund v4 record with "14 ngày làm việc" → corrected to "7 ngày làm việc"
   - Annotation added: `[cleaned: stale_refund_window]`
   - Status: Compliance with current policy v4

2. **Date Normalization**: All effective dates converted to ISO YYYY-MM-DD

3. **Duplicate Deduplication**: Normalized text deduplication applied (remove-on-first-match)

4. **Chunk ID Stabilization**: All cleaned records assigned stable SHA-256–based `chunk_id` for idempotent embedding

---

## Log File Contents

**File**: `artifacts/logs/run_sprint1.log`

```
run_id=sprint1
raw_records=10
cleaned_records=6
quarantine_records=4
cleaned_csv=artifacts\cleaned\cleaned_sprint1.csv
quarantine_csv=artifacts\quarantine\quarantine_sprint1.csv
expectation[min_one_row] OK (halt) :: cleaned_rows=6
expectation[no_empty_doc_id] OK (halt) :: empty_doc_id_count=0
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
expectation[chunk_min_length_8] OK (warn) :: short_chunks=0
expectation[effective_date_iso_yyyy_mm_dd] OK (halt) :: non_iso_rows=0
expectation[hr_leave_no_stale_10d_annual] OK (halt) :: violations=0
embed_upsert count=6 collection=day10_kb
manifest_written=artifacts\manifests\manifest_sprint1.json
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 116.941, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
PIPELINE_OK
```

---

## Definition of Done (DoD) — SATISFIED ✅

- ✅ Log contains `run_id`
- ✅ Log contains `raw_records` (10)
- ✅ Log contains `cleaned_records` (6)
- ✅ Log contains `quarantine_records` (4)
- ✅ Source map in `docs/data_contract.md` with ≥2 sources + failure modes + metrics
- ✅ Pipeline command executed without Hard Halt: `PIPELINE_OK`
- ✅ Manifest written with full pipeline metadata
- ✅ Cleaned CSV exported with stable chunk_ids
- ✅ Quarantine CSV captured (4 anomalous records isolate for review)
- ✅ Embeddings upserted to vector store (6 vectors, collection: `day10_kb`)

---

## Next Steps (Sprint 2 Prep)

1. **Expand Testing**: Add additional raw data exports (malformed dates, missing fields, new doc_ids)
2. **Failure Mode Coverage**: Verify each quarantine reason code with synthetic test cases
3. **Performance Metrics**: Measure cleaning throughput (records/sec) with larger datasets
4. **Contract Versioning**: Add semantic versioning to data_contract.md (e.g., v1.0 → v1.1)
5. **Observability**: Wire freshness_check alerts to monitoring dashboard

---

## Team Notes

- **Data Quality**: 60% cleaned; 40% quarantine rate is acceptable for migration-era export
- **Encoding**: Source data has UTF-8 corruption remnants (policy-v3 migration artifacts) — schedule source remediation
- **Version Bindings**: HR policy version cutoff (2026-01-01) enforced; prevents accidental serving of 2025 guidance
- **Refund Policy**: v4 compliance auto-enforced; no manual intervention needed for legacy "14 day" references

