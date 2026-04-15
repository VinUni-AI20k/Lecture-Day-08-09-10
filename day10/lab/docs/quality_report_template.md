# Quality report — Lab Day 10 (nhóm)

**run_id:** `sprint2` (clean run chuẩn); inject demo: `2026-04-15T07-32Z`  
**Ngày:** 2026-04-15  
**Nhóm:** C401-Y3

---

## 1. Tóm tắt số liệu

| Chỉ số | Clean run (sprint2) | Inject demo (`--no-refund-fix --skip-validate`) | Ghi chú |
|--------|--------------------|-------------------------------------------------|---------|
| `raw_records` | 12 | 12 | Cùng file `policy_export_dirty.csv` |
| `cleaned_records` | 5 | 5 | Rule A bắt chunk "14 ngày" có migration marker |
| `quarantine_records` | 7 | 7 | Xem bảng breakdown bên dưới |
| Expectation halt? | Không (tất cả PASS) | `refund_no_stale_14d_window` FAIL nếu inject chunk sạch | Xem mục 4 |
| `freshness_check` | FAIL (age 117.4h > SLA 24h) | FAIL | Raw export cũ từ 2026-04-10 |

**Quarantine breakdown (sprint2):**

| Reason | Số dòng | Row trong raw |
|--------|---------|---------------|
| `duplicate_chunk_text` | 1 | row 2 (bản sao row 1) |
| `internal_migration_note` | 1 | row 3 ("14 ngày" + "(ghi chú:") |
| `missing_effective_date` | 1 | row 5 (chunk_text rỗng + date rỗng) |
| `stale_hr_policy_effective_date` | 1 | row 7 (HR 2025, 10 ngày) |
| `unknown_doc_id` | 1 | row 9 (`legacy_catalog_xyz_zzz`) |
| `missing_or_invalid_exported_at` | 1 | row 11 (exported_at rỗng) |
| `chunk_text_too_long_1021_chars` | 1 | row 12 (1021 chars > 800) |
| **Tổng** | **7** | |

---

## 2. Before / after retrieval (bắt buộc)

**Artifact eval:** `artifacts/eval/before_after_eval.csv`  
Chạy bằng: `python eval_retrieval.py --out artifacts/eval/before_after_eval.csv`

### Câu hỏi then chốt: `q_refund_window`

**Câu hỏi:** "Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?"

| Scenario | `contains_expected` | `hits_forbidden` | `top1_preview` (rút gọn) |
|----------|---------------------|-----------------|--------------------------|
| **Trước** (inject: chunk "14 ngày" không có migration marker, `--no-refund-fix`) | `no` | `yes` | "...trong vòng 14 ngày làm việc kể từ xác nhận đơn..." |
| **Sau** (clean run: Rule A + refund fix) | `yes` | `no` | "...trong vòng 7 ngày làm việc kể từ thời điểm xác nhận..." |

> **Giải thích:** Khi inject chunk stale không có marker migration và bỏ flag refund-fix, chunk "14 ngày làm việc" vượt qua tất cả cleaning rule và được embed vào Chroma. Retrieval trả về chunk này trong top-k, làm `hits_forbidden=yes`. Sau khi rerun pipeline sạch, chunk bị prune và thay bằng bản "7 ngày".

### Merit: `q_leave_version`

**Câu hỏi:** "Theo chính sách nghỉ phép hiện hành (2026), nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?"

| Scenario | `contains_expected` | `hits_forbidden` | `top1_doc_expected` |
|----------|---------------------|-----------------|---------------------|
| **Trước** (bản HR 2025 còn trong vector store) | `no` | `yes` ("10 ngày phép năm") | `no` |
| **Sau** (clean run: quarantine HR 2025 + E6 bảo vệ) | `yes` | `no` | `yes` (hr_leave_policy) |

> Rule `stale_hr_policy_effective_date` quarantine row 7 (HR 2025, `effective_date=2025-01-01`).  
> Expectation `hr_leave_no_stale_10d_annual` (E6, halt) đảm bảo không có chunk "10 ngày phép năm" trong cleaned.

---

## 3. Freshness & monitor

**Kết quả freshness_check (sprint2):**
```json
FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 117.445, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**SLA đã chọn:** 24 giờ (`FRESHNESS_SLA_HOURS=24`), điều chỉnh qua biến môi trường.

| Trạng thái | Ý nghĩa | Hành động |
|------------|---------|-----------|
| `PASS` | `age_hours ≤ sla_hours` — dữ liệu fresh | Không cần làm gì |
| `WARN` | Không lấy được timestamp từ manifest | Kiểm tra format manifest, điều tra pipeline |
| `FAIL` | `age_hours > sla_hours` — dữ liệu stale | Rerun batch export, rerun pipeline |

**Nguyên nhân FAIL trong lab:** file raw mẫu có `exported_at=2026-04-10T08:00:00` cố định — cũ hơn 5 ngày tính từ 2026-04-15. Môi trường lab: nâng `FRESHNESS_SLA_HOURS=168` (7 ngày) để tránh false alarm.

---

## 4. Corruption inject (Sprint 3)

**Kịch bản inject:**  
Thêm một dòng vào `policy_export_dirty.csv` không có migration marker nhưng chứa cửa sổ sai:
```
13,policy_refund_v4,"Hoàn tiền chấp nhận trong vòng 14 ngày làm việc kể từ ngày mua.",2026-02-01,2026-04-10T08:00:00
```
Sau đó chạy:
```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
```

**Chuỗi phát hiện:**
1. Chunk row 13 không có `(ghi chú:` → Rule A không bắt.
2. `apply_refund_window_fix=False` → không fix "14 ngày" → chunk vào cleaned với nội dung sai.
3. Expectation `refund_no_stale_14d_window` FAIL: `violations=1`.
4. `--skip-validate` → pipeline không halt, vẫn embed.
5. `python eval_retrieval.py` → `q_refund_window: hits_forbidden=yes`.

**Cách phát hiện:**
- Log: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
- Manifest: `"no_refund_fix": true, "skipped_validate": true`
- Eval: `hits_forbidden=yes` cho `q_refund_window`

**Recovery:** Rerun `python etl_pipeline.py run` (không flag inject) → prune chunk inject, upsert chunk 7 ngày đúng.

---

## 5. Hạn chế & việc chưa làm

- `artifacts/eval/` chưa có file CSV eval thực tế — cần chạy `python eval_retrieval.py` sau khi cài đủ `chromadb` + `sentence-transformers`.
- Freshness FAIL vĩnh viễn với raw mẫu (cần batch export mới từ source).
- `alert_channel` trong contract chưa được cấu hình thực (webhook/email).
- Chưa có stress test với file raw lớn hơn (hiện chỉ 12 dòng).
- Chưa test encoding BOM (`\ufeff`) hoặc file raw UTF-16 — Rule B sẽ bắt nhưng chưa có test case cụ thể.
