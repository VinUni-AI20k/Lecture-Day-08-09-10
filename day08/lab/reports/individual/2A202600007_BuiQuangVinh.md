# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** ___________  
**Vai trò trong nhóm:** Eval Owner / Documentation Owner  
**Ngày nộp:** 2026-04-13  

---

## 1. Tôi đã làm gì trong lab này? 

Trong lab này tôi chủ yếu làm ở Sprint 4 và phần tài liệu kỹ thuật của nhóm. Công việc chính của tôi là chạy và đọc kết quả từ `eval.py`, đối chiếu output của pipeline với `test_questions.json`, rồi ghi lại các quan sát quan trọng vào `docs/tuning-log.md` và `docs/architecture.md`. Tôi không tập trung vào viết retrieval logic hay chunking, mà tập trung vào việc trả lời câu hỏi: hệ thống đang sai ở đâu, sai kiểu gì, và bằng chứng nào cho thấy điều đó. Cụ thể, tôi tổng hợp baseline scorecard, xem các câu yếu như `q01`, `q06`, `q07`, `q10`, đọc thêm `logs/grading_run.json` để nhận diện các lỗi thực tế ở bộ câu hỏi grading, rồi chuyển các kết quả này thành technical report ngắn gọn, có luận điểm và bám sát output thật của repo.

---

## 2. Điều tôi hiểu rõ hơn sau lab này 

Điều tôi hiểu rõ hơn sau lab là evaluation trong RAG không chỉ là “chấm đúng hay sai”, mà là công cụ để tách failure mode. Trước đây tôi hay nghĩ nếu answer sai thì nguyên nhân chính là retrieval. Nhưng khi nhìn vào scorecard của nhóm, tôi thấy `Context Recall = 5.00/5` trong baseline, nghĩa là retriever hầu như vẫn lấy đúng source, trong khi `Completeness = 3.20/5` lại thấp hơn nhiều. Từ đó tôi hiểu rõ hơn khác biệt giữa recall và completeness: recall nói evidence có được mang về hay không, còn completeness nói model có dùng đủ evidence đó để trả lời không. Tôi cũng hiểu grounded prompt quan trọng thế nào. Prompt tốt có thể giúp model abstain an toàn ở câu không có thông tin như `ERR-403-AUTH`, nhưng prompt quá “chặt” cũng làm answer bị ngắn quá mức và bỏ mất ý quan trọng.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn 

Điều làm tôi ngạc nhiên nhất là có những câu hệ thống retrieve đúng tài liệu nhưng vẫn trả lời sai hoặc thiếu. Ban đầu tôi giả thuyết rằng baseline thất bại chủ yếu vì dense retrieval bỏ lỡ alias hoặc keyword. Giả thuyết đó đúng một phần với vài câu như `Approval Matrix`, nhưng khi nhìn kỹ vào `q01` và nhất là `gq05`, tôi thấy vấn đề lớn hơn là generation chọn nhầm chi tiết trong chính document đúng. `q01` lấy đúng `sla_p1_2026.pdf` nhưng answer lại nhấn vào “24 giờ viết báo cáo sự cố” thay vì SLA chính “15 phút phản hồi, 4 giờ xử lý”. `gq05` còn rõ hơn: log grading cho thấy source đúng có `it/access-control-sop.md`, nhưng answer lại nhầm approver và thời gian xử lý của `Admin Access`. Phần khó nhất vì vậy không phải chạy code, mà là chứng minh bằng dữ liệu rằng lỗi nằm ở bước nào.

---

## 4. Phân tích một câu hỏi trong scorecard 

**Câu hỏi:** `q01` — “SLA xử lý ticket P1 là bao lâu?”

**Phân tích:**

Đây là câu tôi thấy điển hình nhất để phân biệt retrieval và generation. Ở baseline, câu này có điểm `Faithfulness = 2`, `Relevance = 4`, `Recall = 5`, `Completeness = 1`. Nếu chỉ nhìn answer thì có thể kết luận chung chung là pipeline “trả lời sai”. Nhưng khi nhìn theo scorecard, `Recall = 5` cho biết source kỳ vọng là `support/sla-p1-2026.pdf` đã được retrieve thành công. Log `rag_answer.py` cũng cho thấy top candidates đứng đầu đều là chunk từ đúng file SLA. Như vậy lỗi không nằm ở indexing hay retrieval. Vấn đề nằm ở generation/select: model nhìn thấy đúng tài liệu nhưng chọn nhầm chi tiết phụ “24 giờ để viết báo cáo sự cố sau khi khắc phục” thay vì cặp SLA cốt lõi là “15 phút phản hồi ban đầu, 4 giờ resolution”. Với câu này, tôi cho rằng variant `hybrid` chưa chắc cải thiện nhiều, vì dense đã retrieve đúng source rồi. Đây không phải bài toán exact keyword, mà là bài toán chọn đúng evidence trong cùng tài liệu. Nếu có variant phù hợp hơn, tôi nghĩ rerank hoặc prompt ép model liệt kê đủ “response time + resolution time” sẽ hiệu quả hơn hybrid retrieval.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ làm hai việc. Thứ nhất, chạy đầy đủ `scorecard_variant.md` cho cấu hình `hybrid`. Thứ hai, tôi sẽ thử `use_rerank=True` hoặc sửa prompt để model bắt buộc nêu đủ các ý chính khi câu hỏi là multi-part. Lý do là kết quả eval hiện tại cho thấy điểm nghẽn lớn nhất không còn là recall, mà là answer synthesis ở các câu như `q01`, `gq02`, `gq05`, `gq09`. Thứ 3, phân tích và dựa vào kết quả thu được để giúp nhóm thực hiện tối ưu hơn cho pipeline RAG.

---

