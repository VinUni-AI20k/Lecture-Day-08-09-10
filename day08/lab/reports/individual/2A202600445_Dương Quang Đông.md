# Báo Cáo Cá Nhân - Lab Day 08: RAG Pipeline

**Họ và tên:** Dương Quang Đông  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500-800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi tập trung chính vào Sprint 1 và Sprint 3, tương ứng với vai trò Retrieval Owner của nhóm. Ở Sprint 1, tôi tham gia xây dựng tầng indexing trong `index.py`: xử lý preprocess tài liệu, chia chunk theo section, giữ metadata như `source`, `section`, `effective_date`, và dùng Sentence Transformers để tạo embedding local trước khi lưu vào ChromaDB. Mục tiêu là làm cho tầng retrieval có đầu vào sạch, có cấu trúc và ít mất ngữ cảnh nhất có thể. Ở Sprint 3, tôi chọn variant rerank và tích hợp `rerank()` trong `rag_answer.py` bằng cross-encoder `cross-encoder/ms-marco-MiniLM-L-6-v2`. Cơ chế này nhận các chunk từ dense retrieval, chấm điểm lại theo từng cặp query-chunk rồi chọn top chunk tốt nhất trước khi gọi LLM. Phần tôi làm nối trực tiếp giữa index của Sprint 1, baseline retrieval của pipeline, và phần evaluation trong `eval.py`.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Điều tôi hiểu rõ hơn sau lab là retrieval trong RAG không chỉ là “tìm đúng tài liệu”, mà là tìm đúng đoạn văn đủ tốt để model có thể trả lời ngắn gọn nhưng vẫn grounded. Khi tự tay làm Sprint 1, tôi thấy chunking và metadata ảnh hưởng rất mạnh đến chất lượng retrieval. Nếu chunk bị cắt giữa ý hoặc section không rõ, retriever có thể lấy đúng nguồn nhưng sai bằng chứng. Sau đó, khi làm Sprint 3, tôi hiểu rõ hơn vai trò của rerank. Dense retrieval rất tốt ở bước mở rộng ứng viên, nhưng top đầu vẫn có thể lẫn các chunk gần nghĩa mà chưa phải chunk trả lời trực tiếp câu hỏi. Cross-encoder rerank không thay dense retrieval, mà đóng vai trò lớp lọc cuối để tăng precision. Nói cách khác, dense retrieval giúp tăng recall, còn rerank giúp mô hình tập trung vào evidence sát câu hỏi hơn.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất của tôi là làm cho phần rerank hoạt động ổn định trong pipeline thật, chứ không chỉ viết xong hàm là đủ. Trong quá trình tích hợp, `rag_answer.py` từng bị lẫn code đúng với các đoạn TODO cũ, làm file lỗi cú pháp và khiến `eval.py` không import được. Sau khi dọn lại file và giữ đúng interface cho `rag_answer()`, rerank mới chạy được end-to-end. Điều khiến tôi ngạc nhiên là dù rerank đã chạy đúng, score tổng thể gần như không tốt hơn baseline. Theo log `eval.py`, baseline và variant đều có Faithfulness 3.70, Relevance 3.80, Context Recall 5.00, còn Completeness của rerank còn giảm nhẹ từ 3.60 xuống 3.50. Giả thuyết ban đầu của tôi là rerank sẽ tạo cải thiện rõ hơn, nhưng thực tế cho thấy dense baseline trên bộ dữ liệu này đã khá mạnh, nên phần lợi ích thêm vào của rerank không nhiều.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 - "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Đây là câu hỏi tôi thấy đáng phân tích nhất vì nó cho thấy rõ ranh giới giữa retrieval và generation. Trong log scorecard, cả baseline và variant rerank đều cho kết quả `Khong du du lieu`, nên Faithfulness, Relevance và Completeness đều rất thấp. Tuy nhiên `context_recall = 5` ở cả hai cấu hình cho thấy hệ thống thực ra đã retrieve được đúng nguồn kỳ vọng. Điều đó nghĩa là vấn đề chính không nằm ở Sprint 1 hay ở tầng indexing: metadata và chunking đủ tốt để source cần thiết xuất hiện trong tập bằng chứng.

Theo tôi, lỗi nằm nhiều hơn ở bước sinh câu trả lời và luật abstain. Query này dùng alias “Approval Matrix”, trong khi tài liệu thật là `access-control-sop.md`. Dense retrieval đã mang được đúng tài liệu về, nhưng model vẫn chưa đủ tự tin để kết luận rằng đây chính là tài liệu tương ứng với tên cũ, nên chọn trả lời abstain. Variant rerank không cải thiện trường hợp này vì rerank chỉ sắp xếp lại các chunk đã có, chứ không bổ sung suy luận nối alias với tên mới. Với loại câu hỏi như q07, query transformation hoặc prompt rõ hơn có lẽ sẽ hữu ích hơn rerank.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử tăng `top_k_search` để rerank có nhiều ứng viên hơn trước khi chọn top 3, vì hiện tại dense baseline đã khá mạnh nên rerank chưa có nhiều không gian tạo khác biệt. Ngoài ra, tôi sẽ thử thêm query transformation cho các câu hỏi alias như q07, vì log eval cho thấy rerank không giúp được những trường hợp mà vấn đề nằm ở cách diễn đạt truy vấn hơn là thứ tự chunk.
