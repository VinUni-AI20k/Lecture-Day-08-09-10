# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Vũ Minh Quân
**Vai trò trong nhóm:** Eval Owner
**Ngày nộp:** 13/4/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

- sprint tôi đẫ đóng góp chủ yếu là sprint 4
- công việc của tôi là Implement LLM-as-a-judge cho file eval.py.
- tôi chịu trách nhiệm về cấu hình base line, cấu hình variant, viết hàm score_faithfulness Đánh giá độ trung thực (Faithfulness) của câu trả lời,score_answer_relevance Đánh giá mức độ liên quan giữa Answer và Question,score_context_recall Đánh giá chất lượng retrieval (Context Recall), score_completeness Đánh giá độ đầy đủ của Answer, run_scorecard Đây là hàm chính (main pipeline) để chạy evaluation
---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

- Sau khi hoàn thành lab này, tôi hiểu rõ hơn về chunking và hybrid retrieval trong hệ thống RAG. Trước đây, tôi nghĩ việc chia nhỏ tài liệu chỉ đơn giản là cắt theo độ dài cố định, nhưng qua thực hành, tôi nhận ra chunking ảnh hưởng trực tiếp đến chất lượng truy xuất: nếu chunk quá lớn sẽ chứa nhiều thông tin dư thừa, còn quá nhỏ thì mất ngữ cảnh quan trọng. Ngoài ra, tôi cũng hiểu rõ hơn về hybrid retrieval, tức là kết hợp giữa dense retrieval và sparse retrieval để tận dụng ưu điểm của cả hai. Dense giúp hiểu ngữ nghĩa, trong khi sparse (keyword-based) đảm bảo không bỏ sót các từ khóa quan trọng. Nhờ đó, hệ thống có thể cải thiện đáng kể context recall và độ chính xác của câu trả lời.
_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

- Điều tôi ngạc nhiên nhất là khi implement phần `eval.py`, tôi nhận ra việc đánh giá bằng LLM-as-a-judge không chỉ là gọi API mà còn phải thiết kế prompt và logic chấm điểm sao cho phản ánh đúng các metric. Ban đầu tôi nghĩ chỉ cần đánh giá answer với expected answer là đủ, nhưng thực tế cần tách rõ `faithfulness`, `relevance`, `context recall` và `completeness` để hiểu được nguồn lỗi.
- Lỗi mất nhiều thời gian debug nhất là dữ liệu test có trường `category` hoặc `expected_sources` không đồng nhất, và một số cases thiếu trường `caratoty` (category bị sai tên). Điều đó khiến pipeline bị lỗi khi load input và làm chậm việc kiểm tra kết quả.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** Approval Matrix để cấp quyền hệ thống là tài liệu nào?

**Phân tích:**

Câu hỏi này thú vị vì nó kiểm tra khả năng xử lý alias và truy vấn ngữ nghĩa hơn là chỉ tìm chính xác từ khóa. Với baseline dense, hệ thống có thể trả lời không trúng hoặc bỏ qua vì query dùng tên cũ "Approval Matrix" trong khi nguồn chứa tài liệu hiện hành là "Access Control SOP". Lỗi ở đây chủ yếu là retrieval: tokenizer và chỉ số vector dense có thể không liên kết tốt tên cũ với tiêu đề tài liệu mới, dẫn đến retrieved chunks thiếu evidence đúng.

Variant hybrid + rerank có cơ hội cải thiện vì sparse retrieval sẽ bắt được các từ khóa giống nhau như "Approval Matrix" và "System Access", trong khi dense vẫn giữ lại khả năng hiểu ngữ cảnh. Nếu rerank hoạt động, nó sẽ ưu tiên document có liên quan hơn và trả về nguồn đúng hơn. Như vậy, variant có thể cải thiện rõ so với baseline, đặc biệt trong các câu hỏi alias/tên cũ như case này.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

- Tôi sẽ thử thêm một biến variant chỉ có `hybrid retrieval` mà chưa bật rerank, vì kết quả eval cho thấy nhiều câu alias vẫn cần kết hợp keyword và semantic search trước khi sắp xếp.
- Tôi cũng sẽ thử tối ưu prompt chấm `score_faithfulness` và `score_completeness` để giảm sai số do LLM judge, vì hiện tại điểm số bị ảnh hưởng mạnh bởi cách diễn giải lý do đánh giá.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
