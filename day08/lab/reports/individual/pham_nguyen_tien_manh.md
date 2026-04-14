# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phạm Nguyễn Tiến Mạnh  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 13/4/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

- Tôi chủ yếu tham gia ở Sprint 4, tập trung vào giai đoạn evaluation của hệ thống RAG. Nhiệm vụ chính của tôi là kiểm thử và so sánh chất lượng câu trả lời giữa hai pipeline có cùng phương pháp retrieval dense, trong đó một pipeline có sử dụng thêm bước rerank, còn pipeline còn lại thì không.
- Cụ thể, tôi sử dụng một tập gồm 10 câu hỏi truy vấn để kiểm tra khả năng trả lời của hệ thống. Sau khi chạy test, tôi tiến hành tổng hợp kết quả, so sánh sự khác biệt giữa baselien với variant và đánh báo cáo kết quả cho Documentation Owner để tổng hợp báo cáo chung của nhóm.

---

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

- Tôi hiểu rõ hơn về tầm quan trọng của các phương pháp hybrid retrieval trong hệ thống RAG. Việc kết hợp giữa hai phương pháp là BM25 (dựa trên keyword) và semantic search (dựa trên embedding) giúp hệ thống không chỉ tìm được các tài liệu chứa từ khóa chính xác mà còn hiểu được ngữ cảnh của câu hỏi. Điều này giúp cải thiện đáng kể chất lượng của các đoạn context được retrieve.

- Tôi cũng nhận ra vai trò quan trọng của grounded prompt. Khi sử dụng grounded prompt, mô hình sẽ bị giới hạn trong phạm vi dữ liệu nội bộ đã được cung cấp, từ đó giảm thiểu tình trạng hallucination. Điều này đặc biệt quan trọng trong các hệ thống cần độ chính xác cao như RAG.

---

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Khó khăn lớn nhất mà tôi gặp phải trong quá trình testing là giới hạn về token khi sử dụng API key miễn phí. Ban đầu, nhóm tôi sử dụng LLM Judge để tự động đánh giá chất lượng câu trả lời của hệ thống. Tuy nhiên, do sử dụng API key free nên khi chạy test với nhiều câu hỏi, hệ thống nhanh chóng bị hết quota và không thể tiếp tục nên tôi phải chuyển sang đánh giá thủ công từng câu trả lời.

---

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** ERR-403-AUTH là lỗi gì và cách xử lý?

**Phân tích:**

> Đây là một câu hỏi được thiết kế nhằm kiểm tra khả năng grounded của hệ thống RAG, tức là xem mô hình có chỉ trả lời dựa trên dữ liệu nội bộ hay không. Trong trường hợp này, tài liệu của hệ thống không chứa thông tin liên quan đến lỗi “ERR-403-AUTH”. Kết quả testing cho thấy cả baseline (không rerank) và variant (có rerank) đều xử lý tốt tình huống này. Thay vì cố gắng tạo ra câu trả lời, hệ thống đã phản hồi rằng “Không tìm thấy thông tin về ERR-403-AUTH trong tài liệu hiện có”. Điều này chứng tỏ grounded prompt đã được thiết kế hiệu quả, giúp mô hình tránh việc hallucinate thông tin không có trong dữ liệu.

---

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thời gian tôi sẽ test thêm nhiều variant khác nhau như hybrid search với baseline hay hybrid search với hybrid search kết hợp rerank.

---
