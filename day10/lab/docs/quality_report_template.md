# Quality Report — Lab Day 10 (nhóm)

**run_id:** `sprint2-clean`
**Ngày chạy:** 2026-04-15
**Người phụ trách quality:** Ngô Quang Phúc (Người 3)

---

## 1. Tóm tắt số liệu pipeline

| Chỉ số | Dữ liệu bẩn (trước fix) | Sau pipeline chuẩn | Ghi chú |
|---|---|---|---|
| `raw_records` | 10 | 10 | Không thay đổi nguồn |
| `cleaned_records` | **6** | **6** | Sau clean + dedupe |
| `quarantine_records` | **4** | **4** | Tổng bị loại |
| Expectation halt? | **Có** (E3 FAIL — chunk "14 ngày" còn trong index, bypass bởi `--skip-validate`) | **Không** (9/9 PASS) | Chuẩn = exit 0 |

*Lý do quarantine điển hình trong bộ mẫu:*

| reason | count |
|---|---|
| `unknown_doc_id` (legacy_catalog_xyz_zzz) | 1 |
| `stale_hr_policy_effective_date` (HR 2025-01-01) | 1 |
| `missing_chunk_text` (dòng 5 — empty text) | 1 |
| `duplicate_chunk_text` (dòng 2 = dòng 1) | 1 |

---

## 2. Expectation Suite — danh sách đầy đủ

| ID | Tên | Severity | Pass khi pipeline chuẩn | Fail khi inject |
|---|---|---|---|---|
| E1 | `min_one_row` | **halt** | ✅ | Khi quarantine hết |
| E2 | `no_empty_doc_id` | **halt** | ✅ | Khi doc_id rỗng |
| E3 | `refund_no_stale_14d_window` | **halt** | ✅ | `--no-refund-fix` |
| E4 | `chunk_min_length_8` | warn | ✅ | Inject chunk < 8 ký tự |
| E5 | `effective_date_iso_yyyy_mm_dd` | **halt** | ✅ | Sai format ngày |
| E6 | `hr_leave_no_stale_10d_annual` | **halt** | ✅ | `--skip-validate` |
| **E7** | `each_critical_doc_has_min_chunks` | **halt** | ✅ | Quarantine hết 1 doc |
| **E8** | `no_duplicate_chunk_ids` | **halt** | ✅ | chunk_id bị trùng |
| **E9** | `chunk_text_reasonable_length` | warn | ✅ | Chunk > 2 000 ký tự |

**Quy tắc halt vs warn:**
- **halt** → pipeline dừng, không publish lên vector store (dữ liệu sai hoặc thiếu nghiêm trọng).
- **warn** → pipeline tiếp tục, ghi cảnh báo vào log, team cần xem lại chunking/format.

---

## 3. Metric impact của expectation mới (E7 · E8 · E9)

### E7 — `each_critical_doc_has_min_chunks`

> **Kịch bản chứng minh:** Inject effective_date sai cho toàn bộ chunk `hr_leave_policy`
> → cleaning_rules quarantine hết → `doc_chunk_counts["hr_leave_policy"] = 0` → **E7 HALT**.

| Scenario | `hr_leave_policy` chunks | E7 |
|---|---|---|
| Pipeline chuẩn (`sprint2-clean`) | **1** (`counts={'policy_refund_v4': 2, 'sla_p1_2026': 1, 'it_helpdesk_faq': 2, 'hr_leave_policy': 1}`) | PASS |
| Inject sai ngày toàn bộ HR | 0 | **HALT** |

### E8 — `no_duplicate_chunk_ids`

> **Kịch bản chứng minh:** Nếu `seq` bị reset về 0 giữa chừng (bug trong entrypoint) hoặc
> cùng `doc_id + chunk_text` sinh từ 2 lần gọi khác nhau → hash trùng → **E8 HALT**.

| Scenario | duplicate_chunk_ids | E8 |
|---|---|---|
| Pipeline chuẩn (dedupe bởi E2 cleaning) | 0 | PASS |
| Bug seq-reset | > 0 | **HALT** |

### E9 — `chunk_text_reasonable_length`

> **Kịch bản chứng minh:** Inject 1 chunk ghép nhiều đoạn dài > 2 000 ký tự →
> embedding model (MiniLM) cắt ngầm → retrieval kém → E9 WARN (không halt, nhưng ghi log).

| Scenario | chunks > 2 000 ký tự | E9 |
|---|---|---|
| Bộ mẫu gốc | 0 | PASS (warn không kích) |
| Inject chunk dài | ≥ 1 | **WARN** |

---

## 4. Before / after retrieval (bắt buộc)

> Đính kèm file `artifacts/eval/before_after_eval.csv` sau khi chạy Người 5 (eval_retrieval.py).

**Câu then chốt: `q_refund_window`**

| Scenario | `contains_expected` | `hits_forbidden` | Ghi chú |
|---|---|---|---|
| **Before** (`--no-refund-fix --skip-validate`) | *(điền)* | yes | Còn chunk "14 ngày" |
| **After** (pipeline chuẩn) | yes | no | Đã fix 7 ngày, E3 PASS |

**Merit: `q_leave_version` (HR conflict)**

| Scenario | `contains_expected` | `hits_forbidden` | `top1_doc_id` |
|---|---|---|---|
| **Before** (stale HR 2025 còn trong index) | *(điền)* | yes | *(điền)* |
| **After** (pipeline chuẩn) | yes | no | `hr_leave_policy` |

---

## 5. Freshness & monitor

> *(Điền sau khi Người 4 hoàn thiện `monitoring/freshness_check.py`)*

Kết quả lệnh:
```
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run-id>.json
```

| Trạng thái | Ý nghĩa |
|---|---|
| **PASS** | Manifest mới hơn SLA (vd. < 24h) |
| **WARN** | Manifest cũ 24–48h — cần chạy lại pipeline |
| **FAIL** | Manifest quá cũ (> 48h) hoặc không tồn tại |

---

## 6. Corruption inject (Sprint 3)

**Cách inject:**
```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
```

**Những gì bị phá vỡ:**
- `--no-refund-fix`: chunk "14 ngày làm việc" còn trong index → E3 sẽ fail nếu không `--skip-validate`.
- `--skip-validate`: bỏ qua toàn bộ expectation suite → publish dữ liệu bẩn.
- Kết quả eval: `q_refund_window` → `hits_forbidden=yes`.

**Bằng chứng so sánh:** xem 2 file CSV trong `artifacts/eval/`:

| File | Scenario |
|---|---|
| `before_after_eval.csv` | Pipeline chuẩn — after fix |
| `after_inject_bad.csv` | Sau inject — dữ liệu bẩn |

---

## 7. Hạn chế & việc chưa làm

- E9 chỉ là `warn` — chưa tự động re-chunk khi vượt ngưỡng.
- Chưa có expectation kiểm tra `exported_at` so với ngày hiện tại (freshness từ góc expectation).
- Grading JSONL cần chạy riêng (`grading_run.py`) — xem Người 6.

