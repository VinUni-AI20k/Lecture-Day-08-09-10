# Quality Report — Lab Day 10 (Team 62)

**run_id:** van-clean-1 (baseline) · van-inject-bad (inject) · van-restored (after fix)
**Ngày:** 2026-04-15
**Người thực hiện Sprint 3:** Ngô Hải Văn

---

## 1. Tóm tắt số liệu pipeline

| Chỉ số | van-clean-1 (baseline) | van-inject-bad (inject) | van-restored (after fix) |
|--------|------------------------|-------------------------|--------------------------|
| raw_records | 13 | 13 | 13 |
| cleaned_records | 7 | 7 | 7 |
| quarantine_records | 6 | 6 | 6 |
| cleaning_bom_stripped | 1 | 1 | 1 |
| Expectation halt? | Không (8/8 OK) | **Có** (`refund_no_stale_14d_window` FAIL) | Không (8/8 OK) |
| `--skip-validate` dùng? | Không | **Có** (demo inject có chủ đích) | Không |
| embed_collection_after | 7 | 7 | 7 |
| embed_idempotent | — | true | true |
| freshness_check | FAIL (age=121h > SLA 24h) | FAIL | FAIL |

> **Ghi chú freshness:** CSV mẫu có `exported_at=2026-04-10T08:00:00`, lab chạy ngày 2026-04-15 → age ~121h > SLA 24h. Đây là hành vi kỳ vọng với data snapshot cũ. Xem runbook để giải thích PASS/FAIL theo boundary.

---

## 2. Before / after retrieval

### 2.1 Câu `q_refund_window` — refund window (bắt buộc Pass)

| Scenario | contains_expected | hits_forbidden | Nhận xét |
|----------|-------------------|----------------|-----------|
| `before_fix` | yes | **no** | Pipeline chuẩn: chunk "7 ngày" đúng, không còn "14 ngày" |
| `after_inject` | yes | **yes** | Inject `--no-refund-fix`: chunk "14 ngày làm việc" còn trong index → retrieval trả về forbidden keyword |
| `after_fix` | yes | **no** | Restore pipeline chuẩn: forbidden keyword biến mất |

**Chứng cứ inject:** `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1` — pipeline phát hiện chunk stale và sẽ halt nếu không có `--skip-validate`.

### 2.2 Câu `q_leave_version` — HR policy version (Merit)

| Scenario | contains_expected | hits_forbidden | top1_doc_expected |
|----------|-------------------|----------------|-------------------|
| `before_fix` | yes | no | yes |
| `after_inject` | yes | no | yes |
| `after_fix` | yes | no | yes |

> `q_leave_version` ổn định qua cả 3 scenario vì inject chỉ tắt `--no-refund-fix` (không ảnh hưởng HR policy). Chunk HR 2025 (10 ngày) đã bị quarantine ở Rule 3 (stale effective_date) trước khi vào embed → index không bao giờ chứa "10 ngày phép năm".

---

## 3. Freshness & monitoring

Kết quả `freshness_check=FAIL` ở cả 3 run do CSV mẫu có `exported_at=2026-04-10T08:00:00` (age ~121h > SLA 24h).

**Giải thích:** SLA 24h áp cho "data freshness" (khi nào data được export từ hệ nguồn), không phải thời điểm chạy pipeline. Với data snapshot lab, FAIL là hành vi đúng — hệ thống phát hiện data cũ. Trong production, sẽ set cron re-export mỗi 12h để PASS.

**Boundary đo:** `published_at` (thời điểm pipeline chạy xong embed). Để đo 2 boundary (ingest + publish), cần thêm `ingest_started_at` vào manifest — xem runbook.

---

## 4. Corruption inject (Sprint 3)

**Kịch bản inject:** Chạy `python etl_pipeline.py run --run-id van-inject-bad --no-refund-fix --skip-validate`

**Cơ chế:** Flag `--no-refund-fix` bỏ qua Rule 6 (fix "14 ngày làm việc" → "7 ngày") → chunk stale "14 ngày làm việc" đi vào embed. Flag `--skip-validate` bypass expectation halt để pipeline tiếp tục embed dù E3 fail.

**Tác động quan sát được:**
- `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1` — pipeline phát hiện vi phạm
- Eval `q_refund_window`: `hits_forbidden=yes` — top-k chunk chứa "14 ngày làm việc"
- `embed_prune_removed=1` — pipeline prune chunk cũ từ run trước (idempotency hoạt động)

**Restore:** Chạy lại `python etl_pipeline.py run --run-id van-restored` → E3 pass, `hits_forbidden=no`.

---

## 5. Hạn chế & việc chưa làm

- Freshness chỉ đo 1 boundary (`published_at`). Đo thêm `ingest_started_at` để có 2 boundary (Distinction criterion).
- `q_leave_version` không bị ảnh hưởng bởi inject refund — cần một inject riêng cho HR version để demo đầy đủ hơn.
- BOM strip (Rule 9) không ảnh hưởng retrieval do chunk sau khi strip vẫn có nội dung tương tự; tác động chủ yếu ở text matching chính xác.
