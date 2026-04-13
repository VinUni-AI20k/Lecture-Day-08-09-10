# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Anh Tài  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
>
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

> Tôi chịu trách nhiệm thiết kế hệ thống "stress-test" cho RAG. Tôi đã xây dựng bộ benchmark gồm 50 test-case bao phủ toàn diện 5 tài liệu nghiệp vụ, phân rã thành 8 kịch bản khó như: Edge Case, Insufficient Context, Adversarial, và Multi-hop. Đồng thời, đánh giá trên bộ test-case với model local qwen2.5:7b.

---

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

> Khái niệm tôi thấu hiểu sâu sắc nhất là Evaluation Loop (Vòng lặp đánh giá) kết hợp với Grounded Prompt.  
> Trước đây, tôi đánh giá LLM khá cảm tính qua vài câu hỏi ngẫu nhiên. Sau khi tự tay phân loại 50 test-case, tôi nhận ra việc đánh giá RAG không chỉ đo lường việc "mô hình lấy ra đúng chữ hay không" (Retrieval Accuracy), mà quan trọng không kém là khả năng "từ chối an toàn" (Abstain) khi thiếu dữ kiện.

---

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

> Điều khiến tôi ngạc nhiên và mất nhiều thời gian debug nhất là sự "cố chấp" của LLM khi đối mặt với các câu hỏi bẫy (Adversarial Case) hoặc ngoài phạm vi (Out-of-scope).  
> Ban đầu, tôi giả định chỉ cần nhét context vào và bảo "nếu không có thì nói không biết", mô hình sẽ ngoan ngoãn tuân theo. Thực tế, khi hỏi các câu sai bối cảnh, Qwen2.5:7b đôi khi vẫn cố gắng dùng kiến thức pre-trained để nội suy ra câu trả lời thay vì Abstain. Mất khá nhiều lượt tuning System Prompt tôi mới khắc phục được.

---

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích
>
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

> Câu hỏi: gq07 (Nhóm: Insufficient Context - Hỏi về mức phạt vi phạm cam kết)
> Phân tích:
>
> - Faithfulness (Độ trung thực) đạt điểm tối thiểu 1/5. Đây là một lỗi "Hard Fail" về tính chính xác của dữ liệu.
> - Lỗi nằm ở khâu Generation (Sinh văn bản).
> - Retrieval: Thực hiện tốt nhiệm vụ khi không tìm thấy đoạn văn bản (context) nào liên quan đến "mức phạt" trong 5 tài liệu nghiệp vụ (Context Recall: None).
> - Mặc dù Variant (Hybrid + Rerank) rất hiệu quả trong việc tìm kiếm thông tin ẩn, nhưng ở kịch bản này, nó cho thấy điểm yếu về khả năng kiểm soát đầu ra. Kết quả Scorecard cho thấy cần thắt chặt hơn nữa System Prompt để ép mô hình nhỏ từ chối trả lời thay vì cố gắng sáng tạo nội dung khi context trống.

---

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

> Tôi sẽ thử nghiệm triển khai "LLM-as-a-Judge" (dùng một model lớn hơn như Gemini hoặc GPT-4) để tự động chấm điểm 2 tiêu chí Groundedness (Có dựa vào context không) và Answer Relevance (Trả lời đúng trọng tâm không) cho file CSV kết quả

---

---

_Lưu file này với tên: `reports/individual/[ten_ban].md`_
_Ví dụ: `reports/individual/nguyen_van_a.md`_
