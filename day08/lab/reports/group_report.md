# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** C401 - A4
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Dương Văn Hiệp | Tech Lead | 26ai.hiepnd@vinuni.edu |
| Trịnh Đức Anh | Tech Lead / Retrieval Owner | 26ai.anhtd@vinuni.edu |
| Nguyễn Minh Quân | Eval Owner | 26ai.hiepnd@vinuni.edu |
| Hoàng Thái Dương | Eval Owner | 26ai.quannm@vinuni.edu |
| Bùi Văn Đạt | Retrieval Owner / Documentation Owner | 26ai.datbv@vinuni.edu |
| Hoàng Quốc Chung | Documentation Owner | 26ai.chunghq@vinuni.edu |

**Ngày nộp:** 13/04/2026  
**Repo:** [C401-A4-Day-08-09-10](https://github.com/chrugez/C401-A4-Day-08-09-10)  
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

Nhóm xây dựng một pipeline RAG hoàn chỉnh cho trợ lý nội bộ CS + IT Helpdesk, đi theo luồng `index.py -> ChromaDB -> rag_answer.py -> eval.py`. Ở bước indexing, nhóm xử lý 5 tài liệu nội bộ, tách chunk theo heading và paragraph để giữ nguyên ý nghĩa của từng điều khoản thay vì cắt ngang giữa câu. Theo `architecture.md`, cấu hình chunking dùng khoảng `~400 tokens`, overlap `~80 tokens`, kèm metadata như `source`, `section`, `effective_date`, `department`, `access` để phục vụ citation và kiểm tra đúng phiên bản tài liệu. Embedding được tạo bằng `text-embedding-3-small` và lưu trong ChromaDB với cosine similarity. Ở Sprint 2, nhóm dùng dense retrieval làm baseline, lấy top-10 ứng viên rồi chọn top-3 chunk để build context cho grounded prompt. Ở Sprint 3, nhóm triển khai variant hybrid bằng cách kết hợp dense retrieval với BM25 exact-match nhằm xử lý tốt hơn các query chứa keyword đặc thù như `P1`, `Level 3`, `Approval Matrix`, `ERR-403-AUTH`. Sau đó nhóm dùng `eval.py` để chấm scorecard cho baseline và variant, rồi tổng hợp kết quả vào `architecture.md` và `tuning-log.md`.

**Embedding model:**
- OpenAI `text-embedding-3-small`
- Vector store: ChromaDB `PersistentClient`
- Similarity metric: cosine

**Retrieval variant (Sprint 3):**

Nhóm chọn `hybrid retrieval` làm variant của Sprint 3 vì corpus vừa có nội dung ngôn ngữ tự nhiên vừa có nhiều exact keyword, alias và tên tài liệu cũ/mới. Mục tiêu của biến thể này là tăng khả năng bắt đúng các truy vấn chứa mã lỗi hoặc tên gọi đặc thù mà dense retrieval có thể bỏ sót.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất trong lab.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn.

**Quyết định:** Chọn retrieval variant nào để so sánh với baseline và dùng làm cấu hình chính cho grading run

**Bối cảnh vấn đề:**

Vấn đề lớn nhất mà nhóm phải xử lý không phải là xây một pipeline RAG chạy được, mà là quyết định có nên đổi retrieval strategy hay không. Sau Sprint 2, baseline dense đã trả lời tốt nhiều câu cơ bản, nhưng nhóm vẫn lo rằng với các câu chứa alias, exact keyword hoặc tên tài liệu cũ, dense retrieval có thể thiếu chính xác. Đây là lý do nhóm phải thảo luận kỹ xem nên giữ cấu hình đơn giản, ổn định hay thêm một biến thể retrieval mạnh hơn để tối ưu hiệu năng.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Giữ `dense` | Đơn giản, ổn định, dễ giải thích, chi phí thấp | Có nguy cơ bỏ sót exact keyword, alias hoặc query dạng tên cũ |
| Đổi sang `hybrid` | Kết hợp semantic match và keyword match, phù hợp với corpus có nhiều từ khóa đặc thù | Có thể tăng nhiễu nếu keyword match kéo thêm chunk không đúng trọng tâm |

**Phương án đã chọn và lý do:**

Nhóm quyết định implement `hybrid` như một variant độc lập trong Sprint 3, đồng thời giữ nguyên các tham số khác như `top_k_search = 10`, `top_k_select = 3`, `use_rerank = False` để tuân thủ A/B Rule. Lý do chọn hướng này là vì nó là thay đổi nhỏ nhất nhưng vẫn đủ mạnh để kiểm tra giả thuyết rằng các query có exact keyword sẽ được cải thiện. Đây cũng là một quyết định hợp lý về mặt kỹ thuật vì không làm thay đổi prompt, embedding model hay chunking, nên mọi khác biệt ở scorecard có thể quy về retrieval mode.

**Bằng chứng từ scorecard/tuning-log:**

Kết quả trong `tuning-log.md` cho thấy giả thuyết ban đầu không đúng với dữ liệu eval hiện tại. Baseline dense đạt Faithfulness `4.50`, Answer Relevance `4.80`, Context Recall `5.00`, Completeness `3.90`, trong khi hybrid chỉ đạt lần lượt `4.30`, `4.40`, `5.00`, `3.70`. Câu `q06` là bằng chứng rõ nhất: hybrid kéo model sang context về temporary access thay vì escalation của ticket P1, làm các điểm Faithfulness, Relevance và Completeness cùng giảm mạnh. Vì vậy về mặt A/B, nhóm kết luận dense baseline tốt hơn hybrid trên bộ test_questions.

---

## 3. Kết quả grading questions (100–150 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Câu nào pipeline xử lý tốt nhất? Tại sao?
> - Câu nào pipeline fail? Root cause ở đâu (indexing / retrieval / generation)?
> - Câu gq07 (abstain) — pipeline xử lý thế nào?

**Câu tốt nhất:** ID: `gq07` — Lý do: pipeline abstain đúng với câu hỏi không có thông tin trong tài liệu, tránh hallucination và không bịa ra mức phạt SLA P1

**Câu fail:** ID: `gq02` hoặc `gq05` — Root cause: generation thiếu chi tiết tổng hợp từ nhiều nguồn; answer đúng một phần nhưng chưa chắc đã đáp ứng đủ tất cả tiêu chí của câu hỏi grading

**Câu gq07 (abstain):** Log cho thấy hệ thống trả lời “Không đủ dữ liệu để trả lời từ tài liệu hiện có.” với `sources = []`. Đây là cách xử lý đúng hướng theo SCORING.md vì câu này yêu cầu anti-hallucination hơn là cố trả lời.

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

> Dựa vào `docs/tuning-log.md`. Tóm tắt kết quả A/B thực tế của nhóm.

**Biến đã thay đổi (chỉ 1 biến):** `retrieval_mode` từ `dense` sang `hybrid`

| Metric | Baseline | Variant | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.50/5 | 4.30/5 | -0.20 |
| Answer Relevance | 4.80/5 | 4.40/5 | -0.40 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.90/5 | 3.70/5 | -0.20 |

**Kết luận:**

Variant hybrid kém hơn baseline trong dữ liệu A/B hiện tại. Điểm quan trọng là `Context Recall` của cả hai đều đạt `5.00/5`, nghĩa là vấn đề chính của nhóm không nằm ở chỗ không retrieve được đúng nguồn. Thay vào đó, failure mode nổi bật hơn là generation chưa tổng hợp đủ chi tiết hoặc bị lệch trọng tâm khi context có thêm nhiễu. Dù vậy, `logs/grading_run.json` cho thấy nhóm đã chạy grading bằng `hybrid`. Đây là một quyết định thực thi tại thời điểm 17:00–18:00 dựa trên giả thuyết kỹ thuật ban đầu; sau khi có đầy đủ scorecard và tuning-log, nhóm kết luận rằng nếu chạy lại grading với thông tin hiện có thì `baseline_dense` mới là cấu hình nên chọn.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Dương Văn Hiệp | Nối pipeline end-to-end, hỗ trợ chạy code và luồng chính | 1, 2 |
| Trịnh Đức Anh | Retrieval owner, làm việc với indexing và retrieval strategy | 1, 3 |
| Nguyễn Minh Quân | Eval owner, chấm scorecard và tổng hợp kết quả eval | 3, 4 |
| Hoàng Thái Dương | Eval owner, hỗ trợ phân tích A/B và kết quả câu hỏi | 3, 4 |
| Bùi Văn Đạt | Retrieval owner, phối hợp hoàn thiện tài liệu kỹ thuật `architecture.md` | 3, 4 |
| Hoàng Quốc Chung | Documentation owner, hoàn thiện `tuning-log.md` + `group_report.md`, quản lý repository của nhóm | 4 |

**Điều nhóm làm tốt:**

Nhóm làm tốt ở chỗ có phân vai khá rõ giữa code, retrieval, evaluation và documentation. Các file deliverable quan trọng như `architecture.md`, `tuning-log.md`, `scorecard_baseline.md`, `scorecard_variant.md` đều có dữ liệu thật, không chỉ là template. Ngoài ra nhóm cũng có ý thức dùng scorecard để kiểm tra giả thuyết thay vì chỉ kết luận theo cảm giác.

**Điều nhóm làm chưa tốt:**

Điểm chưa tốt là quyết định kỹ thuật ở thời điểm grading chưa hoàn toàn đồng bộ với kết quả A/B cuối cùng. Log grading cho thấy nhóm dùng `hybrid`, trong khi tài liệu tuning sau đó kết luận `dense` tốt hơn. Điều này cho thấy nhóm cần chốt cấu hình cuối cùng sớm hơn và có một bước review nhanh giữa evaluation owner với documentation owner trước khi đóng log.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nếu có thêm một ngày, nhóm sẽ thử `dense + rerank` thay vì tiếp tục mở rộng retrieval bằng hybrid, vì evidence hiện tại cho thấy recall đã đủ tốt nhưng chất lượng chọn chunk để generation vẫn chưa tối ưu. Nhóm cũng sẽ chỉnh prompt để ép model trả lời đủ các chi tiết phụ quan trọng như tên tài liệu mới, điều kiện kèm theo hoặc quy trình chuẩn, vì các lỗi ở `q07`, `q09`, `q10` đều cùng một pattern là đúng ý chính nhưng thiếu phần bổ sung cần thiết.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
