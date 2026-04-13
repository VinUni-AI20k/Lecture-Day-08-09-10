# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Tùng Lâm  
**Vai trò trong nhóm:** Tech Lead 
**Ngày nộp:** 13/4/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)
Trong lab này, tôi tập trung chủ yếu vào Sprint 1, nơi tôi đảm nhận việc thiết kế và triển khai bước Indexing cho pipeline RAG. Tôi đã đưa ra quyết định sử dụng phương pháp fixed-sized chunking theo từng section của text data, nhằm đảm bảo dữ liệu được chia nhỏ hợp lý và dễ quản lý. Sau đó, tôi thực hiện embedding bằng OpenAI, giúp chuyển đổi các đoạn văn bản thành vector để phục vụ cho việc tìm kiếm ngữ nghĩa. Công việc này đóng vai trò nền tảng, vì Indexing là một trong những bước quan trọng và đầu tiên, tạo tiền đề cho các bước tiếp theo của nhóm như truy vấn, retrieval và generation. Nhờ vậy, phần việc của tôi kết nối trực tiếp với các thành viên khác, đảm bảo pipeline hoạt động trơn tru và hiệu quả.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)
Sau khi hoàn thành lab, tôi hiểu rõ hơn về tầm quan trọng của tiền xử lý dữ liệu trước khi đưa vào pipeline. Việc chunking không chỉ đơn giản là chia nhỏ văn bản, mà còn cần cân nhắc đến cấu trúc nội dung để giữ được ngữ cảnh và ý nghĩa. Tôi nhận ra rằng nếu chunking không hợp lý, quá trình embedding và retrieval sẽ kém hiệu quả, dẫn đến kết quả tìm kiếm không chính xác. Ngoài ra, tôi cũng học được cách lựa chọn database phù hợp để lưu trữ vector embeddings, giúp tối ưu hóa tốc độ truy vấn và khả năng mở rộng. Nhờ lab này, tôi có cái nhìn hệ thống hơn về cách các bước nhỏ trong pipeline liên kết với nhau để tạo nên một giải pháp RAG hoàn chỉnh.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)
Trong quá trình làm lab, tôi ngạc nhiên khi việc chunking dữ liệu tưởng chừng đơn giản lại gây ra nhiều vấn đề hơn dự đoán. Ban đầu, tôi nghĩ rằng việc chunking chỉ cần chạy các thuật toán chunking thông dụng ở hiện tại là được song vẫn quan trọng quá trình data cleaning. Qua đó, tôi nhận ra rằng bước tiền xử lý và kiểm tra tính toàn vẹn dữ liệu quan trọng hơn tôi nghĩ rất nhiều.
_________________

---


Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị. Phân tích:

Baseline trả lời đúng hay sai? Điểm như thế nào?
Lỗi nằm ở đâu: indexing / retrieval / generation?
Variant có cải thiện không? Tại sao có/không?
Câu hỏi:

Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?

Phân tích:

Kết quả Baseline: Trả lời Sai. Điểm Faithfulness đạt 1/5. Mặc dù lấy được các chunk về quy trình cấp quyền, nhưng model đã bị lỗi hư cấu (hallucination) khi khẳng định Contractor có quyền Admin giống nhân viên chính thức.

Vị trí lỗi: Lỗi nằm ở Retrieval kết hợp Generation. Dense retrieval đã mang về các đoạn văn bản có độ tương đồng ngữ nghĩa cao về "Admin Access" nhưng lại thuộc về đối tượng nhân viên (DevOps/SRE). LLM sau đó không nhận diện được sự khác biệt giữa "Nhân viên" và "Contractor" trong ngữ cảnh bị loãng, dẫn đến trả lời sai hoàn toàn chính sách bảo mật.

Sự cải thiện của Variant: Variant có cải thiện rõ rệt. Bằng việc chuyển sang Hybrid Retrieval, hệ thống đã sử dụng Keyword matching để ưu tiên các chunk chứa chính xác từ khóa "Contractor". Việc tăng top_k_select lên 5 cũng cung cấp thêm bối cảnh về "Scope identification" ở Section 1 của tài liệu. Kết quả là LLM nhận diện được Contractor nằm trong phạm vi áp dụng nhưng có quy trình phê duyệt khắt khe hơn (cần cả IT Manager và CISO), giúp điểm Faithfulness tăng lên mức 4/5.

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)
Thử các phương pháp chunking và embedding khác liệu cho đưa ra kết quả khác ko
Nếu có thêm thời gian, tôi sẽ thử nghiệm nhiều phương pháp chunking khác nhau, chẳng hạn như chunking theo độ dài động hoặc theo ngữ nghĩa, để so sánh hiệu quả với cách fixed-sized chunking đã dùng. Đồng thời, tôi cũng muốn thử các mô hình embedding khác ngoài OpenAI, ví dụ như các mô hình mã nguồn mở, để đánh giá sự khác biệt về độ chính xác và tốc độ truy vấn. Việc này sẽ giúp kiểm chứng xem lựa chọn ban đầu có phải là tối ưu hay không, đồng thời mở rộng hiểu biết về cách các kỹ thuật khác nhau ảnh hưởng đến chất lượng kết quả trong pipeline RAG.
_________________

--- 

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
