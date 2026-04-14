# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lưu Lương Vi Nhân

**Vai trò trong nhóm:** Eval Owner

**Ngày nộp:** 13/4/2026

---

## 1. Tôi đã làm gì trong lab này?

Trong lab này, tôi đảm nhận vai trò Eval Owner và tập trung chủ yếu vào Sprint 4: Evaluation & Scorecard. Nhiệm vụ cụ thể của tôi là implement file `eval.py` để tự động hóa quá trình đánh giá RAG Pipeline thông qua bốn metrics: Faithfulness, Answer Relevance, Context Recall và Completeness.

Thay vì chấm thủ công, tôi xây dựng framework theo phương pháp LLM-as-a-Judge — thiết kế các prompt yêu cầu LLM chấm điểm theo thang 1–5 và trình bày lý do rõ ràng. Công việc này kết nối trực tiếp với các Sprint trước: hàm `run_scorecard` chạy toàn bộ pipeline hoàn chỉnh, đọc dữ liệu từ `test_questions.json`, rồi cho ra kết quả định lượng để nhóm so sánh cụ thể giữa Baseline và các Variant cải tiến như Hybrid Retrieval hay Rerank.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Hai khái niệm tôi hiểu sâu hơn hẳn sau lab này là **Evaluation Loop** và cách phân biệt **Context Recall với các Generative Metrics**.

Phân biệt được rõ ràng hai loại lỗi hoàn toàn khác nhau: Retriever tìm sai tài liệu dẫn đến Context Recall thấp, và LLM tự thêm thắt hoặc trả lời lạc đề dù đã có đủ context — biểu hiện qua Faithfulness và Answer Relevance thấp. Mỗi loại lỗi cần được xử lý ở một tầng riêng biệt trong pipeline.

Xây dựng hệ thống giám sát -> evaluation -> lưu log -> tối ưu. Sử dụng loop để cải thiện cũng như các downstream task, hay RL sau này.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Khó khăn lớn nhất là việc parse JSON từ output của LLM-as-a-Judge một cách ổn định. LLM thường sinh thêm các câu dẫn như *"Here is the evaluation:"* trước phần JSON thực sự, khiến `json.loads` báo lỗi JSONDecodeError. Sau một thời gian debug, tôi implement thêm Regex — `re.search(r'\{[^}]+\}', response, re.DOTALL)` — để trích xuất đúng phần JSON cần thiết, thay vì tin tưởng tuyệt đối vào việc LLM luôn tuân theo format.

Điều ngạc nhiên nhất (qua theo dõi `tuning-log.md`) là **Variant 1 dùng Hybrid + Rerank (Cross-encoder) lại có kết quả không tốt hơn Baseline**, thậm chí Faithfulness trung bình rớt nhẹ từ 4.60 xuống 4.50. Ban đầu nhóm tự tin Rerank sẽ luôn giúp định vị đúng chứng cứ, nhưng thực tế mô hình Rerank đôi lúc lại ưu tiên các chunk "có wording tương đồng câu hỏi" thay vì chunk "chứa câu trả lời đúng" (dẫn đến sụt điểm ở câu q04, q06). Với câu q10 (Refund VIP, bị dính 1 điểm toàn tập do LLM abstain quá đà), nhóm nhận ra rằng dù Retriever kéo đúng policy chung đi nữa, nếu thiếu Grounded Prompt Template có rule xử lý ngoại lệ quy định, bước Generation vẫn có thể thất bại. Lỗi không phải lúc nào cũng nằm ở Retriever!

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** q07 — *"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"*
(Độ khó: Hard | Danh mục: Access Control)

Ở **bản Baseline** (chỉ dùng Dense Retrieval), điểm số câu này khá tệ, đặc biệt là Completeness chỉ đạt 2/5. Nguyên nhân cốt lõi là query sử dụng cụm từ cũ ("Approval Matrix") trong khi tài liệu thực tế của IT Security tên là `access-control-sop.md`. Lỗi xuất phát từ bước **Retrieval**: Dense Embedding đơn thuần bỏ lỡ exact keyword/alias, kéo chunk trả lời có phần tên cũ nhưng lại thiếu mapping quan trọng sang tên SOP mới.

Sang **bản Variant** (áp dụng Hybrid Retrieval kết hợp rrf_dense 0.6 và rrf_sparse 0.4 cộng với mô hình rerank `cross-encoder/ms-marco-MiniLM-L-6-v2`), câu trả lời ghi nhận điểm Completeness tăng nhẹ lên 3/5. Lượng lớn thông tin được kéo lại nhờ phần Sparse BM25 bắt thuật ngữ cực khỏe. Dù hybrid tổng thể chưa tối ưu (vì Rerank bị nhiễu ở các câu khác), nhưng riêng câu q07 là minh họa xuất sắc về việc: khi bạn cần tra lịch sử văn bản đổi tên hoặc mã từ khoá chuyên biệt, sức mạnh "bám exact term" của Sparse/Hybrid Retriever rõ ràng hoạt động tốt và cứu Generation khỏi bị hụt thông tin.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Cải thiện hàm `score_context_recall`. Hiện tại hàm đang so sánh partial string trên tên file, cách tiếp cận này có thể gây ra False Positive nếu nhiều tài liệu có tên tương tự nhau. Hướng cải tiến là áp dụng Semantic Similarity hoặc LLM-as-a-Judge trực tiếp lên nội dung chunk — để tự động xác định "chunk này có chứa Expected Knowledge cần thiết hay không", thay vì chỉ dựa vào metadata source name vốn đôi khi bị sai hoặc thiếu ngay từ bước parse tài liệu.

Sử dụng các thư viện như RAGAS, DeepEval, Trulens để thực hiện phần evaluation.
