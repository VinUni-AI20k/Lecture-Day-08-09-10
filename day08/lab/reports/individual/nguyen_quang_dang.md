# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Quang Đăng  
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài:** ~650 từ

---

## 1. Tôi đã làm gì trong lab này?

Trong lab này, tôi phụ trách vai trò Documentation Owner, nên phần đóng góp chính của tôi là biến kết quả kỹ thuật của cả nhóm thành tài liệu có thể kiểm chứng và nộp bài. Cụ thể, tôi cập nhật `docs/architecture.md` theo đúng pipeline thực tế: indexing, retrieval, generation, các tham số top-k, mô hình embedding, và cấu hình LLM. Tôi cũng bổ sung bảng phân vai để mỗi thành viên có trách nhiệm rõ ràng theo sprint. Song song đó, tôi tổng hợp kết quả baseline và variant vào `docs/tuning-log.md`, bao gồm score, delta, nhận xét, kết luận, và Error Tree để tránh việc tuning theo cảm tính. Ngoài ra, tôi tạo và hoàn thiện `reports/group_report.md` để chốt quyết định kỹ thuật cấp nhóm, đảm bảo nội dung khớp với scorecard và log grading. Công việc của tôi kết nối trực tiếp với Retrieval Owner và Eval Owner: các bạn cung cấp output và score, tôi chuẩn hóa thành bằng chứng tài liệu để nộp.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Sau lab, tôi hiểu rõ hơn rằng trong RAG, “lấy đúng tài liệu” chưa đủ để “trả lời tốt”. Trước đây tôi nghĩ context recall cao là đủ, nhưng khi xem scorecard thì thấy dù recall = 5.00/5, relevance và completeness vẫn có thể thấp nếu thứ tự chunk không hợp lý. Điều này giải thích vì sao cùng một bộ evidence, nhưng câu trả lời có thể khác nhau khá nhiều trước/sau rerank.

Tôi cũng hiểu rõ giá trị của grounded prompt và abstain rule. Ở các câu không có thông tin trong corpus, nếu prompt không ép rõ “do not make up information”, mô hình rất dễ trả lời theo kiến thức nền, gây hallucination. Trong bài này, việc đặt prompt theo evidence-only + citation + abstain đã giúp hệ thống an toàn hơn. Với vai trò Documentation Owner, tôi thấy tài liệu không chỉ để “đẹp”, mà là công cụ giúp nhóm đưa quyết định có bằng chứng và tránh mâu thuẫn khi nộp bài.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Khó khăn lớn nhất của tôi không nằm ở viết markdown, mà nằm ở việc giữ tài liệu đồng bộ với code và kết quả mới nhất. Trong quá trình làm, `rag_answer.py` được đồng đội cập nhật liên tục, scorecard cũng thay đổi theo từng lần chạy. Nếu cập nhật tài liệu chậm 1 bước, architecture, tuning log, group report và grading log sẽ mâu thuẫn ngay. Tôi đã gặp trường hợp architecture ghi variant là hybrid + rerank, trong khi tuning log chốt dense + rerank; nếu để nguyên sẽ rất dễ bị trừ điểm vì claim không nhất quán.

Điều ngạc nhiên nữa là một thay đổi nhỏ (bật `use_rerank=True`) lại cải thiện được 3/4 metric, dù retrieval_mode vẫn là dense. Ban đầu tôi kỳ vọng phải đổi sang hybrid mới có cải thiện rõ, nhưng kết quả lại cho thấy quality generation rất nhạy với ranking order. Bài học là không nên đoán theo cảm giác; cần score và delta để kết luận.

---

## 4. Phân tích một câu hỏi trong grading

**Câu hỏi chọn:** gq07 — “Công ty sẽ phạt bao nhiêu nếu team IT vi phạm cam kết SLA P1?”

Với câu này, output trong grading log là “Tôi không biết.”. Đây là kết quả đúng hướng theo tiêu chí anti-hallucination, vì corpus không có thông tin mức phạt tiền tệ cho vi phạm SLA P1. Nếu hệ thống “đoán” ra con số, đó sẽ là hallucination nghiêm trọng và có thể bị penalty.

Phân tích theo pipeline: indexing và retrieval vẫn hoạt động ổn (chunks_retrieved = 3, sources có `support/sla-p1-2026.pdf`), nghĩa là hệ thống tìm được tài liệu liên quan chủ đề SLA. Vấn đề không nằm ở việc “không tìm thấy tài liệu”, mà nằm ở “tài liệu không chứa dữ liệu cần hỏi”. Ở bước generation, grounded prompt đã vô hiệu tác động của kiến thức nền bằng cách ép chỉ trả lời từ context và abstain khi thiếu dữ liệu. Vì vậy hệ thống trả lời ngắn gọn và an toàn.

Variant rerank không làm thay đổi bản chất câu này vì đây là bài toán missing evidence, không phải ranking sai evidence. Điều cần cải thiện tiếp theo là cách abstain “có lý do” (ví dụ: “Không tìm thấy quy định mức phạt trong tài liệu SLA hiện có”), để vừa an toàn vừa giải thích tốt hơn cho người dùng.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Nếu có thêm 1 giờ, tôi sẽ ưu tiên 2 hướng. Thứ nhất, thêm chế độ abstain có giải thích lý do (thiếu evidence ở section nào) để tăng completeness cho các câu insufficient context mà vẫn giữ faithfulness. Thứ hai, chạy A/B nhỏ với `query_transform="expansion"` cho các câu multi-hop dài (như gq06) để xem có tăng relevance không. Tôi chọn 2 hướng này vì scorecard hiện tại cho thấy relevance/completeness vẫn là điểm nghẽn lớn hơn so với context recall.
