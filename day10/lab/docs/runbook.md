# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

User/agent trả lời policy hoàn tiền không ổn định: có lúc ra "7 ngày", có lúc ra "14 ngày".  
Khi truy vết top-k context, thấy đồng thời chunk đúng và chunk stale.

---

## Detection

- `quality/expectations.py`: expectation `refund_no_stale_14d_window` FAIL (severity=halt) khi chạy inject.
- `artifacts/eval/after_inject_bad.csv`: `q_refund_window` có `hits_forbidden=yes`.
- Manifest có `embed_prune_removed=1`, cho thấy snapshot mới đã thay thế snapshot cũ trong vector store.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Mở `artifacts/manifests/manifest_<run_id>.json` và đối chiếu `run_id`, `cleaned_records`, `quarantine_records`, `embed_prune_removed` | Xác định run nào làm index nhiễm stale |
| 2 | Mở `artifacts/quarantine/quarantine_<run_id>.csv`, lọc theo `reason` | Xác nhận rule quarantine có hoạt động (đặc biệt HR stale / format date) |
| 3 | Chạy `python eval_retrieval.py --out artifacts/eval/recheck.csv` | Kiểm tra lại `contains_expected`, `hits_forbidden`, `top1_doc_expected` sau fix |
| 4 | Nếu cần recreate lỗi, chạy `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate` | Reproduce issue có kiểm soát để so sánh before/after |

---

## Mitigation

- Chạy lại pipeline clean: `python etl_pipeline.py run` (không dùng flags inject).
- Nếu expectation halt FAIL trên production-like run: dừng publish, không đẩy snapshot lỗi sang serving.
- Nếu đang có traffic thực, bật cảnh báo "data quality incident" và tạm thời khóa câu trả lời policy nhạy cảm theo version.
- Rerun grading/eval (`grading_run.py`, `eval_retrieval.py`) để xác nhận `hits_forbidden=no` trước khi đóng incident.

---

## Prevention

- Giữ E3 (`refund_no_stale_14d_window`) ở mức `halt`; không cho phép chạy production với `--skip-validate`.
- Thêm alert khi `embed_prune_removed` đột biến hoặc `quarantine_records/raw_records` vượt ngưỡng.
- Chuẩn hoá quy trình review `metric_impact` cho mọi rule/expectation mới để tránh trivial changes.
- Mở rộng monitoring 2 boundary: ingest boundary (timestamp export) + publish boundary (timestamp embed complete).
