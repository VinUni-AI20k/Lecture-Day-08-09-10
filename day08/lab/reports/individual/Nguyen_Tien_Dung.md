# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Tiến Dũng
**Vai trò trong nhóm:** Retrieval Owner 
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Trong dự án RAG Pipeline lần này, với vai trò là Retrieval Owner, tôi chịu trách nhiệm chính trong việc tối ưu hóa quy trình từ lúc lấy dữ liệu từ Vector Database cho đến khi đưa vào Prompt. Tôi tập trung chủ yếu vào Sprint 2 và 3.

> Cụ thể, tôi đã thiết lập hàm build_grounded_prompt để đảm bảo LLM luôn trả lời dựa trên ngữ cảnh (context) và thực hiện nghiêm ngặt quy tắc "không bịa đặt" (abstain logic). Tôi cũng tham gia vào việc phát triển hàm call_llm để hỗ trợ đa mô hình, cho phép hệ thống linh hoạt chuyển đổi giữa OpenAI và Gemini thông qua biến cấu hình LLM_Provider. Công việc của tôi đóng vai trò là "cầu nối" quan trọng: tiếp nhận các chunk dữ liệu từ index.py và kết quả truy xuất từ các hàm retrieve_dense/retrieve_hybrid trong rag_answer.py, sau đó tinh chỉnh chúng thành một cấu trúc prompt mạch lạc để LLM có thể trích xuất thông tin chính xác nhất kèm theo citation [1], [2].



_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Sau lab này, tôi đã hiểu sâu sắc hơn về khái niệm Grounded Prompting (Prompt dựa trên bằng chứng). Trước đây, tôi nghĩ đơn giản là chỉ cần copy context vào prompt là xong. Tuy nhiên, qua thực tế cài đặt, tôi nhận ra rằng việc thiết lập các chỉ dẫn (system instructions) để LLM biết cách xử lý khi thông tin không có trong context là cực kỳ quan trọng để chống Hallucination (ảo giác).

Bên cạnh đó, tôi cũng hiểu rõ hơn về tầm quan trọng của cấu trúc dữ liệu trả về từ khâu Retrieval. Việc giữ lại Metadata (như source, section) không chỉ giúp ích cho việc trích dẫn nguồn (citation) mà còn giúp LLM phân biệt được các phiên bản tài liệu khác nhau (ví dụ: chính sách v3 và v4). Điều này giúp câu trả lời của hệ thống có độ tin cậy cao hơn hẳn so với việc chỉ sử dụng kiến thức nội tại của mô hình.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều khiến tôi ngạc nhiên nhất là sự nhạy cảm của LLM đối với cách trình bày context. Trong quá trình debug, có những lúc mô hình trả lời "Không tìm thấy thông tin" mặc dù dữ liệu đã được truy xuất thành công trong log. Tôi phát hiện ra nguyên nhân là do định dạng của chunk khi nối vào prompt bị rối, khiến LLM khó phân tách giữa các đoạn văn bản khác nhau.

Khó khăn lớn nhất mà tôi gặp phải là việc xử lý các câu hỏi "bẫy" hoặc câu hỏi không có trong dữ liệu (như câu gq07 về mức phạt SLA). Ban đầu, prompt của tôi quá "nhiệt tình" khiến mô hình cố gắng suy luận từ kiến thức có sẵn thay vì từ chối trả lời. Tôi đã phải mất khá nhiều thời gian để tinh chỉnh câu lệnh: "Chỉ sử dụng thông tin được cung cấp. Nếu không thấy, hãy nói rõ là không có trong tài liệu" để đạt được độ chính xác mong muốn.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** `q04` — "Sản phẩm kỹ thuật số có được hoàn tiền không?"

**Phân tích:**
Trong đợt đánh giá này, câu hỏi **q04** là một ví dụ điển hình cho thấy sự khác biệt giữa hai chiến lược truy xuất. 
- **Kết quả Baseline (Dense Search):** Hệ thống thất bại hoàn toàn (Score: Relevance 2, Recall 1). Baseline trả về câu trả lời "Không đủ dữ liệu" và danh sách nguồn trống (`[]`). 
- **Lỗi nằm ở đâu:** Lỗi nằm trọng tâm ở khâu **Retrieval**. Mặc dù thông tin nằm rõ ràng trong tài liệu `policy/refund-v4.pdf` (Điều 3: Ngoại lệ không được hoàn tiền), nhưng phương pháp Dense Search (dựa trên vector embedding) đã không thể tìm thấy chunk này. Có thể do câu hỏi chứa các thuật ngữ cụ thể như "kỹ thuật số" - vốn có trọng số keyword rất cao nhưng vector similarity lại không đủ mạnh để vượt qua các đoạn văn bản khác về chính sách chung.
- **Variant (Hybrid Search):** Kết quả cải thiện tuyệt đối (Score 5/5). Hệ thống trả lời chính xác: "Sản phẩm kỹ thuật số không được hoàn tiền, trừ khi có lỗi do nhà sản xuất..." kèm trích dẫn nguồn [1] chính xác từ file policy.
- **Tại sao cải thiện:** Việc kết hợp thêm **Keyword Search (BM25)** trong bản Hybrid đã phát huy tác dụng tối đa. Cụm từ "Sản phẩm kỹ thuật số" là một từ khóa đặc trưng (Exact match). BM25 đã giúp hệ thống "bắt" được chính xác đoạn văn bản về ngoại lệ mà Dense Search bỏ lỡ. Điều này chứng minh rằng với các tài liệu quy định có nhiều thuật ngữ chuyên môn hoặc danh mục cụ thể, Hybrid Search là lựa chọn sống còn để đảm bảo Context Recall.
_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> Nếu có thêm thời gian, tôi sẽ kiểm tra thêm bước Reranking sử dụng Cross-Encoder. Qua quan sát logs/sprint3/retrieval_debug.json, tôi thấy có nhiều chunk từ các tài liệu không liên quan (như leave-policy) vẫn lọt vào Top 10 với score khá cao do có một vài từ ngữ chung chung. Một mô hình Rerank sẽ giúp lọc bỏ các "nhiễu" này trước khi đưa vào prompt, từ đó giảm thiểu tối đa rủi ro LLM đọc nhầm ngữ cảnh và tăng tính chính xác cho các câu trả lời phức tạp hơn.

_________________

---

