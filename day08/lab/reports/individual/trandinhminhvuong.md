# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Đình Minh Vương  
**Vai trò trong nhóm:** Eval & Docs Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài:** 680 từ

---

## 1. Tôi đã làm gì trong lab này?

Trong lab này, tôi chịu trách nhiệm Sprint 4 (Evaluation) và documentation. Công việc chính:

Đầu tiên, tôi implement evaluation pipeline trong `eval.py` với 4 scoring functions sử dụng LLM-as-Judge (GPT-4o-mini). Mỗi metric có logic riêng: Context Recall tính recall từ expected sources, Faithfulness dùng LLM kiểm tra grounding, Relevance đánh giá answer có trả lời đúng câu hỏi, Completeness so sánh với expected answer.

Thứ hai, implement `run_scorecard()` để chạy tự động 10 test questions, chấm điểm và generate markdown report. Function tích hợp với `rag_answer()` của team, nhận results và chấm theo 4 metrics.

Thứ ba, tôi implement `compare_ab()` để so sánh baseline vs variant, tính delta và export CSV. Sau khi chạy lại đầy đủ bằng `OPENAI_API_KEY` của nhóm, kết quả mới là: Baseline tốt hơn ở Faithfulness (-0.20 cho variant), còn Variant tốt hơn ở Relevance (+0.20) và Completeness (+0.20), Context Recall hòa (5.00/5).

Cuối cùng, tôi cập nhật documentation cho `docs/architecture.md`, `docs/tuning-log.md` và `reports/group_report.md` để phản ánh đúng cấu hình chạy thật bằng OpenAI embeddings (`text-embedding-3-small`), không còn dùng local embedding.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Sau lab này, tôi hiểu sâu hơn về evaluation trong RAG systems. RAG có nhiều failure modes - retrieval lấy sai docs, generation hallucinate, hoặc answer đúng nhưng thiếu chi tiết. Vì vậy cần nhiều metrics để đo các aspects khác nhau, không chỉ "đúng/sai" đơn giản.

Tôi cũng hiểu về LLM-as-Judge - technique mạnh để automate evaluation. Học được cách design prompt cho judge: rõ ràng về scale, yêu cầu structured JSON output, provide examples. GPT-4o-mini chấm khá consistent nhưng đôi khi strict quá (q03 faithfulness = 2 có thể false negative).

Quan trọng nhất: "more complex ≠ better". Evaluation cho thấy Hybrid tạo trade-off chứ không thắng tuyệt đối: Faithfulness giảm nhẹ nhưng Relevance/Completeness tăng nhẹ. Phải test và đo tác động thực tế, không assume advanced technique luôn tốt hơn. A/B testing đúng cách giúp identify root cause: BM25 match keyword có lúc kéo thêm nhiễu.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Điều ngạc nhiên nhất là kết quả A/B comparison thay đổi theo điều kiện chạy thật với API key chung của nhóm. Tôi kỳ vọng Hybrid sẽ thắng rõ ràng, nhưng kết quả thực tế là chỉ cải thiện một phần: Relevance/Completeness tăng nhẹ, đổi lại Faithfulness giảm. Phải deep dive per-question analysis để hiểu vì sao.

Khó khăn lớn nhất là debug các câu alias và insufficient-context như q07, q09. Có câu variant trả lời nghe hợp lý hơn với người đọc nhưng lại bị judge phạt faithfulness vì câu chữ không bám sát chunk trích xuất. Điều này cho thấy cần cân bằng giữa "đúng ý" và "grounded".

Khó khăn khác là thiết kế Context Recall scoring. Ban đầu exact matching fail vì format khác nhau ("policy/refund-v4.pdf" vs "policy_refund_v4.txt"). Phải chuyển sang partial matching bằng filename lowercase mới work.

Cũng gặp LLM-as-Judge timeout khi chấm 10 câu liên tục. Thêm error handling và retry logic để ổn định.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** q06 - "Escalation trong sự cố P1 diễn ra như thế nào?"

**Phân tích:**

Câu này cho thấy rõ tại sao Hybrid kém hơn Dense. Expected: "Ticket P1 auto-escalate lên Senior Engineer nếu không phản hồi trong 10 phút".

**Baseline:** Faithfulness 4/5, Completeness 5/5. Trả lời đầy đủ flow escalation và bám khá sát context.

**Variant:** Faithfulness 5/5, Completeness 4/5. Trả lời ngắn gọn hơn, vẫn đúng trọng tâm về điều kiện auto-escalate sau 10 phút.

**Root cause:** Đây là bài toán weighting và rerank. Hybrid có thể tận dụng keyword tốt, nhưng khi thiếu lớp lọc cuối (cross-encoder), một số câu alias có thể bị giảm grounding score dù nội dung trả lời nhìn chung vẫn hợp lý.

**Lesson:** Không nên đánh giá một retrieval strategy chỉ qua một câu; cần nhìn toàn bộ metric và per-question delta để thấy trade-off thật.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Nếu có thêm 2-3 giờ, tôi sẽ implement ensemble judging - chạy nhiều judges và lấy median score để giảm bias của một model judge duy nhất.

Tôi cũng sẽ thêm more test questions cho edge cases: multi-hop questions (combine info từ 2+ docs), numerical questions (SLA time, refund days), negation questions ("Sản phẩm nào KHÔNG được hoàn tiền?"). Hiện tại 10 câu chưa đủ test thoroughly.

Cuối cùng, implement automated regression testing. Mỗi khi tune pipeline, chạy lại scorecard và compare với previous results. Track improvement over time thay vì chỉ evaluate một lần cuối.
