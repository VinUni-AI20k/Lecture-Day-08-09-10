# Báo Cáo Cá Nhân - Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Tiến Dũng
**Vai trò trong nhóm:** Retrieval Owner - Dense and Prompt  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500-800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này tôi phụ trách phần baseline retrieval và generation trong `rag_answer.py`, chủ yếu ở Sprint 2 và một phần nối pipeline cho Sprint 3. Cụ thể, tôi implement `_get_collection()` để mở hoặc tự build collection `rag_lab` khi chưa có index; `retrieve_dense()` để query ChromaDB bằng embedding và trả về top-k chunks kèm score; `build_context_block()` để format các chunks thành context có đánh số `[1]`, `[2]`; `build_grounded_prompt()` để ép model chỉ trả lời dựa trên context, có citation và biết abstain; `call_llm()` để hỗ trợ cả OpenAI lẫn Gemini; và `rag_answer()` để nối toàn bộ luồng retrieve -> select/rerank -> generate -> trả về answer cùng sources. Tôi kết nối indexing ở `index.py` và evaluation ở `eval.py` vì nếu baseline này không ổn thì scorecard về sau sẽ bị ảnh hưởng theo.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Tôi hiểu rõ hơn rằng retrieval và prompting phải đi cùng nhau. Trước đây tôi nghĩ chỉ cần retrieve đúng source là đủ, nhưng khi làm `build_context_block()` và `build_grounded_prompt()` tôi thấy cùng một tập chunks mà cách đóng gói khác nhau có thể làm answer khác hẳn. Nếu context đưa vào prompt lộn xộn, không có đánh số, không nêu source và section, model rất dễ trả lời mơ hồ hoặc thiếu citation. Tôi cũng hiểu rõ hơn tác dụng của grounded prompt: nó không chỉ để nhắc model đừng bịa mà còn định nghĩa hành vi an toàn khi thiếu dữ liệu. Với use case nội bộ như policy, SLA hay access control, khả năng abstain đúng quan trọng không kém gì việc trả lời đúng vì trả lời sai có thể gây lỗi vận hành.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn nằm ở việc chạy end-to-end trong môi trường thật. Khi tôi chạy `python rag_answer.py`, script ban đầu vướng lỗi encoding của console Windows vì chuỗi tiếng Việt, nên phải chạy lại bằng `python -X utf8 rag_answer.py`. Sau đó pipeline tiếp tục lộ lỗi thực tế hơn: `OPENAI_API_KEY` trong môi trường hiện tại không hợp lệ, dẫn đến `AuthenticationError 401` ngay ở bước embedding trong `get_embedding()` và kéo theo retrieval không lấy được dữ liệu. Điều này giúp tôi hiểu rõ failure mode quan trọng của baseline là code có thể đúng về mặt cấu trúc nhưng vẫn fail nếu phụ thuộc môi trường chưa sạch. Ngoài ra, tôi cũng thấy `_get_collection()` rất cần thiết vì nếu collection chưa có thì baseline retrieval gần như chỉ trả về trạng thái không đủ dữ liệu.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q09 - "ERR-403-AUTH là lỗi gì và cách xử lý?"

**Phân tích:**

Tôi chọn q09 vì đây là câu thể hiện rõ vai trò của grounded prompt và khả năng abstain. Theo `test_questions.json`, câu này không có `expected_sources`, là bộ tài liệu hiện tại không chứa thông tin trực tiếp về mã lỗi `ERR-403-AUTH`. Trong `results/scorecard_baseline.md`, baseline đạt `Faithfulness = 5`, `Relevance = 1`, `Completeness = 3`, còn context recall để `None`. Với tôi, đây là kết quả hợp lý một phần: baseline đã làm đúng việc quan trọng nhất là không bịa ra câu trả lời khi không có chứng cứ. Điểm relevance thấp cho thấy câu trả lời an toàn nhưng chưa thật sự hữu ích cho người dùng có thể do model chỉ dừng ở mức không có thông tin mà chưa đưa thêm hướng xử lý như liên hệ helpdesk.

Lỗi chính ở câu này không nằm ở indexing hay retrieval vì corpus không có tài liệu phù hợp, trọng tâm là tầng generation và policy abstain. Nếu prompt quá yếu, model rất dễ dùng world knowledge để đoán `403` là authorization/authentication error và bị tính là hallucination. Variant hybrid gần như không cải thiện được nhiều cho q09, vì vấn đề không phải tìm thiếu source mà là không có source để tìm. 

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ làm hai việc. Thứ nhất, bổ sung một nhánh xử lý rõ hơn cho các câu không có đủ evidence: thay vì chỉ abstain ngắn, model sẽ trả lời theo mẫu an toàn nhưng vẫn hữu ích hơn, ví dụ nêu rõ không có trong tài liệu hiện tại và gợi ý liên hệ bộ phận phù hợp. Và tôi sẽ thêm fallback local embedding khi `OPENAI_API_KEY` lỗi để baseline retrieval không phụ thuộc hoàn toàn vào một cấu hình môi trường duy nhất.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
