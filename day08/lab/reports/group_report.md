# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** Y3  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Võ Đại Phước, Nguyễn Tùng Lâm | Tech Lead | phuocvodn98@gmail.com, tunglampro7754@gmail.com
 |
| Kiều Đức Lâm, Trần Phan Văn Nhân | Retrieval Owner | lamkdhe180931@fpt.edu.vn, tpvncuber@gmail.com |
| Trần Văn Gia Bân | Eval Owner | tranvangiaban@gmail.com |
| Võ Đại Phước, Trần Văn Gia Bân | Documentation Owner | phuocvodn98@gmail.com, tranvangiaban@gmail.com |

**Ngày nộp:** 13/04/2026  
**Repo:** Lab8-C401-Y3  
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
> - Retrieval mode: dense / hybrid / rerank (Sprint 3 variant). 

Nhóm đã xây dựng một pipeline RAG hoàn chỉnh tập trung vào tính chính xác (precision) và khả năng trích dẫn nguồn gốc (citation).

Chunking decision:
Nhóm sử dụng chunk_size=400 và overlap=80 với chiến lược Paragraph-based splitting. Nhóm nhận thấy tài liệu Policy và SOP có cấu trúc phân đoạn rõ ràng; kích thước 400 tokens là điểm cân bằng lý tưởng giúp giữ trọn vẹn một điều khoản pháp lý mà không làm loãng vector embedding.

Embedding model:
Nhóm sử dụng text-embedding-3-small của OpenAI. Model này cho hiệu suất ổn định trên cả tiếng Anh và tiếng Việt, đồng thời hỗ trợ tốt cho việc tìm kiếm ngữ nghĩa sâu (semantic search).

Retrieval variant (Sprint 3):
Nhóm chọn Hybrid Retrieval (Dense + BM25) kết hợp với việc tăng top_k_select từ 3 lên 5. Lý do là vì bộ dữ liệu chứa nhiều thuật ngữ chuyên biệt (mã lỗi, mã SLA, các tên riêng như Cisco AnyConnect) mà Dense Search thuần túy thường bỏ lỡ do xu hướng "mềm hóa" ngữ nghĩa của nó.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất trong lab.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn.

**Quyết định:** Chuyển đổi từ Dense sang Hybrid

**Bối cảnh vấn đề:**

Trong quá trình chạy Baseline, nhóm gặp vấn đề nghiêm trọng với các câu hỏi yêu cầu độ chính xác tuyệt đối về phiên bản và đối tượng (như câu gq05 về quyền Admin cho Contractor). Hệ thống Dense search thường lấy về các đoạn văn bản có nội dung "gần giống" (ví dụ: quy trình cấp quyền cho nhân viên chính thức) thay vì đúng đối tượng Contractor, dẫn đến lỗi Hallucination.
_________________

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Tăng Top-K Dense | Đơn giản, dễ cài đặt. | Gây nhiễu cho LLM, dễ bị lỗi "Lost in the Middle". |
| Hybrid Search | Bắt được exact keyword, tăng Recall đáng kể. | Cần cài đặt thêm bộ máy tìm kiếm từ khóa (BM25). |
| Query Expansion | Giúp bao phủ nhiều nghĩa của câu hỏi. | Làm chậm tốc độ phản hồi và tốn token. |

**Phương án đã chọn và lý do:**

Nhóm chọn Hybrid Search. Kết quả từ Tuning Log cho thấy các từ khóa như "contractor", "penalty", hay "SLA P1" là các điểm neo (anchor) cực kỳ quan trọng. BM25 giúp đảm bảo các chunk chứa chính xác từ khóa này luôn được ưu tiên, trong khi Dense Search vẫn giữ nhiệm vụ hiểu bối cảnh câu hỏi.xs
_________________

**Bằng chứng từ scorecard/tuning-log:**

gq05 cho Faithfulness từ 1/5 lên 3/4

---

## 3. Kết quả grading questions (100–150 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Câu nào pipeline xử lý tốt nhất? Tại sao?
> - Câu nào pipeline fail? Root cause ở đâu (indexing / retrieval / generation)?
> - Câu gq07 (abstain) — pipeline xử lý thế nào?

**Ước tính điểm raw:** 83 / 98

**Câu tốt nhất:** ID: gq08 — Lý do: Lý do: Pipeline xử lý xuất sắc câu hỏi về "Disambiguation" (phân biệt 3 ngày nghỉ phép và 3 ngày nghỉ ốm). Nhờ Hybrid search, retriever lấy đủ context từ hr_leave_policy.txt để LLM so sánh chính xác hai quy định khác nhau này.

**Câu fail:** ID: gq07 — Root cause: Retrieval/Abstain Logic. Dù Retriever mang về đúng tài liệu SLA, nhưng model Judge chấm điểm Faithfulness thấp (1/5) vì model trả lời "Tôi không biết" (đúng theo yêu cầu abstain khi thiếu thông tin mức phạt), nhưng Judge lại kỳ vọng một sự giải thích sâu hơn về việc tài liệu không đề cập đến mức phạt.

**Câu gq07 (abstain):** Pipeline đã thực hiện đúng cơ chế bảo vệ (Guardrail). Khi query về mức phạt vi phạm SLA (không có trong docs), model đã từ chối bịa đặt và trả lời "Tôi không biết", đảm bảo tính trung thực (Grounded).

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

> Dựa vào `docs/tuning-log.md`. Tóm tắt kết quả A/B thực tế của nhóm.

**Biến đã thay đổi (chỉ 1 biến):** ___________________

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.20/5 | 4.40/5 | +0.20 |
| Answer Relevance | 4.60/5 | 4.60/5 | 0.00 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.40/5 | 3.50/5 | +0.10 |
**Kết luận:**
> Variant tốt hơn hay kém hơn? Ở điểm nào?

Variant sử dụng Hybrid Retrieval mang lại kết quả tốt hơn so với Baseline. Mặc dù điểm Recall giữ nguyên ở mức tuyệt đối (5.00) do tập dữ liệu nhỏ, nhưng sự thay đổi về chất lượng nằm ở tính chính xác của bằng chứng (Faithfulness). Việc kết hợp Keyword search giúp hệ thống định vị chính xác các thuật ngữ như "contractor" hay "SLA P1", tránh việc lấy nhầm các đoạn văn bản có ý nghĩa tương đồng nhưng sai đối tượng. Điều này giúp LLM bớt bị "nhiễu" và giảm thiểu các câu trả lời hư cấu.

_________________

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Võ Đại Phước | merge pull request, support | sprint 1,2,3,4 |
| Trần Văn Gia Bân | eval.py, report nhóm, logs grading question | sprint 4 |
| Kiều Đức Lâm  | retrieve_sparse, retrieve_hybrid, rerank, transformquery | sprint 3 |
| Trần Phan Văn Nhân | retrieve_dense(), call_llm()  | sprint 2 |
| Nguyễn Tùng Lâm | index.py | sprint 1 |

**Điều nhóm làm tốt:**

Nhóm phối hợp nhịp nhàng trong việc bàn giao pipeline từ khâu Indexing sang Retrieval. Vai trò Eval Owner cung cấp số liệu kịp thời giúp nhóm nhận diện ngay các lỗi Hallucination tại câu gq05 để điều chỉnh chiến thuật sang Hybrid kịp lúc.
_________________

**Điều nhóm làm chưa tốt:**

Giai đoạn đầu Sprint 3 gặp khó khăn trong việc cài đặt môi trường và quản lý rate limit của OpenAI API, dẫn đến việc phải chạy lại Evaluation nhiều lần.

_________________

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ scorecard.

Nhóm sẽ tập trung cải thiện Metadata-aware Retrieval. Dựa trên bằng chứng từ câu gq01 (điểm Completeness vẫn chưa tuyệt đối do thiếu bối cảnh phiên bản), việc tích hợp lọc tự động theo effective_date ngay tại bước Retrieval sẽ giúp LLM luôn nhận được phiên bản tài liệu mới nhất, thay vì phải tự suy luận từ bối cảnh cũ. Ngoài ra, nhóm muốn thử nghiệm Reranking sâu hơn bằng Cross-Encoder để tối ưu hóa thứ tự các chunk quan trọng nhất lên hàng đầu.
_________________

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
