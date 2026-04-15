# Runbook - Lab Day 10

## Symptom

- Agent trả lời sai cửa sổ hoàn tiền (lọt "14 ngày làm việc").
- Agent trả lời sai version phép năm (không ra "12 ngày").
- Eval có `hits_forbidden=yes` hoặc `top1_doc_expected=no`.

## Detection

- Kiểm tra log expectations trong `artifacts/logs/run_<run_id>.log`.
- Kiểm tra freshness:
  - `freshness_ingest=PASS/WARN/FAIL`
  - `freshness_publish=PASS/WARN/FAIL`
- Kiểm tra eval CSV:
  - `artifacts/eval/after_inject_bad.csv`
  - `artifacts/eval/before_after_eval.csv`

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|---|---|---|
| 1 | Mở `artifacts/manifests/manifest_<run_id>.json` | Có `run_id`, số record, boundary timestamps |
| 2 | Mở `artifacts/quarantine/quarantine_<run_id>.csv` | Có `reason` rõ và đếm được |
| 3 | Đối chiếu expectation trong log | Xác định expectation nào FAIL và severity |
| 4 | Chạy `eval_retrieval.py` | So sánh `contains_expected`, `hits_forbidden`, `top1_doc_expected` |

## Mitigation

1. Nếu dữ liệu xấu do inject:
   - chạy lại pipeline chuẩn:  
   `python etl_pipeline.py run --run-id sprint4-final`
2. Nếu expectation halt:
   - fix rule data tương ứng, không bypass trong run production.
3. Nếu retrieval vẫn nhiễm stale:
   - kiểm tra log `embed_prune_removed` để chắc đã prune stale vector.

## Prevention

- Giữ expectation mới ở mức `halt` cho các lỗi semantic quan trọng:
  - `refund_no_stale_14d_window`
  - `exported_at_iso_utc`
  - `effective_not_after_exported`
- Giữ topic guard trong contract (`doc_topic_keywords`) để chặn off-topic chunk.
- Duy trì đo freshness 2 boundary để phát hiện stale từ upstream sớm hơn.

## Giải thích PASS/WARN/FAIL freshness

- `PASS`: tuổi dữ liệu <= SLA.
- `WARN`: không parse được timestamp boundary (ví dụ inject cố tình format sai).
- `FAIL`: parse được timestamp nhưng quá SLA (`freshness_sla_exceeded`).
