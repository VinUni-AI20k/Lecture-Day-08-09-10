# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Đỗ Minh Khiêm  
**Vai trò:** Cleaning & Quality Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài:** 520 từ

---

## 1. Tôi phụ trách phần nào? (118 từ)

**File / module:**

Tôi phụ trách hai module chính:
- `transform/cleaning_rules.py` — thêm 3 cleaning rules mới (rules 7, 8, 9) vào hàm `clean_rows()`
- `quality/expectations.py` — thêm 2 expectations mới (E7, E8) vào hàm `run_expectations()`

**Kết nối với thành viên khác:**

- **Kết nối xuống Sang**: Dữ liệu từ pipeline Sang (14 ngày làm việc refund fix) được tôi validate qua expectations
- **Kết nối sang Dũng**: Cleaned CSV tôi output sẽ được Dũng embed vào Chroma và eval trên before_after_eval.csv

**Bằng chứng (commit):**

Commit `7101cb2`: "Khiêm: Sprint 2 - Add 3 cleaning rules (short_chunk, missing_exported_at, bom_strip) + 2 expectations (E7, E8) with metric impact"

---

## 2. Một quyết định kỹ thuật (135 từ)

**Chọn severity cho expectation mới:**

Tôi quyết định E7 (`exported_at_all_populated`) và E8 (`chunk_text_min_length_20`) đều là `warn` (không `halt`), lý do:

1. **exported_at rỗng** là dấu hiệu dữ liệu không đủ metadata, nhưng không phải lỗi critical — vẫn có thể embed và tìm kiếm. Chỉ ảnh hưởng tới freshness tracking nên warn là hợp lý.

2. **chunk_text < 20 ký tự** có thể là label hoặc summary ngắn hợp lệ. Thay vì halt (chặn pipeline), tôi warn để giữ dữ liệu nhưng cảnh báo. Rules 7 đã quarantine những chunk quá ngắn, E8 là double-check trên cleaned rows.

**Chiến lược quarantine:**

Rule 7, 8 sắp xếp sau các rule baseline (doc_id allowlist, effective_date parse, HR stale) nhưng **trước deduplication** (Rule 5) vì khi đó text đã được strip BOM (Rule 9), giảm false duplicate.

---

## 3. Một lỗi hoặc anomaly đã xử lý (148 từ)

**Triệu chứng:**

Phát hiện 3 test cases khi sạo raw data:
- Row 11: "Ngắn quá" (8 ký tự) — chunk quá ngắn không đủ context
- Row 12: exported_at rỗng — dữ liệu metadata không đầy đủ
- Row 13: chunk bắt đầu với U+FEFF (BOM) — từ export Excel cũ có dấu hiệu BOM

**Metric phát hiện:**

- Rule 7 trigger: `quarantine_records` +1 (row 11, `reason=short_chunk, chunk_length=8`)
- Rule 8 trigger: `quarantine_records` +1 (row 12, `reason=missing_exported_at`)
- Rule 9 detection: row 13 bị strip BOM trong `_strip_bom()` helper, sau đó pass qua expectation E8 (chunk ≥ 20 ký tự → pass)

**Fix:**

Rule 9 `_strip_bom()` function normalize U+FEFF từ đầu chunk_text trước khi dedup, tránh text matching error. Sau khi strip, row 13 vẫn đủ dài (>20 ký tự) nên pass E8 và được clean.

---

## 4. Bằng chứng trước / sau (105 từ)

**run_id:** `sprint2_khiem_final`

**Log từ artifacts/logs/run_sprint2_khiem_final.log:**

```
raw_records=13
cleaned_records=7
quarantine_records=6
expectation[exported_at_all_populated] OK (warn) :: missing_exported_at_count=0
expectation[chunk_text_min_length_20] OK (warn) :: short_chunks_(<20_chars)=0
```

**CSV: artifacts/quarantine/quarantine_sprint2_khiem_final.csv**

```
11,it_helpdesk_faq,Ngắn quá,2026-02-01,2026-04-10T08:00:00,short_chunk,,8
12,sla_p1_2026,Ticket P2 không có SLA.,2026-02-01,,missing_exported_at,,
```

6 dòng quarantine (gồm 2 từ tôi thêm) được lưu. Cleaned CSV có 7 rows thay vì 10 raw, chứa đủ bối cảnh và valid metadata.

---

## 5. Cải tiến tiếp theo (30 từ)

Nếu có +2 giờ, tôi sẽ:
- Thêm Rule 10: validate `chunk_id` stable (không bị thay đổi khi re-run) bằng cách test idempotency 2 lần
- Viết unit test cho `_strip_bom()` với test data chứa BOM từ UTF-8 BOM signature
