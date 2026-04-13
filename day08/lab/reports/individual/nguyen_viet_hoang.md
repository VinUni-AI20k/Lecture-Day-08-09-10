# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Việt Hoàng  
**Vai trò trong nhóm:** RAG Developer  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi phụ trách chính Sprint 2 với vai trò RAG Developer, tập trung hoàn thiện baseline `rag_answer.py`. Công việc cốt lõi của tôi gồm ba phần: (1) implement `retrieve_dense()` để truy vấn ChromaDB bằng embedding và lấy Top-K chunks theo độ tương đồng; (2) xây dựng `call_llm()` để kết nối model sinh câu trả lời ổn định (temperature thấp, có xử lý lỗi API key cho cả OpenAI/Gemini); (3) hoàn chỉnh hàm `rag_answer()` theo luồng Retrieve -> Build Context -> Generate -> Extract Sources.  

Tôi cũng thiết kế prompt theo hướng grounded-answer: model chỉ được trả lời dựa trên context đã retrieve, phải gắn citation `[1]`, `[2]` tương ứng với nguồn, và phải nói rõ "không đủ dữ liệu" khi bằng chứng không đủ. Ngoài baseline, tôi có thêm phần mở rộng cho Sprint 3 gồm `retrieve_sparse()`, `retrieve_hybrid()`, `rerank()` và `transform_query()` để nhóm có thể so sánh variant nhanh. Phần này kết nối trực tiếp với P1 (Data Engineer) vì tôi cần metadata thống nhất (`source`, `section`, `effective_date`) để citation hoạt động đúng; đồng thời tạo nền cho P3 (Optimization) và cho P4 (Eval) chấm điểm ở Sprint 4.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, điều tôi hiểu rõ hơn nhất là retrieval quality quyết định trần hiệu năng của cả pipeline RAG. Trước đây tôi nghĩ chỉ cần prompt tốt là model sẽ trả lời ổn, nhưng khi làm thực tế tôi thấy nếu chunk retrieve không đúng trọng tâm thì model dễ suy diễn hoặc trả lời thiếu ý, dù prompt đã ràng buộc. Vì vậy baseline tốt phải ưu tiên chọn đúng context trước khi nói về tối ưu generation.  

Concept thứ hai tôi hiểu sâu hơn là grounded prompting với citation không chỉ để "trông chuyên nghiệp" mà là cơ chế kiểm soát độ tin cậy. Khi ép output có `[1]`, `[2]` và liên kết với metadata nguồn, nhóm có thể trace ngược câu trả lời về tài liệu gốc để debug nhanh: lỗi do index, do retrieve hay do model diễn giải. Tôi cũng thấy cơ chế abstain ("không đủ dữ liệu") rất quan trọng trong môi trường nghiệp vụ: trả lời thiếu còn nguy hiểm hơn trả lời không biết. Nhờ đó baseline có hành vi an toàn hơn và phù hợp làm mốc so sánh cho variant.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất tôi gặp là trường hợp retrieve ra các chunk có điểm similarity khá cao nhưng câu trả lời vẫn không đủ chính xác hoặc không có đủ bằng chứng để trích dẫn trọn vẹn. Giả thuyết ban đầu của tôi là chỉ cần tăng `top_k_search` sẽ cải thiện chất lượng, nhưng thực tế khi tăng quá cao thì nhiễu tăng, context dài hơn và model lại dễ "lạc ý".  

Phần mất nhiều thời gian debug nhất là đồng bộ metadata giữa bước index và bước rag answer. Chỉ cần tên key lệch nhẹ (ví dụ chỗ dùng `source`, chỗ khác dùng `file_name`) là citation format bị hỏng hoặc danh sách sources rỗng, khiến output nhìn đúng bề ngoài nhưng không dùng được cho eval. Tôi xử lý bằng cách chốt schema metadata ngay trong sprint, kiểm tra kỹ từng chunk trả về ở verbose mode, và chuẩn hóa format context `[i] source | section | score=...`. Sau khi sửa dứt điểm phần này, pipeline baseline chạy ổn định hơn rõ rệt và dễ bàn giao cho các bạn làm optimization/evaluation.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** "ERR-403-AUTH là lỗi gì?"

**Phân tích:**

Đây là câu hỏi tôi chọn vì nó kiểm tra đúng khả năng "không bịa" của baseline. Ở bộ tài liệu hiện có, lỗi `ERR-403-AUTH` không xuất hiện trong các văn bản đã index. Kết quả baseline của nhóm trả về theo hướng abstain: nêu rằng không đủ dữ liệu trong context hiện tại để kết luận chính xác, đồng thời không gắn các citation giả. Với tiêu chí chấm điểm, câu này không được điểm cao về completeness (vì không cung cấp định nghĩa lỗi), nhưng lại tốt về faithfulness và factual safety vì không suy đoán ngoài nguồn.  

Phân tích lỗi cho thấy đây không phải lỗi generation, mà là giới hạn ở tầng retrieval/indexing: kho tài liệu chưa chứa tri thức cần thiết. Nếu ép model trả lời "có vẻ đúng" thì sẽ làm giảm độ tin cậy của toàn hệ thống. Khi so baseline với variant (Hybrid/Rerank), kết quả của câu này thường không cải thiện đáng kể vì bản chất dữ liệu gốc vẫn thiếu. Variant chỉ giúp khi câu trả lời có tồn tại nhưng bị retrieve trượt; còn khi knowledge chưa có trong corpus, phương án đúng là mở rộng nguồn dữ liệu hoặc bổ sung tài liệu lỗi hệ thống. Câu này giúp nhóm tôi thống nhất nguyên tắc: ưu tiên an toàn và kiểm chứng được trước khi tối ưu độ trơn tru của câu chữ.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi muốn thử hai cải tiến cụ thể. Thứ nhất, thêm query transform nhẹ cho baseline (chuẩn hóa alias, viết tắt, mã lỗi) trước khi embed, vì nhiều câu nghiệp vụ dùng từ khóa ngắn dễ bị dense retrieval bỏ sót. Thứ hai, bổ sung retrieval guardrail theo ngưỡng điểm: nếu toàn bộ chunks dưới ngưỡng tin cậy thì pipeline tự động abstain sớm và gợi ý người dùng làm rõ câu hỏi. Hai cải tiến này trực tiếp nhắm vào kết quả eval: tăng context relevance cho các câu "khó retrieve" nhưng vẫn giữ được faithfulness và giảm hallucination.

