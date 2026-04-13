# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyen Ngoc Tan  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài:** 500-800 từ

---

## 1. Tôi đã làm gì trong lab này? (100–150 từ)

Trong buổi lab này, tôi tham gia chủ yếu ở Sprint 4 với vai trò phụ trách đánh giá hiệu quả của hệ thống RAG. Công việc chính của tôi là thực hiện kiểm thử và so sánh chất lượng đầu ra giữa hai pipeline sử dụng cùng phương pháp dense retrieval. Điểm khác biệt giữa hai pipeline là một bên có bổ sung bước reranking, trong khi bên còn lại thì không.

Để tiến hành đánh giá, tôi chuẩn bị một tập gồm 10 câu hỏi truy vấn và sử dụng chúng để kiểm tra khả năng trả lời của từng pipeline. Sau khi hoàn tất quá trình chạy thử, tôi tiến hành tổng hợp kết quả, phân tích sự khác biệt giữa hai phiên bản và gửi lại cho Documentation Owner để phục vụ cho việc hoàn thiện báo cáo chung của nhóm.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100–150 từ)

Sau khi hoàn thành lab, tôi nhận thấy rõ hơn hiệu quả của việc kết hợp nhiều phương pháp truy xuất trong hệ thống RAG. Cụ thể, việc sử dụng đồng thời BM25 và semantic search giúp cải thiện đáng kể khả năng tìm kiếm thông tin. Trong khi BM25 phù hợp với việc khớp từ khóa chính xác, thì semantic search lại giúp hiểu được ý nghĩa tổng thể của câu hỏi.

Ngoài ra, tôi cũng hiểu rõ hơn về vai trò của grounded prompt trong việc kiểm soát chất lượng đầu ra. Khi mô hình chỉ được phép sử dụng thông tin từ dữ liệu đã cung cấp, nguy cơ tạo ra nội dung sai lệch (hallucination) sẽ giảm đi đáng kể. Đây là yếu tố quan trọng trong các ứng dụng yêu cầu độ tin cậy cao.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100–150 từ)

Một trong những trở ngại lớn nhất mà tôi gặp phải là giới hạn về số lượng token khi sử dụng API miễn phí. Ban đầu, nhóm dự định áp dụng LLM Judge để tự động hóa quá trình chấm điểm câu trả lời. Tuy nhiên, do hạn mức sử dụng bị giới hạn, hệ thống nhanh chóng hết quota khi thực hiện nhiều lượt test.

Do đó, tôi phải chuyển sang phương pháp đánh giá thủ công. Mặc dù cách này mất nhiều thời gian hơn, nhưng nó cũng giúp tôi có cái nhìn chi tiết hơn về chất lượng câu trả lời và hiểu rõ hơn cách hệ thống phản hồi trong từng tình huống cụ thể.

---

## 4. Phân tích một câu hỏi trong scorecard (150–200 từ)

**Câu hỏi:** ERR-403-AUTH là lỗi gì và cách xử lý?

Câu hỏi này được sử dụng để kiểm tra khả năng tuân thủ dữ liệu (groundedness) của hệ thống RAG. Mục tiêu là xem liệu mô hình có chỉ dựa vào thông tin trong tài liệu hay không. Trong trường hợp này, bộ dữ liệu không chứa bất kỳ thông tin nào liên quan đến lỗi “ERR-403-AUTH”.

Kết quả cho thấy cả hai pipeline đều xử lý đúng theo kỳ vọng. Thay vì cố gắng suy đoán hoặc tạo ra câu trả lời, hệ thống đã phản hồi rằng không có thông tin phù hợp trong tài liệu. Điều này chứng tỏ cơ chế grounded prompt hoạt động hiệu quả, giúp mô hình tránh đưa ra thông tin không chính xác.

Đây là một kết quả tích cực, vì trong bối cảnh RAG, việc không trả lời khi thiếu dữ liệu đáng tin cậy sẽ tốt hơn nhiều so với việc cung cấp thông tin sai. Điều này thể hiện hệ thống đã được thiết kế theo hướng ưu tiên độ chính xác và độ tin cậy.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm thời gian, tôi muốn mở rộng phạm vi thử nghiệm bằng cách áp dụng nhiều cấu hình khác nhau, ví dụ như so sánh hybrid search với các baseline hiện tại, hoặc kết hợp hybrid search với reranking. Điều này sẽ giúp đánh giá toàn diện hơn và tìm ra phương án tối ưu cho hệ thống.