# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Hữu Nam  
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi đã làm Architecture docs và Tuning log trong lab này, tôi chủ yếu tham gia vào sprint 4 khi pipeline đã hoàn thiện và hoạt động, mọi người đã chạy test. Nhiệm vụ chính của tôi là theo dõi các bước của các thành viên trong nhóm và ghi chép lại, nhằm miêu tả rõ pipeline RAG của nhóm từ chunking, indexing đến retrieval và generation. Công việc của tôi kết nối với các thành viên khác bằng cách biến các thử nghiệm rời rạc thành tài liệu có cấu trúc, giúp cả nhóm debug dễ hơn và đánh giá chính xác hiệu quả của từng thay đổi.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi đã hiểu rõ thêm về Dense retrieval và Hybrid retrieval. Trước kia, tôi biết về vector search và nghĩ đơn giản rằng retrieval chỉ cần tìm kiếm các văn bản gần với query nhất về mặt semantic là đã đủ tốt. Tôi cũng cho rằng BM25 và các phương pháp tương tự là thừa thãi và outdated, tuy nhiên, sau buổi học và bài lab này, tôi nhận ra rằng việc kết hợp keyword-based matching (BM25) và embedding sẽ giúp cải thiện khả năng tìm đúng context, đặc biệt cho các câu hỏi có từ khoá cụ thể. 
_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất là debug khi câu trả lời sai nhưng không rõ lỗi nằm ở retrieval hay generation. Ban đầu nhóm tôi giả thuyết là do chunking chưa tốt, có thể indexing hoặc metadata gặp vấn đề, nhưng sau khi kiểm tra thì vấn đề chính lại là nằm ở generation, retrieval đã trả về chunk relevant nhưng model trả lời chưa tốt. Điều này làm tôi nhận ra rằng trong RAG pipeline, mặc dù lỗi thường nằm ở upstream (retrieval) chứ không phải LLM, nhưng không có nghĩa là có thể bỏ qua khâu generation, và đồng thời khi viết prompt phải chú ý tránh tình trạng lost in the middle. 

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** "SLA xử lý ticket P1 đã thay đổi như thế nào so với phiên bản trước?"

**Phân tích:**

Câu hỏi q1 trong file test, tưởng có vẻ đơn giản nhưng sau khi test, cả nhóm đều đau đầu vì đây là test case duy nhất retrieval không hoạt động được như kỳ vọng, cả baseline và variant đều perform rất tệ. Tuy nhiên, sau một hồi debug, nhóm đã nhận ra có vấn đề với phần indexing khiếm cho retrieval gộp phần update note ở cuối và vì thế đã không retrieve chunk quan trọng này. Chính vì vậy, sau khi chunk lại document support/sla-p1-2026.pdf, cả baseline lẫn retrieval đều hoạt động ổn và đạt score 5/5.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi muốn thử áp dụng thêm các hàm heuristic hậu retrieval đơn giản như merge thêm chunk liền trước và liền sau từ cùng 1 nguồn vào các chunk đã có, điều này có thể làm nhiễu LLM nhưng chắc chắn sẽ bảo tồn được context tốt hơn và sẽ không phải là vấn đề quá lớn với các LLM đủ xịn.

_________________

---

