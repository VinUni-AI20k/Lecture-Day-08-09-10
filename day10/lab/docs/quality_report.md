# Quality report - Lab Day 10

**run_id:** `sprint4-final`  
**Ngày:** 2026-04-15

## 1. Tóm tắt số liệu

| Chỉ số | Trước (inject) | Sau (clean) | Ghi chú |
|---|---:|---:|---|
| raw_records | 9 | 10 | Inject file có 9 dòng cố ý lỗi |
| cleaned_records | 3 | 6 | Sau fix pipeline giữ lại thêm dữ liệu hợp lệ |
| quarantine_records | 6 | 4 | Giảm vì bỏ anomaly inject |
| Expectation halt? | Yes | No | Inject fail `refund_no_stale_14d_window` |

## 2. Before / after retrieval

Artifact:
- `artifacts/eval/after_inject_bad.csv`
- `artifacts/eval/before_after_eval.csv`

`q_refund_window`:
- Trước: `contains_expected=yes`, `hits_forbidden=yes` (top-k còn chunk stale 14 ngày).
- Sau: `contains_expected=yes`, `hits_forbidden=no`.

`q_leave_version`:
- Trước: `contains_expected=no`, `top1_doc_expected=no`.
- Sau: `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`.

## 3. Freshness & monitor

Manifest clean (`manifest_sprint4-final.json`):
- `freshness_publish=FAIL` vì `latest_cleaned_exported_at=2026-04-10T08:00:00Z` đã quá SLA 24h.
- `freshness_ingest=FAIL` với cùng lý do trên boundary ingest.

Manifest inject (`manifest_sprint3-inject.json`):
- `freshness_ingest=WARN` do inject timestamp format sai (`2026/04/10 08:00:00`) không parse được.

## 4. Corruption inject (Sprint 3)

Inject đã thêm/làm sai có chủ đích:
- `topic_keyword_mismatch` (off-topic chunk trong `policy_refund_v4`)
- `invalid_exported_at_format`
- `effective_date_after_exported_at`
- `missing_chunk_text`
- giữ `no-refund-fix` + `skip-validate` để ép expectation fail

Kết quả phát hiện:
- `quarantine_sprint3-inject.csv` có đủ reason như trên.
- `run_sprint3-inject.log` ghi `expectation[refund_no_stale_14d_window] FAIL (halt)`.

## 5. Hạn chế & việc chưa làm

- Chưa triển khai GE/pydantic validator độc lập; hiện dùng custom expectation suite.
- Chưa mở rộng bộ eval lên >4 câu cho semantic slices nâng cao.
