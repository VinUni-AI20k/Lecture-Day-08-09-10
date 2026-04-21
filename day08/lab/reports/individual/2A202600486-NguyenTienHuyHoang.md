# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Tiến Huy Hoàng  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 13/04/2026

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab Day 08 này, với vai trò là **Eval Owner**, tôi chịu trách nhiệm chính trong việc thiết lập và vận hành hệ thống đánh giá (Evaluation Pipeline) cho toàn bộ dự án RAG của nhóm. Cụ thể, tôi đã thực hiện các công việc sau:

- **Xây dựng `eval.py`**: Thiết kế logic chấm điểm tự động dựa trên phương pháp **LLM-as-a-Judge**. Tôi đã viết các hàm chấm điểm cho 4 metric cốt lõi: Faithfulness (Độ trung thực), Answer Relevance (Độ liên quan), Context Recall (Độ phủ ngữ cảnh) và Completeness (Sự đầy đủ).
- **Di chuyển sang Google AI Studio**: Do giới hạn rate limit cực kỳ khắt khe của mô hình Gemini 1.5 Flash khi chạy đánh giá hàng loạt (10 câu hỏi đồng thời cho cả Baseline và Variant), tôi đã thực hiện cấu hình lại hệ thống để sử dụng API key từ AI Studio thay vì Vertex AI, giúp pipeline chạy ổn định và mượt mà hơn.
- **Xử lý dữ liệu đầu ra**: Implement các hàm parsing JSON để trích xuất điểm số và lý do (reasoning) từ kết quả phản hồi của LLM Judge. Tôi cũng xử lý các trường hợp LLM trả về format không chuẩn (thiếu ngoặc, kèm markdown) để đảm bảo scorecard được ghi đúng dữ liệu.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau khi trực tiếp xây dựng bộ Eval, tôi đã thực sự hiểu sâu sắc về khái niệm **RAG Triad** (Bộ ba RAG) mà trước đây tôi chỉ nắm được trên lý thuyết qua slide. 

Tôi nhận ra rằng một câu trả lời nghe có vẻ "hay" (High Relevance) chưa chắc đã là một câu trả lời tốt nếu nó không dựa trên dữ liệu thật (Low Faithfulness). Việc đánh giá tách biệt giữa Retriever (thông qua Context Recall) và Generator (thông qua Faithfulness/Relevance) giúp nhóm tôi biết chính xác lỗi nằm ở đâu khi hệ thống trả lời sai. Đặc biệt, tôi hiểu rõ hơn về **Context Recall** — đây là rào cản lớn nhất của RAG. Nếu retriever không lấy được đúng mẩu thông tin (chunk) chứa câu trả lời, thì dù Generator (LLM) có thông minh đến đâu cũng sẽ dẫn đến tình trạng ảo tưởng. Việc đo lường recall giúp chúng tôi điều chỉnh chiến lược chunking và search mode một cách khoa học thay vì đoán mò.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất mà tôi gặp phải chính là lỗi **Rate Limit (429 - Too Many Requests)**. Tôi đã khá bất ngờ khi Gemini 1.5 Flash (vốn được coi là "fast and cheap") lại bị chặn rất nhanh khi thực hiện các tác vụ chấm điểm liên tục cho 20 lượt chạy (10 baseline + 10 variant). Ban đầu, tôi nghĩ logic code của mình bị loop vô tận, nhưng sau khi debug headers trả về từ API, tôi mới nhận ra vấn đề là do quota. Tôi đã phải giải quyết bằng cách thiết lập cơ chế retry và cuối cùng là chuyển hẳn sang vùng API khác mạnh hơn.

Một điều ngạc nhiên khác là sự "khó bảo" của LLM khi làm Judge. Mặc dù đã yêu cầu chỉ xuất JSON (`Output ONLY a JSON object`), nhưng thi thoảng model vẫn thích viết thêm vài câu dẫn dắt hoặc bỏ quên dấu ngoặc kép trong trường reason. Điều này khiến tôi phải viết thêm logic regex và `json.loads` trong khối `try-except` để bảo vệ pipeline không bị crash giữa chừng.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

Tôi chọn phân tích câu hỏi **Q1**: *"Thủ tục xin nghỉ phép cho nhân viên mới (dưới 6 tháng) là gì?"* trong file `results/ab_comparison.csv`.

- **Phân tích kết quả Baseline (Dense)**: Baseline trả lời một quy trình chung gồm 3 bước (HR Portal, Line Manager phê duyệt). Điểm Faithfulness là 5 (đúng với context được lấy), nhưng Relevance chỉ đạt 3. Lý do là vì nó hoàn toàn bỏ lỡ chi tiết quan trọng nhất: nhân viên dưới 6 tháng chỉ có **0.5 ngày phép mỗi tháng**.
- **Phân tích lỗi**: Đây rõ ràng là lỗi **Retrieval**. Khi kiểm tra `context_recall_notes`, tôi thấy rằng retriever chỉ lấy được chunk chứa quy trình xin nghỉ chung, còn chunk chứa chi tiết về quy định "0.5 ngày cho nhân viên mới" đã bị rơi ra ngoài top-k do điểm cosine similarity không đủ cao.
- **Variant (Hybrid) có cải thiện không?**: Đáng tiếc là ở variant Hybrid, hệ thống lại trả về *"Tôi không tìm thấy thông tin cụ thể..."*. Điều này càng khẳng định giả thuyết rằng cách đánh index hoặc từ khóa "nhân viên mới" (new employee) chưa được xử lý tốt trong bộ từ điển BM25 của nhóm, dẫn đến việc lấy sai ngữ cảnh. Lỗi này nằm ở khâu **Indexing/Retrieval**, không phải do LLM bịa chuyện (vì điểm Faithfulness vẫn cao).

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử nghiệm chiến lược **Semantic Chunking**. Kết quả từ Q1 cho thấy việc cắt text theo kích thước cố định (Fixed size) đang làm xé lẻ các quy định đặc thù ra khỏi quy trình chung. Tôi muốn thử cắt text dựa trên sự thay đổi về ngữ nghĩa (embedding distance) để giữ các quy định liên quan trong cùng một chunk. Ngoài ra, tôi sẽ bổ sung thêm một bước **Reranker** (như Cohere Rerank) sau khi Hybrid search trả về kết quả, nhằm đảm bảo các chunk "ngách" nhưng quan trọng sẽ được đẩy lên top-1 cho generator xử lý.

---

*File này được lưu tại: `reports/individual/2A202600486-NguyenTienHuyHoang.md`*
