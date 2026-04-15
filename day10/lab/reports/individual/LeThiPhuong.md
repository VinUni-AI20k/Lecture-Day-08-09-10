# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lê Thị Phương
**Vai trò:** Quality & Expectations  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `quality/expectations.py` — thêm 2 expectation mới: E7 `no_migration_error_marker_in_cleaned` (halt) và E8 `sla_doc_effective_date_min_2026` (warn)
- `artifacts/quarantine/` — đọc và giải thích nội dung quarantine file sau mỗi run
- Tham gia điền bảng `metric_impact` trong `reports/group_report.md`

**Kết nối với thành viên khác:**

E7 là guard tương ứng với Rule 7 của Cleaning Specialist — nếu rule 7 bị bỏ hoặc bug, E7 sẽ halt pipeline trước khi embed. Pipeline Lead gọi `run_expectations()` sau clean, trước embed — tôi đảm bảo signature `(List[Dict], ) → (List[ExpectationResult], bool)` không thay đổi.

**Bằng chứng:**

- E7, E8 được thêm vào cuối `run_expectations()` trong `quality/expectations.py`
- Log `artifacts/logs/run_inject-bad.log`: `expectation[no_migration_error_marker_in_cleaned] FAIL (halt) :: violations=1`

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Chọn severity halt vs warn cho E7 và E8:**

Với E7 (`no_migration_error_marker_in_cleaned`): tôi chọn **halt** vì marker "lỗi migration" là dấu hiệu pipeline trước bị lỗi nguồn gốc — nếu Cleaning Specialist chưa thêm Rule 7, chunk này lọt vào cleaned và embed sẽ làm nhiễu retrieval. Halt ngăn damage trước khi xảy ra.

Với E8 (`sla_doc_effective_date_min_2026`): tôi chọn **warn** vì chunk SLA cũ ít gây hại hơn — SLA P1 không thay đổi thường xuyên như policy refund. Warn vẫn ghi vào log để alert, nhưng không block pipeline, tránh over-engineering cho rủi ro thấp. Phân tầng này giống design pattern của monitoring: **pager-worthy alert (halt)** vs **ticket-worthy alert (warn)**.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Khi chạy `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`, E3 (`refund_no_stale_14d_window`) FAIL với `violations=1` — đúng kỳ vọng. Tuy nhiên E7 cũng FAIL `violations=1` ngay cả khi Cleaning Specialist đã thêm Rule 7.

**Phát hiện:** Đọc kỹ log: `WARN: expectation failed but --skip-validate → tiếp tục embed`. Thực ra đây là hành vi đúng với flag `--skip-validate` — pipeline tiếp tục embed dù E7 halt. Đây không phải bug của expectation, mà là kịch bản inject có chủ đích Sprint 3.

**Xác nhận:** Chạy lại pipeline chuẩn (không flag) → E7 PASS vì Rule 7 đã quarantine chunk "lỗi migration" trước khi vào cleaned → `run_expectations()` không thấy vi phạm. Ghi lại trong quarantine CSV để chứng minh flow đúng.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Log `artifacts/logs/run_inject-bad.log` (trước — dùng `--skip-validate`):
```
run_id=inject-bad
raw_records=10
cleaned_records=5
quarantine_records=5
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
expectation[no_migration_error_marker_in_cleaned] FAIL (halt) :: violations=1
expectation[sla_doc_effective_date_min_2026] OK (warn) :: stale_sla_chunks=0
WARN: expectation failed but --skip-validate → tiếp tục embed
manifest_written=artifacts\manifests\manifest_inject-bad.json
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 122.535, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Log `artifacts/logs/run_clean-run.log` (sau — pipeline chuẩn):
```
run_id=clean-run
raw_records=10
cleaned_records=5
quarantine_records=5
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
expectation[no_migration_error_marker_in_cleaned] OK (halt) :: violations=0
expectation[sla_doc_effective_date_min_2026] OK (warn) :: stale_sla_chunks=0
manifest_written=artifacts\manifests\manifest_clean-run.json
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 122.541, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
PIPELINE_OK
```

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ tích hợp `pydantic` validate schema cleaned trước khi chạy expectation suite: mỗi row phải có `chunk_id: str`, `effective_date: date`, v.v. Validation schema-level bắt lỗi kiểu dữ liệu (ví dụ `effective_date` trả về string thay vì date object sau normalize) trước khi các expectation logic-level chạy — giảm false negative do type mismatch.s
