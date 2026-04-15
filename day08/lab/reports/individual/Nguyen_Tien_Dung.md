# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Tiến Dũng
**Vai trò trong nhóm:** Retrieval Owner (Call LLM + grounded prompt, tinh chỉnh prompt)
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Trong dự án RAG Pipeline lần này, tôi làm công việc tinh chỉnh phần grounded prompt+Gọi LLM API ở vai trò là Retrieval Owner. Tôi tập trung chủ yếu vào Sprint 2 và 3.

> Cụ thể, tôi làm chủ yếu 2 hàm: build_grounded_prompt và call_llm. Hàm call_llm là hàm chọn lựa gọi API của LLM, ở hàm này em cùng với nhóm dùng 2 API, OpenAPI và Gemini. Em đã thiết kế và cùng với nhóm dùng môi trường .env để tự do chọn lựa nên gọi OpenAPI hoặc Gemini bằng LLM_PROVIDER.

> Ở hàm build_grounded_prompt, nó đóng vai trò tương tự như rules của system prompt. Hàm này trả 1 prompt quy định cách mà LLM bắt buộc phải trả lời khi gặp những yêu cầu của người dùng. Em và nhóm em cùng nhau tìm hiểu các hàm dùng build_grounded_prompt như rag_answer và _merge_candidates, cùng với yêu cầu trả lời khi abstain hay include thêm phần citation để làm tăng tính xác thực.



_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Sau buổi lab này, tôi đã hiểu rõ hơn Grounded Prompting (Prompt dựa trên bằng chứng) trong việc kiểm soát prompt. Trước khi học ở đây, tôi từng nghĩ đơn giản là prompt chỉ cần có ngữ cảnh thì LLM sẽ hiểu được. Tuy nhiên, qua buổi học, tôi nhận ra rằng tôi cũng cần có những instructions để LLM biết cách xử lý khi thông tin có/không có trong context là cực kỳ quan trọng để generate câu trả lời hợp lý và ngăn Hallucination (ảo giác).

Bên cạnh đó, tôi cũng hiểu rõ hơn về phần format văn bản như Markdown hay JSON format để LLM phân biệt được kiến thức nào nên dùng vào khi nào và tăng độ chính xác, độ ưu tiên kèm theo citation, 1 yếu tố góp phần tăng tính xác thực của data.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều khiến tôi gặp khó khăn là sự nhạy cảm của LLM đối với cách trình bày context. Trong quá trình debug, có những lúc mô hình trả lời ngoài dự đoán của grading_questions mặc dù dữ liệu đã được truy xuất thành công trong log và có system prompt tốt. Tôi phát hiện ra nguyên nhân là do định dạng của chunk khi nối vào prompt bị rối, khiến LLM khó phân tách giữa các đoạn văn bản khác nhau.

Khó khăn lớn nhất mà tôi gặp phải là việc xử lý các câu hỏi "bẫy" hoặc câu hỏi không có trong dữ liệu (như câu gq07 về mức phạt SLA). Ban đầu, prompt của tôi quá "nhiệt tình" khiến mô hình cố gắng suy luận từ kiến thức có sẵn thay vì từ chối trả lời. Tôi đã phải mất khá nhiều thời gian để tinh chỉnh câu lệnh: "Chỉ sử dụng thông tin được cung cấp. Nếu không thấy, hãy nói rõ là không có trong tài liệu" để đạt được độ chính xác mong muốn.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** `q09` — "ERR-403-AUTH là lỗi gì và cách xử lý?"

**Phân tích:**
Câu hỏi **q09** là một bài kiểm tra then chốt cho khả năng **Abstain Logic** và **chống Hallucination** của pipeline, đặc biệt là phần Prompting mà tôi phụ trách.
**Bot trả lời:** Không đủ dữ liệu hiện có
- **Kết quả Baseline (Dense Search):** Giả sử Baseline không có tối ưu về Grounded Prompting, rất có thể nó sẽ:
    - **Hallucinate:** Cố gắng suy luận từ kiến thức chung về lỗi HTTP 403, mặc dù không có trong tài liệu. (Score: Penalty -50%).
    - Hoặc trả lời mơ hồ, không rõ ràng về việc không có thông tin. (Score: Partial - 5/10 theo Grading Rule của `gq07`).
- **Lỗi nằm ở đâu (nếu có):** Nếu Baseline thất bại, lỗi nằm ở khâu **Generation/Prompting**. Cụ thể là prompt chưa đủ mạnh để buộc LLM phải thừa nhận thiếu thông tin và từ chối trả lời (abstain), thay vì cố gắng "sáng tạo" thông tin. Retrieval có thể không tìm thấy gì (đúng), nhưng LLM vẫn "bịa".
- **Variant (Hybrid Search):** Pipeline của chúng ta (kể cả với Hybrid Search) đã trả lời chính xác: "Không tìm thấy thông tin về ERR-403-AUTH trong tài liệu hiện có. Đây có thể là lỗi liên quan đến xác thực (authentication), hãy liên hệ IT Helpdesk." với `sources: []`.
- **Tại sao cải thiện/hoạt động đúng:** Việc trả lời đúng cho `q09` cho thấy rằng các tinh chỉnh của tôi trong hàm `build_grounded_prompt` đã hoạt động hiệu quả. Tôi đã lồng ghép các chỉ dẫn nghiêm ngặt như *"Chỉ sử dụng thông tin được cung cấp. Nếu không thấy, hãy nói rõ là không có trong tài liệu"* để buộc LLM phải tuân thủ. Mặc dù không có chunk nào được retrieve cho `ERR-403-AUTH`, LLM đã không bịa đặt mà thay vào đó đưa ra một câu trả lời mang tính giúp đỡ nhưng vẫn trung thực về giới hạn thông tin của mình. Đây là một thành công lớn trong việc đảm bảo Faithfulness (trung thực) của hệ thống.
_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> Nếu có thêm thời gian, tôi sẽ kiểm tra thêm bước Reranking sử dụng Cross-Encoder. Qua quan sát logs/sprint3/retrieval_debug.json, tôi thấy có nhiều chunk từ các tài liệu không liên quan (như leave-policy) vẫn lọt vào Top 10 với score khá cao do có một vài từ ngữ chung chung. Một mô hình Rerank sẽ giúp lọc bỏ các "nhiễu" này trước khi đưa vào prompt, từ đó giảm thiểu tối đa rủi ro LLM đọc nhầm ngữ cảnh và tăng tính chính xác cho các câu trả lời phức tạp hơn.

_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
