# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

Agent hoặc người dùng nhận câu trả lời sai về policy:

- **Refund window:** agent trả lời "**14 ngày** làm việc" thay vì **7 ngày** — chunk stale từ policy-v3 còn trong vector store.
- **HR leave:** agent trả lời "**10 ngày** phép năm" thay vì **12 ngày** — bản HR 2025 chưa bị quarantine.
- **Eval score:** `hits_forbidden=yes` trong `artifacts/eval/before_after_eval.csv`; `contains_expected=no`.
- **Freshness FAIL:** `python etl_pipeline.py freshness --manifest ...` trả về `FAIL freshness_sla_exceeded`.

---

## Detection

| Signal | Nguồn | Threshold |
|--------|-------|-----------|
| `hits_forbidden=yes` trong eval CSV | `artifacts/eval/*.csv` | Bất kỳ dòng nào |
| Expectation `refund_no_stale_14d_window` FAIL | log `artifacts/logs/*.log` | severity=halt |
| Expectation `hr_leave_no_stale_10d_annual` FAIL | log | severity=halt |
| Expectation `no_migration_error_marker_in_cleaned` FAIL | log | severity=halt |
| `freshness_check=FAIL` | manifest + log | age_hours > sla_hours (24) |
| `quarantine_records` tăng bất thường | manifest JSON | > baseline (hiện tại = 5) |

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Xem `artifacts/manifests/manifest_<run_id>.json` — kiểm tra `no_refund_fix`, `skipped_validate`, `latest_exported_at` | `no_refund_fix=false`, `skipped_validate=false`; `latest_exported_at` trong 24h |
| 2 | Mở `artifacts/quarantine/quarantine_<run_id>.csv` — đếm dòng `reason=migration_error_marker_detected` và `stale_hr_policy_effective_date` | Có đúng số dòng tương ứng với raw dirty; không có dòng lọt vào cleaned |
| 3 | Đọc log `artifacts/logs/run_<run_id>.log` — tìm dòng expectation | Tất cả `OK (halt)`; không có `FAIL (halt)` |
| 4 | Chạy `python eval_retrieval.py --out artifacts/eval/debug_eval.csv` | `hits_forbidden=no` trên `q_refund_window`; `contains_expected=yes` trên tất cả câu |
| 5 | Kiểm tra Chroma prune: log `embed_prune_removed` | Nếu > 0 thì có chunk cũ đã được xoá đúng cách |

---

## Mitigation

1. **Rerun pipeline chuẩn** (không flag inject): `python etl_pipeline.py run --run-id hotfix-<timestamp>` -- index được refresh, chunk stale bị prune.
2. **Nếu pipeline bị halt** (expectation fail): kiểm tra quarantine CSV, xác nhận dữ liệu nguồn đã sửa, rồi rerun.
3. **Rollback index:** nếu run bị inject nhầm (`--no-refund-fix`), chạy lại pipeline chuẩn — embed prune sẽ xoá vector cũ.
4. **Tạm thời:** cấu hình agent Day 09 dùng collection cũ (run_id trước) trong khi chờ pipeline sạch.

---

## Prevention

- Expectation `no_migration_error_marker_in_cleaned` (severity=halt) bắt chunk lỗi migration trước khi embed.
- CI/CD: chạy `python etl_pipeline.py run --run-id ci-check` tự động khi có CSV mới; fail build nếu exit != 0.
- Freshness alert: cron job mỗi 12h đọc manifest mới nhất, gửi Slack `#data-quality` nếu `status=FAIL`.
- Versioning rule: đọc `hr_leave_min_effective_date` từ `contracts/data_contract.yaml` thay vì hard-code `"2026-01-01"` để dễ update khi chính sách thay đổi (Distinction criterion).