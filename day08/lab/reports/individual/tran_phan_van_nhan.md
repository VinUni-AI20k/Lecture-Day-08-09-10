# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Phan Văn Nhân  
**Vai trò trong nhóm:** Retrieval Owner
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi chủ yếu đảm nhận và hoàn thiện các phần thuộc Sprint 2 của pipeline. Cụ thể, tôi implement hàm retrieve_dense() — chịu trách nhiệm truy xuất các chunk tài liệu liên quan từ vector store dựa trên độ tương đồng ngữ nghĩa — và hàm call_llm() sử dụng OpenAI API để sinh ra câu trả lời cuối cùng từ context đã được retrieve.Để retrieve_dense() hoạt động đúng, tôi cần đảm bảo đầu ra trả về đúng cấu trúc gồm document, metadata, và score, từ đó các phần khác trong pipeline (như reranking hoặc grounded prompt) có thể tiếp nhận dữ liệu mà không bị lỗi. Phần call_llm() của tôi cũng cần nhận context đã được format chuẩn để LLM có thể sinh câu trả lời chính xác. Hai hàm này là cầu nối quan trọng giữa bước indexing của thành viên khác và bước evaluation cuối pipeline.
_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn về chunking và vai trò thực sự của nó trong chất lượng retrieval. Trước đây tôi nghĩ chunking chỉ đơn thuần là chia nhỏ văn bản, nhưng thực tế kích thước chunk và cách chia ảnh hưởng trực tiếp đến việc vector search có lấy đúng thông tin hay không. Nếu chunk quá lớn, thông tin bị loãng; nếu quá nhỏ, ngữ cảnh bị mất.
Bên cạnh đó, tôi cũng hiểu rõ hơn về việc chọn top-k: không phải lúc nào top-k cao hơn cũng tốt hơn. Với top-k = 3, model nhận ít context hơn nhưng thường chính xác hơn; với top-k = 5, model có thêm ngữ cảnh nhưng đôi khi bị nhiễu bởi các chunk không thực sự liên quan. Việc lựa chọn phụ thuộc vào độ phức tạp của câu hỏi và chất lượng của từng chunk được index.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Tôi nghĩ rằng tôi khó ở việc gọi chunk với các tham số như document , metadata, và score (distence), phải mất 1 khoảng thời gian tôi mới hiểu giá trị của score.
_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

Câu hỏi:

Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?

Phân tích:

Kết quả Baseline: Trả lời Sai. Điểm Faithfulness đạt 1/5. Mặc dù lấy được các chunk về quy trình cấp quyền, nhưng model đã bị lỗi hư cấu (hallucination) khi khẳng định Contractor có quyền Admin giống nhân viên chính thức.

Vị trí lỗi: Lỗi nằm ở Retrieval kết hợp Generation. Dense retrieval đã mang về các đoạn văn bản có độ tương đồng ngữ nghĩa cao về "Admin Access" nhưng lại thuộc về đối tượng nhân viên (DevOps/SRE). LLM sau đó không nhận diện được sự khác biệt giữa "Nhân viên" và "Contractor" trong ngữ cảnh bị loãng, dẫn đến trả lời sai hoàn toàn chính sách bảo mật.

Sự cải thiện của Variant: Variant có cải thiện rõ rệt. Bằng việc chuyển sang Hybrid Retrieval, hệ thống đã sử dụng Keyword matching để ưu tiên các chunk chứa chính xác từ khóa "Contractor". Việc tăng top_k_select lên 5 cũng cung cấp thêm bối cảnh về "Scope identification" ở Section 1 của tài liệu. Kết quả là LLM nhận diện được Contractor nằm trong phạm vi áp dụng nhưng có quy trình phê duyệt khắt khe hơn (cần cả IT Manager và CISO), giúp điểm Faithfulness tăng lên mức 4/5.

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Nếu có thời gian tôi sẽ thử parent-child chunking vì trong 2 buổi học gần được được các bạn học và thầy nhắc đến rất nhiều lần và có vẻ hiệu quả của nó khá cao. Sẽ rất thú vị nếu tôi thử nhiệm nó.
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
