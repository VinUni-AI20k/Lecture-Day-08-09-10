# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** Nhóm 13 - E402  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Nguyễn Việt Trung | Tech Lead | trungtomng@gmail.com |
| Trần Ngô Hồng Hà | Retrieval Owner | bgohonghatran@gmail.com |
| Hà Việt Khánh | Retrieval Owner | \*\*\_ |
| Nguyễn Tuấn Kiệt | Eval Owner | junsikkun@gmail.com |
| Mã Khoa Học | Eval Owner | tunglamle132@gmail.com |
| Nguyễn Hữu Nam | Documentation Owner | 26ai.namnh@vinuni.edu.vn |

**Ngày nộp:** 13/04/2026  
**Repo:** https://github.com/TTrungNg/Nhom13-402-Day-08-09-10  
**Độ dài khuyến nghị:** 600–900 từ

---

> **Hướng dẫn nộp group report:**
>
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code, scorecard, hoặc tuning log** — không mô tả chung chung

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn pipeline của nhóm:
>
> - Chunking strategy: size, overlap, phương pháp tách (by paragraph, by section, v.v.)
> - Embedding model đã dùng
> - Retrieval mode: dense / hybrid / rerank (Sprint 3 variant)

**Chunking decision:**
Nhóm thống nhất chunking theo cấu hình baseline để dễ A/B và debug: **chunk size ~400 tokens**, **overlap ~80 tokens**. Thay vì ép “1 kiểu chunking cho mọi tài liệu”, nhóm chọn cách **tùy biến theo từng file** (tài liệu policy/SLA/FAQ/markdown có cấu trúc khác nhau), nhưng vẫn giữ chung các metadata để trace được nguồn và tăng khả năng lọc khi cần (ví dụ `department`, `section_title`, `effective_date`, `prev/next_chunk_id`, `aliases`).

**Embedding model:**

- **Embedding**: `text-embedding-3-small` (OpenAI)
- **Vector store**: ChromaDB persistent (cosine similarity)

**Retrieval variant (Sprint 3):**

> Nêu rõ variant đã chọn (hybrid / rerank / query transform) và lý do ngắn gọn.

Baseline (Sprint 2) là **dense retrieval** (top-k search 10 → chọn 3 chunk đưa vào prompt) và không rerank. Ở Sprint 3, nhóm chọn **hybrid retrieval** (dense + sparse/BM25, merge bằng RRF) vì corpus có cả văn bản tự nhiên lẫn keyword/thuật ngữ. Ngoài ra pipeline có hỗ trợ **query transformation** (đặc biệt decomposition) nhưng khi chạy A/B scorecard nhóm chỉ đổi **một biến** là `retrieval_mode` để đo tác động thật sự.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất trong lab.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn.

**Quyết định:** Chuyển retrieval từ **dense** sang **hybrid** (dense + sparse/BM25) theo A/B rule (chỉ đổi 1 biến)

**Bối cảnh vấn đề:**

Trong baseline dense, nhóm thấy một số câu hỏi có dấu hiệu “trượt keyword” hoặc trả lời không đúng trọng tâm dù retriever vẫn kéo được nguồn (đặc biệt các câu liên quan thuật ngữ/tên tài liệu hoặc câu hỏi dạng insufficient-context). Tuning-log ghi nhận các câu yếu nhất của baseline là **q7, q9, q10**. Với mục tiêu Sprint 3 là thử một variant cải thiện retrieval mà vẫn giữ cấu hình còn lại ổn định, nhóm cần một thay đổi “đủ lớn để thấy khác biệt” nhưng vẫn không phá vỡ pipeline.

**Các phương án đã cân nhắc:**

| Phương án                     | Ưu điểm                           | Nhược điểm                                                            |
| ----------------------------- | --------------------------------- | --------------------------------------------------------------------- |
| Dense-only (giữ nguyên)       | Latency thấp, đơn giản, ít bug    | Dễ bỏ lỡ exact keyword/alias; khó với query dùng tên gọi cũ           |
| Sparse-only (BM25)            | Bắt keyword rất tốt               | Kém với câu hỏi diễn đạt tự nhiên/đồng nghĩa; dễ nhiễu                |
| Hybrid (Dense + Sparse + RRF) | Kết hợp ưu điểm, giảm rủi ro miss | Latency cao hơn; cần implement cẩn thận (key/id mismatch dễ gây rỗng) |

**Phương án đã chọn và lý do:**

Nhóm chọn **hybrid retrieval** vì đây là cải tiến “hợp lý theo failure mode” của baseline: các câu có thuật ngữ/tên tài liệu thường cần keyword signal, trong khi câu hỏi hội thoại vẫn cần semantic match. Để tuân thủ A/B rule, nhóm giữ nguyên `top_k_search=10`, `top_k_select=3`, không bật rerank và không bật query transform khi chấm scorecard, nhằm kết luận rõ ràng tác động của `retrieval_mode`.

**Bằng chứng từ scorecard/tuning-log:**

Theo `docs/tuning-log.md`, chuyển sang hybrid giúp điểm trung bình tăng: **Faithfulness 3.7 → 3.9 (+0.2)**, **Answer Relevance 4.0 → 4.4 (+0.4)**; **Context Recall 5.0 giữ nguyên** và **Completeness 3.9 giữ nguyên**. Nhận xét thực nghiệm trong tuning-log cũng cho thấy hybrid cải thiện ở các câu như q6/q7 (các trường hợp cần keyword matching).

---

## 3. Kết quả grading questions (100–150 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
>
> - Câu nào pipeline xử lý tốt nhất? Tại sao?
> - Câu nào pipeline fail? Root cause ở đâu (indexing / retrieval / generation)?
> - Câu gq07 (abstain) — pipeline xử lý thế nào?

**Điểm raw:**

- **Baseline (dense): 70/98**
- **Variant (hybrid): 60/98** (tụt mạnh ở **gq05** vì trả lời sai approver/thời gian và bỏ yêu cầu training; bị tính **Penalty** do có chi tiết “1 ngày + Line Manager” không có trong `grading_criteria`)

**Câu tốt nhất:** ID: **gq04** — Lý do: cả baseline và variant đều đạt **5/5 Faithfulness, 5/5 Relevance, 5/5 Recall, 4/5 Completeness** (trả đúng “store credit = 110%”, chỉ thiếu nuance “tùy chọn, không bắt buộc”).

**Câu fail:** ID: **gq05** — Root cause: **generation/grounding**. Baseline bị tụt **Faithfulness = 1/5** do khẳng định sai về điều kiện cấp Admin Access cho contractor; variant có cải thiện Faithfulness (4/5) nhưng **Completeness = 2/5** vì sai quy trình phê duyệt và thời gian xử lý so với expected answer.

**Câu gq07 (abstain):** Pipeline đã tránh hallucination (không bịa mức phạt), nhưng “abstain” chưa đạt chuẩn criteria vì chưa nói rõ **“thông tin này không có trong tài liệu hiện có”**. Theo rubric gq07, câu trả lời tốt nhất nên nêu thẳng “tài liệu không quy định penalty” (sau đó mới gợi ý liên hệ đúng bộ phận nếu cần).

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

> Dựa vào `docs/tuning-log.md`. Tóm tắt kết quả A/B thực tế của nhóm.

**Biến đã thay đổi (chỉ 1 biến):** `retrieval_mode: "dense" → "hybrid"` (giữ nguyên top-k, không rerank, không query transform khi chấm scorecard)

| Metric           | Baseline | Variant | Delta |
| ---------------- | -------- | ------- | ----- |
| Faithfulness     | 3.7/5    | 3.9/5   | +0.2  |
| Answer Relevance | 4.0/5    | 4.4/5   | +0.4  |
| Context Recall   | 5.0/5    | 5.0/5   | n/a   |
| Completeness     | 3.9/5    | 3.9/5   | n/a   |

**Kết luận:**

> Variant tốt hơn hay kém hơn? Ở điểm nào?

Variant hybrid **tốt hơn nhẹ** so với baseline, nổi bật ở **Answer Relevance** (+0.4) và cải thiện nhẹ **Faithfulness** (+0.2). Tuy nhiên, vì Recall đã cao sẵn (5.0/5), hybrid không làm tăng Recall mà chủ yếu giúp “đưa đúng loại evidence” lên top-3 để LLM trả lời đúng trọng tâm hơn ở các câu có keyword/thuật ngữ. Các điểm rơi còn lại (ví dụ policy hallucination hoặc câu insufficient-context) cho thấy nhóm cần thêm guardrail/prompt và/hoặc rerank để nâng Faithfulness/Completeness trong vòng tuning tiếp theo.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên        | Phần đã làm                                                                                                                                                                                                                                       | Sprint |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Nguyễn Việt Trung | Tích hợp pipeline + query transformation (expansion/stepback/decomposition/HyDE), fix bug retrieval                                                                                                                                               | 2–3    |
| Trần Ngô Hồng Hà  | Implement dense/sparse/hybrid retrieval + tích hợp vào `rag_answer.py`                                                                                                                                                                            | 2–3    |
| Hà Việt Khánh     | Indexing + metadata trong `index.py`: chunking theo từng loại tài liệu (FAQ theo Q/A, SLA theo mức ưu tiên), chuẩn hóa metadata (doc_id/chunk_id/section_title/department/effective_date/prev-next/aliases/char_count), lưu vào ChromaDB (cosine) | 1      |
| Nguyễn Tuấn Kiệt  | LLM-as-Judge evaluation (`llm_eval.py`), scorecard + A/B artifacts                                                                                                                                                                                | 4      |
| Mã Khoa Học       | Manual evaluation (`manual_eval.py`), tổng hợp nhận xét theo metrics                                                                                                                                                                              | 4      |
| Nguyễn Hữu Nam    | Viết tài liệu nhóm: `docs/architecture.md` và `docs/tuning-log.md`, tổng hợp quyết định kỹ thuật + kết quả test để hỗ trợ debug/eval                                                                                                              | 4      |

**Điều nhóm làm tốt:**

- Tuân thủ **A/B rule** khi tuning: đổi đúng 1 biến (`retrieval_mode`) và ghi rõ trong `docs/tuning-log.md`, giúp kết luận dựa trên số liệu.
- Có **failure-mode checklist** và evidence (scorecard + log) nên debug nhanh hơn (trace theo index → retrieval → generation).

**Điều nhóm làm chưa tốt:**

---

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ scorecard.

Nhóm sẽ ưu tiên (1) **cross-encoder rerank** sau hybrid để giảm nhiễu khi top-k_search tăng, và (2) **siết grounded prompt theo loại câu hỏi** (policy/“tài liệu nào”/insufficient-context) để giảm hallucination. Lý do: scorecard cho thấy Recall đã cao nhưng Faithfulness chưa ổn định, và một số câu có đủ source vẫn bị trừ điểm do model suy diễn vượt context.

---

_File này lưu tại: `reports/group_report.md`_  
_Commit sau 18:00 được phép theo SCORING.md_
