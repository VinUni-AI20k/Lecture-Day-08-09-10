# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Tú Nam 
**Vai trò trong nhóm:**  Retrieval Owner(sprint 1+3)
**Ngày nộp:** 13/4/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Em chủ yếu làm sprint3.
Em làm phần retrieve_sparse + retrieve_hybrid + rerank + transform_query + thử các variant.  
Đối với sprint2 (baseline), phần của em là tuning, nghĩa là để xem các thay đổi của mình có cải thiện gì so với baseline không?

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.
Heading-based + Paragraph fallback: Ưu tiên tách theo heading tự nhiên (=== Section ... === hoặc === Phần ... ===) để giữ cấu trúc tài liệu, sau đó mới split theo paragraph và kích thước nếu section quá dài. Giúp chunk có ý nghĩa rõ ràng và dễ citation hơn.
Dense retrive:Hiểu ngữ nghĩa (semantic), không cần trùng từ, hoạt động tốt với paraphase, câu hỏi tự nhiên
Sparse Retrieval: Match chính xác keyword, tốt với mã lỗi và các từ technical.
Hybrid retrieval: dùng 2 cách retrieve trên nên cân bằng giữa recall và precision
_________________

---
## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Trong quá trình xây dựng hệ thống RAG, điều gây bất ngờ nhất là việc các metric đánh giá không tăng đồng thời như kỳ vọng. Ban đầu, em giả định rằng khi cải thiện retrieval (ví dụ chuyển sang hybrid), cả Answer Relevance và Faithfulness đều sẽ tăng. Tuy nhiên, thực tế cho thấy dù relevance được cải thiện, faithfulness lại có thể giảm do mô hình sinh bị “nhiễu” khi nhận quá nhiều thông tin từ nhiều nguồn.
Khó khăn lớn nhất là debug các lỗi liên quan đến môi trường và pipeline, đặc biệt là việc sai môi trường Python (venv) khiến thư viện không được nhận diện, và việc kiểm soát output của LLM để tránh hallucination. Tôi cũng nhận ra rằng vấn đề không chỉ nằm ở retrieval mà còn ở cách chọn lọc và giới hạn context đưa vào model.
_________________


---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** q09 

**Phân tích:**
Mô hình trả lời "Tôi không biết" là chính xác.Điểm: 1	1	None	1
Lỗi nằm ở: Câu hỏi không có trong database.
Variant không có cải thiện gì. Do không có trong database 
_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."
Em muốn thử đổi Rerank do CrossEncoder sẽ chọn chunk "relevant nhất" khiến cho Completeness thấp(3.9).
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
