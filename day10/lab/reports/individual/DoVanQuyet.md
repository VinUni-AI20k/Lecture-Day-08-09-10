# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Đỗ Văn Quyết
**Vai trò:** Data Ingestion & Contract  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `contracts/data_contract.yaml` — điền `owner_team`, `alert_channel`, `freshness.sla_hours`, `canonical_sources`
- `docs/data_contract.md` — source map 2 nguồn, schema cleaned, quarantine rules, canonical versions
- `transform/cleaning_rules.py` — hàm `load_raw_csv()`, `_normalize_effective_date()`, `write_cleaned_csv()`, `write_quarantine_csv()`

**Kết nối với thành viên khác:**

Tôi cung cấp `ALLOWED_DOC_IDS` và schema cột CSV cho Cleaning Specialist để viết rule. Contract YAML là nguồn tham chiếu duy nhất cho `policy_versioning.hr_leave_min_effective_date` — Cleaning Specialist đọc giá trị này thay vì hard-code. Monitoring Owner dùng `freshness.sla_hours` từ contract để cấu hình SLA check.

**Bằng chứng:**

- `contracts/data_contract.yaml`: `owner_team: "Nhom11-402"`, `freshness.sla_hours: 24`, `alert_channel: "slack:#data-quality"`
- `load_raw_csv()` xử lý encoding UTF-8 và strip whitespace toàn bộ field

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Schema `chunk_id` — hash vs sequential ID:**

Tôi cân nhắc 2 cách tạo `chunk_id`: (a) sequential integer (`doc_id_seq`), hoặc (b) hash SHA-256 ngắn của `doc_id|chunk_text|seq`. Tôi chọn (b) vì `chunk_id` cần **ổn định theo nội dung**: nếu cùng một chunk text xuất hiện ở 2 run khác nhau, nó phải có cùng ID để upsert Chroma không tạo bản ghi mới.

Format cuối: `{doc_id}_{seq}_{sha256[:16]}` — có đủ tiền tố `doc_id` để dễ debug, có `seq` để phân biệt chunk cùng doc, có hash để ổn định theo nội dung. Nhược điểm đã ghi vào `docs/pipeline_architecture.md` mục "Rủi ro đã biết": seq phụ thuộc thứ tự CSV → nếu source thay đổi thứ tự dòng, ID có thể đổi dù text không đổi.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** `write_quarantine_csv()` ban đầu raise `ValueError: dict contains fields not in fieldnames` vì các row quarantine có cột dynamic (`reason`, `effective_date_raw`, `effective_date_normalized`) không đồng nhất giữa các loại lỗi.

**Metric phát hiện:** Exception tại bước ghi quarantine CSV sau lần chạy đầu tiên với file dirty có nhiều loại lỗi khác nhau.

**Fix:** Dùng `DictWriter` với `extrasaction='ignore'` và fieldnames là union hợp lý của tất cả cột có thể xuất hiện: `chunk_id, doc_id, chunk_text, effective_date, exported_at, reason, effective_date_raw, effective_date_normalized`. Các cột không có giá trị ở row đó sẽ ghi rỗng. Điều này đảm bảo file quarantine luôn có header nhất quán để dễ đọc/phân tích.

---

## 4. Bằng chứng trước / sau (80–120 từ)

`run_id=2026-04-15T10-00Z` — `artifacts/quarantine/quarantine_2026-04-15T10-00Z.csv`:

```
chunk_id,doc_id,chunk_text,effective_date,exported_at,reason,effective_date_normalized
2,policy_refund_v4,...,2026-02-01,...,duplicate_chunk_text,
5,policy_refund_v4,,,2026-04-10T08:00:00,missing_effective_date,
7,hr_leave_policy,...,2025-01-01,...,stale_hr_policy_effective_date,2025-01-01
9,legacy_catalog_xyz_zzz,...,2026-02-01,...,unknown_doc_id,
3,policy_refund_v4,...(lỗi migration)...,2026-02-01,...,migration_error_marker_detected,
```

5 dòng quarantine khớp với `quarantine_records=5` trong manifest — xác nhận schema contract đúng và rules hoạt động.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ viết loader tự động đọc `hr_leave_min_effective_date` và `canonical_sources` từ `data_contract.yaml` (dùng `pyyaml`) rồi truyền vào `clean_rows()` thay vì hard-code `"2026-01-01"` trong code. Điều này đáp ứng Distinction criterion "rule versioning không hard-code" và giúp cập nhật policy chỉ cần sửa YAML, không cần sửa Python.
