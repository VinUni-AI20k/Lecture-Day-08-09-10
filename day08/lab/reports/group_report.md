# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** 04  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| 2A202600312 Trần Thanh Phong | Tech Lead | ___ |
| 2A202600064 Hoàng Đinh Duy Anh | Retrieval Owner | dduyanhhoang@gmail.com |
| 2A202600486 Nguyễn Tiến Huy Hoàng | Eval Owner | hoang.nth17@gmail.com |
| 2A202600497 Trần Nhật Vĩ | Documentation Owner | vitrannhat@gmail.com |

**Ngày nộp:** 13/04/2026  
**Repo:** https://github.com/VinUni-AI20k/Lecture-Day-08-09-10.git  
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
> - Chunking strategy: size, overlap, phương pháp tách (by paragraph, by section, v.v.)
> - Embedding model đã dùng
> - Retrieval mode: dense / hybrid / rerank (Sprint 3 variant)

**Chunking decision:**
> VD: "Nhóm dùng chunk_size=500, overlap=50, tách theo section headers vì tài liệu có cấu trúc rõ ràng."

Nhóm dùng `chunk_size=400 tokens` (xấp xỉ 1600 ký tự) và `overlap=80 tokens` (xấp xỉ 320 ký tự), ưu tiên tách theo section header (`=== Section ===`). Quyết định này đến từ đặc thù bộ tài liệu policy/SOP có cấu trúc mục rõ ràng, nên tách theo heading giúp giữ nguyên ý nghĩa từng điều khoản. Overlap 80 được giữ để tránh mất ngữ cảnh ở ranh giới chunk. Metadata chuẩn hóa gồm `source`, `section`, `effective_date`, `department`, `access` để phục vụ citation, debug retrieval, và kiểm tra freshness. Sau Sprint 1, index tạo được 29 chunks từ 5 tài liệu và không có chunk thiếu metadata bắt buộc.

**Embedding model:**

Nhóm dùng `text-multilingual-embedding-002` trên Vertex AI (768-dim), lưu vào ChromaDB (`hnsw:space=cosine`). Ban đầu nhóm thử OpenAI embedding (1536-dim), nhưng khi chuyển môi trường sang Vertex AI thì gặp lỗi mismatch dimension của collection cũ trong ChromaDB. Vì Chroma lock dimension tại thời điểm tạo collection, nhóm xóa thư mục vector DB và build index lại toàn bộ để đảm bảo consistency giữa index-time và query-time embedding.

**Retrieval variant (Sprint 3):**
> Nêu rõ variant đã chọn (hybrid / rerank / query transform) và lý do ngắn gọn.

Variant Sprint 3 mà nhóm chọn là **hybrid retrieval** (Dense + BM25 kết hợp bằng RRF). Lý do chọn: tập câu hỏi có cả semantic query (alias như "Approval Matrix") lẫn exact keyword/mã lỗi (P1, ERR-403), nên giả thuyết ban đầu là hybrid sẽ cân bằng giữa recall ngữ nghĩa và precision từ khóa. Cấu hình thử nghiệm: `dense_weight=0.6`, `sparse_weight=0.4`, giữ nguyên các biến còn lại để đúng A/B rule.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất trong lab.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn.

**Quyết định:** Giữ `retrieval_mode="dense"` làm cấu hình chính để grading, không dùng hybrid làm default.

**Bối cảnh vấn đề:**

Trong Sprint 3, nhóm đứng trước lựa chọn quan trọng: tiếp tục baseline dense (đang ổn định) hay chuyển sang hybrid để tăng chất lượng retrieval. Về mặt lý thuyết, hybrid rất hấp dẫn vì có thể xử lý tốt cả câu hỏi semantic và keyword-heavy. Tuy nhiên, sau khi chạy scorecard và đọc từng câu trong tuning log, nhóm thấy một số câu bị giảm Completeness và Relevance khi thêm BM25. Vấn đề không nằm ở indexing (Context Recall vẫn cao), mà nằm ở chất lượng ranking đầu vào cho generation: BM25 tokenizer đơn giản `.lower().split()` gây nhiễu trên tiếng Việt, kéo sai chunk vào top-3. Nếu giữ hybrid để grading sẽ tăng rủi ro mất điểm các câu multi-part hoặc alias-sensitive.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Dense baseline | Ổn định, semantic matching tốt, score tổng thể cao hơn ở bộ test | Có trường hợp hallucination nhẹ ở generation (q07 baseline Faithfulness=1) |
| Hybrid (Dense + BM25 + RRF) | Lý thuyết tốt cho keyword + semantic, có thể tăng Faithfulness | Dễ nhiễu do BM25 tokenizer tiếng Việt chưa tốt, Completeness giảm rõ |

**Phương án đã chọn và lý do:**

Nhóm chọn **Dense baseline** làm cấu hình chính (`retrieval_mode="dense"`, `use_rerank=False`). Lý do cốt lõi là kết quả thực nghiệm tốt hơn và ổn định hơn trên bộ 10 câu: dense giữ Relevance và Completeness tốt hơn hybrid ở nhiều câu quan trọng (q02, q06, q07, q08). Với hybrid, dù Faithfulness trung bình tăng, nhưng phần suy giảm Completeness là không chấp nhận được cho bối cảnh grading có nhiều câu multi-constraint. Nhóm thống nhất ưu tiên cấu hình ít rủi ro hơn thay vì “nâng cấp” về mặt kỹ thuật nhưng không cải thiện điểm thực tế.

**Bằng chứng từ scorecard/tuning-log:**

- Baseline: Faithfulness 4.60, Relevance 5.00, Context Recall 5.00, Completeness 4.29  
- Variant hybrid: Faithfulness 5.00, Relevance 4.50 (hoặc 5.00 tùy lần chạy), Context Recall 5.00, Completeness giảm mạnh (3.14 trong tuning-log)  
- Từ `docs/tuning-log.md`, hybrid thua baseline ở các câu q02, q06, q07, q08; failure mode nổi bật là q07 alias query và q06 bị kéo chunk nhiễu liên quan emergency access.

---

## 3. Kết quả grading questions (100–150 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Câu nào pipeline xử lý tốt nhất? Tại sao?
> - Câu nào pipeline fail? Root cause ở đâu (indexing / retrieval / generation)?
> - Câu gq07 (abstain) — pipeline xử lý thế nào?

**Ước tính điểm raw:** 80 / 98

**Câu tốt nhất:** ID: q05 — Lý do: Câu hỏi fact đơn rõ ràng, dense và hybrid đều retrieve đúng nguồn `support/helpdesk-faq.md`, answer ngắn gọn, có citation và đạt đủ Faithfulness/Relevance/Recall/Completeness.

**Câu fail:** ID: q07 (với hybrid) — Root cause: Retrieval + Generation. BM25 không xử lý alias tốt trong ngữ cảnh tiếng Việt nên ranking nhiễu; sau đó model không tổng hợp đúng ý "Approval Matrix = Access Control SOP" và có lần trả lời abstain sai.

**Câu gq07 (abstain):** Với rule chấm của đề, pipeline cần nói rõ không có thông tin và không bịa. Từ hành vi q09 trong scorecard, baseline của nhóm có xu hướng abstain an toàn; nếu giữ cấu hình dense và prompt grounded hiện tại thì khả năng cao gq07 được điểm tốt.

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

> Dựa vào `docs/tuning-log.md`. Tóm tắt kết quả A/B thực tế của nhóm.

**Biến đã thay đổi (chỉ 1 biến):** `retrieval_mode`: `dense` -> `hybrid` (giữ nguyên top_k, rerank, prompt, model)

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.60 | 5.00 | +0.40 |
| Relevance | 5.00 | 4.50 | -0.50 |
| Context Recall | 5.00 | 5.00 | 0.00 |
| Completeness | 4.29 | 3.14 | -1.14 |

**Kết luận:**
> Variant tốt hơn hay kém hơn? Ở điểm nào?

Variant hybrid **kém hơn baseline** trên mục tiêu tổng thể. Điểm cộng duy nhất là Faithfulness tăng nhẹ, nhưng đổi lại Completeness giảm sâu và một số câu quan trọng bị regression (đặc biệt q06, q07). Vì grading ưu tiên đúng ý và đầy đủ theo tiêu chí câu hỏi, nhóm quyết định không dùng hybrid làm cấu hình nộp chính. Kết luận này nhất quán với tuning log: bottleneck nằm ở tokenizer sparse retrieval tiếng Việt, không phải ở dense recall.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| 2A202600312 Trần Thanh Phong | Điều phối sprint, nối pipeline end-to-end, tích hợp `rag_answer()` và vận hành demo | 1, 2 |
| 2A202600064 Hoàng Đinh Duy Anh | Xây retrieval stack: indexing retrieval, BM25, hybrid RRF; đồng thời góp phần hoàn thiện `architecture.md` và `tuning-log.md` | 1, 3, 4 |
| 2A202600486 Nguyễn Tiến Huy Hoàng | Chuẩn bị bộ câu hỏi, chạy scorecard, đối chiếu baseline/variant, `eval.py` | 3, 4 |
| 2A202600497 Trần Nhật Vĩ | Hoàn thiện `architecture.md`, `tuning-log.md`, tổng hợp bằng chứng kỹ thuật, `call_llm()`, `tranform_query()` | 2, 4 |

**Điều nhóm làm tốt:**

Nhóm làm tốt ở việc bám A/B rule (chỉ đổi một biến), ghi lại đầy đủ evidence trong tài liệu, và phân tách lỗi theo tầng (indexing/retrieval/generation) thay vì sửa ngẫu nhiên. Việc thống nhất format metadata và scorecard từ sớm giúp các sprint sau chạy nhanh hơn, ít tranh luận cảm tính.

**Điều nhóm làm chưa tốt:**

Nhóm chưa kiểm soát tốt chất lượng tokenizer cho BM25 tiếng Việt trước khi đưa hybrid vào variant chính, dẫn đến mất thời gian debug ở cuối Sprint 3. Ngoài ra, một số lần chạy scorecard có lỗi judge parsing (`LLM Judge Error`) làm nhiễu việc đọc kết quả, cần thêm bước sanitize output ổn định hơn trong `eval.py`.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ scorecard.

Nếu có thêm 1 ngày, nhóm sẽ thử 2 việc có evidence rõ: (1) thay tokenizer BM25 tiếng Việt (ví dụ `underthesea`) và giảm `sparse_weight` từ 0.4 xuống 0.2 để kiểm tra q06/q07 có bớt nhiễu không; (2) siết prompt generation theo checklist bắt buộc liệt kê đủ điều kiện để tăng Completeness (đặc biệt các câu giống q01, q08). Mục tiêu là giữ Relevance cao của dense nhưng giảm thiếu ý ở câu multi-detail.

---
