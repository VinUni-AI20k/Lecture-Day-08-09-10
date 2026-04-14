# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Huỳnh Văn Nghĩa  
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)
Trong lab này tôi đảm nhận vai trò Documentation Owner, tập trung ở Sprint 3 và Sprint 4. Công việc chính của tôi là hoàn thiện tài liệu kiến trúc và tuning log để phản ánh đúng pipeline đang chạy, không để tài liệu chỉ là template. Cụ thể, tôi chốt thông số thực tế trong architecture như chunk size 300, overlap 60, baseline dense top-k 10-3, model gpt-4o-mini, và tách diagram thành từng luồng để demo rõ ràng. Ở tuning log, tôi tổng hợp scorecard từ các lần chạy v1 và v2, điền delta theo từng metric, chỉ ra câu nào cải thiện và câu nào giảm. Tôi phối hợp với Retrieval Owner và Eval Owner để tài liệu khớp với kết quả eval, từ đó hỗ trợ Tech Lead chọn cấu hình nộp cuối.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)
Điều tôi hiểu rõ nhất sau lab là retrieval tốt chưa chắc answer tốt. Trước đây tôi nghĩ context recall cao là đủ, nhưng dữ liệu nhóm cho thấy recall có thể giữ 5.00 mà faithfulness hoặc completeness vẫn thấp. Điều này nghĩa là lỗi có thể nằm ở bước chọn context cuối và cách model hiểu prompt. Khái niệm thứ hai tôi nắm chắc hơn là grounded prompt theo rule. Nếu prompt chỉ nói chung chung kiểu "thiếu dữ liệu thì abstain", model dễ từ chối cả những câu vẫn trả lời được bằng policy chung. Khi thêm rule quyết định cụ thể hơn, chất lượng tăng rõ ở các câu khó như VIP refund. Với tôi, evaluation loop là công cụ để tìm điểm nghẽn thực tế, không chỉ để có bảng điểm đẹp.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)
Điều khiến tôi ngạc nhiên nhất là variant đầu tiên dùng hybrid cộng rerank không tự động tốt hơn baseline. Ban đầu tôi nghĩ thêm BM25 và cross-encoder chắc chắn tăng chất lượng. Thực tế, ở lần chạy chưa tuned, faithfulness còn giảm nhẹ và completeness không tăng. Khó nhất khi debug là giải thích vì sao context recall vẫn cao nhưng câu trả lời vẫn chưa đúng trọng tâm. Lúc đầu nhóm nghi do indexing, nhưng xem scorecard kỹ thì nhiều câu đã retrieve đúng nguồn. Điểm nghẽn nằm nhiều hơn ở rerank kéo lệch chunk và prompt khiến model trả lời quá thận trọng. Từ đó tôi rút ra là phải bám dữ liệu từng câu, không thể kết luận chỉ bằng trực giác.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)
**Câu hỏi:** Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?

**Phân tích:**

Đây là câu tôi thấy rõ nhất giá trị của vòng lặp tuning. Ở baseline v1, câu này có điểm rất thấp: Faithfulness 1, Relevance 1, Completeness 1, dù Context Recall vẫn đạt 5. Điều đó cho thấy retriever đã lấy đúng nguồn nhưng generator chưa dùng tốt ngữ cảnh, chủ yếu trả lời "không đủ dữ liệu" thay vì kết luận rằng tài liệu không có quy trình VIP riêng và cần áp dụng quy trình chuẩn. Ở variant 1 chưa tuned, kết quả gần như không đổi vì rerank đôi lúc đẩy context theo hướng quá an toàn. Sau khi chuyển sang variant 2 với ba thay đổi: blended rerank score, ưu tiên dominant source và prompt rule rõ hơn, điểm tăng lên Faithfulness 4, Relevance 3, Completeness 4. Theo tôi, lỗi chính nằm ở generation cộng post-retrieval control, không nằm ở indexing. Câu này cho thấy cùng một bộ tài liệu, chất lượng trả lời phụ thuộc rất mạnh vào cách chọn và diễn giải context.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)
Nếu có thêm thời gian, tôi sẽ ưu tiên hai hướng. Thứ nhất, thêm alias map cho các cặp tên cũ-mới như Approval Matrix for System Access và Access Control SOP vì q07 cho thấy completeness còn thấp do thiếu mapping này. Thứ hai, tôi sẽ thử cơ chế rerank đa dạng nguồn theo quota mềm, ví dụ ưu tiên nguồn dominant nhưng vẫn giữ một slot cho nguồn bổ trợ, để tránh trường hợp dồn toàn bộ top-k vào một nguồn và bỏ sót bối cảnh cần thiết như ở q06.

---
