# PERSON 1 - CLEANING OWNER - GHI CHÚ

## Metrics Baseline
```
Run ID: baseline-person1
Date: 2024-04-15
raw_records=10
cleaned_records=6
quarantine_records=4
```

## Metrics After Adding 3 Rules
```
Run ID: person1-with-rules
Date: 2024-04-15
raw_records=10
cleaned_records=6
quarantine_records=4
```

## 3 Rules Đã Thêm

### Rule 7: Quarantine chunk_text quá ngắn
- **File:** `transform/cleaning_rules.py` line ~95
- **Logic:** `if len(text.strip()) < MIN_CHUNK_LENGTH (20 chars)`
- **Impact trên data mẫu:** Không có (data mẫu không có chunk < 20 chars)
- **Impact trên inject test:** Sẽ test ở Sprint 3

### Rule 8: Quarantine invalid characters (BOM, null bytes)
- **File:** `transform/cleaning_rules.py` line ~107
- **Logic:** `if '\ufeff' in text or '\x00' in text`
- **Impact trên data mẫu:** Không có
- **Impact trên inject test:** Sẽ test ở Sprint 3

### Rule 9: Quarantine invalid exported_at format
- **File:** `transform/cleaning_rules.py` line ~120
- **Logic:** `if exported_at and not _EXPORTED_AT_PATTERN.match(exported_at)`
- **Impact trên data mẫu:** Không có (tất cả exported_at đều đúng format)
- **Impact trên inject test:** Sẽ test ở Sprint 3

## Quyết Định Kỹ Thuật
- Chọn **quarantine** thay vì **drop** cho các rules trên vì:
  - Không mất dữ liệu vĩnh viễn
  - Có thể review sau
  - Có audit trail với reason rõ ràng

## TODO Sprint 3
- [ ] Tạo inject test data với:
  - Chunk ngắn < 20 chars
  - Text có BOM character
  - exported_at sai format
- [ ] Chạy pipeline với inject data
- [ ] So sánh metrics before/after
- [ ] Ghi vào metric_impact table

## Artifacts
- Baseline log: `artifacts/logs/run_baseline-person1.log`
- With rules log: `artifacts/logs/run_person1-with-rules.log`
- Baseline quarantine: `artifacts/quarantine/quarantine_baseline-person1.csv`
- With rules quarantine: `artifacts/quarantine/quarantine_person1-with-rules.csv`
