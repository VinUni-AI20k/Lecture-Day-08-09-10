# SCORING — Lab Day 10: Data Pipeline & Data Observability

> **Tổng điểm: 100**  
> Cách chia **bám rubric slide** (`lecture-10.html` — Hands-on 10):  
> **ETL ~45% · Documentation ~25% · Quality evidence ~20% · Individual ~10%**  
> Quy đổi thực tế dưới đây dùng **60 nhóm + 40 cá nhân** để **tiếp nối format Day 09** (dễ nhập điểm).

---

## Phân hạng nhóm (Pass / Merit / Distinction)

Áp dụng **sau** khi cộng điểm mục 1–4 (tối đa 60). Hạng giúp phân tầng nhanh trên LMS / bảng tổng kết; có thể **không cộng thêm điểm** nếu lớp chỉ cần nhãn.

| Hạng | Điều kiện tối thiểu (nhóm) |
|------|-----------------------------|
| **Pass** | Đạt đủ checklist mục 1–3 theo bảng điểm; grading JSONL hợp lệ; `gq_d10_01` và `gq_d10_02` đúng theo rubric dưới. |
| **Merit** | Pass + `gq_d10_03` đạt đủ: `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true`; có chứng cứ eval cho `q_leave_version` (hoặc dòng tương đương trong grading JSONL) trong quality report / artifact. |
| **Distinction** | Merit + **một trong các bằng chứng “vượt baseline”** có liên kết rõ (link log/CSV/commit): (a) GE hoặc pydantic validate thật trên schema cleaned; (b) freshness đo **2 boundary** (ingest + publish) có log; (c) eval mở rộng (LLM-judge hoặc bộ slice ≥5 câu) có mô tả phương pháp + 1 ví dụ fail/pass; (d) rule versioning **không hard-code** một ngày cố định (vd đọc cutoff từ contract/env) + chứng minh inject làm đổi quyết định clean. |

**Chống trivial (trừ điểm mục 1 hoặc 3, tối đa −4 mỗi nhóm — quyết định GV):**

- Rule/expectation “mới” **không** làm thay đổi `quarantine_records`, `cleaned_records`, kết quả expectation, hoặc eval **trên ít nhất một** trong: CSV mẫu, inject Sprint 3, hoặc bảng `metric_impact` nhóm tự ghi — coi là trivial.
- Nhóm **không** điền bảng `metric_impact` trong `reports/group_report.md` (mục 2) → dễ bị trừ khi tranh chấp “có làm thật hay không”.

**Công cụ hỗ trợ GV:** `python instructor_quick_check.py` (sanity JSONL/manifest).

---

## Timeline nộp bài (điều chỉnh theo lớp — mặc định giống Day 09)

| Thời điểm | Sự kiện |
|-----------|---------|
| 17:00 | Public `data/grading_questions.json` (nếu giảng viên đã ẩn trước đó) |
| 17:00–18:00 | Chạy `grading_run.py`, hoàn thiện artifact & report |
| **18:00** | **Deadline** code + artifact bắt buộc (xem bảng dưới) |
| Sau 18:00 | Chỉ `reports/group_report.md` và `reports/individual/*.md` (nếu cho phép) |

### Quy tắc commit theo loại file

| Loại | Deadline 18:00 |
|------|----------------|
| `*.py`, `contracts/*.yaml` | Bắt buộc |
| `artifacts/eval/grading_run.jsonl`, CSV eval, `artifacts/manifests/*.json` | Bắt buộc (trừ khi GV chỉ cần 1 run) |
| `docs/pipeline_architecture.md`, `data_contract.md`, `runbook.md`, quality report | Bắt buộc |
| `reports/*.md` | Theo quy định lớp (thường cho phép muộn) |

---

## Phần Nhóm — 60 điểm

### 1. ETL & pipeline (27 điểm) — ~45% của 60

| Tiêu chí | Điểm |
|-----------|------|
| `python etl_pipeline.py run` exit 0 (pipeline chuẩn, không `--skip-validate` trừ khi có lý do ghi trong runbook) | 10 |
| Log có `run_id`, `raw_records`, `cleaned_records`, `quarantine_records` khớp artifact | 5 |
| `transform/cleaning_rules.py` có **≥ 3 rule mới** so với baseline nhận được (mỗi rule: comment/docstring + tên gọi rõ); **trừ** nếu GV đánh giá trivial (xem phần Phân hạng) | 6 |
| Embed idempotent + index khớp cleaned: upsert `chunk_id`, rerun 2 lần không phình tài nguyên; sau publish không còn vector id lạc hậu (baseline có prune) — có thể kiểm `embed_prune_removed` trong log hoặc đếm collection | 6 |

### 2. Documentation nhóm (15 điểm) — ~25% của 60

| Tiêu chí | Điểm |
|-----------|------|
| `docs/pipeline_architecture.md` có sơ đồ + ranh giới ingest/clean/embed | 5 |
| `docs/data_contract.md` có source map (≥2 nguồn) + schema/owner | 5 |
| `docs/runbook.md` đủ 5 mục Symptom→Prevention (có thể ngắn nhưng đúng thứ tự) | 5 |

### 3. Quality evidence (18 điểm) — ~20% của 60 + một phần grading

| Tiêu chí | Điểm |
|-----------|------|
| `quality/expectations.py` có **≥ 2 expectation mới** so với baseline + phân biệt warn/halt; **trừ** nếu trivial | 6 |
| Before/after: có ≥2 dòng chứng cứ eval (CSV) hoặc 2 file so sánh inject vs clean; **Merit khuyến nghị** thêm dòng cho `q_leave_version` | 6 |
| Quality report (theo `docs/quality_report_template.md`) có run_id + interpret | 6 |

### 4. Grading JSONL (tùy lớp — mặc định 0–12 điểm trừ vào mục 3 hoặc tách riêng)

Nếu dùng `grading_questions.json` (3 câu):

| Tiêu chí | Điểm |
|-----------|------|
| `artifacts/eval/grading_run.jsonl` tồn tại, **đúng 3 dòng** `gq_d10_01` … `gq_d10_03`, mỗi dòng JSON hợp lệ | 2 |
| `gq_d10_01`: `contains_expected=true` và `hits_forbidden=false` | 4 |
| `gq_d10_02`: `contains_expected=true` | 3 |
| `gq_d10_03`: `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true` | 3 |

> Nếu không dùng grading: phân bổ 12 điểm vào mục 3 (quality evidence) theo tỷ lệ GV.  
> `top1_doc_matches` do `grading_run.py` ghi khi câu hỏi có `expect_top1_doc_id` trong JSON.

---

## Phần Cá nhân — 40 điểm

### 5. Individual report (30 điểm)

File: `reports/individual/[ten].md` · **400–650 từ**

| Mục | Nội dung | Điểm |
|-----|----------|------|
| Phần phụ trách cụ thể | File + function / rule | 8 |
| 1 quyết định kỹ thuật | warn vs halt, idempotency, freshness boundary | 8 |
| 1 sự cố / anomaly | Phát hiện + fix + evidence | 8 |
| Before/after | Trích log hoặc CSV | 4 |
| Cải tiến 2h | Một việc cụ thể | 2 |

> **0 điểm mục** nếu không có run_id / tên file thật / chỉ paraphrase slide.

**Gợi ý phân tầng cá nhân (không đổi tổng 40):** báo cáo có **số liệu cụ thể** (delta `quarantine_records`, một dòng `expectation[...] FAIL`, hoặc `top1_doc_expected=no` trước fix) → ưu tiên mức cao trong cùng nhóm Merit.

### 6. Code contribution (10 điểm)

| Tiêu chí | Điểm |
|-----------|------|
| Vai trò khớp commit / comment / ownership trong group report | 4 |
| Giải thích được phần code mình khai báo | 4 |
| Không mâu thuẫn report ↔ repo | 2 |

### Luật phạt nặng (giống tinh thần Day 09)

| Vi phạm | Hệ quả |
|---------|--------|
| Report không khớp artifact (khai báo làm embed nhưng không có commit/change collection) | **0/40 cá nhân** |
| Sao chép report giữa thành viên | **0/40 các bên** |

---

## Bonus (+3 tối đa)

| Hành động | Điểm |
|-----------|------|
| Tích hợp Great Expectations hoặc pydantic model validate thật (không chỉ placeholder) | +2 |
| Freshness đo ở 2 boundary (ingest + publish) có log minh chứng | +1 |

> Bonus **chồng** với điều kiện Distinction (a)/(b): Distinction không cộng thêm điểm nếu đã nhận bonus cùng hạng mục — GV chọn cách ghi nhận nhất quán.

---

## FAQ

**Phải dùng Chroma giống Day 09 không?**  
Không bắt buộc trùng collection; mặc định `day10_kb`. Quan trọng là **chứng minh** pipeline của bạn feed index nào.

**`freshness_check=FAIL` trên data mẫu?**  
CSV mẫu có `exported_at` cũ — **FAIL là hợp lý**. Nhóm ghi trong runbook: SLA áp cho “data snapshot” hay cho “pipeline run”; có thể đổi `FRESHNESS_SLA_HOURS` hoặc cập nhật timestamp có chủ đích để PASS, miễn **giải thích nhất quán**.

**Có cần LLM để eval không?**  
Không. Baseline dùng retrieval + keyword. Nhóm có thể mở rộng LLM-judge (ghi rõ trong docs).

**Thiếu GPU?**  
`all-MiniLM-L6-v2` chạy CPU được; lab chỉ vài chục chunk.
**`instructor_quick_check.py` là gì?**  
Script đọc `grading_run.jsonl` / manifest để GV lọc nhanh lỗi format hoặc thiếu câu trước khi chấm sâu — không thay thế đánh giá chất lượng rule.

