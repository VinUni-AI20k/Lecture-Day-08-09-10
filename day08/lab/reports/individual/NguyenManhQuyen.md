# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Mạnh Quyền  
**MSSV:** 2A202600481  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này tôi phụ trách phần evaluation, nên công việc chính tập trung ở Sprint 4 nhưng có liên kết trực tiếp với Sprint 2 và Sprint 3. Tôi dùng `data/test_questions.json` để theo dõi câu hỏi kiểm thử, đọc output của `rag_answer.py`, rồi dùng `eval.py` để chấm bốn metric: faithfulness, relevance, context recall và completeness. Tôi cũng đối chiếu các scorecard trong `results/` như `scorecard_variant_dense.md`, `scorecard_variant_hybrid.md`, `scorecard_variant_hyde.md`, `scorecard_variant_multi_query.md` và `scorecard_variant_sparse.md` để xem mode nào thực sự ổn hơn trên bộ câu hỏi grading. Nếu scorecard cho thấy câu nào fail do retrieve sai hoặc generate suy diễn, tôi phải chỉ ra lỗi nằm ở đâu để cả nhóm quyết định có nên đổi retrieval mode, sửa prompt hay thêm guardrail abstain.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn rằng evaluation trong RAG không thể chỉ nhìn một metric. Ban đầu tôi nghĩ retrieve đúng source là gần như đủ, nhưng khi xem scorecard tôi thấy context recall cao vẫn chưa đảm bảo answer tốt. Tôi cũng hiểu rõ hơn sự khác nhau giữa faithfulness và completeness. Faithfulness trả lời câu hỏi “model có bám vào evidence không”, còn completeness hỏi “nó có nói đủ các ý quan trọng không”. Một pipeline có thể retrieve đúng tài liệu, nhưng nếu prompt hoặc cách chọn chunk không tốt thì model vẫn bỏ sót điều kiện hoặc ngoại lệ. Tôi cũng thấy rõ giá trị của evaluation loop: không phải cứ thêm kỹ thuật mới như HyDE hay multi-query là điểm sẽ tự tăng; phải có scorecard thật để kiểm chứng.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi ngạc nhiên nhất là kết quả thực tế không hoàn toàn giống kỳ vọng trong `docs/tuning-log.md`. Trong phần mô tả tuning, HyDE được xem là hướng cải tiến chính, nhưng các scorecard mới trong `results/` lại cho thấy `variant_dense` đang nhỉnh hơn về tổng thể. Điều này nhắc tôi rằng documentation và giả thuyết chỉ là điểm khởi đầu; quyết định cuối cùng phải dựa trên output đang chạy được. Khó khăn lớn nhất là phân biệt lỗi retrieval với lỗi generation. Có những câu nhìn bề ngoài như “model trả lời sai”, nhưng khi soi scorecard thì hóa ra retriever đã lấy đúng source rồi. Với vai trò Eval Owner, phần tốn thời gian nhất là đọc notes từng câu để tìm đúng failure mode thay vì chỉ nhìn điểm trung bình.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** `gq05` — “Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?”

**Phân tích:**

Đây là câu tôi thấy giá trị nhất để đánh giá pipeline vì nó không phải bài toán “có tìm được tài liệu hay không”, mà là bài toán “đã có đúng nguồn rồi nhưng có tổng hợp đúng hết ý không”. Theo `data/test_questions.json`, expected answer cần đủ các ý: contractor vẫn thuộc phạm vi áp dụng, Admin Access Level 4 cần phê duyệt bởi IT Manager và CISO, thời gian xử lý là 5 ngày làm việc, và có thêm training security bắt buộc. Trong scorecard hiện tại, `variant_dense` cho câu này Faithfulness = 3, Relevance = 4, Recall = 5, Completeness = 2; còn `hybrid`, `hyde`, `multi_query`, `sparse` đều rơi xuống Faithfulness = 1, Relevance = 1, Recall = 5, Completeness = 1. Điểm mấu chốt là Recall vẫn bằng 5, tức retriever đã mang về đúng source `it/access-control-sop.md`. Vì vậy lỗi chính không nằm ở indexing hay retrieval, mà nằm ở generation hoặc cách ghép context: model không gom đủ các chi tiết phân tán trong nhiều section rồi bắt đầu suy diễn thêm. Dense vẫn là mode đỡ tệ nhất ở câu này, nên với góc nhìn evaluation tôi xem đây là bằng chứng rằng mode mới chưa chắc đã tốt hơn.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ làm hai việc. Thứ nhất, tôi sẽ bổ sung một bảng phân loại lỗi theo từng câu trong `eval.py`, tách rõ lỗi retrieval, hallucination và thiếu ý. Thứ hai, tôi sẽ thử chỉnh `top_k_select` hoặc thêm rule coverage theo section cho câu multi-detail như `gq05`, vì kết quả hiện tại cho thấy retrieve đúng source nhưng answer vẫn thiếu hoặc bịa.
