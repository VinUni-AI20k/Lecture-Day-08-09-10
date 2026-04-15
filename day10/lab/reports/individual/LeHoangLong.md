# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lê Hoang Long 
**Vai trò:** Pipeline & Architecture Lead  
**Ngày nộp:** 15-4-2026  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `etl_pipeline.py` — toàn bộ entrypoint: hàm `cmd_run()`, `cmd_embed_internal()`, `cmd_freshness()`, `main()`
- `docs/pipeline_architecture.md` — sơ đồ Mermaid, bảng ranh giới trách nhiệm

**Kết nối với thành viên khác:**

Tôi điều phối luồng gọi giữa các module: `cmd_run()` gọi `clean_rows()` (Cleaning Specialist), `run_expectations()` (Quality), rồi `cmd_embed_internal()` (Embed). Manifest JSON là artifact trung gian mà Monitoring Owner đọc để chạy freshness check. Tôi thống nhất format `run_id` và tên file artifact với toàn nhóm để log không bị lẫn lộn giữa các lần chạy.

**Bằng chứng:**

- `run_id` sinh tự động UTC timestamp: `run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%MZ")`
- Manifest ghi đủ `raw_records`, `cleaned_records`, `quarantine_records`, `run_id`, `latest_exported_at`
- File log: `artifacts/logs/run_2026-04-15T10-00Z.log`

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Chiến lược prune vector cũ trước upsert:**

Khi thiết kế `cmd_embed_internal()`, tôi đứng trước lựa chọn: (a) chỉ upsert và để index tích lũy, hoặc (b) prune id không còn trong cleaned trước khi upsert. Tôi chọn (b) vì đây là yêu cầu cốt lõi của observability: **index phải là snapshot của cleaned hiện tại**, không phải union của mọi run.

Nếu chỉ upsert, một chunk bị quarantine ở run sau vẫn còn vector cũ trong Chroma → agent retrieval vẫn thấy chunk "14 ngày làm việc" dù pipeline đã pass. Prune giải quyết điều này: `drop = prev_ids - set(current_ids)` → `col.delete(ids=drop)`. Tôi đặt severity là `WARN` nếu prune gặp lỗi (exception) thay vì halt, vì lỗi prune không blocking nhưng cần ghi log để debug.

Log ghi `embed_prune_removed=N` cho phép Monitoring Owner xác nhận "publish boundary" sau mỗi run.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Lần đầu chạy `python etl_pipeline.py run` với `--run-id` chứa dấu `:` (vd `2026-04-15T10:00Z`), Windows raise `FileNotFoundError` khi tạo file log/manifest vì `:` không hợp lệ trong tên file trên NTFS.

**Metric phát hiện:** Exception traceback tại `_log(log_path, ...)` — `log_path` chứa `:` trong tên.

**Fix:** Chuẩn hóa `run_id` khi dùng làm tên file: `run_id.replace(':', '-')` ở mọi chỗ tạo path (`log_path`, `cleaned_path`, `quar_path`, `man_path`). Sinh `run_id` mặc định dùng `%Y-%m-%dT%H-%MZ` (dấu `-` thay `:`) từ đầu để tránh vấn đề trên mọi OS.

Sau fix: `artifacts/logs/run_2026-04-15T10-00Z.log` tạo thành công trên cả Windows và Linux.

---

## 4. Bằng chứng trước / sau (80–120 từ)

`run_id=2026-04-15T10-00Z` — pipeline chuẩn (không flag inject):

**Manifest (sau):**
```json
{
  "run_id": "2026-04-15T10-00Z",
  "raw_records": 10,
  "cleaned_records": 5,
  "quarantine_records": 5,
  "no_refund_fix": false,
  "skipped_validate": false
}
```

So với `ci-smoke` (baseline — trước khi thêm rule 7 quarantine_migration_error_marker):
```json
{ "cleaned_records": 6, "quarantine_records": 4 }
```

`cleaned_records` giảm từ 6 xuống 5 do rule mới quarantine thêm row "lỗi migration" — đúng với `metric_impact` trong group report.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ tách `cmd_run()` thành pipeline DAG rõ ràng hơn: mỗi bước (ingest, clean, validate, embed) trả về `StepResult` với `status`, `duration_ms`, và `record_delta`. Điều này cho phép freshness check đo **2 boundary riêng** (ingest timestamp vs publish timestamp) thay vì chỉ dùng `latest_exported_at` từ source, đáp ứng Distinction criterion của SCORING.
