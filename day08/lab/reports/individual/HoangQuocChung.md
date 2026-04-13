# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Hoàng Quốc Chung - 2A202600070 
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này tôi làm vai trò Documentation Owner, tập trung chủ yếu ở Sprint 3 và Sprint 4. Công việc chính của tôi là đọc lại kết quả chạy pipeline, tổng hợp các quyết định kỹ thuật của nhóm và chuyển chúng thành tài liệu có thể dùng để nộp và để cả nhóm cùng bám theo. Cụ thể, tôi phụ trách hoàn thiện `docs/tuning-log.md` bằng cách đối chiếu scorecard baseline và variant, ghi lại đúng biến A/B mà nhóm đã đổi, phân tích câu nào cải thiện, câu nào tệ hơn, rồi chốt cấu hình cuối cùng nên dùng cho grading run. Ngoài ra tôi còn tổng hợp nội dung cho `group_report.md`, liên kết phần retrieval, generation và evaluation thành một câu chuyện kỹ thuật thống nhất. Công việc của tôi phụ thuộc trực tiếp vào đầu ra từ Tech Lead, Retrieval Owner và Eval Owner, vì tôi phải dùng đúng số liệu, đúng cấu hình và đúng failure mode mà nhóm đã quan sát được.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này tôi hiểu rõ hơn hai khái niệm là evaluation loop và A/B tuning trong RAG. Trước đó tôi nghĩ tuning chủ yếu là “thử một cách retrieval mới xem có tốt hơn không”, nhưng khi làm thật tôi thấy nếu không có scorecard thì rất dễ kết luận theo cảm giác. Trong bài này, baseline dense có `Context Recall = 5.00/5`, nghĩa là hệ thống đã lấy đúng nguồn khá tốt, nhưng `Completeness` vẫn thấp hơn các metric còn lại. Điều đó giúp tôi hiểu rằng một pipeline RAG không phải cứ retrieve đúng là đủ; chất lượng cuối cùng còn phụ thuộc vào cách model tổng hợp câu trả lời từ context. Tôi cũng hiểu rõ hơn quy tắc A/B: chỉ được đổi một biến để khi so sánh baseline và variant, nhóm biết chính xác sự khác biệt đến từ retrieval mode, chứ không bị lẫn với top-k, prompt hay rerank.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi ngạc nhiên nhất là hybrid retrieval không giúp hệ thống tốt hơn dù về lý thuyết nó có vẻ hợp lý với bộ tài liệu này. Ban đầu tôi và nhóm nghĩ rằng vì corpus có nhiều từ khóa đặc thù như `P1`, `Level 3`, `Approval Matrix`, `ERR-403-AUTH`, nên hybrid sẽ tăng chất lượng rõ rệt. Nhưng khi nhìn vào scorecard mới, baseline dense lại tốt hơn: Faithfulness `4.50` so với `4.30`, Answer Relevance `4.80` so với `4.40`, và Completeness `3.90` so với `3.70`. Khó khăn lớn nhất của tôi không phải là viết tài liệu, mà là viết sao cho tài liệu phản ánh đúng kết quả thật, không “hợp thức hóa” giả thuyết ban đầu. Tôi phải đọc kỹ từng câu yếu như `q06`, `q07`, `q09`, `q10` để xác định nhóm đang gặp lỗi retrieval hay generation, rồi ghi lại kết luận một cách trung thực trong tuning-log và group report.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** `q07` - "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Ở câu `q07`, baseline không hẳn retrieve sai, vì `Context Recall = 5/5` cho thấy hệ thống đã lấy được đúng nguồn cần thiết. Tuy nhiên answer của baseline chỉ trả lời rằng tài liệu là `"Approval Matrix for System Access"`, trong khi expected answer yêu cầu nêu rõ đây là tên cũ và tên hiện tại của tài liệu là `Access Control SOP`. Vì vậy baseline chỉ đạt Faithfulness `2/5`, Relevance `4/5`, Completeness `2/5`. Theo tôi, lỗi chính nằm ở generation hơn là indexing hay retrieval. Hệ thống đã có đủ context, nhưng model chưa tổng hợp được quan hệ “tên cũ - tên mới” và chỉ lặp lại một phần thông tin dễ thấy nhất trong chunk. Variant hybrid không cải thiện được lỗi này, thậm chí Relevance còn giảm từ `4/5` xuống `3/5`, trong khi Faithfulness và Completeness vẫn giữ ở mức thấp. Điều đó củng cố kết luận trong tuning-log rằng việc đổi retrieval mode từ dense sang hybrid không xử lý được failure mode của nhóm. Nếu muốn sửa câu này, hướng hợp lý hơn là rerank hoặc chỉnh prompt để ép model trả lời đầy đủ hơn khi câu hỏi có yếu tố mapping giữa tên cũ và tên mới của tài liệu.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ đề xuất nhóm thử `dense + rerank` thay vì tiếp tục mở rộng retrieval bằng hybrid, vì scorecard cho thấy baseline đã có recall rất cao nhưng vẫn yếu ở các câu cần chọn đúng chi tiết để tổng hợp. Ngoài ra tôi muốn chỉnh grounded prompt theo hướng buộc model nêu đủ các chi tiết phụ quan trọng như tên mới của tài liệu, điều kiện đi kèm hoặc quy trình chuẩn, vì các câu `q07`, `q09`, `q10` đều cho thấy vấn đề nằm ở độ đầy đủ của câu trả lời hơn là ở việc thiếu nguồn.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
