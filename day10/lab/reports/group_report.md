# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Team 62  
**Thành viên:**
| # | Tên | Vai trò (Day 10) | Email |
|---|-----|------------------|-------|
| 1 | Phan Thanh Sang | Ingestion Owner | sang.phan2409@gmail.com |
| 2 | Đỗ Minh Khiêm | Cleaning / Quality Owner | dokhiem562@gmail.com |
| 3 | Trần Tiến Dũng | Embed Owner | tiendungtran2005@gmail.com |
| 4 | Ngô Hải Văn | Inject & Evidence Owner | ngohaivan7@gmail.com |
| 5 | Trần Đình Minh Vương | Monitoring / Docs Owner | vuongsky55.cv@gmail.com |

**Ngày nộp:** 2026-04-15  
**Repo:** https://github.com/hvan128/team62-lecture-Day-08-09-10  
**Độ dài:** ~950 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

**Nguồn raw:** CSV mẫu `data/raw/policy_export_dirty.csv` mô phỏng export từ policy management system. File chứa 13 records (sau khi Văn inject thêm) với các failure mode: duplicate, missing effective_date, stale HR version (10 ngày phép năm), stale refund window (14 ngày), missing exported_at, và BOM characters.

**Tóm tắt luồng:**
1. **Ingest:** Load raw CSV → 13 records (10 baseline + 3 inject test)
2. **Transform:** Apply cleaning rules → 7 cleaned + 6 quarantine
   - Allowlist doc_id (policy_refund_v4, sla_p1_2026, it_helpdesk_faq, hr_leave_policy)
   - Normalize effective_date (DD/MM/YYYY → YYYY-MM-DD)
   - Quarantine HR < 2026-01-01, short chunk (<20 chars), missing exported_at
   - Fix refund 14→7 days, dedupe, strip BOM (1 record có BOM)
3. **Quality:** Run 8 expectations (6 baseline + 2 mới) → 3 halt, 5 warn → ALL PASS
4. **Embed:** Upsert 7 chunks vào ChromaDB collection `day10_kb` (idempotent)
5. **Monitor:** Generate manifest + freshness check (FAIL: age 121h > SLA 24h)

**run_id:** Lấy từ `--run-id` flag hoặc auto-generate UTC timestamp (vd: `sprint1`, `vuong-sprint4-test`, `van-inject-bad`). Ghi trong log dòng đầu: `run_id=sprint1`.

**Lệnh chạy một dòng:**
```bash
python etl_pipeline.py run --run-id sprint1
```

**Artifacts chính:**
- Manifest: `artifacts/manifests/manifest_sprint1.json`, `manifest_vuong-sprint4-test.json`
- Log: `artifacts/logs/run_sprint1.log`, `run_vuong-sprint4-test.log`
- Cleaned: `artifacts/cleaned/cleaned_sprint1.csv` (6 rows), `cleaned_vuong-sprint4-test.csv` (7 rows)
- Quarantine: `artifacts/quarantine/quarantine_sprint1.csv` (4 rows), `quarantine_vuong-sprint4-test.csv` (6 rows)

---

## 2. Cleaning & expectation (150–200 từ)

**Baseline rules (6):** Allowlist doc_id, normalize effective_date (ISO), quarantine HR stale (<2026-01-01), quarantine empty chunk_text/effective_date, dedupe chunk_text, fix refund 14→7 days.

**Baseline expectations (6):** min_one_row (halt), no_empty_doc_id (halt), refund_no_stale_14d_window (halt), chunk_min_length_8 (warn), effective_date_iso_yyyy_mm_dd (halt), hr_leave_no_stale_10d_annual (halt).

**Nhóm thêm (Khiêm - Cleaning & Quality Owner):**

**Rules mới (3):**
- **Rule 7:** Quarantine short_chunk (<20 chars) → loại chunk không đủ context
- **Rule 8:** Quarantine missing_exported_at → cần timestamp cho freshness check
- **Rule 9:** Strip BOM (\ufeff) từ đầu chunk_text → normalize trước dedupe

**Expectations mới (2):**
- **E7:** exported_at_all_populated (warn) → validate rule 8
- **E8:** chunk_text_min_length_20 (warn) → validate rule 7

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| Rule 7: short_chunk | quarantine_records=4 (sprint1) | quarantine_records=6 (vuong-sprint4-test) | artifacts/quarantine/quarantine_vuong-sprint4-test.csv |
| Rule 8: missing_exported_at | quarantine_records=4 (sprint1) | quarantine_records=6 (nếu inject thiếu exported_at) | artifacts/logs/run_sprint1.log |
| Rule 9: bom_stripped | cleaning_bom_stripped=0 (sprint1) | cleaning_bom_stripped=1 (vuong-sprint4-test) | artifacts/logs/run_vuong-sprint4-test.log line 5 |
| E7: exported_at_all_populated | OK (warn) sprint1 | OK (warn) vuong-sprint4-test | artifacts/logs/run_vuong-sprint4-test.log line 13 |
| E8: chunk_text_min_length_20 | OK (warn) sprint1 | OK (warn) vuong-sprint4-test | artifacts/logs/run_vuong-sprint4-test.log line 14 |

**Metric impact thực tế từ log:**
- `cleaning_bom_stripped=1` → Rule 9 hoạt động (1 record có BOM được strip)
- `quarantine_records` tăng từ 4 (sprint1) lên 6 (vuong-sprint4-test) → Rules 7, 8 hoạt động
- Tất cả expectations PASS → data quality đảm bảo

**Rule chính (baseline + mở rộng):**
- Allowlist doc_id → quarantine unknown_doc_id
- Normalize effective_date → quarantine invalid_effective_date_format
- Quarantine HR stale → quarantine stale_hr_policy_effective_date
- Fix refund 14→7 → expectation refund_no_stale_14d_window (halt)
- Dedupe → quarantine duplicate_chunk_text
- Strip BOM → metric cleaning_bom_stripped
- Short chunk → quarantine short_chunk
- Missing exported_at → quarantine missing_exported_at

**Ví dụ 1 lần expectation fail (Sprint 3 inject):**
- Chạy `python etl_pipeline.py run --no-refund-fix --skip-validate --run-id inject-bad`
- Expectation `refund_no_stale_14d_window` FAIL (halt) → pipeline halt (nếu không skip)
- Log: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
- Cách xử lý: Rerun với fix enabled (mặc định) → expectation PASS

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject (Sprint 3):**

**Scenario 1: Stale Refund Window (14 days)**
- Command: `python etl_pipeline.py run --no-refund-fix --skip-validate --run-id inject-bad`
- Impact: Chunk `policy_refund_v4` chứa "14 ngày làm việc" thay vì "7 ngày làm việc"
- Expectation: `refund_no_stale_14d_window` FAIL (halt) → skip để embed data xấu

**Scenario 2: Missing exported_at**
- Inject: Xóa cột `exported_at` trong raw CSV
- Impact: Freshness check WARN (không thể verify SLA)
- Expectation: `exported_at_all_populated` FAIL (warn) → không halt

**Kết quả định lượng (từ CSV / bảng):**

| Metric | Before (clean) | After (inject bad) | Evidence |
|--------|----------------|-------------------|----------|
| `q_refund_window` contains_expected | yes | yes (nhưng sai nội dung) | artifacts/eval/before_after_eval.csv |
| `q_refund_window` hits_forbidden | no | yes (chứa "14 ngày") | artifacts/eval/eval_after_inject.csv |
| `q_leave_version` contains_expected | yes | yes | artifacts/eval/before_after_eval.csv |
| `q_leave_version` hits_forbidden | no | no | artifacts/eval/before_after_eval.csv |
| cleaned_records | 6 | 6 (nhưng chất lượng xấu) | artifacts/manifests/manifest_inject-bad.json |
| quarantine_records | 4 | 4 | artifacts/manifests/manifest_inject-bad.json |
| freshness_check | FAIL (age 120h) | FAIL (age 120h) | artifacts/logs/run_inject-bad.log |

**Evidence files:**
- Before (clean): `artifacts/eval/before_after_eval.csv` (run_id=sprint1)
- After (inject): `artifacts/eval/eval_after_inject.csv` (run_id=van-inject-bad)
- Restored: `artifacts/eval/eval_after_fix.csv` (run_id=van-restored)
- Grading: `artifacts/eval/grading_run.jsonl` (3 câu: gq_d10_01, gq_d10_02, gq_d10_03 - ALL PASS)

**Grading results:**
- `gq_d10_01` (refund): `contains_expected=true`, `hits_forbidden=false` ✓
- `gq_d10_02` (SLA P1): `contains_expected=true` ✓
- `gq_d10_03` (HR leave): `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true` ✓

**Chứng cứ q_leave_version (Merit):**
- Câu hỏi: "Theo chính sách nghỉ phép hiện hành (2026), nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?"
- Before: `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes` (hr_leave_policy)
- After inject HR stale: `contains_expected=no` (nếu inject HR < 2026-01-01 → quarantine → không có trong cleaned)
- Evidence: `artifacts/eval/before_after_eval.csv` dòng `q_leave_version`

---

## 4. Freshness & monitoring (100–150 từ)

**SLA:** 24 giờ (default từ `FRESHNESS_SLA_HOURS=24` trong `.env`)

**Ý nghĩa:**
- **PASS:** `age_hours <= 24` → data đủ mới, agent có thể tin tưởng
- **WARN:** Không có timestamp trong manifest → không thể verify freshness
- **FAIL:** `age_hours > 24` → data stale, cần re-export hoặc điều chỉnh SLA

**Manifest mẫu (sprint1):**
```json
{
  "run_id": "sprint1",
  "latest_exported_at": "2026-04-10T08:00:00",
  "run_timestamp": "2026-04-15T08:57:03.562649+00:00",
  "age_hours": 120.951,
  "sla_hours": 24.0,
  "reason": "freshness_sla_exceeded"
}
```

**Status:** FAIL (age 120.951h > 24h)

**Giải thích:** CSV mẫu có `exported_at = 2026-04-10` (5 ngày trước) → vượt SLA. Trong production, cần:
1. Re-export data với timestamp mới
2. Hoặc điều chỉnh SLA phù hợp với export frequency (vd: 48h nếu export 2 ngày/lần)
3. Hoặc hiển thị banner warning cho user

**Command kiểm tra:**
```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint1.json
# Output: FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.951, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Monitoring boundary:**
- **Ingest boundary:** `exported_at` từ nguồn (khi data được export)
- **Publish boundary:** `run_timestamp` khi embed xong (khi data available cho agent)

---

## 5. Liên hệ Day 09 (50–100 từ)

Pipeline Day 10 cung cấp corpus cho multi-agent system Day 09:

**Cùng nguồn:** `data/docs/` chứa 5 file policy (access_control_sop, hr_leave_policy, it_helpdesk_faq, policy_refund_v4, sla_p1_2026) — dùng chung cho cả Day 09 và Day 10.

**Tích hợp:**
- Day 10 mô phỏng "export từ DB/API" → CSV raw → clean → validate → embed vào ChromaDB
- Day 09 agent query ChromaDB collection để lấy context
- Collection: Day 10 dùng `day10_kb` (có thể khác Day 09 nếu Day 09 dùng collection riêng)

**Lợi ích:** Day 10 đảm bảo data quality (freshness, validation, no stale version) trước khi Day 09 agent sử dụng. Nếu Day 10 phát hiện stale refund window (14 ngày) → quarantine → Day 09 agent không nhận được chunk sai.

**Workflow:** Day 10 pipeline chạy định kỳ (vd: mỗi 12h) → refresh corpus → Day 09 agent luôn có data mới nhất.

---

## 6. Rủi ro còn lại & việc chưa làm

**Rủi ro:**
1. **Freshness SLA:** CSV mẫu có `exported_at` cũ (5 ngày) → FAIL. Cần cập nhật timestamp hoặc điều chỉnh SLA.
2. **Quarantine approval:** Hiện tại quarantine chỉ log, chưa có workflow approve/merge lại.
3. **Schema drift:** Nếu nguồn thêm cột mới, cleaning_rules cần cập nhật allowlist.
4. **Embed cost:** Rerun toàn bộ corpus mỗi lần → tốn tài nguyên. Cần incremental embed cho production.
5. **Version conflict:** Nếu có nhiều version policy cùng lúc, cần thêm logic chọn version canonical.

**Việc chưa làm:**
- Great Expectations integration (bonus +2 điểm)
- Freshness đo ở 2 boundary (ingest + publish) có log chi tiết (bonus +1 điểm)
- LLM-judge eval (thay vì keyword-based)
- Incremental embed (chỉ embed chunk thay đổi)
- Alert system (email/Slack khi expectation fail)
- Quarantine approval workflow (UI/CLI để review + merge)

**Peer review (3 câu hỏi từ slide Phần E):**
1. **Freshness boundary:** Đo ở ingest (`exported_at`) hay publish (`run_timestamp`)? → Cả 2 (ghi trong runbook)
2. **Idempotency:** Rerun 2 lần có duplicate vector không? → Không (upsert + prune)
3. **Halt vs warn:** Expectation nào halt, nào warn? → Halt: min_one_row, no_empty_doc_id, refund_no_stale_14d_window, effective_date_iso, hr_leave_no_stale_10d_annual. Warn: chunk_min_length_8, exported_at_all_populated, chunk_text_min_length_20.
