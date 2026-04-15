# Báo cáo cá nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Đặng Đinh Tú Anh (2A202600019)  
**Vai trò:** Ingestion Owner — D10-T01  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** 400–650 từ

---

## 1. Tôi phụ trách phần nào?

Tôi đảm nhiệm **D10-T01 — Ingestion & Schema Mapping**, bao gồm hai file chính:

- `etl_pipeline.py` — phần ingest: đọc file raw, validate input path, log `raw_records` với `task_id=D10-T01` và `owner=Dang Dinh Tu Anh` vào structured event log.
- `docs/data_contract.md` — điền đầy đủ source map (3 nguồn: `policy_export_dirty.csv`, `hr_leave_policy.txt`, `it_helpdesk_faq.txt`), failure mode, metric/alert cho từng nguồn; hoàn thiện schema cleaned (5 cột với kiểu dữ liệu, constraint, ghi chú); bổ sung bảng quy tắc quarantine vs drop và phần versioning canonical.

**Kết nối với thành viên khác:**

- Kết quả ingest (`raw_records=10`) được log ngay đầu pipeline, làm đầu vào cho D10-T02 (Quach Gia Duoc — cleaning). Manifest `manifest_sprint1.json` ghi lại `raw_path`, `raw_records`, `cleaned_records` để D10-T05 (Hoang Kim Tri Thanh) dùng cho freshness check.
- Schema cleaned trong `docs/data_contract.md` là tài liệu tham chiếu cho D10-T03 (Pham Quoc Dung) khi viết expectation suite.

**Bằng chứng:** Log `run_sprint1.log` dòng `event_json` với `task_id=D10-T01, owner=Dang Dinh Tu Anh, event=ingest_raw_count`.

---

## 2. Một quyết định kỹ thuật

Khi điền source map trong `docs/data_contract.md`, tôi phải quyết định **mức độ chi tiết của failure mode** cho từng nguồn. Thay vì liệt kê chung chung "dữ liệu lỗi", tôi chọn gắn từng failure mode với **expectation cụ thể và severity tương ứng**:

- Nguồn `policy_export_dirty.csv`: failure mode "stale refund window 14 ngày" → gắn với `no_stale_refund_window` (severity=**halt**) — pipeline dừng ngay nếu còn chunk sai.
- Nguồn `it_helpdesk_faq.txt`: failure mode "ngày sai format DD/MM/YYYY" → gắn với `effective_date_iso_yyyy_mm_dd` (severity=**halt**) và hành động quarantine.
- Nguồn `hr_leave_policy.txt`: failure mode "version conflict 10 vs 12 ngày phép" → gắn với `hr_leave_no_stale_10d_annual` (severity=**halt**) và cutoff `effective_date >= 2026-01-01`.

Lý do: nếu failure mode không gắn được metric/expectation cụ thể thì không observable — không biết khi nào lỗi xảy ra. Quyết định này giúp team D10-T03 biết rõ expectation nào cần viết để bao phủ từng nguồn.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Khi chạy `python etl_pipeline.py run --run-id sprint1` lần đầu, pipeline **exit code 3** với lỗi:

```
ERROR: chromadb chưa cài. pip install -r requirements.txt
PIPELINE_ERROR: embed stage failed.
```

Log cho thấy `task_id=D10-T05, event=embed_import_error` — lỗi thuộc phần Hoang Kim Tri Thanh (embed), không phải ingest. Tuy nhiên pipeline dừng trước khi ghi manifest. Tôi xác định nguyên nhân: lệnh `python` trong terminal đang trỏ vào Anaconda base (`/opt/anaconda3/bin/python`), không phải `.venv` nơi `chromadb` đã được cài. Fix: chạy lại bằng `/Users/tuanhdangdinh/Lab8-C401-E3/.venv/bin/python etl_pipeline.py run --run-id sprint1`. Pipeline pass hoàn toàn (`PIPELINE_OK`) và manifest được ghi đầy đủ. Đây là bài học về môi trường Python và tầm quan trọng của việc đọc `task_id` trong log để triage đúng owner.

---

## 4. Bằng chứng trước / sau

**Run ID:** `sprint1` — log tại `artifacts/logs/run_sprint1.log`, manifest tại `artifacts/manifests/manifest_sprint1.json`.

| Metric | Lần chạy 1 (Anaconda base) | Lần chạy 2 (.venv) |
|--------|---------------------------|---------------------|
| `raw_records` | 10 | 10 |
| `cleaned_records` | 6 | 6 |
| `quarantine_records` | 4 | 4 |
| Embed | FAIL (`embed_import_error`) | OK (`embed_upsert count=6`) |
| Pipeline status | exit 3 | **PIPELINE_OK** |

Tất cả 6 expectation đều `OK` ở cả hai lần chạy — xác nhận ingest và schema mapping đúng. Freshness check `FAIL` do `exported_at=2026-04-10` cũ hơn SLA 24h (~116 giờ) — đây là behavior **đúng và có chủ đích** của monitoring.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ bổ sung vào `etl_pipeline.py` phần **log `quarantine_rate`** ngay trong bước ingest (D10-T01): tính `quarantine_records / raw_records * 100` và ghi event `high_quarantine_rate_alert` với `level=WARN` khi tỉ lệ vượt 30%. Hiện tại run `sprint1` có `quarantine_rate=40%` (4/10) — vượt ngưỡng alert đã ghi trong `docs/data_contract.md` nhưng pipeline không tự phát hiện — đây là khoảng trống observability cần lấp.
