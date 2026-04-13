# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** Nhóm 02 Zone 1 
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Nguyễn Duy Minh Hoàng | Tech Lead | ___ |
| Đào Anh Quân | Retrieval Owner | ___ |
| Nguyễn Đôn Đức | Retrieval + Grounded answer Owner | ___ |
| Nguyễn Lê Minh Luân | Eval Owner | ___ |
| Vũ Quang Phúc | Documentation Owner | ___ |

**Ngày nộp:** 13/04/2026  
**Repo:** Day8-Lab8-9-10

---

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

Pipeline của nhóm gồm 4 tầng: Index → Retrieve → Generate → Evaluate. Toàn bộ tài liệu nội bộ (5 file `.txt`) được đọc và xử lý qua `index.py`, sau đó câu hỏi được xử lý qua `rag_answer.py`, và kết quả được chấm điểm bởi `eval.py`.

**Chunking decision:**

Nhóm dùng **heading-based chunking**: split tài liệu theo dấu phân cách section `===...===` trước, đảm bảo mỗi chunk giữ nguyên một điều khoản/ý hoàn chỉnh. Với section dài quá ngưỡng (`chunk_size=400 tokens, overlap=80 tokens`), tiếp tục split theo paragraph với overlap để không mất thông tin biên. Lý do chọn heading-based thay vì cắt cứng theo token: tài liệu có cấu trúc rõ ràng (section headers) và cắt giữa điều khoản gây mất ngữ cảnh cho generation layer.

**Embedding model:**

OpenAI `text-embedding-3-small` — dùng nhất quán cả lúc index (`index.py`) lẫn lúc query (`rag_answer.py`) để đảm bảo không gian vector tương đồng. Vector store: ChromaDB `PersistentClient` với `hnsw:space=cosine`.

**Retrieval variant (Sprint 3):**

Nhóm chọn **Hybrid Retrieval (Dense + BM25) + Cross-encoder Rerank**. Lý do: corpus lẫn lộn ngôn ngữ tự nhiên (policy text) và từ khoá kỹ thuật (mã lỗi, tên tài liệu cũ như "Approval Matrix"). BM25 giúp exact keyword matching mà dense embedding bỏ lỡ; rerank dùng cross-encoder `ms-marco-MiniLM-L-6-v2` để chọn 3 chunk liên quan nhất từ top-10 candidates.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Chọn retrieval mode nào cho Sprint 3 — tiếp tục tối ưu Dense hay chuyển sang Hybrid + Rerank?

**Bối cảnh vấn đề:**

Sau khi hoàn thành baseline (dense retrieval), nhóm quan sát từ scorecard: Context Recall đã đạt 5.0/5 — retriever dense lấy đúng document cho hầu hết câu. Nhưng Completeness chỉ 4.0/5 và có 2 câu điểm rất thấp (q07 completeness=2, q09 faithfulness=2). Error Tree chỉ ra hai ứng viên nguyên nhân: (1) retrieval bỏ lỡ alias/keyword, (2) generation không abstain đúng cách. Nhóm phải quyết định: fix ở tầng retrieval hay generation.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Hybrid + Rerank | Giải quyết exact keyword (ERR-403, Approval Matrix); BM25 không cần API | Phức tạp hơn; RRF cần tune trọng số; cross-encoder tốn compute |
| Query Expansion | Giải quyết alias query mà không đổi index; sinh sub-query qua LLM | Tốn thêm API call; sub-query loãng có thể làm giảm precision |
| Fix generation prompt | Chi phí thấp, không đổi retrieval; trực tiếp vào root cause q07/q09 | Chưa có thời gian test đủ |

**Phương án đã chọn và lý do:**

Nhóm chọn **Hybrid + Rerank** vì giả thuyết ban đầu là retrieval thiếu keyword coverage (q07: alias "Approval Matrix", q09: mã "ERR-403-AUTH"). Biến này rõ ràng và có thể đo được bằng A/B test một biến.

**Bằng chứng từ scorecard/tuning-log:**

Kết quả thực tế từ scorecard cho thấy giả thuyết **không đúng**: Context Recall vẫn 5.0/5 ở cả hai config — dense đã retrieve đúng ngay từ đầu. Variant hybrid+rerank **cải thiện** q06 completeness (4→5) nhưng **làm xấu** q09 (completeness 3→1 vì model abstain cùn: "Tôi không biết"). Tổng thể Variant thấp hơn Baseline (Relevance −0.20, Completeness −0.10). Kết luận: lỗi thực sự nằm ở **generation layer** (prompt), không phải retrieval.

---

## 3. Kết quả grading questions (100–150 từ)

> _(Kết quả bên dưới dựa trên internal scorecard với `test_questions.json` — grading questions public sau 17:00 chưa được chạy chính thức tại thời điểm nộp báo cáo. Các nhận xét về pattern được suy ra từ scorecard nội bộ.)_

**Ước tính điểm raw:** ~62 / 98

**Câu tốt nhất:** q01, q02, q03, q05, q08 (SLA / Refund / Access Control / IT Helpdesk / HR Policy — đều đạt 5/5/5/5). Nguyên nhân: câu hỏi trực tiếp, một document, dense embedding đủ mạnh để lấy đúng chunk, generation không cần abstain.

**Câu fail:** q07 (Approval Matrix alias — completeness=2/5, cả hai config). Root cause: nằm ở **generation**, không phải retrieval. Dense đã retrieve đúng `access_control_sop` (Context Recall=5) nhưng model không nêu được tên tài liệu hiện tại "Access Control SOP" vì prompt không có instruction cite document name. q09 (ERR-403-AUTH — insufficient context): baseline faithfulness=2/5 do model suy diễn thêm thay vì abstain hoàn toàn.

**Câu gq07 (abstain — phạt vi phạm SLA P1):** Baseline (dense) có khả năng hallucinate mức phạt từ prior knowledge vì tài liệu không đề cập penalty. Variant (hybrid+rerank) dự kiến abstain rõ hơn ("Tôi không biết") nhưng thiếu gợi ý hữu ích — tương tự pattern q09 variant trong test scorecard.

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

**Biến đã thay đổi (chỉ 1 biến):** `retrieval_mode`: `"dense"` → `"hybrid"` + `use_rerank=True`

_(Tất cả tham số khác giữ nguyên: chunk_size=400, overlap=80, top_k_search=10, top_k_select=3, llm=gpt-4o-mini, temperature=0)_

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.60/5 | 4.60/5 | 0 |
| Answer Relevance | 4.50/5 | 4.30/5 | −0.20 |
| Context Recall | 5.00/5 | 5.00/5 | 0 |
| Completeness | 4.00/5 | 3.90/5 | −0.10 |

**Kết luận:**

Variant **tệ hơn** baseline tổng thể (−0.20 Relevance, −0.10 Completeness; Faithfulness và Context Recall không đổi). Kết quả hỗn hợp ở cấp độ câu hỏi:

- **q06 (Escalation P1):** Variant tốt hơn — Completeness tăng 4→5. Hybrid retrieval kéo thêm chunk escalation workflow đầy đủ hơn.
- **q09 (ERR-403-AUTH):** Variant tệ hơn rõ rệt — F/R/C đều từ 2-3 xuống 1. Hybrid+rerank làm model abstain hoàn toàn "Tôi không biết" thay vì partial guidance, LLM-as-Judge đánh giá thấp hơn.
- **q07 (Approval Matrix):** Cả hai config đều completeness=2 — vấn đề không phải retrieval.

Bài học quan trọng: **Context Recall = 5.0 trên cả 3 strategies** — dense embedding đã đủ tốt với corpus nhỏ (~29 chunks, 5 tài liệu). Đầu tư vào hybrid/rerank không mang lại cải thiện; cần tập trung vào **generation prompt** thay thế.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nguyễn Duy Minh Hoàng | Kiến trúc tổng thể, review code, điều phối team | Sprint 1–4 |
| Đào Anh Quân | `index.py`: preprocess, heading-based chunking, ChromaDB setup | Sprint 1 |
| Nguyễn Đôn Đức | `rag_answer.py`: dense retrieval, grounded prompt, citation, `temperature=0` fix, distance→score bug | Sprint 2, 3 |
| Nguyễn Lê Minh Luân | `eval.py`: 10 test questions, `run_scorecard()`, `compare_ab()` | Sprint 4 |
| Vũ Quang Phúc | `architecture.md`, `tuning-log.md` | Sprint 4 |

**Điều nhóm làm tốt:**

Pipeline hoàn chỉnh end-to-end, chạy được và có kết quả đo lường. Áp dụng A/B rule nghiêm chỉnh (chỉ đổi 1 biến mỗi lần). Error Tree giúp phân tích root cause có hệ thống. Cả nhóm đều nắm được toàn bộ pipeline, không chỉ phần mình làm.

**Điều nhóm làm chưa tốt:**

Dành quá nhiều thời gian tuning retrieval (Sprint 3) trong khi lỗi thực sự nằm ở generation (grounded prompt). Nếu ưu tiên sửa prompt cho q07 và q09 từ sớm, tổng điểm có thể cải thiện đáng kể mà không cần thay đổi kiến trúc retrieval.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

**1. Cải thiện grounded prompt (tác động cao nhất):** Bằng chứng từ scorecard: q07 completeness=2 (cả baseline lẫn variant) và q09 faithfulness=2 (baseline). Sẽ thêm hai instruction: (a) "Nếu người dùng dùng tên cũ/alias, hãy nêu tên tài liệu hiện tại trong câu trả lời"; (b) "Nếu chủ đề không được đề cập trong bất kỳ tài liệu nào, nêu rõ lý do và gợi ý kênh hỗ trợ phù hợp." Hai thay đổi này không cần đổi code retrieval, chỉ edit chuỗi prompt trong `build_grounded_prompt()`.

**2. Tăng `top_k_select` từ 3 → 5 cho câu hỏi multi-hop:** Bằng chứng từ q06 (Escalation P1): variant hybrid retrieve thêm chunk → completeness tăng 4→5. Thử tăng `top_k_select=5` trên baseline dense để xem Completeness q06 có tăng mà không cần đổi retrieval mode.

---

*File này lưu tại: `reports/GROUP_REPORT.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
