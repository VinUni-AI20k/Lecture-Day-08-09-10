# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phạm Đan Kha  
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 13/04/2026  
**Độ dài:** ~600 từ

---

## 1. Tôi đã làm gì trong lab này? (148 từ)

Đảm nhận vai trò Tech Lead, trọng tâm của tôi là đảm bảo hệ thống chạy xuyên suốt (end-to-end) không xảy ra lỗi từ Sprint 1 đến Sprint 4. Cụ thể, trong Sprint 1 và 2, tôi trực tiếp quản lý việc ráp nối các module: từ khâu khởi tạo và kết nối ChromaDB (`index.py`) đến việc thiết lập API Client để gọi mô hình `llama-3.1-8b-instant` của Groq. Tôi là người implement hàm `call_llm` với cơ chế quản lý API Key qua file `.env`, đồng thời xây dựng bộ khung hàm `rag_answer` tổng để luân chuyển dữ liệu từ bước Retrieval sang Generation. Khi team chuyển sang Sprint 3, tôi làm việc cùng Retrieval Owner để tích hợp mô hình Rerank (`ms-marco-MiniLM-L-6-v2`) vào giữa pipeline mà không làm vỡ cấu trúc cũ, đồng thời quản lý Git version để đảm bảo toàn bộ code được push chuẩn xác trước deadline 18:00.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (135 từ)

Dưới góc độ hệ thống, khái niệm tôi thấm thía nhất là sự nhạy cảm của "Luồng dữ liệu" (Data Flow) trong RAG và sức mạnh của "Grounded Prompt". Trước đây tôi nghĩ mô hình LLM là phần phức tạp nhất, nhưng khi tự tay nối code, tôi nhận ra LLM chỉ là bộ phận xử lý cuối cùng; chất lượng đầu ra phụ thuộc 100% vào định dạng của ngữ cảnh (context) được bơm vào. Việc tôi phải cẩn thận code hàm `build_context_block` – chèn thêm metadata `[1], [2]`, tên file và điểm số `score` vào trước mỗi đoạn text – chính là chìa khóa kỹ thuật để "ép" mô hình LLM sinh ra trích dẫn chuẩn xác. Nếu pipeline truyền lộn xộn các biến văn bản, LLM sẽ ngay lập tức bị ảo giác.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (145 từ)
Khó khăn lớn nhất và tiêu tốn nhiều thời gian debug nhất của tôi là vấn đề xử lý ngoại lệ (Exception Handling) khi giao tiếp với API LLM. Khi nhóm chạy hàng loạt 10 câu hỏi qua hệ thống `eval.py` (sử dụng rerank), mạng đôi khi chập chờn hoặc gọi API quá giới hạn (rate limit) khiến toàn bộ script bị crash, làm mất kết quả đánh giá giữa chừng. Giả thuyết ban đầu của tôi là chỉ cần dùng lệnh `try-except` cơ bản là đủ, nhưng thực tế tôi phải cấu trúc lại hàm `call_llm` để có cơ chế "Fallback" (tự động chuyển sang nhà cung cấp dự phòng như OpenAI hoặc Gemini) nếu Groq bị lỗi. Điều này giúp tôi nhận ra một pipeline RAG thực tế đòi hỏi độ dung lỗi (fault tolerance) khắt khe hơn rất nhiều so với script chạy demo.

---

## 4. Phân tích một câu hỏi trong scorecard (162 từ)

**Câu hỏi:** q09 - "ERR-403-AUTH là lỗi gì và cách xử lý?"

**Phân tích:** Đây là một câu hỏi bẫy (không có thông tin trong tài liệu) nhằm kiểm tra khả năng chống ảo giác (Anti-hallucination) của hệ thống. Ở cả hai cấu hình Baseline và Variant, hệ thống của nhóm đều xuất sắc trả lời *"Tôi không tìm thấy thông tin..."* và đạt điểm Faithfulness 5/5. 

Từ góc nhìn của Tech Lead, tôi đánh giá thành công này hoàn toàn nhờ vào khâu Generation. Tại bước Retrieval, thuật toán vẫn trả về 3 chunks (dù độ tương đồng cosine rất thấp vì không khớp nghĩa). Tuy nhiên, Prompt Template do nhóm thiết lập có chỉ thị hệ thống cực kỳ nghiêm ngặt: *"If the context is insufficient... say you do not know"*. Kết hợp với việc cấu hình tham số `Temperature = 0`, mô hình đã bị khóa chặt tính sáng tạo, từ chối việc tự bịa ra kiến thức để trả lời. Nhờ đó, nhóm tránh được hình phạt trừ 50% số điểm.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (90 từ)

Nếu có thêm thời gian, tôi sẽ nâng cấp kiến trúc phần mềm bằng cách gói toàn bộ pipeline này thành một API service độc lập sử dụng **FastAPI**. Hiện tại, mỗi lần gọi script, hệ thống phải load lại các mô hình Cross-encoder nặng nề vào bộ nhớ rất tốn thời gian. Việc bọc nó thành một API giúp mô hình luôn ở trạng thái sẵn sàng (loaded in RAM). Kết hợp thêm bộ nhớ đệm (Redis Cache) cho các truy vấn trùng lặp, tốc độ phản hồi của hệ thống sẽ đạt chuẩn production.