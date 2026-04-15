# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Hoàng Văn Kiên 
**Vai trò:** Cleaning Specialist  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `transform/cleaning_rules.py` — thêm 3 rule mới: `quarantine_stale_sla_effective_date` (Rule 4), `normalize_whitespace_in_chunk_text` (Rule 5), `quarantine_migration_error_marker` (Rule 7)
- Ghi `metric_impact` cho từng rule trong `reports/group_report.md` bảng 2a

**Kết nối với thành viên khác:**

Tôi làm việc song song với Quality (Rule 7 cần có E7 expectation tương ứng). Pipeline Lead gọi `clean_rows()` — tôi đảm bảo signature không thay đổi để không break `etl_pipeline.py`. Contract Owner cung cấp `ALLOWED_DOC_IDS` và `policy_versioning` để tôi viết rule đúng allowlist.

**Bằng chứng:**

- Hàm `_collapse_whitespace()` trong `cleaning_rules.py`
- Comment `metric_impact` trong docstring từng rule mới
- `quarantine_records` thay đổi từ 4 (ci-smoke baseline) lên 5 (pipeline chuẩn sau rule 7)

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Quarantine vs fix cho chunk "lỗi migration":**

Baseline đã có Rule 9 fix chunk "14 ngày làm việc" thành "7 ngày làm việc". Khi thêm Rule 7 cho chunk "lỗi migration", tôi đứng trước lựa chọn: (a) cũng fix bằng cách chỉ sửa cửa sổ hoàn tiền như Rule 9, hoặc (b) quarantine hoàn toàn.

Tôi chọn (b) vì chunk này mang marker rõ ràng `"lỗi migration"` từ pipeline trước — ngay cả sau khi sửa số ngày, context chunk vẫn chứa nội dung gây nhiễu ("ghi chú: bản sync cũ policy-v3"). Để vào vector store, agent retrieval có thể nhận context nhiễu dù số ngày đúng. Quarantine sạch hơn: version chuẩn đã có chunk `policy_refund_v4` "7 ngày làm việc" không có ghi chú lỗi, đủ để trả lời đúng.

Quyết định này làm `cleaned_records` giảm 1 (từ 6 xuống 5) và `quarantine_records` tăng 1 — có ý nghĩa observability rõ ràng.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Rule 7 use `text.lower()` nhưng `text` tại thời điểm check là sau `_collapse_whitespace()` (Rule 5). Ban đầu tôi viết Rule 7 trước Rule 5 trong luồng → `text` chưa được normalize → pattern `"lỗi migration"` có thể bị bỏ sót nếu có whitespace thừa giữa 2 chữ.

**Metric phát hiện:** Test thủ công inject row `"lỗi  migration"` (2 dấu cách) → Rule 7 không bắt được → chunk lọt vào cleaned → E7 `no_migration_error_marker_in_cleaned` FAIL.

**Fix:** Đổi thứ tự: Rule 5 (normalize whitespace) chạy **trước** Rule 7 (check marker). Code: `text = _collapse_whitespace(text)` ở dòng trước `if "lỗi migration" in text.lower()`. Sau fix: cả `"lỗi migration"` và `"lỗi  migration"` đều bị bắt đúng.

---

## 4. Bằng chứng trước / sau (80–120 từ)

`run_id=2026-04-15T10-00Z` — so sánh với `ci-smoke` (baseline chưa có rule 7):

**ci-smoke (trước — cleaned_records=6):**
```
policy_refund_v4_2_c96089a43e33aa9d,policy_refund_v4,Yêu cầu hoàn tiền...14 ngày... [cleaned: stale_refund_window],2026-02-01,...
```
Chunk "lỗi migration" được fix thành 7 ngày và vào cleaned.

**2026-04-15T10-00Z (sau — cleaned_records=5):**
Chunk đó không xuất hiện trong cleaned CSV. File quarantine có thêm dòng:
```
3,policy_refund_v4,...lỗi migration...,2026-02-01,...,migration_error_marker_detected,
```

`hits_forbidden=no` trên `q_refund_window` sau pipeline chuẩn — không còn chunk nhiễu.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ viết bộ unit test `pytest` cho từng rule trong `clean_rows()`: mỗi test inject một loại dirty row và assert `quarantine_records` tăng đúng 1. Hiện tại chỉ có kiểm chứng thủ công qua CSV. Unit test tự động hóa việc phát hiện regression khi rule được sửa đổi (ví dụ thứ tự rule 5 và 7 bị đảo lại).
