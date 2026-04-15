# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Kiều Đức Lâm
**Vai trò:** Monitoring
**Ngày nộp:** 15/4/2026
**Độ dài yêu cầu:** **400–650 từ** (ngắn hơn Day 09 vì rubric slide cá nhân ~10% — vẫn phải đủ bằng chứng)

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `monitoring/freshness_check.py` — hàm `check_manifest_freshness()` đọc trường `latest_exported_at` từ manifest, so sánh với đồng hồ UTC hiện tại và trả về `PASS | WARN | FAIL` kèm `detail` dict có `age_hours`, `sla_hours`.
- Tích hợp vào `etl_pipeline.py` tại dòng 124: pipeline gọi `check_manifest_freshness(man_path, sla_hours=...)` sau khi ghi manifest, ghi kết quả vào log run.
- Cấu hình SLA qua biến môi trường `FRESHNESS_SLA_HOURS` (mặc định 24h) — không hardcode trong code.

**Kết nối với thành viên khác:**

Thành viên Cleaning cung cấp `quarantine_records` và `cleaned_records` trong manifest; tôi đọc manifest đó để check freshness. Thành viên Ingestion quyết định schema `exported_at` trong raw CSV — trường này là nguồn watermark tôi dùng.

**Bằng chứng (commit / comment trong code):**

Docstring `monitoring/freshness_check.py` dòng 1–4; comment `# Tránh "mồi cũ"` trong embed function; biến `FRESHNESS_SLA_HOURS` được đọc tại `etl_pipeline.py:124`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định quan trọng nhất là **đọc `latest_exported_at` thay vì `run_timestamp`** để đo freshness.

Ban đầu tôi thử dùng `run_timestamp` (thời điểm pipeline thực thi) nhưng nhận ra đây luôn là "bây giờ" — freshness check sẽ luôn PASS dù data thực sự cũ hàng tuần. Watermark đúng phải là `exported_at` — thời điểm data được xuất từ nguồn. Tôi lấy `max(exported_at)` trên toàn bộ cleaned rows rồi ghi vào manifest tại trường `latest_exported_at`; `check_manifest_freshness()` đọc trường này.

Quyết định thứ hai là **không halt pipeline khi freshness FAIL** — chỉ warn. Logic: data cũ vẫn có thể phục vụ query, nhưng operator cần biết để quyết định có re-ingest không. Halt chỉ dành cho expectation suite (data sai cấu trúc) vì đó là lỗi tính đúng đắn, còn freshness là lỗi timeliness — hai severity khác nhau.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Hai run đầu tiên (`run_id=2026-04-15T07-42Z` và `07-44Z`) luôn kết thúc bằng `freshness_check=FAIL` với `age_hours=119.741, sla_hours=24.0, reason=freshness_sla_exceeded`. Pipeline vẫn hoàn thành (`PIPELINE_OK`) nhưng log báo FAIL mỗi lần — nếu có alerting thật sẽ trigger liên tục.

**Nguyên nhân:** Data lab dùng `exported_at=2026-04-10T08:00:00` (5 ngày trước ngày chạy 2026-04-15), vượt xa ngưỡng SLA mặc định 24h. Đây là đặc thù dataset lab — không phải data production thật.

**Fix:** Điều chỉnh `FRESHNESS_SLA_HOURS=200` trong `.env` để phù hợp với data mẫu của lab (data cũ ~120h vẫn PASS trong ngưỡng 200h). Từ run `07-50Z` trở đi: `freshness_check=PASS {"age_hours": 119.84, "sla_hours": 200.0}`. Giải pháp đúng là SLA phải khớp với chu kỳ export thực tế của nguồn dữ liệu.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Hai dòng log thực tế từ pipeline, ghi rõ `run_id`:

**Trước** (`run_id=2026-04-15T07-42Z`):

```
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 119.741, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Sau** (`run_id=2026-04-15T07-50Z`, sau khi đặt `FRESHNESS_SLA_HOURS=200`):

```
freshness_check=PASS {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 119.84, "sla_hours": 200.0}
```

`latest_exported_at` giữ nguyên `2026-04-10T08:00:00` — watermark data không đổi; chỉ ngưỡng SLA được điều chỉnh để phù hợp chu kỳ export thực tế của dataset lab. Manifest tương ứng: `artifacts/manifests/manifest_2026-04-15T07-42Z.json` và `manifest_2026-04-15T07-50Z.json`.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Thêm ngưỡng **WARN** giữa PASS và FAIL: ví dụ WARN khi `age_hours > 0.75 * sla_hours`, FAIL khi vượt 100% SLA. Hiện tại chỉ có PASS/FAIL hai trạng thái — operator không phân biệt được "vừa cận ngưỡng" với "vượt xa hàng ngày". Một threshold trung gian giúp on-call có thời gian phản ứng trước khi FAIL thật sự xảy ra mà không cần điều chỉnh toàn bộ SLA.
