# Lab Day 10 — Data Pipeline & Data Observability

**Môn:** AI in Action (AICB-P1)  
**Chủ đề:** ETL / cleaning / expectation suite / embed / freshness / before-after evidence  
**Thời gian:** 4 giờ (4 sprints × ~60 phút)  
**Tiếp nối:** Day 08 RAG · Day 09 Multi-agent — **cùng case CS + IT Helpdesk**, hôm nay làm **tầng dữ liệu** trước khi agent “đọc đúng version”.

**Slide:** [`../lecture-10.html`](../lecture-10.html)

---

## Bối cảnh

Vector store và agent Day 09 chỉ ổn nếu **pipeline ingest → clean → validate → publish** ổn. Lab này mô phỏng:

- Export “raw” từ hệ nguồn (CSV mẫu) có **duplicate**, **dòng thiếu ngày**, **doc_id lạ**, **ngày hiệu lực không ISO**, **xung đột version HR (10 vs 12 ngày phép)**, và **chunk policy sai cửa sổ hoàn tiền (14 vs 7 ngày)** — đúng narrative slide 3 Day 10 + mở rộng phân tầng.
- Nhóm phải có **log số record**, **quarantine**, **expectation halt có kiểm soát**, **run_id** trên manifest, và **bằng chứng before/after** trên retrieval test.

---

## Mục tiêu học tập

| Mục tiêu                                              | Sprint     |
| ----------------------------------------------------- | ---------- |
| Ingest + map schema + log raw                         | Sprint 1   |
| Cleaning rules + cleaned CSV + quarantine             | Sprint 1–2 |
| Expectation suite + embed Chroma (idempotent)         | Sprint 2   |
| Inject corruption + so sánh eval + quality report     | Sprint 3   |
| Freshness check + runbook + hoàn thiện docs & báo cáo | Sprint 4   |

---

## Cấu trúc thư mục

```
lab/
├── etl_pipeline.py           # Sprint 1–2: run ingest→clean→validate→embed
├── eval_retrieval.py         # Sprint 3–4: before/after retrieval (CSV)
├── grading_run.py            # JSONL cho câu grading (public muộn — xem SCORING)
├── instructor_quick_check.py # GV: sanity artifact grading/manifest (tuỳ chọn)
│
├── transform/
│   └── cleaning_rules.py     # Baseline rules — sinh viên mở rộng
├── quality/
│   └── expectations.py       # Baseline expectations — sinh viên mở rộng
├── monitoring/
│   └── freshness_check.py    # Đọc manifest + SLA đơn giản
│
├── contracts/
│   └── data_contract.yaml    # Contract dữ liệu — điền owner/SLA
│
├── data/
│   ├── docs/                 # 5 tài liệu (kế thừa nội dung Day 09 / policy)
│   ├── raw/
│   │   └── policy_export_dirty.csv   # Export bẩn mẫu
│   ├── test_questions.json           # Golden retrieval (3 câu)
│   └── grading_questions.json        # 2 câu chấm (keyword-based)
│
├── artifacts/                # Không commit chroma_db; commit được log/manifest/eval mẫu
│   ├── logs/
│   ├── manifests/
│   ├── quarantine/
│   └── eval/
│
├── docs/
│   ├── pipeline_architecture.md
│   ├── data_contract.md
│   ├── runbook.md
│   └── quality_report_template.md
│
├── reports/
│   ├── group_report.md
│   └── individual/
│       └── template.md
│
├── requirements.txt
└── .env.example
```

---

## Setup

```bash
cd lab
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

**Lần đầu** SentenceTransformers có thể tải model `all-MiniLM-L6-v2` (~90MB) — cần mạng.

---

## Chạy pipeline (Definition of Done tối thiểu)

```bash
# Luồng chuẩn: fix stale refund 14→7, expectation pass, embed
python etl_pipeline.py run

# Kiểm tra freshness theo manifest vừa tạo
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run-id>.json
```

**Eval retrieval (sau khi đã embed):**

```bash
python eval_retrieval.py --out artifacts/eval/before_after_eval.csv
cat artifacts/eval/before_after_eval.csv
```

> **Ghi chú chấm điểm:** `hits_forbidden` quét **toàn bộ top-k** chunk ghép lại (không chỉ top-1), để phát hiện “câu trả lời nhìn đúng nhưng context vẫn còn chunk stale” — đúng tinh thần observability.  
> **Index snapshot:** sau mỗi lần `run`, embed **upsert** theo `chunk_id` và **xoá id không còn trong cleaned** để tránh vector cũ làm fail grading (quan sát được “publish boundary”).

**Sprint 3 — inject có chủ đích (embed dữ liệu “xấu”, bỏ qua halt):**

```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
# So sánh với file eval sau khi chạy lại pipeline chuẩn (không flag inject)
```

**Grading (sau 17:00):**

```bash
python grading_run.py --out artifacts/eval/grading_run.jsonl
```

**Giảng viên — kiểm tra nhanh artifact (tuỳ chọn):**

```bash
python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl
python instructor_quick_check.py --manifest artifacts/manifests/manifest_<run-id>.json
```

---

## 4 Sprints (chi tiết)

### Sprint 1 (60') — Ingest & schema

- Đọc `data/raw/policy_export_dirty.csv` (hoặc bản raw nhóm tự tạo thêm).
- Điền **source map** ngắn trong `docs/data_contract.md` (ít nhất 2 nguồn / failure mode / metric).
- Chạy `python etl_pipeline.py run --run-id sprint1` và lưu log.

**DoD:** Log có `raw_records`, `cleaned_records`, `quarantine_records`, `run_id`.

---

### Sprint 2 (60') — Clean + validate + embed

- Baseline đã có sẵn: allowlist `doc_id`, chuẩn hoá `effective_date`, quarantine HR cũ, fix refund 14→7, dedupe, v.v. Nhóm phải thêm ≥ **3 rule mới** và ≥ **2 expectation mới** (đếm trên file nhận được).
- **Chống trivial:** mỗi rule/expectation mới phải có **tác động đo được** trên bộ mẫu hoặc trên inject (ghi trong `reports/group_report.md` bảng *metric_impact*: ví dụ `quarantine_records` tăng khi inject BOM, `expectation X fail` trước khi fix, v.v.). Rule chỉ “strip space” mà không đổi số liệu / không có kịch bản chứng minh → **trừ theo SCORING**.
- Đảm bảo embed **idempotent** (upsert `chunk_id` + prune id thừa sau publish — baseline đã làm).

**DoD:** `python etl_pipeline.py run` **exit 0** với expectation không halt (trừ khi demo có chủ đích).

---

### Sprint 3 (60') — Inject corruption & before/after

- Cố ý làm hỏng dữ liệu (duplicate thêm, sai policy, hoặc `--no-refund-fix` + `--skip-validate`).
- Lưu **2 file eval** hoặc 1 file có cột `scenario` (nhóm tự quy ước) + ảnh chụp / đoạn log chứng minh.
- Hoàn thành `docs/quality_report_template.md` thành `docs/quality_report.md` (hoặc để nguyên tên template nếu GV quy định khác — ghi rõ trong group report).

**DoD:** Có đoạn văn + số liệu chứng minh retrieval **tệ hơn** trước khi fix và **tốt hơn** sau fix (ít nhất câu `q_refund_window`). **Merit:** thêm một dòng chứng cứ cho `q_leave_version` (hoặc tương đương trong grading: `gq_d10_03`) — xem `SCORING.md`.

---

### Sprint 4 (60') — Monitoring + docs + báo cáo

- Điền `docs/pipeline_architecture.md`, `docs/data_contract.md`, `docs/runbook.md`.
- `python etl_pipeline.py freshness --manifest …` — giải thích PASS/WARN/FAIL trong runbook.
- Hoàn thành `reports/group_report.md` + mỗi người `reports/individual/[ten].md`.

**DoD:** README nhóm có “một lệnh chạy cả pipeline”; peer review 3 câu hỏi (slide Phần E) được ghi trong group report hoặc runbook.

---

## Deliverables (nộp bài)

| Item                                                          | Ghi chú                                                      |
| ------------------------------------------------------------- | ------------------------------------------------------------ |
| `etl_pipeline.py` + `transform/` + `quality/` + `monitoring/` | Có thể mở rộng file, không xóa entrypoint bắt buộc           |
| `contracts/data_contract.yaml`                                | Điền owner, SLA, nguồn                                       |
| `artifacts/logs/`, `manifests/`, `quarantine/`, `eval/`       | Ít nhất 1 run “tốt” + evidence inject                        |
| `docs/*.md` (3 file + quality report)                         | Theo template                                                |
| `reports/group_report.md`                                     |                                                              |
| `reports/individual/*.md`                                     | Mỗi thành viên                                               |
| `artifacts/eval/grading_run.jsonl`                            | Nếu khóa học chấm grading (3 câu: `gq_d10_01` … `gq_d10_03`) |

---

## Phân vai (gợi ý — đồng bộ slide Hands-on 10)

| Vai                          | Trách nhiệm                                        | Sprint chính |
| ---------------------------- | -------------------------------------------------- | ------------ |
| **Ingestion Owner**          | raw paths, logging, manifest                       | 1            |
| **Cleaning / Quality Owner** | `cleaning_rules.py`, `expectations.py`, quarantine | 1–3          |
| **Embed Owner**              | Chroma collection, idempotency, eval               | 2–3          |
| **Monitoring / Docs Owner**  | freshness, runbook, 3 docs, group report           | 4            |

---

## Debug order (nhắc từ slide Day 10)

```
Freshness / version → Volume & errors → Schema & contract → Lineage / run_id → mới đến model/prompt
```

---

## Tài nguyên tham khảo

- Slide: [`../lecture-10.html`](../lecture-10.html)
- Lab Day 09 (orchestration): [`../../day09/lab/README.md`](../../day09/lab/README.md)
- Great Expectations (tuỳ chọn nâng cao): https://docs.greatexpectations.io/
- ChromaDB: https://docs.trychroma.com/
