# PLAN_INDIVIDUALS — Lab Day 10: Data Pipeline & Data Observability

> **Nhóm:** C401 — D6  
> **Thành viên:** 6 người  
> **Deadline cứng:** 18:00 hôm nay (code + artifact)  
> **Format điểm:** 60 nhóm + 40 cá nhân = 100

---

## Tổng quan vai trò & phân công

| # | Thành viên | Vai trò chính | Sprint chính | File chịu trách nhiệm |
|---|-----------|---------------|--------------|----------------------|
| 1 | **Lê Huy Hồng Nhật** | **Tech Lead + Ingestion Owner** | 1 + điều phối | `etl_pipeline.py`, `contracts/data_contract.yaml`, `artifacts/manifests/` |
| 2 | **Nguyễn Quốc Khánh** | **Cleaning Owner** | 1–2 | `transform/cleaning_rules.py` (≥3 rule mới) |
| 3 | **Nguyễn Tuấn Khải** | **Quality / Expectation Owner** | 2–3 | `quality/expectations.py` (≥2 expectation mới) |
| 4 | **Phan Văn Tấn** | **Embed & Eval Owner** | 2–3 | `eval_retrieval.py`, `grading_run.py`, `artifacts/eval/` |
| 5 | **Lê Công Thành** | **Monitoring & Docs Owner** | 3–4 | `monitoring/freshness_check.py`, `docs/runbook.md`, `docs/pipeline_architecture.md` |
| 6 | **Nguyễn Quế Sơn** | **Docs & Report Owner** | 4 | `docs/data_contract.md`, `docs/quality_report_template.md → quality_report.md`, `reports/group_report.md` |

---

## Thứ tự thực hiện (Dependency Graph)

```
Sprint 1 (làm TRƯỚC, song song Nhật + Khánh)
  ├── Nhật: setup môi trường, chạy pipeline baseline, kiểm tra log
  └── Khánh: đọc dirty CSV, thiết kế ≥3 rule mới trong cleaning_rules.py

        ↓ (Khánh commit cleaning_rules → Khải dùng cleaned rows)

Sprint 2 (Khải + Tấn song song)
  ├── Khải: viết expectation mới, test halt/warn
  └── Tấn: chạy embed baseline, kiểm tra idempotency (rerun 2 lần)

        ↓ (Embed xong → Tấn chạy eval)

Sprint 3 (Tấn + Tuấn Khải phối hợp)
  ├── Tấn: inject corruption (--no-refund-fix --skip-validate), lưu before/after CSV
  └── Khải: xác nhận expectation fail đúng khi inject

        ↓ (Có artifact đủ → Thành + Sơn viết docs)

Sprint 4 (Thành + Sơn song song, mọi người viết individual report)
  ├── Thành: freshness check, runbook, pipeline_architecture
  └── Sơn: data_contract.md, quality_report.md, group_report.md
  └── Tất cả: viết reports/individual/[ten].md
```

> **Qui tắc chống bottleneck:** Nhật phải có pipeline `exit 0` trước **cuối Sprint 1**. Tất cả công việc sau đó phụ thuộc log thật có `run_id`.

---

## Chi tiết từng người

---

### 👤 1. Lê Huy Hồng Nhật — Tech Lead + Ingestion Owner

**Vai trò:** Đảm bảo pipeline chạy end-to-end, quản lý `run_id`, điều phối merge conflict.

#### Sprint 1 — Ingest & Setup

**Nhiệm vụ bắt buộc:**
- [ ] Setup môi trường: `python -m venv .venv`, `pip install -r requirements.txt`, `cp .env.example .env`
- [ ] Chạy `python etl_pipeline.py run --run-id sprint1` → kiểm tra log có đủ 4 trường: `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`
- [ ] Lưu log vào `artifacts/logs/run_sprint1.log` (pipeline tự sinh nhưng phải commit)
- [ ] Điền `contracts/data_contract.yaml`: owner, SLA, mô tả nguồn

**Hàm cần hiểu & giám sát (không cần sửa nếu đã đúng):**
- `cmd_run()` trong `etl_pipeline.py` — kiểm tra luồng ingest→clean→validate→embed→manifest
- `load_raw_csv()` trong `transform/cleaning_rules.py` — đọc dirty CSV
- `_log()` trong `etl_pipeline.py` — đảm bảo log file được tạo

**Phối hợp:** Sau khi `exit 0`, gửi `run_id` và đường dẫn log cho cả nhóm.

#### Sprint 4 — Coordination

- [ ] Review toàn bộ artifact trước deadline 18:00
- [ ] Đảm bảo manifest JSON tồn tại và có đủ fields (`run_id`, `cleaned_records`, `quarantine_records`)
- [ ] Viết `reports/individual/le_huy_hong_nhat.md` (400–650 từ)

**Chịu trách nhiệm nếu sai:**
- Pipeline không chạy được (`exit ≠ 0`) → **mất 10 điểm ETL**
- Log thiếu `run_id` hoặc 4 metrics → **mất 5 điểm log**
- `manifest_*.json` thiếu hoặc sai format → ảnh hưởng freshness check + grading

---

### 👤 2. Nguyễn Quốc Khánh — Cleaning Owner

**Vai trò:** Mở rộng `transform/cleaning_rules.py` với ≥3 rule mới thực sự có tác động đo được.

#### Sprint 1–2 — Cleaning Rules

**Nhiệm vụ bắt buộc:**
- [ ] Đọc kỹ `data/raw/policy_export_dirty.csv` để hiểu dữ liệu bẩn thật sự có những vấn đề gì ngoài baseline
- [ ] Thêm **≥3 rule mới** vào hàm `clean_rows()` trong `transform/cleaning_rules.py`
- [ ] Mỗi rule mới phải: có **comment/docstring giải thích**, **tên gọi rõ** (rule7, rule8...), và **thay đổi ít nhất 1 trong**: `quarantine_records`, kết quả expectation, hoặc eval
- [ ] Ghi `metric_impact` cho từng rule vào `reports/group_report.md` mục 2a (bảng số liệu)

**Hàm cần hoàn thành:**
- `clean_rows()` trong `transform/cleaning_rules.py` — thêm các block rule mới SAU rule 6 (baseline), giữ nguyên signature `(rows, *, apply_refund_window_fix)` → `(cleaned, quarantine)`
- *(Nếu cần thêm helper)* thêm hàm `_check_<ten_rule>(row) -> bool` riêng → gọi từ `clean_rows()`

**Gợi ý hướng rule mới (chọn ≥3, phải có bằng chứng số liệu):**
- Rule kiểm tra BOM character / ký tự lạ đầu `chunk_text`
- Rule kiểm tra `exported_at` không rỗng và đúng định dạng datetime ISO
- Rule giới hạn `chunk_text` tối đa X ký tự (quá dài → quarantine hoặc truncate log)
- Rule kiểm tra `doc_id` trong `ALLOWED_DOC_IDS` ở `contracts/data_contract.yaml` (đồng bộ với Nhật)
- Rule phát hiện `chunk_text` toàn khoảng trắng / chỉ số / không có tiếng Việt

**⚠️ Chú ý chống trivial:**
- Rule chỉ strip space mà không đổi số record → **GV sẽ trừ điểm**
- Phải có kịch bản chứng minh: inject row vi phạm → log cho thấy `quarantine_records` tăng

**Phối hợp:** Sau khi thêm rule, thông báo Nhật chạy lại pipeline để lấy log mới. Thông báo Khải để viết expectation bao phủ rule mới.

**Chịu trách nhiệm nếu sai:**
- `cleaning_rules.py` có <3 rule mới → **mất 6 điểm ETL**
- Rule trivial (không đổi số liệu) → **GV trừ thêm**
- `clean_rows()` crash → toàn bộ pipeline fail → ảnh hưởng cả nhóm

---

### 👤 3. Nguyễn Tuấn Khải — Quality / Expectation Owner

**Vai trò:** Mở rộng `quality/expectations.py` với ≥2 expectation mới, phân biệt rõ warn/halt.

#### Sprint 2 — Expectation Suite

**Nhiệm vụ bắt buộc:**
- [ ] Thêm **≥2 expectation mới** vào hàm `run_expectations()` trong `quality/expectations.py`
- [ ] Mỗi expectation mới phải: có **label `warn` hoặc `halt` rõ ràng**, có **tên unique** (E7, E8...), **liên kết với rule mới của Khánh** hoặc một data property mới
- [ ] Chạy thử để xác nhận expectation **fail** khi inject data xấu và **pass** khi data clean
- [ ] Ghi thêm vào bảng `metric_impact` trong group report: expectation nào fail trước khi fix

#### Sprint 3 — Inject & Verify

- [ ] Kết hợp với Tấn chạy: `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`
- [ ] Xác nhận log có dòng `expectation[...] FAIL (halt)` đúng expectation mình viết
- [ ] Giữ lại log của inject run (dùng làm before evidence)

**Hàm cần hoàn thành:**
- `run_expectations()` trong `quality/expectations.py` — thêm các block E7, E8... SAU E6 (baseline), giữ nguyên signature `(cleaned_rows)` → `(List[ExpectationResult], bool)`
- *(Nếu muốn tách)* tạo hàm helper `_expect_<ten>(rows) -> ExpectationResult`

**Gợi ý hướng expectation mới (chọn ≥2, phải phân biệt warn/halt):**
- `E7` (halt): `exported_at` của cleaned rows không được rỗng (phối hợp với rule mới của Khánh)
- `E8` (warn): tỷ lệ `quarantine_records / raw_records` không vượt ngưỡng X% (quarantine rate check)
- `E9` (halt): tất cả `doc_id` trong cleaned phải có trong `ALLOWED_DOC_IDS`
- `E10` (warn): không có `chunk_text` quá ngắn (<20 ký tự)

**⚠️ Lưu ý quan trọng:**
- Expectation mới dùng `severity="halt"` → khi fail sẽ dừng pipeline (chỉ dùng điều kiện chắc chắn fail khi data bẩn)
- Expectation dùng `severity="warn"` → log FAIL nhưng pipeline vẫn tiếp tục
- Nếu E7 halt fail trên **clean data** → pipeline sẽ không chạy qua → phải test kỹ với Nhật

**Chịu trách nhiệm nếu sai:**
- <2 expectation mới → **mất 6 điểm Quality evidence**
- Expectation mới không gây `should_halt=True` khi inject → không chứng minh được halt control
- Expectation crash (exception ngoài `ExpectationResult`) → pipeline crash

---

### 👤 4. Phan Văn Tấn — Embed & Eval Owner

**Vai trò:** Đảm bảo embed idempotent, chạy eval before/after, tạo `grading_run.jsonl`.

#### Sprint 2 — Idempotency Verify

**Nhiệm vụ bắt buộc:**
- [ ] Sau khi Nhật có pipeline `exit 0`: chạy `python etl_pipeline.py run` **2 lần liên tiếp** với cùng data
- [ ] Kiểm tra log có `embed_prune_removed=0` ở lần 2 (không phình vector store) → chứng minh idempotency
- [ ] Kiểm tra số lượng collection Chroma không tăng sau rerun

#### Sprint 3 — Before/After Eval & Inject

- [ ] Chạy `python eval_retrieval.py --out artifacts/eval/before_clean_eval.csv` (**trước** khi apply fix — cần phối hợp với Nhật chạy inject mode)
- [ ] Inject: `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`
- [ ] Chạy `python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv`
- [ ] Chạy lại pipeline chuẩn: `python etl_pipeline.py run --run-id sprint3-clean`
- [ ] Chạy `python eval_retrieval.py --out artifacts/eval/after_clean_eval.csv`
- [ ] So sánh 3 file CSV: `contains_expected`, `hits_forbidden` trước và sau rõ ràng khác nhau
- [ ] Commit cả 2–3 file CSV vào `artifacts/eval/`

#### Sprint 4 (sau 17:00) — Grading Run

- [ ] Sau khi GV public `grading_questions.json`: chạy `python grading_run.py --out artifacts/eval/grading_run.jsonl`
- [ ] Xác nhận JSONL có **đúng 3 dòng** (`gq_d10_01`, `gq_d10_02`, `gq_d10_03`), mỗi dòng JSON hợp lệ
- [ ] Kiểm tra: `gq_d10_01` → `contains_expected=true`, `hits_forbidden=false`; `gq_d10_02` → `contains_expected=true`; `gq_d10_03` → cả 3 fields true
- [ ] Commit `grading_run.jsonl` trước 18:00

**Hàm cần hiểu (không cần sửa nếu đã đúng):**
- `cmd_embed_internal()` trong `etl_pipeline.py` — kiểm tra logic prune + upsert; sửa nếu `embed_prune_removed` không xuất hiện
- `main()` trong `eval_retrieval.py` — kiểm tra `must_contain_any`, `must_not_contain` khớp với câu hỏi trong JSON
- `main()` trong `grading_run.py` — hiểu cách tính `contains_expected`, `hits_forbidden`, `top1_doc_matches`

**⚠️ Rủi ro quan trọng:**
- Nếu embed fail (ChromaDB lỗi) → `grading_run.py` sẽ fail → **mất toàn bộ grading score (12 điểm)**
- `hits_forbidden` quét **toàn bộ top-k** (không chỉ top-1) — chunk stale cũ chưa prune sẽ fail
- `grading_questions.json` **public lúc 17:00** — phải chạy và commit trong 1 giờ

**Chịu trách nhiệm nếu sai:**
- Không có `before_after_eval.csv` → mất 6 điểm quality evidence
- `grading_run.jsonl` thiếu dòng hoặc sai format → mất 2 điểm format + điểm từng câu
- Vector store không idempotent (phình sau rerun) → mất 6 điểm ETL embed

---

### 👤 5. Lê Công Thành — Monitoring & Docs Owner

**Vai trò:** Vận hành freshness check, viết runbook và pipeline_architecture.

#### Sprint 3–4 — Monitoring

**Nhiệm vụ bắt buộc:**
- [ ] Sau khi Nhật có manifest file: chạy `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run-id>.json`
- [ ] Ghi lại kết quả PASS/WARN/FAIL và giải thích SLA trong `docs/runbook.md`
- [ ] *(Bonus +1)* Nếu muốn freshness boundary thứ 2 (publish boundary): thêm `publish_timestamp` vào manifest trong `etl_pipeline.py` và so sánh cả 2 mốc trong `check_manifest_freshness()`

**Hàm cần hiểu & có thể mở rộng:**
- `check_manifest_freshness()` trong `monitoring/freshness_check.py` — hiểu cách đọc `latest_exported_at` và tính `age_hours`; nếu muốn bonus boundary thứ 2 thì thêm logic đọc `publish_timestamp`
- `parse_iso()` trong `monitoring/freshness_check.py` — không cần sửa

**Hàm mở rộng tùy chọn (cho Distinction/Bonus):**
- Thêm field `publish_timestamp` vào `manifest` dict trong `cmd_run()` (`etl_pipeline.py`)
- Thêm tham số `check_publish_boundary=True` vào `check_manifest_freshness()` để đo 2 mốc

#### Sprint 4 — Documentation

- [ ] Hoàn thiện `docs/pipeline_architecture.md`:
  - **Bắt buộc:** có sơ đồ (Mermaid hoặc ASCII) thể hiện: `raw → clean → validate → embed → serving`
  - Thêm: điểm đo freshness, chỗ ghi `run_id`, file quarantine
  - Điền bảng "Ranh giới trách nhiệm" (5 thành phần: Ingest/Transform/Quality/Embed/Monitor)
  - Mô tả idempotency strategy (upsert `chunk_id` + prune)
  - Liên hệ Day 09
- [ ] Hoàn thiện `docs/runbook.md` — điền đủ 5 mục: **Symptom → Detection → Diagnosis → Mitigation → Prevention**
- [ ] Viết `reports/individual/le_cong_thanh.md` (400–650 từ)

**Chịu trách nhiệm nếu sai:**
- `pipeline_architecture.md` thiếu sơ đồ → **mất 5 điểm docs**
- `runbook.md` thiếu ≥1 trong 5 mục Symptom→Prevention → **mất 5 điểm docs**
- Freshness FAIL không giải thích trong runbook → bị đặt câu hỏi khi chấm

---

### 👤 6. Nguyễn Quế Sơn — Docs & Report Owner

**Vai trò:** Tổng hợp tài liệu, viết group report, đảm bảo deliverable list đầy đủ.

#### Sprint 4 — Documentation & Report

**Nhiệm vụ bắt buộc:**
- [ ] Hoàn thiện `docs/data_contract.md`:
  - **Bắt buộc:** Source map ≥2 nguồn (CSV raw + ít nhất 1 nguồn thứ 2 như docs folder)
  - Điền bảng schema cleaned (5 cột: `chunk_id`, `doc_id`, `chunk_text`, `effective_date`, `exported_at`)
  - Quy tắc quarantine vs drop + ai approve merge lại
  - Phiên bản canonical (policy refund v4 là source of truth nào)
  - **Đồng bộ với** `contracts/data_contract.yaml` (Nhật điền trước)
- [ ] Hoàn thiện `docs/quality_report_template.md` thành `docs/quality_report.md`:
  - Điền `run_id` thật (lấy từ Nhật)
  - Bảng số liệu trước/sau (raw/cleaned/quarantine từ log Nhật)
  - Before/after retrieval — dán dòng CSV từ Tấn
  - Kết quả freshness từ Thành
  - Mô tả inject corruption (Sprint 3)
- [ ] Hoàn thiện `reports/group_report.md`:
  - Mục 1: Pipeline tổng quan, lệnh chạy 1 dòng, run_id
  - Mục 2: Cleaning rules mới + bảng `metric_impact` (lấy từ Khánh)
  - Mục 2: Expectation mới + ví dụ fail (lấy từ Khải)
  - Mục 3: Before/after inject (lấy từ Tấn)
  - Mục 4: Freshness monitoring (lấy từ Thành)
  - Mục 5: Liên hệ Day 09
  - Mục 6: Rủi ro còn lại
- [ ] Điền bảng thành viên trong group_report với vai trò thực tế
- [ ] Viết `reports/individual/nguyen_que_son.md` (400–650 từ)

**⚠️ Chú ý:**
- `quality_report.md` phải có `run_id` thật — không được dùng `___` placeholder
- Bảng metric_impact trong group_report là **bắt buộc** — thiếu bảng này → GV trừ điểm khi tranh chấp

**Chịu trách nhiệm nếu sai:**
- `data_contract.md` thiếu source map ≥2 nguồn → **mất 5 điểm docs**
- `quality_report.md` thiếu run_id hoặc không có before/after → **mất 6 điểm quality evidence**
- `group_report.md` thiếu metric_impact → rủi ro bị xem là trivial

---

## Checklist hoàn thành (Master Checklist)

### 🔴 Phần Nhóm — phải đủ trước 18:00

#### ETL & Pipeline (27 điểm)
- [ ] `python etl_pipeline.py run` exit 0 (**Nhật** verify)
- [ ] Log có: `run_id`, `raw_records`, `cleaned_records`, `quarantine_records` (**Nhật**)
- [ ] `transform/cleaning_rules.py` có ≥3 rule mới có tác động đo được + comment (**Khánh**)
- [ ] Bảng metric_impact ở group_report cho từng rule mới (**Khánh → Sơn**)
- [ ] Embed idempotent: rerun 2 lần không phình; log có `embed_prune_removed` (**Tấn**)
- [ ] Manifest JSON tồn tại tại `artifacts/manifests/` (**Nhật**)

#### Documentation (15 điểm)
- [ ] `docs/pipeline_architecture.md` có sơ đồ + ranh giới ingest/clean/embed (**Thành**)
- [ ] `docs/data_contract.md` có source map ≥2 nguồn + schema/owner (**Sơn**)
- [ ] `docs/runbook.md` đủ 5 mục Symptom→Prevention (**Thành**)

#### Quality Evidence (18 điểm)
- [ ] `quality/expectations.py` có ≥2 expectation mới + phân biệt warn/halt (**Khải**)
- [ ] Có ≥2 file eval CSV chứng minh before/after (`artifacts/eval/`) (**Tấn**)
- [ ] `docs/quality_report.md` có run_id + interpret before/after (**Sơn**)

#### Grading JSONL (12 điểm — sau 17:00)
- [ ] `artifacts/eval/grading_run.jsonl` tồn tại, đúng 3 dòng (**Tấn**)
- [ ] `gq_d10_01`: `contains_expected=true`, `hits_forbidden=false` (**Tấn + Khánh**)
- [ ] `gq_d10_02`: `contains_expected=true` (**Tấn**)
- [ ] `gq_d10_03`: `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true` (**Tấn**)

---

### 🔵 Phần Cá nhân — mỗi người tự làm

| File | Người | Checklist |
|------|-------|-----------|
| `reports/individual/le_huy_hong_nhat.md` | Nhật | 400–650 từ, có run_id, file thật, quyết định kỹ thuật, anomaly |
| `reports/individual/nguyen_quoc_khanh.md` | Khánh | Như trên — khai báo rule nào, số liệu quarantine trước/sau |
| `reports/individual/nguyen_tuan_khai.md` | Khải | Như trên — khai báo expectation nào, ví dụ FAIL log |
| `reports/individual/phan_van_tan.md` | Tấn | Như trên — khai báo eval, CSV, grading run |
| `reports/individual/le_cong_thanh.md` | Thành | Như trên — khai báo freshness, runbook, pipeline_architecture |
| `reports/individual/nguyen_que_son.md` | Sơn | Như trên — khai báo docs tổng hợp, group report |

**Luật cứng:**
- Report phải khớp commit thực tế trong repo
- Không được sao chép report của nhau (0/40 cả hai bên)
- Paraphrase slide = 0 điểm mục

---

## Ma trận trách nhiệm sai sót

| Vấn đề | Người chịu trách nhiệm chính | Hậu quả điểm |
|--------|------------------------------|--------------|
| Pipeline không exit 0 | Nhật | −10 ETL |
| Log thiếu 4 metrics | Nhật | −5 ETL |
| <3 rule mới hoặc rule trivial | Khánh | −6 ETL (GV có thể thêm) |
| <2 expectation mới | Khải | −6 Quality |
| Expectation không phân biệt warn/halt | Khải | Hỏi khi chấm |
| Embed phình sau rerun (không idempotent) | Tấn | −6 ETL |
| Thiếu before/after eval CSV | Tấn | −6 Quality |
| `grading_run.jsonl` sai format / thiếu dòng | Tấn | −2 đến −12 |
| `pipeline_architecture.md` thiếu sơ đồ | Thành | −5 Docs |
| `runbook.md` thiếu mục Symptom→Prevention | Thành | −5 Docs |
| `data_contract.md` thiếu source map | Sơn | −5 Docs |
| `quality_report.md` không có run_id | Sơn | −6 Quality |
| `group_report.md` thiếu metric_impact | Sơn + Khánh | Rủi ro trivial penalty |
| Individual report không khớp commit | Từng người | 0/40 cá nhân |
| Sao chép report | Hai người liên quan | 0/40 cả hai |

---

## Lịch trình gợi ý trong ngày

| Thời gian | Hoạt động | Ai |
|-----------|-----------|-----|
| Hiện tại | Setup env, đọc CSV bẩn, phân chia branch | **Nhật** (chủ trì) |
| Sprint 1 | Nhật: chạy pipeline baseline; Khánh: thiết kế rule mới | **Nhật + Khánh** song song |
| Sprint 2 | Khải: viết expectation; Tấn: test idempotency | **Khải + Tấn** song song |
| Sprint 3 | Tấn: inject + eval; Khánh+Khải: xác nhận metrics | **Tất cả kỹ thuật** |
| Sprint 4 (trước 17:00) | Thành + Sơn: hoàn thiện docs; Mọi người: individual report | **Thành + Sơn** chủ trì |
| **17:00–18:00** | Tất cả: chạy grading_run.py, final commit, push | **Tấn** lead, **Nhật** review |
| **18:00 CỨNG** | Push lần cuối code + artifact | **Nhật** verify |
| Sau 18:00 | Hoàn thiện reports nếu được phép | **Sơn** tổng hợp |

---

## Gợi ý phối hợp tránh merge conflict

1. **Mỗi người làm trên branch riêng** (`branch/khanh-cleaning`, `branch/khai-expectation`...)
2. **File riêng biệt = ít conflict:** Khánh chỉ sửa `cleaning_rules.py`; Khải chỉ sửa `expectations.py`; Tấn chỉ commit vào `artifacts/eval/`
3. **Điểm giao duy nhất nguy hiểm:** `etl_pipeline.py` — chỉ Nhật sửa; người khác comment PR nếu cần thay đổi
4. **Sau mỗi Sprint:** Nhật merge branch → chạy pipeline → xác nhận `exit 0` → announce `run_id` mới

---

## Phân hạng nhóm & mục tiêu

| Hạng | Cần đạt | Ai đảm bảo |
|------|---------|-----------|
| **Pass** | Checklist mục 1–3 đủ; grading JSONL hợp lệ; `gq_d10_01`+`gq_d10_02` đúng | **Nhật + Tấn** |
| **Merit** | Pass + `gq_d10_03` đầy đủ (`contains_expected + hits_forbidden + top1_doc_matches`); evidence cho `q_leave_version` | **Tấn + Khải** |
| **Distinction** | Merit + 1 trong: GE/pydantic validate thật; freshness 2 boundary; LLM-judge / ≥5 câu eval; rule versioning không hard-code | **Thành** (freshness boundary) hoặc **Khánh+Khải** (GE) |

---

*File này được tạo tự động từ đọc `SCORING.md`, `README.md` và toàn bộ codebase hiện tại. Cập nhật nếu có thay đổi phân công.*
