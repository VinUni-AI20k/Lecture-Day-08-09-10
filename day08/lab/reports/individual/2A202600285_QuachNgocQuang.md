# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Quách Ngọc Quang  
**Vai trò trong nhóm:** Tech Lead / Retrieval & LLM Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong dự án Lab Day 08, tôi đảm nhiệm vai trò **Tech Lead** và trực tiếp chịu trách nhiệm thiết kế hạ tầng truy xuất và tích hợp mô hình ngôn ngữ cho hệ thống RAG IT Helpdesk. Đóng góp chính của tôi tập trung vào giai đoạn tối ưu hóa khả năng truy xuất và đảm bảo tính ổn định của pipeline:

- **Sparse Retrieval (BM25)**: Tôi đã trực tiếp triển khai thuật toán `BM25Okapi` trong module `rag_answer.py`. Đây là thành phần then chốt giúp hệ thống truy xuất chính xác các thuật ngữ kỹ thuật, mã lỗi (như ERR-403) và các tài liệu có tên cũ (alias) mà tìm kiếm ngữ nghĩa (Dense Search) thường bỏ sót.
- **Kiến trúc LLM Đa nền tảng (Gateway)**: Trước thách thức về giới hạn hạn mức (Quota 429) của mô hình Gemini, tôi đã thiết kế và triển khai logic chuyển đổi mô hình linh hoạt. Tôi đã tích hợp **DeepSeek** và **OpenAI** vào hệ thống, cho phép chuyển đổi nhà cung cấp chỉ qua cấu hình môi trường (.env), đảm bảo pipeline luôn trong trạng thái vận hành.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Trải qua quá trình thực thi, tôi đã đạt được sự am hiểu sâu sắc về **sự cộng hưởng giữa Keyword và Semantic Search**. Thay vì coi Dense Search là giải pháp thay thế, tôi nhận ra BM25 là lớp bảo vệ quan trọng cho độ chính xác (Precision) khi xử lý dữ liệu đặc thù ngành IT. Keyword search là phương pháp không thể thiếu khi người dùng tìm kiếm theo mã lỗi hoặc tên tài liệu viết tắt.

Bên cạnh đó, tôi thực sự hiểu rõ giá trị của việc **Thiết kế hệ thống độc lập với nhà cung cấp (Provider Agnosticism)**. Việc bóc tách logic xử lý prompt ra khỏi SDK của từng hãng (như tách biệt giữa `google.generativeai` và `openai`) giúp Tech Lead có khả năng điều phối tài nguyên linh hoạt, tránh bị "vendor lock-in" và đảm bảo hệ thống bền bỉ hơn khi một trong các gateway gặp sự cố kỹ thuật hoặc giới hạn chi phí.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn kỹ thuật lớn nhất là việc xử lý **Tokenization đồng bộ cho BM25**. Khi lấy document trực tiếp từ ChromaDB, tôi phải thiết lập quy trình tiền xử lý văn bản sao cho khớp với cách mà mô hình embedding đã xử lý ở Sprint 1, đồng thời vẫn phải đảm bảo các từ khóa kỹ thuật không bị bẻ gãy (split) sai lệch, gây mất điểm `Context Recall`.

Về phương diện vận hành, tôi khá ngạc nhiên khi thấy ranh giới mong manh giữa thành công và thất bại của một hệ thống RAG đôi khi nằm ở **Hạ tầng API**. Việc Gemini 1.5/2.5 liên tục trả về mã lỗi 429 dù lượng request chưa lớn đã buộc tôi phải thay đổi toàn bộ kế hoạch LLM trong thời gian ngắn. Tuy nhiên, khó khăn này lại giúp tôi hoàn thiện module `call_llm` với khả năng fallback thông minh, nâng cao đáng kể tính Resilience cho dự án.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — *"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"*

**Phân tích:** 
Đây là một trong những trường hợp thử thách nhất trong bộ scorecard vì "Approval Matrix" là **tên cũ (alias)** của tài liệu, trong khi tiêu đề văn bản hiện tại đã đổi thành "Access Control SOP". 

- **Kết quả Baseline (Dense Search):** Thường cho kết quả `Context Recall` thấp hoặc sai lệch vì embedding của cụm từ "Approval Matrix" không có sự tương đồng ngữ nghĩa cao với "Access Control SOP". Do đó, retriever chỉ lấy được các tài liệu chung chung, dẫn đến LLM trả lời "Không tìm thấy thông tin".
- **Kết quả Variant (BM25):** Giải pháp Sparse Search do tôi triển khai đã phát huy tác dụng tối đa ở đây. BM25 đã bắt trúng dòng ghi chú kỹ thuật: *"Tài liệu này trước đây có tên 'Approval Matrix...'"* có trong văn bản.

Kết hợp với **DeepSeek**, hệ thống đã trích xuất thành công và trả lời chính xác tên tài liệu là "Access Control SOP [1]". Qua câu hỏi này, tôi khẳng định rằng việc triển khai BM25 không chỉ là một variant cộng thêm, mà là yêu cầu bắt buộc để xử lý các bài toán tìm kiếm theo định danh hoặc thuật ngữ cũ trong doanh nghiệp — nơi mà dữ liệu thường không đồng nhất về cách gọi tên.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ tập trung vào việc **tối ưu hóa tiền xử lý dữ liệu (Pre-processing)** để loại bỏ các ký tự nhiễu, giúp thuật toán BM25 hoạt động chính xác hơn nữa. Bên cạnh đó, tôi muốn thử nghiệm thêm các cấu hình **Top-K Retrieval** linh hoạt cho từng loại câu hỏi khác nhau để đảm bảo ngữ cảnh (context) gửi cho LLM luôn là những thông tin cô đọng và chất lượng nhất.

---