# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** ___________  
**Vai trò:** Ingestion / Cleaning — Ingestion + Data Contract (Sprint 1)  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ** (ngắn hơn Day 09 vì rubric slide cá nhân ~10% — vẫn phải đủ bằng chứng)

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `docs/data_contract.md`
- `etl_pipeline.py run --run-id sprint1` (entrypoint vận hành pipeline)
- Artifacts kiểm chứng: `artifacts/logs/run_sprint1.log`, `artifacts/cleaned/cleaned_sprint1.csv`, `artifacts/quarantine/quarantine_sprint1.csv`, `artifacts/manifests/manifest_sprint1.json`

**Kết nối với thành viên khác:**

Trong Sprint 1, tôi tập trung phần ingestion baseline và data contract để tạo đầu vào ổn định cho các bạn phụ trách cleaning/quality ở Sprint 2. Tôi điền source map trong `docs/data_contract.md` với các nguồn chính (`policy_export_dirty.csv`, canonical policy/refund, canonical HR leave), nêu failure mode và metric/alert để cả nhóm dùng chung tiêu chí kiểm tra. Sau đó tôi chạy pipeline với `run_id=sprint1` để tạo bộ artifacts chuẩn ban đầu. Bộ này được dùng làm mốc để thành viên quality mở rộng rule/expectation ở Sprint 2 và thành viên monitoring dùng manifest/freshness ở Sprint 4.

**Bằng chứng (commit / comment trong code):**

- Log có đủ DoD Sprint 1: `run_id=sprint1`, `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`.
- Manifest ghi nhận run thành công và metadata cần thiết để trace lại pipeline.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

> VD: chọn halt vs warn, chiến lược idempotency, cách đo freshness, format quarantine.

Quyết định kỹ thuật tôi chọn ở Sprint 1 là giữ pipeline chạy theo luồng đầy đủ `ingest -> clean -> validate -> embed` ngay từ lần run đầu, thay vì chỉ dừng ở bước đọc raw. Lý do: nếu chỉ kiểm đếm raw thì chưa chứng minh được publish boundary và chưa tạo đủ artifacts cho các sprint sau. Với `run_id=sprint1`, tôi chấp nhận việc freshness có thể FAIL do dữ liệu mẫu cũ, nhưng vẫn ưu tiên tạo `cleaned/quarantine/manifest` để thiết lập khả năng quan sát đầu cuối. Tôi cũng ghi rõ source map trong `docs/data_contract.md` để mỗi failure mode có metric đi kèm (ví dụ tỉ lệ quarantine, expectation halt với stale refund window). Cách này giúp nhóm có cùng “ngôn ngữ dữ liệu” trước khi thêm rule mới, tránh tranh luận cảm tính khi bước vào Sprint 2.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

> Mô tả triệu chứng → metric/check nào phát hiện → fix.

Anomaly tôi gặp khi chạy Sprint 1 là pipeline qua được ingest/clean/validate nhưng fail ở bước embed do lỗi môi trường liên quan `torchvision` (stack trace báo `operator torchvision::nms does not exist`, kéo theo `ModuleNotFoundError: BertModel`). Triệu chứng thể hiện rõ: log đã in đủ các expectation `OK`, nhưng process dừng trước khi ghi `manifest_written` và `PIPELINE_OK`. Tôi xác định đây không phải lỗi logic cleaning mà là conflict dependency runtime. Cách xử lý: gỡ package `torchvision` đang lệch phiên bản trong môi trường local, sau đó chạy lại đúng lệnh `python etl_pipeline.py run --run-id sprint1`. Kết quả sau fix: pipeline in `embed_upsert count=6`, ghi manifest thành công và kết thúc `PIPELINE_OK`. Việc này giúp tôi tách bạch rõ lỗi “hạ tầng môi trường” với lỗi “chất lượng dữ liệu”.

---

## 4. Bằng chứng trước / sau (80–120 từ)

> Dán ngắn 2 dòng từ `before_after_eval.csv` hoặc tương đương; ghi rõ `run_id`.

Tôi dùng so sánh trước/sau ở mức ingestion-cleaning cho Sprint 1 (tương đương before/after ở tầng dữ liệu thô -> dữ liệu publish):

- **Before (raw):** `raw_records=10` từ `data/raw/policy_export_dirty.csv`.
- **After (publish input):** `cleaned_records=6`, `quarantine_records=4` trong `run_sprint1.log`.

Ví dụ dòng dữ liệu sau clean trong `cleaned_sprint1.csv`:
- `policy_refund_v4_2_...,"...7 ngày... [cleaned: stale_refund_window]"`

Ví dụ dòng bị quarantine trong `quarantine_sprint1.csv`:
- record `chunk_id=7` có reason `stale_hr_policy_effective_date`
- record `chunk_id=9` có reason `unknown_doc_id`

Các bằng chứng này cho thấy rule clean và cơ chế quarantine đã tác động đo được ngay ở Sprint 1.

---

## 5. Cải tiến tiếp theo (40–80 từ)

> Nếu có thêm 2 giờ — một việc cụ thể (không chung chung).

Nếu có thêm 2 giờ, tôi sẽ bổ sung script kiểm tra “artifact diff” tự động giữa các run (so sánh `cleaned/quarantine/manifest` theo `run_id`) và xuất bảng tóm tắt metric thay đổi. Việc này giúp Sprint 2–3 chứng minh `metric_impact` nhanh hơn, giảm thao tác thủ công khi viết `group_report.md`.
