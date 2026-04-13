# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Huy Hồng Nhật
**Mã sinh viên:** 2A202600099
**Vai trò trong nhóm:** Tech Lead
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (150 từ)

Với vai trò Tech Lead, tôi chịu trách nhiệm xây dựng nền tảng kỹ thuật và định hướng kiến trúc cho dự án RAG Prototype. Trong Sprint 1, tôi thiết lập cấu trúc repository, triển khai hệ thống quản lý cấu hình tập trung thông qua `config.py` và `.env`, đồng thời xây dựng skeleton cho file core `index.py`. Tôi cũng là người đưa ra quyết định về **chiến lược semantic chunking**, lựa chọn cắt theo các đề mục `===` thay vì độ dài ký tự cố định nhằm đảm bảo giữ được ngữ cảnh đầy đủ của từng phần chính sách.

Ở các Sprint tiếp theo, tôi thiết kế **System Prompt** với các quy tắc grounding chặt chẽ để hạn chế hallucination, đồng thời thiết lập ngưỡng **abstain threshold** (0.35) cho hệ thống. Vai trò của tôi là điều phối và kết nối các module, từ phần tiền xử lý dữ liệu của Khánh và Khải đến phần đánh giá chất lượng của Tấn và Thành. Cuối cùng, tôi chịu trách nhiệm thực hiện Grading Run và đảm bảo các file báo cáo (`grading_run.json`, `scorecard.md`) tuân thủ đúng quy trình của Lab.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (150 từ)

Sau lab này, tôi hiểu rõ hơn về cơ chế **Hybrid Retrieval** và vai trò của việc kết hợp giữa Semantic Search (Dense) và Keyword Search (Sparse). Trước đây, tôi thường ưu tiên Embedding, nhưng với các bộ dữ liệu chứa nhiều thuật ngữ kỹ thuật như "P1 SLA", "ERR-403" hoặc các tên tài liệu như "Approval Matrix", phương pháp BM25S cho thấy hiệu quả cao trong việc truy xuất chính xác.

Bên cạnh đó, tôi nhận thấy tầm quan trọng của việc xây dựng **Evaluation Loop** tự động. Việc sử dụng các metric như Faithfulness và Context Recall giúp đánh giá chất lượng hệ thống một cách khách quan, từ đó đưa ra các điều chỉnh như `top_k` hoặc trọng số RRF dựa trên dữ liệu thay vì cảm tính. Đặc biệt, khái niệm "Abstain Accuracy" giúp tôi hiểu rằng một hệ thống RAG hiệu quả không chỉ trả lời đúng mà còn cần biết khi nào nên từ chối trả lời nếu không có đủ thông tin.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (150 từ)

Khó khăn lớn nhất tôi gặp phải là vấn đề **xử lý đường dẫn linh hoạt (Path Resolution)**. Ban đầu, các script thường gặp lỗi khi chạy từ các thư mục làm việc (CWD) khác nhau. Tôi đã phải điều chỉnh lại hệ thống bằng cách sử dụng `Path(__file__).parent` và định nghĩa `LAB_DIR` để đảm bảo tính ổn định bất kể chạy từ vị trí thực thi nào.

Một điểm đáng chú ý là sự nhạy cảm của **LLM-as-Judge** đối với định dạng câu trả lời. Ở giai đoạn đầu, điểm Faithfulness thấp không phải do nội dung sai, mà do định dạng trích dẫn nguồn chưa đúng chuẩn khiến hệ thống đánh giá không thể xác định được context tương ứng. Sau khi điều chỉnh prompt để cố định định dạng trích dẫn `[1]`, `[2]`, điểm số đã được cải thiện đáng kể mà không cần thay đổi thuật toán retrieval. Điều này cho thấy khâu Generation có vai trò quan trọng trong việc đảm bảo tính chính xác của câu trả lời.

---

## 4. Phân tích một câu hỏi trong scorecard (200 từ)

Tôi chọn câu hỏi **q06** trong `test_questions.json` để phân tích vì nó thể hiện rõ sự khác biệt giữa hai phương pháp truy xuất.

**Câu hỏi:** "Escalation trong sự cố P1 diễn ra như thế nào?"

**Phân tích:**

* **Kết quả Baseline (Dense):** Đạt 5/5 về Faithfulness, Relevance và Recall, nhưng **Completeness chỉ đạt 4/5**. Câu trả lời nêu đúng nội dung chính về việc escalate sau 10 phút, nhưng lại bao gồm thêm các thông tin không cần thiết liên quan đến quy trình xử lý sự cố, làm giảm tính tập trung của câu trả lời.
* **Kết quả Variant (Hybrid):** Đạt **5/5 cho tất cả các metric**. Nhờ kết hợp BM25S để bắt chính xác từ khóa "escalate", hệ thống truy xuất được các đoạn context phù hợp hơn. Kết quả là câu trả lời tập trung vào quy trình escalation và các mốc thời gian cụ thể.
* **Kết luận:** Vấn đề của Baseline nằm ở khâu **Retrieval**. Việc chỉ sử dụng vector similarity khiến hệ thống lấy các đoạn có nội dung tương đồng nhưng không trực tiếp liên quan đến "Escalation". Hybrid Retrieval đã cải thiện đáng kể vấn đề này bằng cách kết hợp giữa ngữ nghĩa và từ khóa.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (100 từ)

Nếu có thêm thời gian, tôi sẽ tập trung nghiên cứu sâu hơn về **Query Rewriting bằng HyDE**. Kết quả đánh giá cho thấy phương pháp này giúp cải thiện Context Recall đáng kể đối với các câu hỏi có thuật ngữ chuyên môn. Ngoài ra, tôi cũng muốn tối ưu thêm bước **reranking bằng CrossEncoder** để loại bỏ các chunk không liên quan trong Hybrid mode, từ đó duy trì điểm Faithfulness ổn định ngay cả khi tăng `top_k`.

---

*Lưu file này với tên: `reports/individual/2A202600099_Lê Huy Hồng Nhật.md`*
