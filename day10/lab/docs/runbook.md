# Runbook — Lab Day 10 (incident tối giản)

---

## Incident 1: Stale Refund Window (14 days instead of 7 days)

### Symptom

- **User/Agent observation:** Agent trả lời "14 ngày làm việc" khi được hỏi về cửa sổ hoàn tiền, thay vì "7 ngày làm việc" theo policy mới nhất (v4).
- **Retrieval test:** `q_refund_window` trả về chunk chứa "14 ngày làm việc" trong top-k results.
- **Impact:** User nhận thông tin sai → khiếu nại / mất niềm tin.

### Detection

**Metric/Alert:**
- `expectation[refund_no_stale_14d_window] FAIL` → pipeline halt
- `hits_forbidden=yes` trong eval CSV (chunk chứa "14 ngày" xuất hiện trong top-k)
- `freshness_check=FAIL` → data export cũ hơn SLA 24h

**Command:**
```bash
# Kiểm tra expectation log
grep "refund_no_stale_14d_window" artifacts/logs/run_<run_id>.log

# Kiểm tra eval
cat artifacts/eval/before_after_eval.csv | grep "q_refund_window"
```

### Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/manifest_<run_id>.json` | Xem `no_refund_fix=true` (flag inject) hoặc `skipped_validate=true` |
| 2 | Mở `artifacts/cleaned/cleaned_<run_id>.csv` | Tìm chunk `policy_refund_v4` chứa "14 ngày làm việc" |
| 3 | Mở `artifacts/quarantine/quarantine_<run_id>.csv` | Kiểm tra có record nào bị quarantine do stale version không |
| 4 | Chạy `python eval_retrieval.py --out artifacts/eval/diagnosis.csv` | Xác nhận `hits_forbidden=yes` cho `q_refund_window` |
| 5 | Kiểm tra raw export | Xem `data/raw/policy_export_dirty.csv` có chứa "14 ngày" không |

**Root cause:**
- Raw export chứa version cũ của policy (14 ngày)
- Cleaning rule `apply_refund_window_fix=False` (do flag `--no-refund-fix` trong inject test)
- Hoặc: expectation bị skip (`--skip-validate`)

### Mitigation

**Immediate fix:**
```bash
# Rerun pipeline với fix enabled (mặc định)
python etl_pipeline.py run --run-id fix-refund-$(date +%Y%m%d)

# Verify expectation pass
grep "refund_no_stale_14d_window" artifacts/logs/run_fix-refund-*.log
# Expected: expectation[refund_no_stale_14d_window] OK (halt) :: violations=0

# Verify eval
python eval_retrieval.py --out artifacts/eval/after_fix.csv
cat artifacts/eval/after_fix.csv | grep "q_refund_window"
# Expected: hits_forbidden=no
```

**Rollback (nếu cần):**
- Restore từ manifest trước đó: `manifest_<previous_run_id>.json`
- Rerun embed từ cleaned CSV cũ

**Communication:**
- Thông báo user: "Data đã được cập nhật, vui lòng thử lại"
- Ghi incident log: run_id, thời gian phát hiện, thời gian fix

### Prevention

1. **Expectation enforcement:** Không cho phép `--skip-validate` trong production
2. **Alert:** Monitor `expectation[refund_no_stale_14d_window]` → alert nếu FAIL
3. **Owner:** Policy team review export trước khi ingest
4. **Automation:** Cron pipeline mỗi 12h để refresh data (đảm bảo freshness < 24h SLA)
5. **Guardrail (Day 11):** Thêm pre-answer check: nếu câu hỏi về refund, verify chunk không chứa "14 ngày"

---

## Incident 2: Freshness SLA Exceeded

### Symptom

- **Observation:** `freshness_check=FAIL` trong pipeline log
- **Manifest:** `age_hours > sla_hours` (vd: 120.951 > 24.0)
- **Impact:** Agent trả lời dựa trên data cũ → không phản ánh policy mới nhất

### Detection

**Metric/Alert:**
```bash
# Kiểm tra freshness từ manifest
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run_id>.json
# Output: FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.951, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Alert threshold:** `age_hours > 24` → FAIL

### Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `latest_exported_at` trong manifest | So sánh với `run_timestamp` |
| 2 | Tính `age_hours = (now - latest_exported_at) / 3600` | Xem có vượt SLA không |
| 3 | Kiểm tra raw export | Xem `exported_at` trong CSV có cập nhật không |
| 4 | Kiểm tra pipeline schedule | Xem cron job có chạy đúng không |

**Root cause:**
- Raw export không được refresh (nguồn không export mới)
- Pipeline không chạy theo schedule
- SLA quá chặt (24h) so với tần suất export thực tế

### Mitigation

**Option 1: Re-export data**
```bash
# Yêu cầu nguồn export lại với timestamp mới
# Sau đó rerun pipeline
python etl_pipeline.py run --run-id fresh-$(date +%Y%m%d)
```

**Option 2: Điều chỉnh SLA**
```bash
# Nếu export frequency là 48h, điều chỉnh SLA
export FRESHNESS_SLA_HOURS=48
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run_id>.json
```

**Option 3: Banner warning**
- Hiển thị banner: "Data có thể không phản ánh policy mới nhất (cập nhật lần cuối: <date>)"

### Prevention

1. **Cron schedule:** Chạy pipeline mỗi 12h để đảm bảo freshness < 24h
   ```bash
   # Crontab
   0 */12 * * * cd /path/to/lab && python etl_pipeline.py run
   ```
2. **Alert:** Monitor freshness status → alert nếu FAIL
3. **Owner:** Data team đảm bảo export frequency khớp SLA
4. **Automation:** Trigger pipeline khi có export mới (event-driven)
5. **Boundary monitoring:** Đo freshness ở 2 điểm:
   - Ingest boundary: `exported_at` từ nguồn
   - Publish boundary: `run_timestamp` khi embed xong

---

## Incident 3: Expectation Halt (HR Leave Policy Stale Version)

### Symptom

- **Pipeline:** `PIPELINE_HALT: expectation suite failed (halt).`
- **Expectation:** `expectation[hr_leave_no_stale_10d_annual] FAIL (halt) :: violations=1`
- **Impact:** Pipeline không embed → agent không có data mới

### Detection

**Metric/Alert:**
```bash
# Kiểm tra expectation log
grep "hr_leave_no_stale_10d_annual" artifacts/logs/run_<run_id>.log
# Output: expectation[hr_leave_no_stale_10d_annual] FAIL (halt) :: violations=1
```

### Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra cleaned CSV | Tìm chunk `hr_leave_policy` chứa "10 ngày phép năm" |
| 2 | Kiểm tra quarantine CSV | Xem có record HR bị quarantine do `stale_hr_policy_effective_date` không |
| 3 | Kiểm tra raw export | Xem có chunk HR với `effective_date < 2026-01-01` không |
| 4 | Review cleaning rule | Xác nhận rule quarantine HR stale có chạy không |

**Root cause:**
- Raw export chứa HR policy version cũ (10 ngày phép năm, effective_date < 2026-01-01)
- Cleaning rule không quarantine đúng → chunk cũ vào cleaned
- Expectation phát hiện conflict version → halt

### Mitigation

**Immediate fix:**
```bash
# Kiểm tra quarantine
cat artifacts/quarantine/quarantine_<run_id>.csv | grep "hr_leave_policy"

# Nếu không có trong quarantine → bug cleaning rule
# Fix: Cập nhật cleaning_rules.py để quarantine HR < 2026-01-01

# Rerun pipeline
python etl_pipeline.py run --run-id fix-hr-$(date +%Y%m%d)

# Verify expectation pass
grep "hr_leave_no_stale_10d_annual" artifacts/logs/run_fix-hr-*.log
# Expected: expectation[hr_leave_no_stale_10d_annual] OK (halt) :: violations=0
```

### Prevention

1. **Cleaning rule:** Đảm bảo quarantine HR policy với `effective_date < 2026-01-01`
2. **Expectation:** Giữ `severity=halt` để ngăn embed data xấu
3. **Owner:** HR team review export trước khi ingest
4. **Automation:** Alert khi có HR policy mới → trigger review
5. **Version control:** Thêm cột `version` vào schema để track rõ ràng

---

## Incident 4: Duplicate Vectors (Idempotency Failure)

### Symptom

- **Observation:** Collection count tăng sau mỗi lần rerun (vd: 6 → 12 → 18)
- **Impact:** Retrieval trả về duplicate chunks → agent nhầm lẫn

### Detection

**Metric/Alert:**
```bash
# Kiểm tra collection count trong log
grep "embed_collection_after" artifacts/logs/run_<run_id>.log
# Expected: embed_collection_after=6 (expected=6)
# Actual: embed_collection_after=12 (expected=6) → FAIL
```

### Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `chunk_id` generation | Xem có stable hash không (doc_id + chunk_text + seq) |
| 2 | Kiểm tra upsert logic | Xem có dùng `col.upsert(ids=...)` không |
| 3 | Kiểm tra prune logic | Xem có xóa old IDs không còn trong cleaned không |
| 4 | Rerun 2 lần với cùng data | Verify count không tăng |

**Root cause:**
- `chunk_id` không stable (vd: dùng random UUID)
- Dùng `col.add()` thay vì `col.upsert()`
- Không prune old vectors

### Mitigation

**Immediate fix:**
```bash
# Xóa collection và rebuild
# (Cẩn thận: mất data cũ)
python -c "import chromadb; client = chromadb.PersistentClient('./chroma_db'); client.delete_collection('day10_kb')"

# Rerun pipeline
python etl_pipeline.py run --run-id rebuild-$(date +%Y%m%d)

# Verify idempotent
python etl_pipeline.py run --run-id rebuild-$(date +%Y%m%d)
grep "embed_idempotent=true" artifacts/logs/run_rebuild-*.log
```

### Prevention

1. **Stable chunk_id:** Dùng hash `sha256(doc_id + chunk_text + seq)[:16]`
2. **Upsert:** Dùng `col.upsert(ids=...)` thay vì `col.add()`
3. **Prune:** Xóa old IDs không còn trong cleaned sau mỗi run
4. **Test:** Rerun 2 lần với cùng data → verify count không đổi
5. **Log:** Ghi `embed_collection_before` và `embed_collection_after` để monitor

---

## Incident 5: Missing Exported_at (Freshness Check Impossible)

### Symptom

- **Observation:** `freshness_check=WARN {"reason": "no_timestamp_in_manifest"}`
- **Impact:** Không thể verify freshness → không biết data có stale không

### Detection

**Metric/Alert:**
```bash
# Kiểm tra manifest
cat artifacts/manifests/manifest_<run_id>.json | grep "latest_exported_at"
# Output: "latest_exported_at": "" → WARN
```

### Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra raw CSV | Xem cột `exported_at` có rỗng không |
| 2 | Kiểm tra cleaning rule | Xem có quarantine `missing_exported_at` không |
| 3 | Kiểm tra expectation | Xem `exported_at_all_populated` có FAIL không |

**Root cause:**
- Raw export thiếu `exported_at` timestamp
- Cleaning rule không quarantine → vào cleaned
- Expectation `severity=warn` → không halt

### Mitigation

**Immediate fix:**
```bash
# Yêu cầu nguồn export lại với exported_at
# Hoặc: backfill exported_at = run_timestamp (fallback)

# Rerun pipeline
python etl_pipeline.py run --run-id fix-timestamp-$(date +%Y%m%d)

# Verify freshness check
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_fix-timestamp-*.json
# Expected: PASS hoặc FAIL (không WARN)
```

### Prevention

1. **Cleaning rule:** Quarantine `missing_exported_at` (rule 8)
2. **Expectation:** Nâng `exported_at_all_populated` lên `severity=halt` nếu freshness critical
3. **Owner:** Data team đảm bảo export có timestamp
4. **Fallback:** Dùng `run_timestamp` nếu `exported_at` rỗng (ghi rõ trong manifest)
5. **Alert:** Monitor `expectation[exported_at_all_populated]` → alert nếu FAIL
