# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** `[Chưa cung cấp]`  
**Thành viên:**


| Tên              | Vai trò                        | Email                                                   |
| ---------------- | ------------------------------ | ------------------------------------------------------- |
| Lê Hồng Quân     | Tech Lead, Documentation Owner | [hongquanliv@gmail.com](mailto:hongquanliv@gmail.com)   |
| Đoàn Sĩ Linh     | Retrieval Owner                | [doansilinh04@gmail.com](mailto:doansilinh04@gmail.com) |
| Nguyễn Đức Hải   | Eval Owner                     | `[Chưa cung cấp]`                                       |
| Phạm Thanh Lam   | Index Owner                    | `[Chưa cung cấp]`                                       |
| Dương Trung Hiếu | Tester, Document Writer        | [duonghieu734@gmail.com](mailto:duonghieu734@gmail.com) |


**Ngày nộp:** `2026-04-13`  
**Repo:** `[Chưa cung cấp]`  
**Độ dài khuyến nghị:** 600–900 từ

---

> **Hướng dẫn nộp group report:**
>
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code, scorecard, hoặc tuning log** — không mô tả chung chung

---

## 1. Pipeline nhóm đã xây dựng

**Chunking decision:**

Nhóm xây dựng một pipeline RAG đầy đủ gồm ba tầng: indexing, retrieval và grounded generation. Ở bước indexing, `index.py` preprocess 5 tài liệu nội bộ, giữ các metadata như `source`, `section`, `effective_date`, `department`, `access`, rồi chunk theo heading `=== ... ===`. Cấu hình chunking hiện tại là `chunk_size = 280`, `overlap = 50`; nếu section dài thì code cắt tiếp theo ký tự với overlap để giữ ngữ cảnh. Với tài liệu access control, nhóm bổ sung thêm một alias chunk cho tên cũ `Approval Matrix for System Access`.

**Embedding model:**

Nhóm dùng OpenAI embedding `text-embedding-3-small` và lưu vector vào ChromaDB `PersistentClient`, collection `rag_lab`, với cosine similarity.

**Retrieval variant (Sprint 3):**

Baseline của nhóm là `dense retrieval` với `top_k_search = 10`, `top_k_select = 3`, không rerank. Variant hiện tại không cố định một retrieval mode duy nhất mà dùng `retrieval_mode = "auto"`, kết hợp query router, query expansion, source filter và prompt v3. Lý do chọn hướng này là các thử nghiệm `hybrid + rerank` trước đó không outperform baseline, trong khi một số câu cross-document và câu dùng alias cần retrieval linh hoạt hơn nhưng vẫn phải giữ được độ ổn định của dense search.

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:** Giữ `dense` làm nền và chuyển sang variant kiểu `auto router + query expansion/filter + prompt v3` thay vì tiếp tục dùng `hybrid + rerank` toàn cục.

**Bối cảnh vấn đề:**

Ở các lần chạy trước, nhóm nhận thấy baseline dense khá ổn ở các câu đơn tài liệu nhưng hụt ở câu nhiều vế hoặc cross-document, đặc biệt là `gq06`. Khi thử tăng độ phức tạp bằng `hybrid + rerank`, kết quả không tốt lên ổn định, thậm chí có run còn gây regression. Vì vậy nhóm phải chọn giữa việc tiếp tục theo hướng retrieval phức tạp hơn, hay quay lại dense làm lõi rồi chỉ bổ sung những lớp điều chỉnh có mục tiêu.

**Các phương án đã cân nhắc:**


| Phương án                          | Ưu điểm                                          | Nhược điểm                                                          |
| ---------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------- |
| `hybrid + rerank` cho mọi query    | Lý thuyết mạnh hơn, giữ được semantic + keyword  | Kém ổn định, khó kiểm soát, có run không tốt hơn baseline           |
| `dense` + router/filter/prompt mới | Ít phá baseline, sửa đúng nhóm lỗi quan sát được | Không phải A/B “một biến” thật sự sạch, phải quản lý nhiều rule hơn |


**Phương án đã chọn và lý do:**

Nhóm chọn phương án thứ hai. Dense search đã cho recall tốt ở nhiều câu, nên thay vì đổi toàn bộ retrieval mode, nhóm giữ dense làm lõi rồi chỉ thêm query router, query expansion, source filter và prompt v3. Cách này bám sát evidence từ scorecard hơn: câu fail chủ yếu do thiếu đúng source thứ hai hoặc trả lời thiếu ý, chứ không phải do dense search hỏng hoàn toàn.

**Bằng chứng từ scorecard/tuning-log:**

Theo `docs/tuning-log.md`, baseline có `Context Recall = 4.67/5` và `Completeness = 3.4/5`, còn variant tăng lên `5.0/5` và `3.9/5`. Case rõ nhất là `gq06`: baseline chỉ retrieve `1/2` expected sources, variant retrieve đủ `2/2` và trả lời gần đầy đủ quy trình.

---

## 3. Kết quả grading questions

**Ước tính điểm raw:** `[Chưa thể suy ra chính xác chỉ từ grading_run.json]`

**Câu tốt nhất:** ID: `gq06` — Lý do: variant xử lý đúng bài toán cross-document khó nhất của bộ grading, retrieve đủ hai nguồn kỳ vọng và trả lời đúng quy trình cấp quyền tạm thời.

**Câu fail:** ID: `gq05` ở baseline — Root cause: generation/tổng hợp answer sai ý chính dù source đã đúng; baseline kết luận contractor không được cấp `Admin Access`, trong khi expected answer là có thể cấp nếu đủ điều kiện.

**Câu gq07 (abstain):** Pipeline xử lý theo hướng abstain, không bịa mức phạt SLA P1. Đây là hành vi an toàn và đúng tinh thần anti-hallucination, dù ở variant câu này bị chấm `relevance` thấp hơn baseline.

---

## 4. A/B Comparison — Baseline vs Variant

**Biến đã thay đổi:** Nâng cấp bước retrieve và generate bằng router, prompt mới, query expansion và source filter.


| Metric         | Baseline | Variant | Delta |
| -------------- | -------- | ------- | ----- |
| Faithfulness   | 4.9      | 5.0     | +0.1  |
| Relevance      | 4.8      | 4.8     | +0.0  |
| Context Recall | 4.67     | 5.0     | +0.33 |
| Completeness   | 3.4      | 3.9     | +0.5  |


**Kết luận:**

Variant hiện tốt hơn baseline trên bộ `grading_questions.json`, chủ yếu nhờ cải thiện ở `Context Recall` và `Completeness`. Bằng chứng mạnh nhất là `gq06` và `gq05`: baseline thiếu evidence hoặc tổng hợp sai, còn variant đã trả lời đúng hướng hơn. Tuy vậy, nhóm cũng ghi nhận đây không phải A/B test “một biến” hoàn toàn sạch, vì variant là một gói thay đổi gồm router, filter, prompt và query expansion. Regression đáng chú ý nhất là `gq07`, nơi variant vẫn abstain đúng nhưng bị chấm `relevance` thấp hơn.

---

## 5. Phân công và đánh giá nhóm

**Phân công thực tế:**


| Thành viên       | Phần đã làm                                                | Sprint     |
| ---------------- | ---------------------------------------------------------- | ---------- |
| Lê Hồng Quân     | Điều phối task, chốt hướng tuning, tổng hợp docs và report | Sprint 2–4 |
| Đoàn Sĩ Linh     | Retrieval logic, kiểm tra candidate/source                 | Sprint 2–3 |
| Nguyễn Đức Hải   | Evaluation, scorecard, grading run                         | Sprint 4   |
| Phạm Thanh Lam   | Indexing, chunking, metadata, build ChromaDB               | Sprint 1   |
| Dương Trung Hiếu | Test output, đọc kết quả, hỗ trợ viết tài liệu             | Sprint 3–4 |


**Điều nhóm làm tốt:**

Nhóm chia việc theo pipeline nên có thể làm song song mà không chờ nhau quá lâu. Khi có scorecard, cả nhóm quay lại dùng cùng một nguồn evidence để bàn tiếp, thay vì sửa cảm tính. Việc leader tổng hợp kết quả từ `architecture.md`, `tuning-log.md`, scorecard và `grading_run.json` cũng giúp các quyết định sau đó nhất quán hơn.

**Điều nhóm làm chưa tốt:**

Phần tuning của nhóm vẫn chưa thật sự tối ưu. Variant hiện tại đã cải thiện rõ ở một số case như `gq05` và `gq06`, nhưng mức tăng tổng thể so với baseline vẫn còn khiêm tốn và chưa đồng đều giữa các câu. Điều này cho thấy nhóm mới xử lý được một số failure mode nổi bật, chứ chưa tìm ra một hướng tune đủ mạnh để nâng chất lượng toàn bộ pipeline một cách rõ rệt.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

Nếu có thêm thời gian, nhóm sẽ làm một `Variant 2` sạch hơn về mặt thực nghiệm: tách riêng `prompt v3` và `router/filter` để biết chính xác thành phần nào tạo ra phần lớn cải thiện. Nhóm cũng muốn thử thêm một vòng đánh giá focused vào những câu cross-document và abstain như `gq06` và `gq07`, vì đây là hai loại câu phản ánh rõ nhất chất lượng thật của pipeline.

---

