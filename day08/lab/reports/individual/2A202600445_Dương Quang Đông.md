# Báo Cáo Cá Nhân - Lab Day 08: RAG Pipeline

**Họ và tên:** Dương Quang Đông  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500-800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi tập trung chủ yếu vào Sprint 1 và Sprint 3 với vai trò Retrieval Owner. Ở Sprint 1, tôi tham gia chuẩn hóa dữ liệu đầu vào cho retrieval: hỗ trợ preprocess tài liệu, chia chunk theo section, giữ metadata như `source`, `section`, `effective_date`, rồi lưu vào ChromaDB để các bước sau có thể truy vết nguồn rõ ràng. Ở Sprint 3, tôi chọn hướng **Hybrid retrieval** thay vì reranking và implement trực tiếp trong `rag_answer.py` qua hai hàm `retrieve_sparse()` và `retrieve_hybrid()`. Cụ thể, tôi dùng BM25 để lấy tín hiệu keyword từ toàn bộ chunk, sau đó kết hợp kết quả dense retrieval và sparse retrieval bằng Reciprocal Rank Fusion với trọng số dense 0.6 và sparse 0.4. Tôi chọn hybrid vì nó phù hợp hơn với bộ dữ liệu của bài lab: vừa có câu mô tả tự nhiên, vừa có các keyword đặc thù như SLA, P1, Level 3, ERR-403 và Approval Matrix.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn rằng retrieval trong RAG không chỉ là “lấy đúng tài liệu”, mà là lấy đúng đoạn evidence để model có thể trả lời ngắn gọn nhưng vẫn grounded. Khi làm phần indexing, tôi thấy chunking và metadata ảnh hưởng trực tiếp đến chất lượng retrieve: nếu chunk cắt giữa ý hoặc section mơ hồ, hệ thống có thể lấy đúng file nhưng sai đoạn bằng chứng. Khi sang Sprint 3, tôi hiểu thêm sự khác nhau giữa dense, sparse, hybrid và reranking. Dense mạnh ở semantic search, sparse mạnh ở exact keyword, còn hybrid phù hợp khi corpus pha trộn cả hai kiểu tín hiệu. Tôi cũng hiểu rõ vì sao tôi không chọn reranking ở vòng này: rerank chủ yếu tăng precision bằng cách sắp xếp lại candidate đã có, trong khi bài lab này có nhiều truy vấn cần bắt đúng keyword hoặc alias ngay từ bước retrieve. Vì vậy, vấn đề đáng ưu tiên hơn là recall của retrieval, không phải một lớp chấm điểm lại ở cuối.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất của tôi là làm cho biến thể hybrid chạy đúng end-to-end thay vì chỉ dừng ở mức ý tưởng. `retrieve_sparse()` phải đọc lại toàn bộ documents từ ChromaDB, tokenize ổn định, dựng BM25 index, rồi trả kết quả cùng format với dense retrieval để `rag_answer()` dùng chung được. Sau đó, ở `retrieve_hybrid()`, tôi còn phải gộp hai danh sách kết quả bằng RRF sao cho không bị trùng chunk và vẫn giữ metadata nhất quán. Điều làm tôi ngạc nhiên là dù hybrid rất hợp lý về mặt retrieval, scorecard cuối cùng của baseline dense và variant hybrid lại bằng nhau: Faithfulness 4.50, Relevance 4.20, Context Recall 5.00, Completeness 3.80. Kết quả này cho tôi thấy một bài học quan trọng: chọn đúng kỹ thuật chưa chắc tạo ra chênh lệch điểm nếu nút thắt thật sự nằm ở generation, prompt grounding, hoặc dữ liệu thiếu evidence cho một số câu hỏi.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 - "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Đây là câu hỏi tôi thấy đáng phân tích nhất vì nó giúp phân biệt khá rõ lỗi retrieval với lỗi generation. Trong cả `scorecard_baseline.md` và `scorecard_variant.md`, câu q07 đều đạt Faithfulness 5, Relevance 5, Context Recall 5 nhưng Completeness chỉ 2. Điều đó cho thấy hệ thống đã retrieve đúng nguồn cần thiết ở cả hai cấu hình, nên vấn đề không còn nằm ở indexing hay việc có tìm ra tài liệu hay không. Nói cách khác, dense baseline đã đủ tốt để kéo đúng evidence vào context, còn hybrid chỉ giúp củng cố thêm khả năng match alias và keyword chứ chưa tạo khác biệt ở điểm số cuối.

Điểm thiếu nằm ở bước trả lời. Tài liệu đúng là `access-control-sop.md`, và trong chunk có thông tin cho biết tài liệu này trước đây từng được gọi là “Approval Matrix for System Access”. Tuy nhiên câu trả lời của model mới dừng ở mức mô tả đây là tài liệu quy định quy trình cấp quyền, chứ chưa nói rõ tên hiện tại là **Access Control SOP** và chưa khai thác đầy đủ chi tiết alias cũ. Trường hợp này cũng giải thích vì sao tôi chọn hybrid thay vì reranking ở Sprint 3: nếu candidate đúng đã được retrieve từ đầu, reranking chỉ đổi thứ tự chunk chứ không tự làm model trả lời đầy đủ hơn. Với q07, bước cải thiện hợp lý hơn ở vòng sau sẽ là query transformation hoặc siết grounded prompt để model nêu rõ cả tên mới lẫn tên cũ của tài liệu.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử hai hướng tiếp theo. Thứ nhất là query transformation cho các câu hỏi dạng alias như q07, ví dụ mở rộng “Approval Matrix” thành “Access Control SOP” hoặc “Approval Matrix for System Access” trước khi retrieve. Thứ hai là thử pipeline dense/hybrid → rerank → top-3 select để xem reranking có cải thiện precision sau khi recall đã đủ tốt hay không. Như vậy, hybrid vẫn là lựa chọn hợp lý ở vòng này, còn reranking sẽ là bước tối ưu tiếp theo nếu nhóm muốn đào sâu hơn.
