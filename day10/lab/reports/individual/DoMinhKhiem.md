# Báo cáo cá nhân — Lab Day 10

**Họ tên:** Đỗ Minh Khiêm  
**Vai trò:** Cleaning & Quality Owner (Sprint 2)  
**run_id tham chiếu:** sprint2_khiem · sprint2_khiem_final

---

## 1. Phần phụ trách cụ thể

| File | Nội dung |
|------|----------|
| `transform/cleaning_rules.py` | Thêm helper `_strip_bom()` strip U+FEFF từ đầu text; thêm 3 rules (7, 8, 9) vào `clean_rows()`: `short_chunk` (< 20 ký), `missing_exported_at` (empty), `bom_strip` (normalize U+FEFF trước dedup) |
| `quality/expectations.py` | Thêm 2 expectations mới (E7, E8) vào `run_expectations()`: `exported_at_all_populated` (warn), `chunk_text_min_length_20` (warn) |
| `data/raw/policy_export_dirty.csv` | Thêm 3 test rows (11, 12, 13) để trigger rule 7/8/9: short text, missing exported_at, BOM prefix |

---

## 2. Quyết định kỹ thuật: severity warn vs halt cho expectation mới

E7 (`exported_at_all_populated`) và E8 (`chunk_text_min_length_20`) được chọn `severity=warn` (không halt) vì:

**E7 logic:** exported_at rỗng → dữ liệu metadata không đầy đủ nhưng vẫn embed được. Nếu halt, mất luôn row; warn thì giữ dữ liệu và trigger cảnh báo SLA/freshness check.

**E8 logic:** chunk_text < 20 ký tự → có thể là label/title hợp lệ. Rule 7 đã quarantine (<20) ở pipeline logic, E8 là double-check trên cleaned rows. Nếu halt sẽ quá ngặt.

**Sắp xếp rule trong clean_rows():**
- Rule 7 (short_chunk) và Rule 8 (missing_exported_at) chạy **sau** rule baseline (doc_id allowlist, effective_date parse, HR stale, empty text) 
- Nhưng **trước** rule 5 (dedup) để đảm bảo không bị mất row vì dedup trước
- Rule 9 (bom_strip) chạy **trước** rule 5 (dedup) để strip BOM trước khi so sánh text → tránh false duplicate từ BOM

---

## 3. Sự cố / anomaly phát hiện

**Triệu chứng & phát hiện:**

Khi thiết kế rules mới, tôi cần verify chúng hoạt động đúng bằng test data. Nhưng baseline 10 rows CSV không trigger được các rule mới vì:
- Không có row nào có chunk_text < 20 ký tự
- Tất cả rows đều có exported_at
- Không có row nào bắt đầu với BOM

**Data injection:**

Thêm 3 rows test vào CSV:
- Row 11: `it_helpdesk_faq, "Ngắn quá" (8 ký tự)` → trigger Rule 7 (short_chunk)
- Row 12: `sla_p1_2026, "Ticket P2...", exported_at=""` → trigger Rule 8 (missing_exported_at)
- Row 13: `policy_refund_v4, "️Chunk... (start with U+FEFF BOM)"` → trigger Rule 9 (bom_strip)

**Metric trigger:**

Chạy pipeline 2 lần:
- `sprint2_khiem` (baseline 10 rows): cleaned=6, quarantine=4 (không bao gồm test rows)
- `sprint2_khiem_final` (13 rows): cleaned=7, quarantine=6 (+2 từ rule 7/8, +1 từ rule 9 pass sau strip)

**Fix code:**

Verify `_strip_bom()` function hoạt động: row 13 bị strip BOM, text còn lại >20 ký tự nên pass E8 và được clean.

---

## 4. Before / after (trích log và CSV)

**Baseline run** (`run_id=sprint2_khiem`):
```
raw_records=10
cleaned_records=6
quarantine_records=4
expectation[exported_at_all_populated] OK (warn) :: missing_exported_at_count=0
expectation[chunk_text_min_length_20] OK (warn) :: short_chunks_(<20_chars)=0
```

**After thêm 3 test rows** (`run_id=sprint2_khiem_final`):
```
raw_records=13
cleaned_records=7
quarantine_records=6
expectation[exported_at_all_populated] OK (warn) :: missing_exported_at_count=0
expectation[chunk_text_min_length_20] OK (warn) :: short_chunks_(<20_chars)=0
embed_upsert count=7
```

**CSV excerpt — quarantine_sprint2_khiem_final.csv (rows trigger):**
```
11,it_helpdesk_faq,Ngắn quá,2026-02-01,2026-04-10T08:00:00,short_chunk,,8
12,sla_p1_2026,Ticket P2 không có SLA.,2026-02-01,,missing_exported_at,,
```

Quarantine tăng từ 4 → 6 dòng (row 11, 12 từ rules mới). Cleaned tăng từ 6 → 7 (row 13 BOM strip pass). Tất cả expectations vẫn OK (warn severity không block). Embed successfully upsert 7 chunks vào Chroma collection `day10_kb`.

---

## 5. Cải tiến nếu có thêm 2 giờ

Viết test harness idempotency: chạy pipeline 2 lần với cùng raw CSV, so sánh `cleaned_sprint2_khiem_v1.csv` vs `cleaned_sprint2_khiem_v2.csv` bằng hash. Phải check:
- Số rows giống nhau (cleaned_records)
- `chunk_id` stable (không bị random)
- Quarantine rows giống nhau
- Nếu khác → có bug nondeterministic (vd set iteration order, random seed). Commit test case để CI catch regression.
