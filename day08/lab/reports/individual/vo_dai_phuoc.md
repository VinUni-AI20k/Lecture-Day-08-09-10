# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Võ Đại Phước
**Vai trò trong nhóm:** Tech Lead
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

- Chịu trách nhiệm hướng dẫn, support các bạn implement hoàn thiện các function từ index.py (sprint 1), các hàm retrieval theo kiểu dense, sparse, etc, ...
- Các code sau khi được implement sẽ được review và merge vào main thông qua PR
- Chịu trách nhiệm chạy kết quả cuối cùng trong khác thí nghiệm
_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)
- Cách để có thể đánh giá theo 4 tiêu chí Faithfulness, Relevance, Recall, Completeness để đánh giá 1 RAG pipeline hoàn hảo,
giúp biết được phần index, retrive hay generation đang bị fail
- Việc tuning các phương pháp và tham số tương đối tốn thời gian để investigate lỗi nằm ở đâu, và chọn con số cho phù hơp
_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

- Phân vân khi chọn phương pháp, tham số select vì khi tuning, kết quả không thay đổi nhiều
- Mất thời gian debug khi openai api key bị đè và key trong dict để lấy context trong eval.py nhưng 
trong lúc review PR lại không nhận ra, lúc test full pipeline tốn nhiều thời gian check lại code
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

> Chạy file log, tổng hợp lại hết các cả các case cần phải chạy benchmark cho tất cả phương pháp, tất cả câu hỏi để tránh bị miss khi so sánh A/B
> Thêm 1 vài data nhiễu có cụm từ gần giống nghĩa để testing độ nhạy của embedding khi truy vấn
> Tinh chỉnh prompt cho LLM-as-judge, prompt còn đơn giản, LLM có thể chưa đánh giá chính xác
> Audit lại hết các query, context, llm answer và đánh giá của llm-as-judge để hiểu vì sao có các số metric đầu ra
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
