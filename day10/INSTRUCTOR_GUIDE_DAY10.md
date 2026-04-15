# Hướng dẫn giảng viên — Day 10: Data Pipeline & Data Observability

Tài liệu đi kèm slide: [`lecture-10.html`](lecture-10.html) (46 slide). Trong trình duyệt: **← →** hoặc **Space** chuyển slide; **N** bật/tắt speaker notes (trùng `<aside class="notes">` trong HTML).

**Bài lab:** [`lab/README.md`](lab/README.md) — nên nhắc đến `run_id`, `before/after eval`, inject corruption khi vào khối Hands-on / Phần E.

**Mục đích file này:** cho giảng viên **kiến thức cốt lõi**, **lộ trình giảng**, **vấn đề hay gặp**, **câu hỏi lớp**, **nối lab**, **đào sâu**. Mã `D10-Sxx` lấy từ ghi chú slide; `day10_slide_blueprint.yaml` có thể không có trong repo.

---

## Cách dùng từng mục trong “Theo từng slide”

| Mục | Ý nghĩa |
|-----|---------|
| **Kiến thức** | Khái niệm buộc phải truyền đạt — có thể copy lên bảng phụ. |
| **Lộ trình giảng** | Thứ tự câu / ví dụ — chỉnh thời lượng theo lớp. |
| **Hay nhầm** | Trả lời sẵn khi lớp im hoặc đi sai hướng. |
| **Hỏi lớp** | Dừng 10–20 giây cho suy nghĩ hoặc trao đổi cặp. |
| **Lab** | Liên hệ thư mục / lệnh cụ thể trong `day10/lab/`. |
| **Đào sâu** | Link hoặc từ khóa tìm thêm khi sinh viên “hỏi thêm”. |

---

## 0. Chuẩn bị trước giờ

| Việc cần làm | Gợi ý |
|----------------|--------|
| Mở slide + rehearsal | Khối **Phần A–D** = lý thuyết có nhịp; **Hoạt động + đáp án** = nhịp chậm lại; **Hands-on + Phần E** = tăng tốc hướng dẫn lab. |
| Case xuyên suốt 3 ngày | CS + IT Helpdesk: **refund 7 ngày**, **P1 SLA**, **access SOP** — mọi ví dụ cố gắng trỏ về cùng artifact. |
| Đáp án mẫu (4 slide xanh) | Dùng để **chốt** sau hoạt động; nhấn “không duy nhất đúng” để tránh học vẹt. |
| Lab smoke | Máy GV: `cd lab && pip install -r requirements.txt && python etl_pipeline.py run` — tránh lỗi môi trường giờ lên lớp. |
| Chấm nhanh / phân hạng | Sau khi sinh viên nộp: `python grading_run.py` rồi `python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl`. Rubric **Pass / Merit / Distinction** và tiêu chí **chống trivial** nằm trong [`lab/SCORING.md`](lab/SCORING.md). |

**Tham khảo chung:**

- [Great Expectations — Expectations](https://docs.greatexpectations.io/docs/reference/learn/terms/expectation/)
- [Monte Carlo — Data Observability pillars](https://www.montecarlodata.com/blog-data-observability/)
- [AWS — What is CDC?](https://aws.amazon.com/what-is/change-data-capture/)
- [Google SRE — Monitoring distributed systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)

### Lab Day 10 — Phân tầng sinh viên (tóm tắt)

- **Dữ liệu mẫu** (`data/raw/policy_export_dirty.csv`): thêm export lạ, ngày không ISO, HR version conflict (10 vs 12 ngày) — buộc suy nghĩ versioning + allowlist + parse ngày.
- **Grading 3 câu** (`gq_d10_01` … `gq_d10_03`): câu 3 kiểm `expect_top1_doc_id` + `must_not` stale trong **toàn top-k** (theo tinh thần refund).
- **Chống trivial**: nhóm phải điền bảng `metric_impact` trong `reports/group_report.md`; GV có thể trừ điểm nếu rule/expectation không đổi số liệu trên mẫu hoặc inject.
- **Embed prune**: pipeline xóa vector id không còn trong cleaned để tránh “mồi cũ” làm fail grading sau các lần inject — nhắc lớp chạy lại `run` chuẩn trước khi nộp `grading_run.jsonl`.

---

## Timeline buổi học (9:00–13:00 · 4 giờ) — lý thuyết slide 1–37

Timeline này chỉ cho **buổi sáng / buổi lý thuyết**. **Từ slide 38** (Hands-on, hướng dẫn sprint, Phần E, demo, tổng kết slide, Q&A trên deck) thuộc **buổi thực hành** — GV xếp lịch riêng và bám [`lab/README.md`](lab/README.md) + [`lab/SCORING.md`](lab/SCORING.md).

Tổng **240 phút**, gồm **10 phút giải lao**. Phần còn lại **230 phút** trải trên **slide 1–37**. Khi trễ giờ, ưu tiên **Hoạt động + đáp án** (10–11, 19–20, 22–23, 31–32) và **Phần D** (timebox, idempotency, runbook); có thể rút ví dụ “đào sâu” ở Phần B/C.

| Giờ | Phút | Nội dung chính | Slide (tham chiếu) |
|-----|------|----------------|-------------------|
| **9:00–9:24** | 24 | Mở buổi, learning outcome, mục tiêu & rubric như “hợp đồng”, continuity 3 ngày | 1–5 |
| **9:24–10:10** | 46 | **Phần A** + **Hoạt động 1** + chốt đáp án mẫu | 6–11 |
| **10:10–10:20** | 10 | **Giải lao** | — |
| **10:20–11:04** | 44 | Pipeline trong AI stack, ingestion, khung source map, **Phần B** + **Hoạt động 2** + đáp án | 12–20 |
| **11:04–11:44** | 40 | Transform & dirty data, **Hoạt động 3** + đáp án; data quality as code; **5 pillars** | 21–25 |
| **11:44–12:06** | 22 | **Phần C** + **Dark statement** | 26–30 |
| **12:06–12:32** | 26 | **Hoạt động 4** (incident triage) + đáp án; orchestration, retry, **idempotency** (bản lý thuyết trước khi vào Phần D) | 31–33 |
| **12:32–13:00** | 28 | **Phần D**: timebox triage, idempotency patterns, orchestrator mental model, runbook post-incident — **3–5’ cuối** nhắc nối buổi TH (đọc trước `lab/README.md`, `run_id`, before/after) **không** mở slide 38+ | 34–37 |

**Ghi chú vận hành**

- **Slide 38–46:** không nằm trong timeline buổi sáng; dùng khi dạy buổi thực hành hoặc tự học có hướng dẫn.
- **Hoạt động** (10–11, 19–20, 22–23, 31–32): giữ timebox trên từng slide; lớp đông có thể giảm thời share, tăng thời làm nhóm có prompt rõ.
- **12:06–12:32 (31–33):** tập trung timebox triage nhóm + chốt metric; slide 33 giữ nhịp **tương tác ngắn** (idempotent key / rerun) để không ăn thời Phần D.
- **12:32–13:00 (34–37):** nếu lớp mỏi, xen **hỏi nhanh / đứng lên ~1 phút** giữa timebox và pattern; nếu dư thời gian, đào sâu một walk-through runbook hoặc nhắc lại thứ tự **Freshness → Volume → Schema → Lineage** (slide 30).

---

## Theo từng slide (1–46)

### Slide 1 — Title: Data Pipeline & Data Observability

- **Tiêu đề trên slide:** Data Pipeline & Data Observability (hero).
- **Kiến thức:** AI production = model + **data path** + serving; “observability” là quan sát **chuỗi giá trị dữ liệu** tới câu trả lời, không chỉ log app.
- **Lộ trình giảng:** (1) Nhắc Day 08 grounded + Day 09 điều phối. (2) Chỉ SVG: data → pipeline → vector → agent; nhấn **Quality** và **Observe**. (3) Câu đóng: “Hôm nay không học tên công cụ mà học **vết nứt** hay gặp.”
- **Hay nhầm:** Nhầm observability với “dashboard đẹp” — sửa: dashboard là **triệu chứng**; observability là **suy luận nguyên nhân** (có giả thuyết + bằng chứng).
- **Hỏi lớp:** “Nếu chỉ đo một thứ trước khi xem prompt, các em đo gì?” (Gợi ý trả lời: **Freshness** - độ tươi của dữ liệu, vì data cũ là nguyên nhân hàng đầu gây sai lệch ở production).
- **Lab:** Chưa cần; nhắn pipeline lab là “đo được trước/sau”.
- **Đào sâu:** D10-S01; OpenTelemetry (nếu hỏi trace hệ thống).

---

### Slide 2 — Instructor

- **Kiến thức:** Learning outcome ở mức **course** (detect trước user); audience đã có RAG/multi-agent.
- **Lộ trình giảng:** Điền tên/chức danh; 30–45 giây; không đọc hết bullet — chọn 2 bullet “focus” + “goal”.
- **Hay nhầm:** “AI engineer không cần biết data” — đối chứng: **accountability** cuối cùng thường là người ship agent.
- **Hỏi lớp:** “Ai trong nhóm từng bị đổ lỗi model trong khi lỗi là CSV?” (Gợi ý trả lời: Đây là câu hỏi kinh nghiệm; chốt lại rằng **AI accountability** bao gồm cả data quality).
- **Lab:** Gợi ý phân vai lab (ingestion / clean / embed / docs) trùng bullet slide Hands-on.
- **Đào sâu:** `deck_meta` blueprint nếu có.

---

### Slide 3 — Data DB sai → agent “hallucinate”

- **Kiến thức:** **Stale / wrong version** trong index → câu trả lời có vẻ hợp lý nhưng sai nghiệp vụ; khác **hallucination** thuần (không có grounding).
- **Lộ trình giảng:** Kể chuỗi: sync 02:00 fail → vector “hôm qua” → user phản đối policy; chi phí **niềm tin** và **thời gian điều tra**. Chỉ diagram, **chưa** định nghĩa ETL.
- **Hay nhầm:** Mọi sai đều do model — nhắc checklist: freshness → volume → schema → lineage (preview slide 30).
- **Hỏi lớp:** “Metric đầu tiên em check?” (Gợi ý trả lời: **Freshness SLA** hoặc **Document Version** hiện tại trong Vector Store).
- **Lab:** `data/raw/policy_export_dirty.csv` + chunk “14 ngày” — đúng cùng narrative.
- **Đào sâu:** D10-S02; bài viết về “stale retrieval” / “negative cache” trong RAG.

---

### Slide 4 — Mục tiêu học tập & đầu ra

- **Kiến thức:** Ba lớp deliverable: **chạy được** (script), **quan sát được** (expectation + monitor), **chứng minh được** (before/after).
- **Lộ trình giảng:** Learn 4h / Lab 4h — đọc rubric slide (ETL 45%, docs 25%, …) như **hợp đồng** với sinh viên.
- **Hay nhầm:** “Chỉ cần notebook” — chấp nhận nếu có **một lệnh reproduce** + log + `run_id`; khuyến khích `etl_pipeline.py`.
- **Hỏi lớp:** “Thế nào là một bằng chứng before/after **hợp lệ**?” (Gợi ý trả lời: Phải có cùng `input_query`, cùng `run_id`, và thấy rõ sự thay đổi từ sai sang đúng sau khi fix data).
- **Lab:** `lab/README.md` mục Sprint + `SCORING.md`.
- **Đào sâu:** D10-S03 + `deliverables` blueprint.

---

### Slide 5 — Nhắc lại mạch 3 ngày

- **Kiến thức:** **Continuity** artifact: cùng docs/case qua Day 08 → 09 → 10; Day 10 không phải môn mới tách rời.
- **Lộ trình giảng:** Đọc chip case (refund, P1, access) như **dữ liệu phải đúng version**; 1 câu: “Agent Day 09 chỉ tốt nếu corpus Day 10 sạch và tươi.”
- **Hay nhầm:** Học viên nghĩ Day 10 “chỉ ETL offline” — nối lại **agent + eval**.
- **Hỏi lớp:** “Một thay đổi policy PDF ảnh hưởng tới chỗ nào trong stack Day 09?” (Gợi ý trả lời: Ảnh hưởng tới **Retriever worker** - nó sẽ cung cấp context cũ cho LLM, dẫn đến sai lệch kết quả cuối).
- **Lab:** `lab/data/docs/` trùng domain Day 09.
- **Đào sâu:** `continuity` + `cross_day_case_study` trong blueprint.

---

### Slide 6 — Phần A · 1/4 — Triệu chứng agent ↔ tầng data

- **Kiến thức:** **Phân tầng lỗi:** triệu chứng UI (câu cũ, trích sai nguồn, spike sau deploy) → nghi ngờ freshness / dedupe / parser / schema.
- **Lộ trình giảng:** Quy tắc vàng: đo **freshness + volume** trước khi đụng prompt/model. Vẽ ví dụ 1 hàng trên slide lên bảng.
- **Hay nhầm:** Nhầm **retrieval gap** (chunk đúng nhưng rank sai) với **data bug** (chunk sai) — cách tách: golden question + đọc **metadata version** + so sánh với source.
- **Hỏi lớp:** “Triệu chứng ‘sau deploy mới sai’ gợi ý lỗi ở tầng nào?” (Gợi ý trả lời: Tầng **Parser** hoặc **Schema Mapping** - logic transform bị thay đổi gây mất thông tin hoặc sai format).
- **Lab:** `eval_retrieval.py` — top-k + keyword như proxy “đúng chunk chưa”.
- **Đào sâu:** D10-S04 (nếu map hoạt động); sách “Debugging ML” (khái niệm data slice).

---

### Slide 7 — Phần A · 2/4 — RACI tối giản

- **Kiến thức:** RACI rút gọn cho nhóm nhỏ: vẫn cần **tên trên artifact** (contract, runbook, alert).
- **Lộ trình giảng:** Startup: 1 người nhiều vai **được**, nhưng không được “không ai ký data contract”. Giảm căng thẳng corporate vs startup (ghi chú HTML).
- **Hay nhầm:** “Không có SME thì không làm được” — thay bằng: **source of truth** link + risk log + owner tạm.
- **Hỏi lớp:** “Ai chịu khi policy PDF đổi mà agent chưa re-embed?” (Gợi ý trả lời: Theo RACI, là **AI/Applied Engineer** hoặc **Data Engineer** vận hành pipeline; SME chỉ chịu trách nhiệm nội dung PDF).
- **Lab:** `contracts/data_contract.yaml` — field `owner_team`.
- **Đào sâu:** RACI trong data mesh / data product literature.

---

### Slide 8 — Phần A · 3/4 — SLA freshness (nghiệp vụ)

- **Kiến thức:** SLA freshness nên gắn **điểm đo** (sau clean? sau publish index?) và **ngôn ngữ nghiệp vụ** (≤ 4h sau khi PDF ký).
- **Lộ trình giảng:** PDF static vs ticket stream — SLA khác nhau; warning vs page on-call.
- **Hay nhầm:** Đo freshness ở cron start thay vì **publish** — dẫn đến “pipeline green nhưng user vẫn thấy cũ”.
- **Hỏi lớp:** “Nếu chỉ đo `ingest_done` mà không đo `index_visible`, em bỏ sót gì?” (Gợi ý trả lời: Bỏ sót các bước **Embedding** và **Indexing**; dữ liệu có thể đã "done" ở ingest nhưng chưa hiện diện với Agent).
- **Lab:** `monitoring/freshness_check.py` + manifest — thảo luận vì sao data mẫu có thể FAIL SLA (cố ý dạy).
- **Đào sâu:** SRE Book chương monitoring; typo “reflet” trên slide → sửa miệng **reflect**.

---

### Slide 9 — Phần A · 4/4 — Checklist trước embed

- **Kiến thức:** **Quality gate** trước khi tốn tiền embed: schema, encoding (UTF-8 + tiếng Việt), version metadata, skim 20 dòng + vài golden query.
- **Lộ trình giảng:** Checklist = “đừng embed mù”; có thể bảo nhóm copy vào `docs/` lab.
- **Hay nhầm:** Embed rồi mới phát hiện encoding lỗi — chi phí **xóa index + rebuild** cao.
- **Hỏi lớp:** “3 câu golden tối thiểu em sẽ chọn cho corpus CS là gì?” (Gợi ý trả lời: 3 câu hỏi về các chính sách hay thay đổi nhất: **Refund policy**, **Login issues**, và **SLA xử lý ticket**).
- **Lab:** `data/test_questions.json` như seed golden.
- **Đào sâu:** Chunking strategy (heading-based) — nối slide Phần B file PDF.

---

### Slide 10 — Hoạt động 1 — ETL hay ELT? Batch hay Streaming?

- **Kiến thức:** Phân loại theo **latency, governance, cost, debugability** — không tranh luận nhãn tuyệt đối.
- **Lộ trình giảng:** Cầu nối từ case 3 ngày (ghi chú HTML): 4’ cá nhân + 4’ nhóm + 4’ chốt; luân phiên nhóm trình bày 1 scenario.
- **Hay nhầm:** “Streaming luôn tốt hơn batch” — bàn về **độ phức tạp vận hành** và **exactly-once**.
- **Hỏi lớp:** “Scenario nào **bắt buộc** audit trail raw?” (Gợi ý trả lời: Các scenario liên quan đến **Compliance** hoặc **Legal** - cần lưu data gốc để đối chứng khi có tranh chấp).
- **Lab:** CSV batch trong lab; mở rộng tùy chọn stream — không bắt buộc.
- **Đào sâu:** D10-S04; so sánh ELT trên warehouse vs ETL trên app server.

---

### Slide 11 — Đáp án mẫu — Hoạt động 1

- **Kiến thức:** Đáp án **hợp lý** không duy nhất; điểm nằm ở **biện minh trade-off**.
- **Lộ trình giảng:** Chốt sau 4’ share (ghi chú HTML); nhấn từ khóa governance + cost trên slide đáp án.
- **Hay nhầm:** Học thuộc bảng — sửa: “đổi 1 giả định (VD PII) thì đáp án đổi thế nào?”
- **Hỏi lớp:** “Mask PII trong lake — ETL hay ELT hợp lý hơn? Vì sao?” (Gợi ý trả lời: **ETL** vì PII cần được che giấu/mã hóa *trước* khi lưu vào storage chung để đảm bảo an toàn dữ liệu).
- **Lab:** README Sprint 1 “map schema” — liên hệ quyết định ETL/ELT concept.
- **Đào sâu:** Lakehouse security patterns.

---

### Slide 12 — Data pipeline là gì trong AI stack?

- **Kiến thức:** Tầng: Sources → Pipeline → Storage/Serving → Agent; vector store phản ánh chất lượng tầng dưới.
- **Lộ trình giảng:** Hỏi nhanh: “Vector store là storage hay serving?” → cả hai có thể; then chốt **publish boundary**.
- **Hay nhầm:** “Chỉ cần vector DB tốt” — bỏ quên **ingest contract** và **transform**.
- **Hỏi lớp:** “Serving layer của nhóm em ở đâu: sau embed hay sau rerank?” (Gợi ý trả lời: Thường là sau **Rerank** (nếu có) để context đi vào LLM là context chất lượng nhất đã được chọn lọc).
- **Lab:** `etl_pipeline.py run` → Chroma = serving cho retrieval lab.
- **Đào sâu:** D10-S05.

---

### Slide 13 — Ingestion đa nguồn

- **Kiến thức:** Ingestion = **kéo + kiểm soát lỗi** (CDC, rate limit, backpressure, retry, DLQ); không phải “đọc file xong”.
- **Lộ trình giảng:** Liệt kê 4 loại nguồn trên slide; mỗi loại 1 failure mode nhanh.
- **Hay nhầm:** Coi API pagination là “chuyện nhỏ” — đến khi **429** làm mất trang dữ liệu.
- **Hỏi lớp:** “Backoff không jitter thì rủi ro gì?” (Gợi ý trả lời: Gây ra hiện tượng **Thundering Herd** - nhiều máy cùng retry vào một thời điểm cố định, làm sập hệ thống nguồn).
- **Lab:** Raw CSV mô phỏng export API/DB — mở rộng gọi API thật (optional).
- **Đào sâu:** D10-S06.

---

### Slide 14 — Nhắc nhanh trước khi vẽ source map

- **Kiến thức:** Khung 3 câu: **Nguồn nào · Hỏng kiểu gì · Đo cái gì**; template `source → method → check → owner`.
- **Lộ trình giảng:** Viết một hàng mẫu lên bảng trước khi nhóm làm Hoạt động 2.
- **Hay nhầm:** Source map chỉ liệt kê tool — thiếu **metric** là không triển khai được observability.
- **Hỏi lớp:** “Với CRM API, em đo freshness thế nào nếu không có `updated_at`?” (Gợi ý trả lời: Sử dụng **Ingest Timestamp** và so sánh **Record Count** hoặc **Data Hash** giữa các lần pull gần nhất).
- **Lab:** `docs/data_contract.md` phần source map.
- **Đào sâu:** D10-S06 + D10-S07.

---

### Slide 15 — Phần B · 1/4 — CDC vs snapshot

- **Kiến thức:** Snapshot + watermark: đơn giản, độ trễ cao; CDC: độ trễ thấp, vận hành + schema drift phức tạp hơn.
- **Lộ trình giảng:** Nhắc: **lab không bắt buộc CDC** — chỉ cần hiểu trade-off (ghi chú HTML).
- **Hay nhầm:** Bắt buộc Kafka/Debezium cho mọi bài toán — không.
- **Hỏi lớp:** “Policy PDF đổi 1 lần/tuần — CDC có overkill không?” (Gợi ý trả lời: **Có**, vì tần suất thay đổi thấp, chỉ cần batch sync theo ngày là đủ và tiết kiệm chi phí vận hành hơn).
- **Lab:** Batch CSV đủ; optional đọc AWS CDC doc.
- **Đào sâu:** AWS CDC; logical decoding Postgres.

---

### Slide 16 — Phần B · 2/4 — API ingestion

- **Kiến thức:** Retry-After, backoff + jitter, cursor pagination, checkpoint, partial page → DLQ.
- **Lộ trình giảng:** Liên hệ Hoạt động 2: mỗi API có **owner + checkpoint** (ghi chú HTML).
- **Hay nhầm:** Retry vô hạn trên 5xx — làm **đúp** dữ liệu hoặc ban IP.
- **Hỏi lớp:** “Checkpoint đặt ở đâu: DB riêng hay file?” (Gợi ý trả lời: Nên đặt ở một **Persistent State Store** hoặc **DB riêng** để an toàn hơn khi pipeline crash/restart).
- **Lab:** Mở rộng ingest từ HTTP (optional).
- **Đào sâu:** RFC 6585 (429); tài liệu rate limit vendor.

---

### Slide 17 — Phần B · 3/4 — Files PDF/HTML

- **Kiến thức:** **Content hash** vs **logical version** (`policy_v4`); OCR confidence; chunk theo heading để tránh trộn điều khoản.
- **Lộ trình giảng:** Case: hai file tên giống khác version — embed nhầm nếu chỉ nhìn tên.
- **Hay nhầm:** “Parser PDF = truth” — cần đo **lỗi OCR** và flag.
- **Hỏi lớp:** “Hash đổi nhưng `policy_version` không đổi — tin cái nào?” (Gợi ý trả lời: Tin **Hash**, vì nội dung thực tế đã thay đổi; version có thể do con người quên cập nhật tay).
- **Lab:** `data/docs/*.txt` đã chuẩn; sinh viên có thể thêm PDF.
- **Đào sâu:** Layout-aware PDF parsers (từ khóa tìm hiểu).

---

### Slide 18 — Phần B · 4/4 — Queue · backpressure · DLQ

- **Kiến thức:** Tách **ingest nhanh** khỏi **transform chậm**; queue depth = signal; poison message → DLQ.
- **Lộ trình giảng:** Chốt trước Hoạt động 2: mỗi luồng có buffer + owner (ghi chú HTML).
- **Hay nhầm:** DLQ = “thùng rác” — thực tế là **không mất sự kiện** + cần replay process.
- **Hỏi lớp:** “Khi queue depth tăng đột biến, em ưu tiên scale consumer hay giảm producer?” (Gợi ý trả lời: Tùy tình huống, nhưng thường là **scale consumer** để xử lý nhanh backlog; nếu nguồn đã overload thì phải áp dụng **backpressure** lên producer).
- **Lab:** Không bắt buộc queue thật — mô tả trong `pipeline_architecture.md`.
- **Đào sâu:** SQS DLQ patterns (AWS docs).

---

### Slide 19 — Hoạt động 2 — Mapping Ingestion Risks

- **Kiến thức:** Áp khung 3 câu hỏi lên bài CS + IT: DB + API + PDF; 2 rủi ro + 1 monitor tối thiểu.
- **Lộ trình giảng:** Nhóm 10’ + share 4’; không cần diagram hoàn hảo — cần **owner + metric**.
- **Hay nhầm:** Liệt kê 10 monitor mỏng — yêu cầu **1 ưu tiên E2E freshness** trước.
- **Hỏi lớp:** “Rủi ro ‘CRM trả partial JSON’ em phát hiện bằng gì?” (Gợi ý trả lời: Sử dụng **Schema Validation** mạnh hoặc check **Required Fields** trong layer ingestion/validation).
- **Lab:** `docs/data_contract.md` + `runbook.md` phần Detection.
- **Đào sâu:** D10-S07.

---

### Slide 20 — Đáp án mẫu — Hoạt động 2

- **Kiến thức:** Owner đổi theo tổ chức; bắt buộc **tên vai**; ví dụ PostgreSQL + CRM + PDF SOP.
- **Lộ trình giảng:** Nhấn owner có thể thay đổi (ghi chú HTML); so sánh với bài nhóm 1–2 nhóm.
- **Hay nhầm:** Monitor chung chung “check API OK” — không có **SLO cụ thể**.
- **Hỏi lớp:** “Metric nào phân biệt ‘ingest chạy’ vs ‘publish tới index’?” (Gợi ý trả lời: **Rows Ingested count** vs **Vectors Upserted count** (hoặc successful index visible timestamp)).
- **Lab:** `FRESHNESS_SLA_HOURS` + giải thích trong runbook.
- **Đào sâu:** SLO cho ingestion pipelines.

---

### Slide 21 — Transform: làm sạch và chuẩn hoá

- **Kiến thức:** Raw vs cleaned; dedupe, date parse, unicode, schema; ảnh hưởng trực tiếp tới **embedding distance** và **chunk boundary**.
- **Lộ trình giảng:** 1 ví dụ: cùng nội dung nhưng whitespace/encoding khác → vector khác đủ để gây duplicate retrieval.
- **Hay nhầm:** Clean “trên notebook một lần” — không tái lập được — nhắc **code hoá rule**.
- **Hỏi lớp:** “Silent drop vs quarantine — khi nào chọn cái nào?” (Gợi ý trả lời: **Silent drop** cho rác hoàn toàn (log vô nghĩa, spam); **Quarantine** cho dữ liệu quan trọng nhưng lỗi định dạng cần cứu/fix tay).
- **Lab:** `transform/cleaning_rules.py` + `artifacts/quarantine/`.
- **Đào sâu:** D10-S08.

---

### Slide 22 — Hoạt động 3 — Dirty data repair

- **Kiến thức:** Quyết định **drop / flag / reject**; quarantine vs silent drop có hậu quả compliance khác nhau.
- **Lộ trình giảng:** Nhóm 8–10’; tối thiểu **5 rule**; nhắc có đáp án mẫu 7 rule ở slide sau.
- **Hay nhầm:** Drop hết NULL mà không log — mất **lineage** vì sao mất dòng.
- **Hỏi lớp:** “Một dòng refund thiếu `order_id` — em làm gì trước khi embed?” (Gợi ý trả lời: **Flag** hoặc **Quarantine**; tuyệt đối không drop vì đây là dữ liệu nghiệp vụ quan trọng cần truy vết).
- **Lab:** Mở rộng rule trên `policy_export_dirty.csv`.
- **Đào sâu:** D10-S09.

---

### Slide 23 — Đáp án mẫu — Hoạt động 3

- **Kiến thức:** Bộ rule mẫu + `quarantine.csv` + `run_id` để audit.
- **Lộ trình giảng:** 7 rule dư so với 5 — nhấn quarantine vs silent drop (ghi chú HTML).
- **Hay nhầm:** Học viên copy nguyên rule mà không hiểu **điều kiện áp dụng** — hỏi “rule nào đụng PII?”
- **Hỏi lớp:** “Rule nào nên là **halt** thay vì warn?” (Gợi ý trả lời: Các rule vi phạm **Data Contract** nghiêm trọng như mất cột ID, lỗi encoding không thể đọc, hoặc duplicate khóa chính quy mô lớn).
- **Lab:** `quality/expectations.py` severity.
- **Đào sâu:** Data cleaning pattern catalog (OpenRefine concepts).

---

### Slide 24 — Data quality as code

- **Kiến thức:** Six dimensions (completeness, consistency, …); **expectation = code**; version control; halt có kiểm soát.
- **Lộ trình giảng:** Tương tác: 3 expectation “bắt buộc” cho corpus lớp (học viên gọi tên).
- **Hay nhầm:** “Test = quality” — test là behavior cụ thể; expectation là **khẳng định trên tập dữ liệu**.
- **Hỏi lớp:** “Expectation nào **không nên** halt toàn pipeline?” (Gợi ý trả lời: Các lỗi nhỏ, không ảnh hưởng đến logic trả lời như: thiếu tag phụ, sai format metadata không quan trọng, hoặc typos).
- **Lab:** `quality/expectations.py`; optional Great Expectations.
- **Đào sâu:** Great Expectations docs; D10-S10.

---

### Slide 25 — 5 pillars of data observability

- **Kiến thức:** Freshness, distribution, volume, schema, lineage — câu chuyện dashboard: 17h stale, −28% volume, drift schema.
- **Lộ trình giảng:** Hỏi: “Pillar nào dễ quên ở startup?” (thường **lineage** + **distribution**).
- **Hay nhầm:** Chỉ nhìn volume — distribution lệch vẫn là **incident** (ghi chú slide C3).
- **Hỏi lớp:** “Lineage giúp gì khi agent sai mà pipeline vẫn green?” (Gợi ý trả lời: Giúp truy vết ngược về **Data Source** để xem dữ liệu gốc có đúng không, hoặc tìm ra bước transform nào đã làm biến đổi nội dung sai lệch).
- **Lab:** `manifest` JSON + log như mini-lineage run.
- **Đào sâu:** Monte Carlo blog pillars; D10-S11.

---

### Slide 26 — Phần C · 1/4 — Schema evolution

- **Kiến thức:** Additive vs breaking; contract ở **biên**; parser deploy + theo dõi null%; đổi cột có thể **đổi ranh giới chunk**.
- **Lộ trình giảng:** Nối transform với versioning corpus RAG (ghi chú HTML).
- **Hay nhầm:** “Thêm cột không ảnh hưởng” — có thể ảnh hưởng **join** và **metadata filter** retrieval.
- **Hỏi lớp:** “Đổi tên cột `customer_id` → `cust_id` — breaking ở đâu trong stack?” (Gợi ý trả lời: Breaking ở **Ingestion Layer** (không tìm thấy cột), **SQL transform**, **Metadata mapping** của Agent, và các **Filters** trong RAG).
- **Lab:** `contracts/data_contract.yaml` version bump.
- **Đào sâu:** Avro/Protobuf compatibility modes.

---

### Slide 27 — Phần C · 2/4 — Warn · quarantine · halt

- **Kiến thức:** Ba mức xử lý; không phải mọi lỗi đều dừng pipeline; agent không đọc quarantine nếu contract + serving rõ.
- **Lộ trình giảng:** Tránh binary pass/fail trong đầu học viên (ghi chú HTML); ví dụ: 2% NULL → warn; 40% → halt.
- **Hay nhầm:** Halt quá nhiều → pipeline không bao giờ xanh — cần **SLO error budget** cho data.
- **Hỏi lớp:** “Khi nào warn đủ để ship nhưng halt thì không?” (Gợi ý trả lời: Khi tỷ lệ lỗi rất nhỏ (ví dụ < 1%) và không nằm ở các documents "hot-path" thường xuyên được truy vấn).
- **Lab:** `--skip-validate` chỉ cho demo có chủ đích + ghi runbook.
- **Đào sâu:** SRE error budgets áp dụng cho data pipelines.

---

### Slide 28 — Phần C · 3/4 — Distribution & anomaly

- **Kiến thức:** Volume ổn nhưng **phân phối** lệch → ingest “chạy nhưng sai” (vd toàn bộ event từ 1 shard).
- **Lộ trình giảng:** Volume ổn distribution lệch vẫn incident (ghi chú HTML).
- **Hay nhầm:** Chỉ alert khi `rows=0` — bỏ sót skew.
- **Hỏi lớp:** “Ví dụ skew trong ticket CS là gì?” (Gợi ý trả lời: Đột biến 90% ticket đến từ một phòng ban hoặc một lỗi duy nhất (do API filter sai hoặc cache lỗi)).
- **Lab:** Thống kê `doc_id` trong cleaned CSV (homework nhỏ).
- **Đào sâu:** Statistical monitoring (KS test, etc.) — chỉ nêu tên nếu hỏi sâu.

---

### Slide 29 — Phần C · 4/4 — SLI gợi ý cho RAG/agent

- **Kiến thức:** SLI: citation freshness, grounding rate, hit@k golden, latency **pipeline vs LLM** tách nhau.
- **Lộ trình giảng:** Cầu nối sang slide dark-statement (ghi chú HTML).
- **Hay nhầm:** Gộp latency pipeline vào latency LLM — sai chỗ tối ưu.
- **Hỏi lớp:** “SLI nào phát hiện stale tốt hơn: latency hay freshness index?” (Gợi ý trả lời: **Freshness index** vì nó phản ánh trực tiếp thời gian thực của dữ liệu mà Agent đang sử dụng).
- **Lab:** `eval_retrieval.py` như proxy hit@k đơn giản.
- **Đào sâu:** SRE SLI/SLO; papers “RAG evaluation”.

---

### Slide 30 — Dark statement — Đừng debug model trước

- **Kiến thức:** Thứ tự sưu tầm: **Freshness → Volume → Schema → Lineage → root cause**; chốt câu slogan slide.
- **Lộ trình giảng:** Nhắc lại trước incident triage (ghi chú slide 31 notes); 30 giây + lặp lại cuối giờ.
- **Hay nhầm:** Fine-tune model khi corpus cũ — expensive và sai hướng.
- **Hỏi lớp:** “Bằng chứng tối thiểu để chứng minh không phải lỗi model là gì?” (Gợi ý trả lời: Show **Metadata version** hoặc **Content chunk** mà Agent lấy ra từ Vector DB - nếu chunk đó cũ/sai thì lỗi ở Data).
- **Lab:** Before/after sau khi sửa data.
- **Đào sâu:** D10-S11 + D10-S12.

---

### Slide 31 — Hoạt động 4 — Incident triage

- **Kiến thức:** On-call: chọn **dashboard trước** khi mở code; flow 5 bước trên slide (Detect → …).
- **Lộ trình giảng:** Nhóm 8’ + chốt 6’; role-play “user đang chờ P1”.
- **Hay nhầm:** Mở hết dashboard song song — không timebox (nối Phần D slide 34).
- **Hỏi lớp:** “Bước đầu tiên trong slide — em đọc metric nào cụ thể?” (Gợi ý trả lời: Đọc **Freshness SLA** (thời gian nạp cuối của vector index) để biết hệ thống đã trễ bao lâu).
- **Lab:** `docs/runbook.md` điền mục Symptom/Detection.
- **Đào sâu:** D10-S12.

---

### Slide 32 — Đáp án mẫu — Hoạt động 4

- **Kiến thức:** Đáp án phải có **tên metric** (freshness_hours, rows_ingested, …) không chỉ chữ Detect/Isolate.
- **Lộ trình giảng:** Nhấn mạnh đáp án gắn metric cụ thể (ghi chú HTML).
- **Hay nhầm:** Viết “kiểm tra hệ thống” — không chấm được.
- **Hỏi lớp:** “Metric nào phân biệt ‘ingest chạy’ vs ‘publish tới index’?” (Gợi ý trả lời: **Rows Ingested count** vs **Vectors Upserted count**).
- **Lab:** Log `embed_upsert count` + manifest timestamp.
- **Đào sâu:** RED method cho incidents.

---

### Slide 33 — Orchestration, scheduling, retry, idempotency

- **Kiến thức:** DAG tối giản; cron + dependency; retry exponential; **idempotency** để rerun an toàn.
- **Lộ trình giảng:** Tương tác: step nào rerun dễ **duplicate embedding** nhất?
- **Hay nhầm:** Random `uuid` mỗi lần embed → không idempotent.
- **Hỏi lớp:** “Key ổn định cho chunk nên là gì?” (Gợi ý trả lời: Nên là **Hash của nội dung chunk** kết hợp với **ID của document gốc** để đảm bảo tính duy nhất và không đổi khi rerun).
- **Lab:** `chunk_id` ổn định trong `cleaning_rules.py` + Chroma upsert.
- **Đào sâu:** D10-S13; Airflow concepts.

---

### Slide 34 — Phần D · 1/4 — Triage có timebox

- **Kiến thức:** 0–5’ freshness, 5–12’ volume/errors, 12–20’ schema/lineage; hết time → **mitigate** (rollback, banner) + ghi incident.
- **Lộ trình giảng:** Timebox giúp thấy on-call không đoán mò vô hạn (ghi chú HTML).
- **Hay nhầm:** “Phải tìm root cause mới được mitigate” — trong P1 có thể **rollback trước**.
- **Hỏi lớp:** “Mitigate không cần biết root cause 100% — ví dụ?” (Gợi ý trả lời: **Rollback** về phiên bản dữ liệu sạch gần nhất hoặc treo banner **"Dữ liệu đang bảo trì"** trên UI của Agent).
- **Lab:** Ghi “timebox” trong runbook khi mô tả inject scenario.
- **Đào sâu:** Incident response playbooks (PagerDuty, etc.).

---

### Slide 35 — Phần D · 2/4 — Idempotency patterns

- **Kiến thức:** Natural key upsert; partition overwrite; delete-insert trong transaction; **staging → swap alias** cho vector index.
- **Lộ trình giảng:** Ví dụ duplicate embedding khi rerun không có key ổn định (ghi chú HTML).
- **Hay nhầm:** “Delete all rồi insert” trên production đang serve — downtime; dùng **blue/green** index.
- **Hỏi lớp:** “Swap alias giảm rủi ro gì so với upsert trực tiếp lên collection đang serve?” (Gợi ý trả lời: Giúp dữ liệu hiển thị **toàn bộ hoặc không gì cả** (atomic), tránh tình trạng Agent đọc trúng lúc collection đang xóa dở hoặc nạp dở gây thiếu context).
- **Lab:** Rerun `etl_pipeline.py run` hai lần — quan sát `count` Chroma.
- **Đào sâu:** Durable execution / workflow idempotency keys.

---

### Slide 36 — Phần D · 3/4 — Orchestrator mental model

- **Kiến thức:** Trigger, retry, SLA alert, sensor upstream, `run_id`, backfill không phá prod alias.
- **Lộ trình giảng:** Tránh tranh luận Airflow vs Prefect (ghi chú HTML) — cùng câu hỏi: dependency + alert + idempotency.
- **Hay nhầm:** Chọn tool trước khi có **DAG mental** trên giấy.
- **Hỏi lớp:** “Sensor khác trigger thế nào?” (Gợi ý trả lời: **Trigger** là điều kiện khởi chạy (vd: tới giờ cron); **Sensor** là điều kiện chờ đợi dữ liệu sẵn sàng mới chạy bước tiếp (vd: chờ file xuất hiện trên S3)).
- **Lab:** Mô tả DAG trong `pipeline_architecture.md` (ASCII/Mermaid).
- **Đào sâu:** Prefect / Dagster docs (chọn một).

---

### Slide 37 — Phần D · 4/4 — Runbook post-incident

- **Kiến thức:** Symptom → Detection → Diagnosis → Mitigation → Prevention; tài sản cho lần sau.
- **Lộ trình giảng:** Liên hệ Day 11 safety: runbook = guardrail vận hành (ghi chú HTML).
- **Hay nhầm:** Postmortem chỉ blame người — thiếu **action item** trên pipeline.
- **Hỏi lớp:** “Prevention: expectation nào thêm sau sự cố refund sai?” (Gợi ý trả lời: Thêm expectation kiểm tra **Range giá trị của refund** (không < 0, không quá lớn) và **Metadata freshness** của policy source).
- **Lab:** `docs/runbook.md` hoàn chỉnh.
- **Đào sâu:** Google SRE postmortem culture (rút gọn).

---

### Slide 38 — Hands-on 10 — ETL + Quality + Monitoring

- **Kiến thức:** Sprint 1–4; rubric slide; vai trò nhóm; **bắt buộc** chứng cứ data → answer/retrieval.
- **Lộ trình giảng:** Đọc deliverable list trên slide; nhấn “không chỉ nộp script” (ghi chú notes HTML).
- **Hay nhầm:** Chỉ embed lại không có **eval** — không đủ quality evidence.
- **Hỏi lớp:** “Nhóm em sẽ inject corruption kiểu gì để before/after rõ nhất?” (Gợi ý trả lời: Xóa cột ngày tháng hiệu lực của policy hoặc sửa giá trị hoàn tiền từ 7 thành 14 ngày trong file raw).
- **Lab:** Toàn bộ `lab/README.md` + `SCORING.md`.
- **Đào sâu:** D10-S14 + `practice_4h` blueprint.

---

### Slide 39 — Hướng dẫn thực hành 1 — setup & Sprint 1–2

- **Kiến thức:** Folder tree tối thiểu; run order `ingest → clean → validate → embed`; log mẫu `raw_records` / `cleaned_records` / `run_id`.
- **Lộ trình giảng:** Chiếu tree; live demo 1 lệnh nếu có mạng; nhấn log trước/sau (ghi chú HTML).
- **Hay nhầm:** Quên `run_id` — không chấm được và không debug được nhóm khác.
- **Hỏi lớp:** “Tại sao `quarantine_records` quan trọng cho chấm điểm?” (Gợi ý trả lời: Chứng minh được pipeline có **Quality Gate** tốt, biết cách cô lập dữ liệu lỗi thay vì silently drop hoặc nạp sai data).
- **Lab:** `python etl_pipeline.py run`, `artifacts/`.
- **Đào sâu:** blueprint sprints 1–2.

---

### Slide 40 — Hướng dẫn thực hành 2 — Sprint 3–4 & evidence

- **Kiến thức:** Inject: missing / duplicate / wrong format / encoding; evidence: CSV eval, quality report, screenshot monitor, báo cáo cá nhân 4 ý.
- **Lộ trình giảng:** Nhấn cố ý làm hỏng rồi đo (ghi chú HTML); chỉ rõ `before_after_eval.csv`.
- **Hay nhầm:** Chụp màn hình không gắn `run_id` — không làm chứng cứ hợp lệ.
- **Hỏi lớp:** “Evidence nào chứng minh **rerun idempotent**?” (Gợi ý trả lời: Log cho thấy **Vector Count** không đổi hoặc bằng đúng **Cleaned Record Count** sau khi chạy pipeline lần thứ hai).
- **Lab:** `python etl_pipeline.py run --no-refund-fix --skip-validate` + `eval_retrieval.py`; `grading_run.py`.
- **Đào sâu:** `report_template` blueprint.

---

### Slide 41 — Phần E · 1/4 — Definition of Done

- **Kiến thức:** `run_id`, log số record, expectation halt có kiểm soát, before/after, README một lệnh.
- **Lộ trình giảng:** Chốt DoD để nhóm không tranh cãi “xong” (ghi chú HTML).
- **Hay nhầm:** “Chạy trên máy tôi” không có `requirements.txt` pin version.
- **Hỏi lớp:** “Checklist nào trên slide em cho là khó nhất?” (Gợi ý trả lời: Thường là **Before/After Evidence** vì nó đòi hỏi phải có cả dữ liệu lỗi và dữ liệu sạch để đối chứng thuyết phục).
- **Lab:** `SCORING.md` deadline theo loại file.
- **Đào sâu:** Twelve-Factor app cho data jobs (rút gọn).

---

### Slide 42 — Phần E · 2/4 — Peer review

- **Kiến thức:** 10’ đổi bàn; 3 câu hỏi slide (rerun duplicate? freshness đo ở đâu? flag đi đâu?); trả lời bằng **file + log**.
- **Lộ trình giảng:** Khuyến khích đổi repo/zip (ghi chú HTML); GV đi vòng 1 vòng.
- **Hay nhầm:** Peer review thành **khen chung chung** — bắt buộc 3 bullet feedback có action.
- **Hỏi lớp:** “Câu hỏi nào trong 3 câu nhóm em trả lời kém nhất?” (Gợi ý trả lời: Thường là câu về **Idempotency** vì nhiều nhóm chưa quen với việc thiết kế hệ thống chạy lại an toàn).
- **Lab:** Ghi 3 bullet vào `group_report.md`.
- **Đào sâu:** Code review checklist cho data.

---

### Slide 43 — Phần E · 3/4 — Git & artifact hygiene

- **Kiến thức:** `.env.example`, pin dependency, `data/sample/`, docs cùng commit; docs **25%** điểm (nhắc lại rubric).
- **Lộ trình giảng:** Nhắc README rõ = điểm cộng (ghi chú HTML).
- **Hay nhầm:** Commit `.env` có secret — nhắc `.gitignore`.
- **Hỏi lớp:** “File nào **không** nên commit nhưng phải có mẫu?” (Gợi ý trả lời: File `.env` chứa API keys và secrets; thay vào đó chỉ commit file `.env.example`).
- **Lab:** `lab/.gitignore`, `.env.example`.
- **Đào sâu:** Git LFS nếu data lớn (chỉ khi hỏi).

---

### Slide 44 — Phần E · 4/4 — Demo 3 phút

- **Kiến thức:** Cấu trúc: use case → inject → đo freshness/volume → rerun idempotent → before/after + `run_id` khớp evidence.
- **Lộ trình giảng:** Giao mỗi nhóm chuẩn bị demo (ghi chú HTML); GV làm timer.
- **Hay nhầm:** Demo chỉ chạy code không có **câu chuyện bệnh nhân** (user impact).
- **Hỏi lớp:** “30 giây cuối em nhấn mạnh điều gì?” (Gợi ý trả lời: Nhấn mạnh vào **Kết quả Before/After** - con số cụ thể chứng minh chất lượng Agent tăng lên sau khi xử lý Data).
- **Lab:** Script demo đọc từ `README` nhóm.
- **Đào sâu:** Elevator pitch structure.

---

### Slide 45 — Tổng kết — Dữ liệu sạch + quan sát tốt

- **Kiến thức:** 4 takeaway trên slide; nối Day 11 guardrails; **60–80% effort** thường là data work (nếu slide có).
- **Lộ trình giảng:** Tương tác: một dashboard — ưu tiên **data observability** làm spine, agent metrics là lớp phụ khi đã có lineage (notes HTML).
- **Hay nhầm:** “Xong Day 10 là xong data mãi mãi” — nhắc **vòng đời** version policy.
- **Hỏi lớp:** “Một việc em làm ngày mai để bảo vệ corpus?” (Gợi ý trả lời: Thiết lập **Auto-alert** cho Freshness và Schema drift).
- **Lab:** Nộp đúng `artifacts/eval/` + report.
- **Đào sâu:** D10-S15 + `continuity.next_day`.

---

### Slide 46 — Q&A

- **Kiến thức:** Tổng hợp mâu thuẫn dashboard; cân bằng **cost observe** vs **cost incident**.
- **Lộ trình giảng:** Mở floor 5–10’; nếu im, ném lại câu slide 45.
- **Hay nhầm:** “Phải mua công cụ observability mới làm được” — không; bắt đầu từ manifest + log + golden eval.
- **Hỏi lớp:** “Câu chưa rõ nhất sau Day 10?” (Gợi ý trả lời: Lắng nghe và giải đáp nốt các thắc mắc về **tooling** hoặc **lineage phức tạp**).
- **Lab:** Office hour / forum link (GV điền).
- **Đào sâu:** D10-S15 interaction.

---

## Câu hỏi “khó” tổng hợp (mọi slide)

| Câu hỏi | Hướng trả lời ngắn |
|---------|-------------------|
| ETL vs ELT tốt hơn? | Phụ thuộc **nơi transform** và **ai được xem raw** (governance + khả năng SQL trên lake). |
| Có cần Kafka không? | Không bắt buộc cho lab; queue đơn giản đủ minh họa backpressure/DLQ. |
| Great Expectations bắt buộc? | Không; cần **kiểm tra version trong code** + halt có kiểm soát. |
| “Data quality 100%?” | Không; có **risk appetite** — warn / quarantine / halt. |
| LLM judge cho data quality? | Cẩn thận bias/cost; ưu tiên rule + mẫu human trên corpus nhỏ. |
| “Chỉ cần vector DB mạnh?” | Không thay thế **contract + transform + observability** ở tầng trước serving. |
| “Observability vs monitoring?” | Monitoring = biết **có chuyện**; observability = **vì sao** + **ở tầng nào** nhanh. |

---

## Bản quyền / trích dẫn slide

Trong `lecture-10.html`, nhiều slide ghi `[Sources]` trỏ tới `day10_slide_blueprint.yaml` và `day06-lecture-slides.html`. Giữ consistency khi xuất bản tài liệu khóa học.

---

*Tệp đồng bộ với `lecture-10.html` (46 slide). Khi thêm/bớt slide, cập nhật lại mục “Theo từng slide” và bảng “Cách dùng” nếu đổi cấu trúc giảng dạy.*
