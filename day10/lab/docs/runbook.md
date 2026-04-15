# Runbook — Lab Day 10 (incident tối giản)

**Nhóm:** C401-Y3  
**Cập nhật:** 2026-04-15

---

## Incident 1: Agent trả lời sai cửa sổ hoàn tiền ("14 ngày" thay vì "7 ngày")

### Symptom

User hoặc agent retrieval trả về: *"Yêu cầu hoàn tiền được chấp nhận trong vòng **14 ngày** làm việc"*  
Đúng phải là **7 ngày** theo `policy_refund_v4` (canonical).

### Detection

| Metric / signal | Giá trị báo lỗi |
|-----------------|-----------------|
| Expectation `refund_no_stale_14d_window` | FAIL — `violations > 0` |
| Eval `q_refund_window` → `hits_forbidden` | `yes` |
| Eval `q_refund_window` → `contains_expected` | `no` |
| Manifest `no_refund_fix` | `true` |

### Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/manifest_<run_id>.json` | Tìm `"no_refund_fix": true` hoặc `"skipped_validate": true` → pipeline chạy inject mode |
| 2 | Mở `artifacts/quarantine/quarantine_<run_id>.csv` | Kiểm tra cột `reason`; nếu không có `internal_migration_note` cho chunk "14 ngày" → Rule A không bắt được |
| 3 | Chạy `python eval_retrieval.py --out artifacts/eval/check_now.csv` | Xem cột `hits_forbidden` cho `q_refund_window`; `yes` = vector store còn chunk stale |
| 4 | Xem `artifacts/logs/run_<run_id>.log` | Tìm dòng `expectation[refund_no_stale_14d_window] FAIL` |

### Mitigation

1. Rerun pipeline sạch (không flag inject):
   ```bash
   python etl_pipeline.py run --run-id hotfix-refund
   ```
2. Pipeline upsert + prune tự động thay thế chunk cũ bằng chunk 7 ngày.
3. Chạy lại eval để xác nhận `hits_forbidden=no`, `contains_expected=yes`:
   ```bash
   python eval_retrieval.py --out artifacts/eval/after_hotfix.csv
   ```
4. Nếu vẫn fail: kiểm tra `CHROMA_COLLECTION` và `CHROMA_DB_PATH` trong `.env` đúng với collection đang phục vụ.

### Prevention

- Expectation `refund_no_stale_14d_window` (halt) đã bảo vệ — đừng dùng `--skip-validate` trong môi trường prod.
- Thêm CI kiểm tra manifest `no_refund_fix` phải là `false` trước khi deploy.
- Nối sang Day 11: guardrail LLM có thể kiểm tra output agent trước khi trả lời user.

---

## Incident 2: Freshness FAIL — dữ liệu quá cũ (age_hours vượt SLA 24h)

### Symptom

Log cuối pipeline in:
```
freshness_check=FAIL {"age_hours": 117.4, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Manifest `latest_exported_at` cũ hơn 24 giờ so với `run_timestamp`.

### Detection

| Metric / signal | Giá trị báo lỗi |
|-----------------|-----------------|
| `freshness_check` trong log | `FAIL` |
| `age_hours` trong manifest | > `sla_hours` (24.0) |

### Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Đọc `artifacts/manifests/manifest_<run_id>.json` | Xem `latest_exported_at` — so với ngày hôm nay |
| 2 | Kiểm tra source batch script | Batch export có chạy đúng giờ không? File raw có được cập nhật không? |
| 3 | Chạy `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run_id>.json` | Xác nhận PASS/WARN/FAIL và age_hours |

### Mitigation

- **Ngắn hạn:** Nâng `FRESHNESS_SLA_HOURS` trong `.env` (chỉ cho môi trường dev/test):
  ```
  FRESHNESS_SLA_HOURS=168
  ```
- **Dài hạn:** Yêu cầu batch export mới từ source DB/API, sau đó rerun pipeline:
  ```bash
  python etl_pipeline.py run
  ```
- Tạm thời hiển thị banner "Dữ liệu có thể chưa cập nhật nhất" cho user nếu freshness FAIL.

### Prevention

- Cấu hình `alert_channel` thực trong `contracts/data_contract.yaml` (webhook Slack/email).
- Schedule batch export tự động và kiểm tra freshness sau mỗi run qua CI.
- SLA 24h phù hợp cho production; trong lab dùng `FRESHNESS_SLA_HOURS=168` (7 ngày) để tránh noise.

---

## Incident 3: Pipeline HALT — expectation fail không mong muốn

### Symptom

Pipeline exit với code 2 và in:
```
PIPELINE_HALT: expectation suite failed (halt).
```

### Detection

Dòng trong log: `expectation[<tên>] FAIL (halt) :: <detail>`

### Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Đọc log `artifacts/logs/run_<run_id>.log` | Tìm dòng `FAIL (halt)` — xác định expectation nào fail |
| 2 | Mở `artifacts/cleaned/cleaned_<run_id>.csv` (nếu tồn tại) | Xem dữ liệu đã qua cleaning — tìm dòng vi phạm |
| 3 | Mở `artifacts/quarantine/quarantine_<run_id>.csv` | Xem lý do quarantine — có dòng lọc sai không? |

**Expectation hay gặp fail và nguyên nhân:**

| Expectation | Nguyên nhân phổ biến |
|-------------|---------------------|
| `min_one_row` | Toàn bộ raw bị quarantine (allowlist sai, file rỗng) |
| `refund_no_stale_14d_window` | Chunk "14 ngày" không có migration marker + `--no-refund-fix` |
| `hr_leave_no_stale_10d_annual` | HR 2025 lọt qua cleaning (kiểm tra rule stale date) |
| `exported_at_not_empty` | Cleaning rule B bị tắt hoặc data thiếu exported_at |
| `all_doc_ids_in_allowlist` | Allowlist chưa đồng bộ giữa cleaning_rules và expectations |

### Mitigation

1. Fix source dữ liệu hoặc cập nhật rule tương ứng.
2. Rerun: `python etl_pipeline.py run --run-id fix-<issue>`.
3. Chỉ dùng `--skip-validate` khi **chủ đích demo inject** (Sprint 3) — không dùng trong prod.

### Prevention

- Kiểm tra raw CSV trước khi ingest: đủ doc_id, đủ exported_at, không chunk quá dài.
- Thêm expectation mới khi phát hiện failure mode mới (nối sang Day 11).

---

## Debug order (từ slide Day 10)

```
Freshness / version → Volume & errors → Schema & contract → Lineage / run_id → mới đến model/prompt
```
