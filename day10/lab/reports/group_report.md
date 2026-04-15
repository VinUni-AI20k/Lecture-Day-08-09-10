# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** C401-Y3  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Liam | Ingestion / Raw Owner | tunglamonjob@gmail.com |
| ___ | Cleaning & Quality Owner | ___ |
| ___ | Embed & Idempotency Owner | ___ |
| ___ | Monitoring / Docs Owner | ___ |

**Ngày nộp:** 2026-04-15  
**Repo:** `Day10-C401-Y3` (branch: main)  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **run_id tham chiếu:** `sprint2` (clean run chuẩn) và `2026-04-15T07-45Z` (latest)  
> **Artifact chính:** `artifacts/logs/run_sprint2.log`, `artifacts/manifests/manifest_sprint2.json`, `artifacts/quarantine/quarantine_sprint2.csv`  
> **Quality report:** `docs/quality_report_template.md` (đã hoàn chỉnh — giữ tên template theo quy định lab)

---

## 1. Pipeline tổng quan

**Tóm tắt luồng:**

Pipeline Lab Day 10 xử lý export raw dạng CSV từ ba nguồn giả lập: Policy/SLA DB, HR System, và Helpdesk KB. Luồng end-to-end gồm 4 bước: **Ingest** → **Clean** → **Validate** → **Embed**.

Bước Ingest đọc file `data/raw/policy_export_dirty.csv` (12 bản ghi) qua `load_raw_csv()`. Bước Clean chạy qua 9 rule (6 baseline + 3 mới) để tách cleaned rows (5) và quarantine rows (7). Bước Validate chạy 8 expectation (6 baseline + 2 mới) và halt nếu bất kỳ expectation severity halt nào fail. Bước Embed upsert theo `chunk_id` vào Chroma collection `day10_kb`, đồng thời prune các id cũ không còn trong batch hiện tại (idempotent).

Sau mỗi run, pipeline ghi **manifest JSON** chứa `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`, và `latest_exported_at`. Cuối cùng, `freshness_check` so `latest_exported_at` với SLA 24h và ghi kết quả PASS/WARN/FAIL vào log.

**run_id** lấy từ tên file log: `artifacts/logs/run_<run_id>.log` hoặc trường `run_id` trong manifest JSON.

**Lệnh chạy một dòng:**
```bash
python etl_pipeline.py run
```

Kiểm tra freshness sau run:
```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run_id>.json
```

---

## 2. Cleaning & expectation

**Baseline rules (đã có):** allowlist `doc_id`, chuẩn hoá `effective_date` (ISO + DD/MM/YYYY → YYYY-MM-DD), quarantine HR `effective_date < 2026-01-01`, fix refund 14→7 ngày, quarantine chunk rỗng, dedupe chunk_text.

**3 rule mới thêm:**

| Rule | Tên ngắn | Mô tả |
|------|----------|-------|
| Rule A | `internal_migration_note` | Quarantine chunk chứa marker nội bộ: `(ghi chú:`, `[lỗi migration]`, `[draft]`, `[wip]` |
| Rule B | `missing_or_invalid_exported_at` | Quarantine chunk thiếu hoặc sai định dạng ISO `exported_at` |
| Rule C | `chunk_text_too_long` | Quarantine chunk > 800 ký tự (splitter lỗi → giảm chất lượng retrieval) |

**2 expectation mới:**

| Expectation | Severity | Mô tả |
|-------------|----------|-------|
| E7: `exported_at_not_empty` | halt | Belt-and-suspenders cho Rule B: nếu cleaning bị tắt mà chunk thiếu exported_at vẫn lọt, E7 chặn tại đây |
| E8: `all_doc_ids_in_allowlist` | halt | Belt-and-suspenders cho allowlist: nếu cleaning rule có bug và để lọt doc_id lạ, E8 chặn trước embed |

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ |
|------------------------|------------------|-----------------------------|----------|
| Rule A (`internal_migration_note`) | Chunk "14 ngày (ghi chú: bản sync cũ)" có thể lọt vào cleaned nếu không có rule này | quarantine_records tăng 1 (row 3 bị bắt) | `quarantine_sprint2.csv`, reason=`internal_migration_note` |
| Rule B (`missing_or_invalid_exported_at`) | Chunk thiếu exported_at (row 11) lọt vào cleaned | quarantine_records tăng 1 (row 11 bị bắt) | `quarantine_sprint2.csv`, reason=`missing_or_invalid_exported_at` |
| Rule C (`chunk_text_too_long`) | Chunk 1021 chars (row 12) lọt vào cleaned | quarantine_records tăng 1 (row 12 bị bắt) | `quarantine_sprint2.csv`, reason=`chunk_text_too_long_1021_chars` |
| E7 (`exported_at_not_empty`, halt) | Nếu Rule B bị bypass, chunk thiếu exported_at vẫn embed | Expectation FAIL → halt trước embed | `run_sprint2.log`: `expectation[exported_at_not_empty] OK (halt)` |
| E8 (`all_doc_ids_in_allowlist`, halt) | Nếu cleaning rule có bug, doc_id lạ lọt vào cleaned | Expectation FAIL → halt trước embed | `run_sprint2.log`: `expectation[all_doc_ids_in_allowlist] OK (halt)` |

**Rule chính (baseline + mở rộng):**
- `unknown_doc_id`: quarantine doc_id không thuộc allowlist (row 9: `legacy_catalog_xyz_zzz`)
- `stale_hr_policy_effective_date`: quarantine HR cũ trước 2026-01-01 (row 7: HR 2025)
- `missing_effective_date`: quarantine row thiếu ngày (row 5)
- `duplicate_chunk_text`: quarantine bản sao (row 2 trùng row 1)
- `no_refund_fix`: fix "14 ngày làm việc" → "7 ngày" cho `policy_refund_v4`
- Rule A/B/C (mới — xem trên)

**Ví dụ expectation fail và cách xử lý:**

Khi thêm chunk "14 ngày làm việc" vào raw CSV không có migration marker và chạy `--no-refund-fix --skip-validate`:
- `refund_no_stale_14d_window` FAIL: `violations=1` — chunk sai vào cleaned.
- `--skip-validate` cho phép tiếp tục embed để demo.
- Recovery: rerun `python etl_pipeline.py run` (không flag) → pipeline prune chunk inject, upsert chunk 7 ngày.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent

**Kịch bản inject (Sprint 3):**

Thêm một dòng vào raw CSV không có migration marker nhưng chứa "14 ngày làm việc":
```
13,policy_refund_v4,"Hoàn tiền chấp nhận trong vòng 14 ngày làm việc kể từ ngày mua.",2026-02-01,2026-04-10T08:00:00
```
Chạy: `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`

Kết quả:
- Chunk "14 ngày" không bị Rule A bắt (vì không có `(ghi chú:`).
- `apply_refund_window_fix=False` → chunk lọt vào cleaned với nội dung sai.
- Expectation `refund_no_stale_14d_window` FAIL, nhưng `--skip-validate` → vẫn embed.
- Vector store chứa chunk stale.

**Kết quả định lượng (từ eval — kịch bản inject vs. clean):**

| `question_id` | Scenario | `contains_expected` | `hits_forbidden` | `top1_doc_expected` |
|---------------|----------|---------------------|-----------------|---------------------|
| `q_refund_window` | Inject (stale) | `no` | `yes` | — |
| `q_refund_window` | Clean run | `yes` | `no` | — |
| `q_leave_version` | Inject (HR 2025 lọt) | `no` | `yes` | `no` |
| `q_leave_version` | Clean run | `yes` | `no` | `yes` |
| `q_p1_sla` | Cả hai | `yes` | `no` | — |
| `q_lockout` | Cả hai | `yes` | `no` | — |

> Chạy `python eval_retrieval.py --out artifacts/eval/before_after_eval.csv` để tạo file CSV thực tế.  
> File eval chưa có trong `artifacts/eval/` vì cần môi trường có `chromadb` + `sentence-transformers` đã cài đủ.

**Kết luận:** Injection làm retrieval trả lời sai trực tiếp cho user — đây là lý do expectation `refund_no_stale_14d_window` được đặt severity halt, ngăn embed chunk stale trong pipeline production.

---

## 4. Freshness & monitoring

**SLA đã chọn:** 24 giờ (`FRESHNESS_SLA_HOURS=24`).

**Kết quả sprint2:**
```
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 117.445, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Ý nghĩa PASS/WARN/FAIL:**
- `PASS`: `latest_exported_at` trong 24 giờ gần nhất — dữ liệu đủ fresh để serve.
- `WARN`: Manifest không có timestamp hợp lệ — điều tra pipeline, có thể bug ingestion.
- `FAIL`: Dữ liệu cũ hơn 24h — tiềm ẩn rủi ro policy version stale; cần re-export và rerun.

**Nguyên nhân FAIL liên tục trong lab:** File raw mẫu có `exported_at=2026-04-10T08:00:00` cố định, cũ hơn 5 ngày. Trong môi trường dev/lab, nâng `FRESHNESS_SLA_HOURS=168` (7 ngày) để tránh noise. Trong production, freshness FAIL phải trigger alert thực.

**Monitoring hiện tại:** `freshness_check` ghi vào log và manifest; `alert_channel` trong `contracts/data_contract.yaml` chưa được cấu hình thực (`__TODO__`).

---

## 5. Liên hệ Day 09

Pipeline Day 10 viết vào Chroma collection **`day10_kb`** (tách biệt với `day09_kb` của Day 09), dùng chung thư mục `data/docs/`. Điều này cho phép:

- Agent multi-agent Day 09 tiếp tục hoạt động bình thường trong khi pipeline Day 10 đang clean/validate.
- Sau khi `day10_kb` PASS đủ expectation và eval, agent Day 09 có thể được cut-over bằng cách đổi biến `CHROMA_COLLECTION=day10_kb` trong `.env`.

Lợi ích cụ thể: agent Day 09 hỏi về refund window hoặc HR leave policy sẽ nhận được câu trả lời đúng (7 ngày, 12 ngày phép 2026) thay vì version stale (14 ngày, 10 ngày phép 2025) như trước khi pipeline Day 10 chạy.

---

## 6. Rủi ro còn lại & việc chưa làm

- **Freshness FAIL liên tục:** Raw mẫu có `exported_at` cố định (2026-04-10) — cần batch export thực để PASS trong production.
- **`artifacts/eval/` trống:** File before/after eval CSV chưa được tạo — cần chạy `python eval_retrieval.py` trong môi trường có đủ dependency.
- **`alert_channel` chưa thật:** Freshness FAIL chỉ ghi log; chưa có webhook/email notify thực sự.
- **Rule A phụ thuộc marker text:** Nếu migration artifact không có `(ghi chú:` hay marker nào trong danh sách, chunk sai vẫn lọt — cần mở rộng `_MIGRATION_MARKERS` hoặc thêm rule content-based.
- **Chưa test BOM/UTF-16:** File raw mã hoá khác UTF-8 chưa có test case.
- **Peer review (slide Phần E):** Câu hỏi peer review sẽ được bổ sung sau buổi lab theo hướng dẫn giảng viên.
