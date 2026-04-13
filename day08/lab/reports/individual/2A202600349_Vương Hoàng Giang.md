# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Vương Hoàng Giang 
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Với vai trò Tech Lead, tôi chịu trách nhiệm thiết kế kiến trúc tổng thể và đảm bảo pipeline RAG hoạt động thông suốt từ đầu đến cuối. Trong Sprint 1 và 2, tôi trực tiếp code `index.py` (xử lý chunking, nhúng vector) và `rag_answer.py` để dựng lên hệ thống Baseline cơ bản. Ở Sprint 3 và 4, tôi giao phần implement chi tiết (thuật toán Hybrid Search và hệ thống LLM-as-Judge) cho các thành viên khác. Công việc chính của tôi lúc này là code reviewer và hệ thống hóa: tôi kiểm tra chất lượng thuật toán BM25 của Retrieval Owner, giám sát logic chấm điểm của Eval Owner, và trực tiếp đánh giá chéo (cross-check) kết quả A/B Testing để đưa ra quyết định kỹ thuật cuối cùng cho nhóm.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Qua lab này, đặc biệt là khi review kết quả từ các thành viên, tôi hiểu sâu sắc về bản chất của **Hybrid Retrieval** và sự đánh đổi (trade-off) trong tìm kiếm thông tin. Trước đây, tôi nghĩ việc kết hợp Dense (tìm ngữ nghĩa) và Sparse/BM25 (tìm từ khóa) chắc chắn sẽ mang lại kết quả tốt hơn. Tuy nhiên, khi kiểm tra log hệ thống, tôi nhận ra BM25 có thể mang lại "False Positives" – tức là tìm ra đoạn văn chứa rất nhiều từ khóa giống hệt câu hỏi, nhưng ngữ cảnh hoàn toàn lạc đề. Nếu không có cơ chế lọc nhiễu tốt, các chunk rác này sẽ đẩy chunk ngữ nghĩa đúng ra khỏi Top 3, làm giảm chất lượng đầu vào của LLM.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Điều làm tôi ngạc nhiên nhất khi đánh giá kết quả A/B Testing của nhóm là khi chuyển từ Dense (Baseline) sang Hybrid (Variant), điểm số Faithfulness và Relevance lại bị giảm nhẹ (khoảng 0.1). Giả thuyết ban đầu của tôi (khi duyệt phương án dùng Hybrid) là nó sẽ cải thiện hoặc ít nhất giữ nguyên điểm. Tuy nhiên, vì tập dữ liệu của Lab khá nhỏ và sạch, Baseline đã đạt mức "kịch trần" (Ceiling Effect) với điểm Context Recall là 5.0/5. Do đó, việc team thêm BM25 không giúp tìm thêm tài liệu mới mà ngược lại, vô tình đẩy một vài chunk chứa "từ khóa nhiễu" lên top, làm LLM bị phân tâm khi sinh câu trả lời.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** q07 - "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Đây là một câu hỏi gài bẫy sử dụng tên cũ (alias) của tài liệu. Điều thú vị là Baseline (chỉ dùng Vector) đã xử lý cực kỳ xuất sắc, tìm đúng file `access-control-sop.md` vì mô hình embedding tự nhận diện được liên kết ngữ nghĩa.

Tuy nhiên, dù trả lời đúng trọng tâm, điểm Completeness của câu này chỉ đạt 2.0/5 ở cả 2 chiến lược Dense và Hybrid. Phân tích sâu hơn với Eval Owner, tôi nhận thấy lỗi không nằm ở tầng Retrieval mà do mâu thuẫn ở tầng **Generation vs Evaluation**. Grounded prompt của hệ thống được cấu hình rất nghiêm ngặt: *"Keep your answer short, clear"*, nên LLM chỉ giải thích ngắn gọn tài liệu này dùng để làm gì. Trong khi đó, `expected_answer` lại mong đợi model phải chỉ ra rõ ràng việc "tài liệu này đã được đổi tên". Hệ thống RAG thực tế hoạt động rất tốt, lỗi xuất phát từ việc tiêu chí chấm điểm khắt khe và lệch so với hành vi được định hướng ban đầu.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Dựa trên việc Hybrid Search làm giảm nhẹ độ chính xác do nhiễu từ BM25, nếu có thêm thời gian, tôi sẽ định hướng nhóm implement thêm **Cross-Encoder Reranking**. Chúng tôi sẽ mở rộng phễu tìm kiếm của Hybrid lên `top_k_search = 20` để lấy tối đa Độ phủ (Recall), sau đó dùng mô hình Rerank để đọc kỹ và lọc ra 3 chunk chính xác nhất (tăng Precision) đưa vào Prompt, khắc phục triệt để điểm yếu False Positives hiện tại.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
