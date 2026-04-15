# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Hồ Thị Tố Nhi 
**Vai trò:** Monitoring / Docs Owner
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `monitoring/freshness_check.py` — hàm `check_manifest_freshness()`, `parse_iso()`
- `docs/runbook.md` — 5 mục: Symptom → Detection → Diagnosis → Mitigation → Prevention
- `docs/quality_report_template.md` — điền đầy đủ số liệu before/after, freshness, Sprint 3
- Đọc và giải thích kết quả `python etl_pipeline.py freshness --manifest ...` sau mỗi run

**Kết nối với thành viên khác:**

Tôi đọc manifest do Pipeline Lead tạo ra để chạy freshness check. Kết quả freshness check ghi vào log là tín hiệu cuối cùng trước khi pipeline kết thúc — tôi là "last line of defense" về observability. Quality Report tổng hợp kết quả từ tất cả vai trò khác.

**Bằng chứng:**

- `monitoring/freshness_check.py`: `parse_iso()` xử lý cả format có timezone và không có timezone
- `docs/runbook.md` có đủ 5 mục theo thứ tự SCORING yêu cầu
- Log dòng cuối: `freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 122.0, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}`

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Xử lý timestamp không có timezone trong `parse_iso()`:**

Source system trong bộ mẫu ghi `exported_at = "2026-04-10T08:00:00"` — không có timezone info. Python `datetime.fromisoformat()` parse thành naive datetime, và khi so sánh với `datetime.now(timezone.utc)` (aware datetime) sẽ raise `TypeError: can't compare offset-naive and offset-aware datetimes`.

Tôi fix bằng cách detect `dt.tzinfo is None` sau khi parse và gán `tzinfo=timezone.utc`: `dt = dt.replace(tzinfo=timezone.utc)`. Giả định UTC là hợp lý vì source export thường là UTC trong môi trường đồng nhất. Nếu source có timezone khác, cần thêm config `SOURCE_TIMEZONE` trong contract YAML — ghi vào mục Prevention của runbook.

Quyết định này đảm bảo `freshness_check` không crash với timestamp thực tế từ bộ mẫu.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_ci-smoke.json` trả về `WARN {"reason": "no_timestamp_in_manifest"}` thay vì FAIL hay PASS.

**Phát hiện:** Đọc manifest `ci-smoke`: `"latest_exported_at": "2026-04-10T08:00:00"` — trường có giá trị. Trace vào `check_manifest_freshness()`: `ts_raw = data.get("latest_exported_at") or data.get("run_timestamp")` → `ts_raw` = `"2026-04-10T08:00:00"` → `parse_iso(str(ts_raw))` → trả về `None`.

**Nguyên nhân:** `parse_iso()` kiểm tra `ts.endswith("Z")` rồi gọi `fromisoformat()` — nhưng string `"2026-04-10T08:00:00"` không có `Z` và không có `+HH:MM`, `fromisoformat()` trả về naive datetime, code cũ không gán tzinfo → so sánh crash → except ValueError → trả về None.

**Fix:** Thêm `if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)` sau `fromisoformat()`. Sau fix: FAIL với `age_hours=122.0`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

`run_id=2026-04-15T10-00Z` — dòng log freshness (sau fix `parse_iso`):

```
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 122.0, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

So với lần đầu (trước fix — parse_iso trả None):
```
freshness_check=WARN {"reason": "no_timestamp_in_manifest", "manifest": {...}}
```

FAIL thay vì WARN là hành vi đúng: dữ liệu mẫu có ngày 2026-04-10, lab ngày 2026-04-15 → đã 5 ngày → vi phạm SLA 24h. WARN sai lệch sẽ che giấu sự cố freshness thật sự trong production.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ mở rộng `freshness_check.py` để đo **2 boundary riêng**: (1) `ingest_boundary = latest_exported_at` từ source, (2) `publish_boundary = run_timestamp` từ manifest. So sánh cả 2 với SLA cho phép phân biệt "source crawl chậm" vs "pipeline chạy chậm" — thông tin này quan trọng khi điều tra incident theo runbook.
