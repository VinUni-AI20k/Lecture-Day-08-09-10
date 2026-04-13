# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trinh Duc Anh 
**Vai trò trong nhóm:** Tech Lead   
**Ngày nộp:** 13/4/2026 
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)
 Đảm nhiệm vai trò Tech Lead và tập trung chính vào Sprint 2 và Sprint 3. Ở Sprint 2, em hoàn thiện luồng baseline RAG trong `rag_answer.py`: implement `retrieve_dense()` để truy vấn ChromaDB bằng embedding, hoàn thiện `call_llm()` để gọi model với chế độ ổn định, và nối các bước retrieve → select → generate trong `rag_answer()`. em cũng bổ sung guardrail abstain: khi không có bằng chứng hoặc model xác nhận thiếu dữ liệu thì trả về câu trả lời từ chối và `sources = []`.  

Sang Sprint 3,em chọn hướng Hybrid Retrieval. Cụ thể, em implement `retrieve_sparse()` bằng BM25 (`rank_bm25`) và `retrieve_hybrid()` theo công thức Reciprocal Rank Fusion để kết hợp dense + sparse. Ngoài ra, em thêm hàm so sánh baseline vs variant theo dạng bảng Markdown để nhóm dễ đối chiếu khi điền tuning log. Phần của em kết nối trực tiếp với công việc của các bạn phụ trách đánh giá/điểm số vì output đã có citation, source list và logic abstain nhất quán để chấm scorecard thuận lợi hơn.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Điều em hiểu rõ nhất sau lab này là retrieval chất lượng cao quan trọng hơn việc “chỉ đổi model mạnh hơn”. Việc chỉ cần prompt chặt là đủ, nhưng khi làm thực tế thấy nếu top-k context ban đầu sai hoặc nhiễu thì model vẫn trả lời kém dù prompt tốt. Vì vậy, khâu retrieve (dense/hybrid/rerank) là nền móng của toàn pipeline.  

Concept thứ hai em hiểu sâu hơn là grounded answer không chỉ nằm ở câu lệnh “đừng bịa”. Grounding đúng nghĩa cần ba lớp: (1) context được cấu trúc rõ để model biết trích từ đâu, (2) prompt ép hành vi citation/abstain, (3) hậu kiểm ở tầng code để chuẩn hóa output khi model trả lời lệch format. Việc thêm hậu xử lý citation và source rỗng khi abstain giúp output ổn định hơn đáng kể khi chạy nhiều câu hỏi liên tiếp. cũng rút ra rằng “đúng kỹ thuật” phải đi cùng “đúng format đánh giá”, nếu không thì scorecard sẽ thiếu nhất quán giữa các lần chạy.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)


Khó khăn lớn nhất của em là mô hình đôi khi trả lời đúng nội dung nhưng lại không gắn citation `[1]`, đặc biệt ở câu liên quan approval/level quyền. Ban đầuu giả thuyết lỗi nằm ở retrieval vì sợ top chunk chưa đúng. Nhưng khi soi log thấy source trả về đúng tài liệu (`it/access-control-sop.md`) và answer cũng đúng factual, chỉ thiếu định dạng citation. Như vậy nguyên nhân chính nằm ở generation format consistency, không phải retrieval recall.  

Một vấn đề khác là phần so sánh strategy in log bị lặp ở vài lần chạy do cấu hình test trong `__main__` và cách gọi compare nhiều lần. Về mặt chất lượng câu trả lời thì không sai, nhưng gây khó đọc khi đối chiếu kết quả. Từ đó ưu tiên chỉnh output thành bảng tóm tắt rõ ràng để người chấm nhìn được ngay: số source, có abstain hay không, preview câu trả lời. Bài học lớn là trong hệ thống RAG phục vụ đánh giá, “khả năng debug” và “tính quan sát được” quan trọng gần như ngang với độ chính xác của model.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** ERR-403-AUTH là lỗi gì?

**Phân tích:**

Với baseline dense, câu hỏi này được retrieve ra một số chunk có điểm thấp và không chứa thực thể “ERR-403-AUTH” trong tài liệu chuẩn. Kết quả trả về là “Không đủ dữ liệu để trả lời từ tài liệu hiện có.” và `sources = []`. Theo góc nhìn scorecard, đây là một trường hợp baseline “trả lời đúng cách” dù không đưa ra nội dung nghiệp vụ: faithfulness cao vì không bịa, relevance ở mức chấp nhận được do phản hồi trực tiếp trạng thái thiếu dữ liệu, context recall thấp vì tài liệu thật sự không có chứng cứ cho mã lỗi này.  

Khi chạy variant hybrid (dense + BM25), kết quả không cải thiện về nội dung câu trả lời và vẫn abstain. Điều này hợp lý vì hybrid chỉ giúp tăng recall khi dữ liệu tồn tại dưới dạng keyword/alias khác nhau; còn ở đây có khả năng evidence không có trong corpus index nên cả dense lẫn sparse đều không thể “tạo” kiến thức mới. Điểm tích cực là variant không làm pipeline trả lời ảo, nghĩa là guardrail grounded vẫn giữ được. Từ câu hỏi này,  kết luận rằng mục tiêu của tuning không phải lúc nào cũng là “trả lời được nhiều hơn”, mà là “trả lời đáng tin hơn”: có bằng chứng thì trích dẫn, không có bằng chứng thì từ chối rõ ràng và source rỗng.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)


Nếu có thêm thời gian, em sẽ thử hybrid có chuẩn hóa tiếng Việt tốt hơn ở tầng sparse tokenizer (tách từ, xử lý dấu và ký hiệu) vì BM25 hiện tại còn đơn giản, có thể bỏ sót biến thể câu hỏi.em cũng muốn thêm một bước lightweight rerank sau hybrid (ví dụ top-10 → top-3) để giảm nhiễu trước khi vào prompt, vì một số câu trả lời đúng nhưng chưa nhất quán citation cho thấy context đưa vào vẫn còn “na ná đúng” thay vì thật sự tối ưu.

---

