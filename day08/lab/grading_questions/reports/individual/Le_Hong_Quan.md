# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Hồng Quân  
**Vai trò trong nhóm:** Tech Lead / Leader  
**Ngày nộp:** 2026-04-13

---

## 1. Tôi đã làm gì trong lab này? 

Trong lab này tôi giữ vai trò leader, nên phần việc chính của tôi là chia task theo pipeline, kết nối kết quả của từng thành viên, và chốt hướng tune để cả nhóm không làm chồng chéo. Tôi chia team theo ba phần chính: indexing + retrieval, generation + prompt, và evaluation + documentation. Ngoài việc điều phối, tôi là người theo dõi các lần chạy baseline và variant, đọc scorecard, xác định câu nào fail nặng nhất, rồi chuyển các kết quả đó thành quyết định kỹ thuật tiếp theo. Tôi cũng chịu trách nhiệm tổng hợp `architecture.md`, `tuning-log.md`, scorecard cho bộ grading questions, và viết phần báo cáo nhóm.

---

## 2. Điều tôi hiểu rõ hơn sau lab này 

Sau lab này tôi hiểu rõ hơn rằng một pipeline RAG tốt không chỉ phụ thuộc vào model, mà phụ thuộc rất nhiều vào cách chia trách nhiệm giữa indexing, retrieval và generation. Trước đây tôi nghĩ nếu retrieve đúng tài liệu thì answer sẽ gần như tự đúng, nhưng thực tế không phải vậy. Một câu có thể retrieve đúng source nhưng vẫn trả lời sai hoặc thiếu ý nếu prompt không đủ chặt, hoặc nếu chunk đang gộp nhiều điều khoản gần nhau. Tôi cũng hiểu rõ hơn vai trò của evaluation loop. Điểm số như `Faithfulness`, `Recall`, `Completeness` không chỉ để “chấm”, mà còn giúp khoanh vùng lỗi. Ví dụ, recall thấp thường gợi ý thiếu evidence ở retrieval, còn completeness thấp dù recall cao lại gợi ý vấn đề nằm ở generation hoặc cách model tổng hợp thông tin.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi bất ngờ nhất là variant đầu tiên không tốt hơn baseline dù nhóm đã thêm nhiều kỹ thuật hơn như hybrid và rerank. Trực giác ban đầu của tôi là “thêm nhiều tầng hơn” sẽ làm hệ thống mạnh hơn, nhưng kết quả cho thấy điều ngược lại: phức tạp hơn chưa chắc tốt hơn. Khó khăn lớn nhất là xác định lỗi nằm ở đâu khi một câu trả lời sai. Nếu chỉ nhìn output cuối thì rất dễ kết luận sai. Có những câu thực ra retrieval đã đúng source, nhưng model lại suy luận quá tay. Ngược lại, có câu prompt khá tốt nhưng retrieval lại bỏ sót một nguồn quan trọng. Trường hợp mất thời gian debug nhất là các câu cross-document, vì chúng yêu cầu nhiều evidence đồng thời. Từ đó tôi rút ra rằng leader phải giữ nhịp đánh giá theo từng tầng, không được sửa lan man.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** `gq06` — “Lúc 2 giờ sáng xảy ra sự cố P1, on-call engineer cần cấp quyền tạm thời cho một engineer xử lý incident. Quy trình cụ thể như thế nào và quyền này tồn tại bao lâu?”

**Phân tích:**

Đây là câu tôi thấy tiêu biểu nhất vì nó kiểm tra đúng điểm yếu của RAG: câu hỏi nhiều vế và cần tổng hợp từ nhiều tài liệu. Ở baseline, câu này có `Context Recall = 2/5` và `Completeness = 2/5`. Nguyên nhân chính không nằm ở index, mà ở retrieval: hệ thống chỉ lấy được nguồn về SLA P1 nhưng thiếu `it/access-control-sop.md`, nên answer chỉ nói chung chung về việc xử lý incident mà không trả ra quy trình cấp quyền tạm thời, thời hạn `24 giờ`, yêu cầu Tech Lead phê duyệt, hay việc phải ghi log. Khi đọc scorecard, tôi thấy đây là failure mode rất rõ: thiếu evidence trước khi generate. Sau đó nhóm chuyển sang variant có `auto` router, query expansion, source filter và tăng `top_k_select`. Kết quả là variant retrieve đủ `2/2` expected sources, và điểm của câu này tăng mạnh lên gần như đầy đủ. Điều này củng cố cho tôi rằng với câu multi-hop, leader phải ưu tiên sửa retrieval flow trước khi đổ lỗi cho model.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ yêu cầu nhóm tách riêng từng thay đổi trong variant để chạy A/B sạch hơn, thay vì gộp router, prompt mới và filter vào cùng một lần. Tôi cũng muốn thử một variant chỉ thay đổi prompt để xem phần cải thiện hiện tại đến từ retrieval hay generation nhiều hơn. Ngoài ra, tôi sẽ bổ sung một bảng mapping failure mode → fix cụ thể để lần tune sau ra quyết định nhanh hơn.

---

