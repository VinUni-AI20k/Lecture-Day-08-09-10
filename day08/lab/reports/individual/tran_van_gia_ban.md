# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Văn Gia Bân
**Vai trò trong nhóm:** Tech Lead / Retrieval Owner / Eval Owner / Documentation Owner  
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Trong lab này, với vai trò Eval Owner, tôi chịu trách nhiệm chính trong việc thiết kế kiến trúc tổng thể và trực tiếp triển khai Sprint 4 (Evaluation & Scorecard). Tôi đã xây dựng hệ thống chấm điểm tự động sử dụng phương pháp LLM-as-Judge, tích hợp qua OpenAI API để đánh giá 10 câu hỏi kiểm thử dựa trên 4 metrics chuẩn: Faithfulness, Relevance, Context Recall và Completeness.

Bên cạnh đó, tôi hỗ trợ phần Retrieval Owner trong việc thiết lập logic Hybrid Search và Reranking ở Sprint 3. Công việc của tôi đóng vai trò là "điểm cuối" của pipeline, giúp kết nối các nỗ lực indexing của đồng đội với kết quả thực tế, từ đó đưa ra những con số cụ thể (Delta) để chứng minh hiệu quả của việc tuning hệ thống so với bản Baseline ban đầu.
_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.
Sau lab này, tôi thực sự hiểu sâu sắc về Evaluation Loop và tầm quan trọng của Reranking. Trước đây, tôi nghĩ chỉ cần chọn model nhúng (embedding) tốt là đủ. Tuy nhiên, khi chạy thử Scorecard, tôi nhận ra rằng dù Retriever tìm đúng chunk, nhưng nếu thứ tự các chunk bị nhiễu, LLM vẫn có khả năng bị lạc đề hoặc mất tính Faithfulness.

Việc áp dụng Reranker sau Hybrid Search giúp tôi hiểu rằng RAG không chỉ là tìm kiếm thông tin, mà là việc "lọc và xếp hạng" để cung cấp cho LLM một ngữ cảnh (context) tinh khiết nhất. Quy trình đánh giá lặp đi lặp lại giúp tôi nhận ra rằng mỗi thay đổi nhỏ trong top_k hay chiến thuật chunking đều trực tiếp ảnh hưởng đến điểm số cuối cùng, biến việc phát triển AI từ cảm tính thành định lượng rõ ràng.
_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?
Điều làm tôi ngạc nhiên nhất chính là sự chênh lệch giữa giả thuyết ban đầu và thực tế khi triển khai Hybrid Search. Tôi từng tin rằng việc kết hợp Keyword Search (BM25) và Vector Search sẽ luôn cho kết quả tốt hơn. Tuy nhiên, trong quá trình debug, tôi mất rất nhiều thời gian xử lý lỗi "nhiễu ngữ cảnh" khi cả hai phương thức đều trả về quá nhiều chunk trùng lặp hoặc không liên quan ở các câu hỏi quá ngắn.

Khó khăn lớn nhất là việc cấu hình file .env và xử lý rate limit khi chạy LLM-as-Judge cho cả 10 câu hỏi cùng lúc. Ban đầu, tôi dùng gpt-4o và bị timeout liên tục. Sau đó, tôi phải tối ưu lại bằng cách chuyển sang gpt-4o-mini và tinh chỉnh prompt để model Judge trả về JSON chuẩn xác, giúp việc parse dữ liệu vào Scorecard không bị gãy giữa chừng.
_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** 

Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?

**Phân tích:**

Kết quả Baseline: Trả lời Sai. Điểm Faithfulness đạt 1/5. Mặc dù lấy được các chunk về quy trình cấp quyền, nhưng model đã bị lỗi hư cấu (hallucination) khi khẳng định Contractor có quyền Admin giống nhân viên chính thức.

Vị trí lỗi: Lỗi nằm ở Retrieval kết hợp Generation. Dense retrieval đã mang về các đoạn văn bản có độ tương đồng ngữ nghĩa cao về "Admin Access" nhưng lại thuộc về đối tượng nhân viên (DevOps/SRE). LLM sau đó không nhận diện được sự khác biệt giữa "Nhân viên" và "Contractor" trong ngữ cảnh bị loãng, dẫn đến trả lời sai hoàn toàn chính sách bảo mật.

Sự cải thiện của Variant: Variant có cải thiện rõ rệt. Bằng việc chuyển sang Hybrid Retrieval, hệ thống đã sử dụng Keyword matching để ưu tiên các chunk chứa chính xác từ khóa "Contractor". Việc tăng top_k_select lên 5 cũng cung cấp thêm bối cảnh về "Scope identification" ở Section 1 của tài liệu. Kết quả là LLM nhận diện được Contractor nằm trong phạm vi áp dụng nhưng có quy trình phê duyệt khắt khe hơn (cần cả IT Manager và CISO), giúp điểm Faithfulness tăng lên mức 4/5.
_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."
Nếu có thêm thời gian, tôi sẽ thử nghiệm chiến thuật Recursive Character Chunking thay vì chunking cố định. Kết quả eval hiện tại cho thấy một số câu trả lời vẫn bị thiếu ý (Completeness thấp) do các đoạn văn bản quan trọng bị cắt đôi ở giữa chừng. Ngoài ra, tôi muốn triển khai thêm một tầng Query Expansion (HyDE) để mở rộng câu hỏi của người dùng trước khi search. Tôi tin rằng điều này sẽ giúp cải thiện Context Recall lên mức tuyệt đối, đặc biệt là với các câu hỏi mang tính khái quát cao.
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
