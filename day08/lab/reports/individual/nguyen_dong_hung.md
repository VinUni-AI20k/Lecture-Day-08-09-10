# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyen-Dong-Hung  
**MSSV:** 2A202600392  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi phụ trách phần retrieval của pipeline và hỗ trợ nối retrieval với bước trả lời trong `rag_answer.py`. Ở Sprint 2, tôi tập trung vào baseline retrieval: nhận query, lấy top-k chunk từ index, chọn các chunk phù hợp nhất, rồi build context block để đưa vào grounded prompt. Mục tiêu của tôi không chỉ là retrieve được dữ liệu, mà là retrieve đúng dữ liệu để model trả lời ngắn, rõ và có citation. Sang Sprint 3, tôi tập trung vào các trường hợp dense retrieval dễ bỏ sót, nhất là query có alias, tên cũ của tài liệu hoặc keyword đặc thù như “P1”, “Level 3” hay mã lỗi. Phần tôi làm kết nối trực tiếp với `index.py` vì retrieval phụ thuộc mạnh vào chunking và metadata, đồng thời cũng ảnh hưởng trực tiếp tới chất lượng grounded answer ở bước generation.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn hai khái niệm là retrieval quality và grounded prompt. Trước đây tôi nghĩ nếu model đủ mạnh thì phần answer sẽ tự tốt, nhưng khi làm lab tôi thấy chất lượng answer phụ thuộc rất lớn vào việc retrieve đúng context. Nếu retrieve sai tài liệu hoặc lấy nhầm đoạn quá rộng, model vẫn có thể trả lời trôi chảy nhưng không còn bám chứng cứ. Tôi cũng hiểu rõ hơn sự khác nhau giữa dense retrieval và hybrid retrieval. Dense retrieval mạnh ở câu hỏi diễn đạt tự nhiên, nhưng có thể hụt khi query dùng alias, tên cũ hoặc exact keyword. Hybrid retrieval phù hợp hơn trong corpus nội bộ vì tài liệu vừa có câu văn tự nhiên, vừa có nhiều thuật ngữ cố định như “Approval Matrix”, “P1” hoặc mã lỗi. Điều đó giúp tôi nhìn retrieval như một bài toán chọn evidence, không chỉ là search đơn thuần.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi ngạc nhiên nhất là retrieval sai không phải lúc nào cũng nhìn ra ngay ở answer. Có những trường hợp model trả lời nghe hợp lý, câu chữ mượt, nhưng khi đối chiếu lại thì source không đúng hoặc evidence chưa đủ mạnh. Khó khăn lớn nhất là phân biệt lỗi nằm ở retrieval hay generation. Ban đầu tôi có xu hướng nghĩ prompt chưa tốt hoặc model chưa hiểu câu hỏi, nhưng khi nhìn lại pipeline thì nhiều lỗi thực ra bắt đầu từ việc top-k không chứa đúng chunk cần thiết. Giả thuyết ban đầu của tôi là dense retrieval có thể đủ tốt cho bộ tài liệu nhỏ. Thực tế cho thấy với các câu hỏi có alias hoặc tên tài liệu cũ, dense retrieval vẫn có thể bỏ sót ngữ cảnh quan trọng. Điều này làm tôi hiểu rằng tuning retrieval thường đáng làm trước khi chỉnh prompt hay đổi model.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** Approval Matrix để cấp quyền hệ thống là tài liệu nào?

**Phân tích:**

Tôi chọn câu hỏi này vì nó thể hiện khá rõ điểm yếu của retrieval. Trong `test_questions.json`, đây là câu `q07` và được ghi chú là query alias hoặc tên cũ. Baseline dense retrieval có khả năng trả lời chưa tốt cho câu này dù thông tin thực sự có trong bộ tài liệu. Lý do là query dùng tên “Approval Matrix”, trong khi tài liệu hiện tại lại có tên “Access Control SOP”. Nếu retrieval dựa chủ yếu vào embedding similarity, hệ thống có thể không ưu tiên đúng chunk nói về việc đổi tên tài liệu hoặc không lấy được đoạn có alias liên quan. Vì vậy lỗi chính nằm ở retrieval hơn là generation. Prompt grounded có thể đã chặt, nhưng nếu context đầu vào không chứa đúng bằng chứng thì model cũng khó trả lời chính xác.

Với một variant như hybrid retrieval hoặc query transformation, câu này có cơ hội cải thiện rõ hơn. Hybrid giúp kết hợp semantic similarity với keyword overlap, còn query transformation có thể mở rộng query từ “Approval Matrix” sang “Access Control SOP”. Nếu top-k đã chứa đúng chunk cần thiết, bước generation chỉ cần tóm tắt ngắn gọn và gắn đúng source. Theo tôi, đây là ví dụ tốt cho thấy tune retrieval có tác động thực tế hơn đổi model ở giai đoạn đầu.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử query transformation cho các câu có alias hoặc tên cũ, vì `q07` cho thấy dense retrieval dễ hụt ở kiểu truy vấn này. Tôi cũng muốn thêm một bước rerank nhẹ sau khi retrieve top-10 để giảm noise trước khi build context block. Mục tiêu là tăng context recall ổn định ở các câu medium và hard, thay vì chỉ nhìn vào chất lượng answer cuối cùng.

---

*Lưu file này với tên: `reports/individual/nguyen_dong_hung.md`*
