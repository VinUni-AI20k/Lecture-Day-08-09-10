# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trần Đình Minh Vương  
**Vai trò:** Monitoring / Docs Owner (Sprint 4)  
**Ngày nộp:** 2026-04-15  
**Độ dài:** ~550 từ

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
- `monitoring/freshness_check.py` — baseline đã có, verify hoạt động đúng
- `docs/pipeline_architecture.md` — sơ đồ ASCII + ranh giới 5 thành phần
- `docs/data_contract.md` — source map 2 nguồn + schema 5 cột + owner
- `docs/runbook.md` — 5 incidents với đủ 5 mục (Symptom→Prevention)
- `reports/group_report.md` — tổng hợp metric_impact + evidence

**Kết nối với thành viên khác:**
- Khiêm: Lấy bảng metric_impact (3 rules + 2 expectations) để ghi vào group report
- Vân: Lấy evidence before/after từ Sprint 3 inject (eval CSV + manifest)
- Sang: Lấy thông tin ingest flow để vẽ sơ đồ pipeline
- Dũng: Lấy thông tin embed idempotency để ghi trong architecture

**Bằng chứng (commit / comment trong code):**
- Commit `499a505`: feat(day10): Complete Sprint 4 - Monitoring/Docs Owner
- Commit `630c369`: docs(day10): Update team members table to match assignment image
- Files: 3 docs/*.md + 1 reports/group_report.md + artifacts (manifest, log)

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Quyết định:** Đo freshness ở 2 boundary (ingest + publish) thay vì chỉ 1 điểm.

**Lý do:** 
- **Ingest boundary:** `exported_at` từ nguồn → đo độ "tươi" của data khi export từ DB/API
- **Publish boundary:** `run_timestamp` khi embed xong → đo độ "tươi" khi data available cho agent

**Trade-off:**
- Ưu điểm: Phát hiện được bottleneck ở 2 giai đoạn (export chậm vs pipeline chậm)
- Nhược điểm: Phức tạp hơn, cần 2 metric thay vì 1

**Implementation:**
- Baseline `freshness_check.py` đã đo `latest_exported_at` (ingest boundary)
- Manifest ghi cả `run_timestamp` (publish boundary)
- Runbook giải thích cả 2: "Monitoring boundary: Ingest (`exported_at`) + Publish (`run_timestamp`)"

**Kết quả:** 
- `manifest_vuong-sprint4-test.json`: `latest_exported_at=2026-04-10`, `run_timestamp=2026-04-15T09:25:38`
- Age: 121h → FAIL (vượt SLA 24h)

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Freshness check luôn FAIL với `age_hours > 120h`, ngay cả khi rerun pipeline.

**Phát hiện:**
- Chạy `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint1.json`
- Output: `FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.951, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}`
- Kiểm tra raw CSV: `data/raw/policy_export_dirty.csv` có `exported_at = 2026-04-10` (5 ngày trước)

**Root cause:** CSV mẫu có timestamp cũ (mô phỏng data stale), không phải bug pipeline.

**Fix:** 
- Không fix CSV (vì đây là kịch bản test hợp lệ)
- Ghi rõ trong runbook: "CSV mẫu có `exported_at` cũ → FAIL là expected behavior"
- Đề xuất 3 options: (1) Re-export data mới, (2) Điều chỉnh SLA lên 48h, (3) Hiển thị banner warning

**Bằng chứng:** `docs/runbook.md` Incident 2 — Freshness SLA Exceeded

---

## 4. Bằng chứng trước / sau (80–120 từ)

**run_id:** `sprint1` (before), `vuong-sprint4-test` (after verify)

**Before (sprint1):**
```
raw_records=10
cleaned_records=6
quarantine_records=4
freshness_check=FAIL {"age_hours": 120.951, "sla_hours": 24.0}
```

**After (vuong-sprint4-test):**
```
raw_records=13
cleaned_records=7
quarantine_records=6
cleaning_bom_stripped=1
embed_idempotent=true
freshness_check=FAIL {"age_hours": 121.427, "sla_hours": 24.0}
```

**Eval evidence (from Vân's Sprint 3):**
- `artifacts/eval/before_after_eval.csv`: `q_refund_window` → `contains_expected=yes`, `hits_forbidden=no`
- `artifacts/eval/grading_run.jsonl`: ALL 3 questions PASS (gq_d10_01, gq_d10_02, gq_d10_03)

**Freshness command:**
```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_vuong-sprint4-test.json
# Output: FAIL (expected)
```

---

## 5. Cải tiến tiếp theo (40–80 từ)

**Nếu có thêm 2 giờ:**

**Freshness đo 2 boundary có log chi tiết (bonus +1 điểm):**
- Thêm metric `ingest_to_publish_lag` = `run_timestamp - latest_exported_at`
- Log riêng 2 boundary: `freshness_ingest=FAIL`, `freshness_publish=PASS`
- Alert riêng: nếu ingest FAIL → nguồn chậm; nếu publish FAIL → pipeline chậm

**Implementation:**
- Sửa `monitoring/freshness_check.py`: thêm function `check_dual_boundary()`
- Log: `freshness_ingest_age=121h FAIL`, `freshness_publish_lag=0.5h PASS`, `ingest_to_publish_lag=0.5h`
- Runbook: thêm section "Dual Boundary Monitoring"

**Lợi ích:** Phân biệt được bottleneck ở nguồn vs pipeline → fix đúng chỗ.
