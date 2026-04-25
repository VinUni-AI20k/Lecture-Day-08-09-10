# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Thị Thùy Trang  
**Vai trò trong nhóm:** Tech Lead   
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Tôi phụ trách Sprint 1 và Sprint 2, tập trung xây dựng pipeline RAG nền tảng và đảm bảo hệ thống hoạt động.
> Ở Sprint 1, tôi kết hợp cùng với vai trò Retrieval Owner để hoàn thành pipeline indexing gồm preprocess, chunking, embedding và lưu trữ vào chromadb. Tôi debug hàm preprocess để lấy được đầy đủ nội dung các file data, đặc biệt là file it_helpdesk_faq.txt. Ngoài ra, tôi kiểm soát chất lượng chunking để tránh cắt sai ngữ cảnh.
> Ở Sprint 2, tôi phát triển luồng trả lời hoàn chỉnh: retrieve_dense() để truy vấn dữ liệu, call_llm() để sinh câu trả lời, và xây dựng rag_answer() để kết hợp context với prompt.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chunking không chỉ đơn giản là chia nhỏ văn bản, mà là chia sao cho mỗi đoạn vẫn giữ được ý nghĩa hoàn chỉnh. Nếu chunk quá nhỏ hoặc bị cắt giữa câu / điều khoản, retrieval sẽ trả về thông tin thiếu ngữ cảnh, dẫn đến câu trả lời sai. Nếu chunk quá lớn thì embedding sẽ kém chính xác. Vì vậy, cần chọn kích thước chunk và overlap hợp lý để cần bằng giữa độ đầy đủ ngữ cảnh và khả năng tìm kiếm.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Vấn đề không đúng kỳ vọng là hệ thống không retrieve được nội dung trong file it_helpdesk_faq.txt, dù dữ liệu đã được index; nội dung chunk bị lặp. Ngoài ra, trong quá trình gọi LLM, tôi cũng gặp lỗi 503 khi sử dụng Gemini API, gây gián đoạn trong việc kiểm thử.
> Lỗi mất nhiều thời gian debug nhất là lỗi lặp lại chunk, cũng như là không retrieve được nội dung. Ban đầu, tôi nghĩ rằng vấn đề là do sai sót trong chunking, nhưng khi kiểm tra lại, nguyên nhân thực tế lại là do không lấy được thông tin trong file cộng với chạy file index.py nhiều lần dẫn đến việc sai sót trong chromadb, dẫn đến lặp lại.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** q07 – “Approval Matrix để cấp quyền hệ thống là tài liệu nào?”

**Phân tích:**
> Ở baseline, retrieval trả về đúng các chunk từ access-control-sop.md, trong đó chunk 1 chứa thông tin quan trọng: “Tài liệu này trước đây có tên ‘Approval Matrix for System Access’”. Đây là thông tin alias giúp trả lời câu hỏi. Tuy nhiên, các chunk còn lại (Section 1, Section 3) chỉ mô tả phạm vi và quy trình, không trực tiếp liên quan, gây nhiễu.
> Như vậy, retrieval đúng nhưng chưa tối ưu (có noise). Đây là dạng câu hỏi khó vì sử dụng tên cũ (alias) thay vì tên hiện tại của tài liệu. Dense retrieval vẫn tìm được do có từ “Approval Matrix” trong chunk, nhưng không đảm bảo luôn ổn định với các alias khác.
> Với variant (hybrid retrieval), khả năng cải thiện nằm ở việc ưu tiên match keyword “Approval Matrix” mạnh hơn, giúp chunk chứa alias được rank cao nhất và giảm nhiễu. Trường hợp này cho thấy hybrid retrieval phù hợp với query có alias hoặc tên cũ.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> Nếu có thêm thời gian, tôi sẽ làm phần hybrid retrieval (kết hợp dense + BM25) vì kết quả eval cho thấy dense retrieval bỏ sót các thông tin chứa keyword cụ thể như “tech” hoặc mã lỗi, dù chúng có trong tài liệu. Điều này dẫn đến việc hệ thống không lấy được đúng context và trả lời thiếu chính xác.  

_________________

