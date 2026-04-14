# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trịnh Uyên Chi  

**Vai trò trong nhóm:** Documentation Owner  

**Ngày nộp:** 13/04/2026 

**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Tôi làm chủ yếu phần Sprint 4, với vai trò Documentation Owner, tôi tập trung vào việc chuẩn hóa tài liệu hệ thống RAG. 
> Về tài liệu, tôi trực tiếp hoàn thiện file **`architecture.md`** nhằm làm rõ luồng kiến trúc hệ thống, đồng thời xây dựng báo cáo **`tuning-log.md`** để ghi nhận chi tiết các kết quả thực nghiệm và thông số tối ưu hóa. 
> Ngoài ra, tôi lên kế hoạch tổng thể và phân công cho từng thành viên. Để đảm bảo bài lab chạy trơn tru, tôi cố gắng đồng bộ tiến độ thường xuyên cho mọi người. Điều này giúp toàn đội nắm bắt chéo kết quả của nhau, đồng thời mỗi cá nhân đều biết chính xác mục tiêu phần việc cần hoàn thành.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Trước lab, tôi nghĩ cắt text (Chunking) chỉ đơn giản là đếm số từ rồi chia đều. Sau khi ngồi nói chuyện với teammate về phần chunking và xem những chunks được in ra sau khi cắt, tôi hiểu đây là nghệ thuật bảo toàn ngữ cảnh. Tùy theo từng tình huống, từng loại dữ liệu sẽ có cách chọn đúng số chunk token kết hợp với Overlap. Việc này giúp AI không bị đứt gãy thông tin khi đọc các document về quy trình và FAQ theo từng câu.

> Ngoài ra, khi thấy có điều bất thường, trong tình huống này là chạy thử lần đầu tiên thấy score của các chunk giống y chang nhau dù AI trả lời đúng, phải debug ngay lập tức vì không bao giờ có chuyện score giống hệt nhau được. Từ đó, tôi mới thấy tầm quan trọng của việc hiểu nguyên nhân cốt lõi gây ra sai sót (sai do index, retrieval hay generation?), tránh việc xác định nhầm và mất thời gian sửa lỗi khác.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Trong giai đoạn tinh chỉnh RAG, nhóm vấp phải nút thắt cổ chai nghiêm trọng không phải ở kỹ năng code, mà ở thời gian chờ đợi hệ thống xử lý. Khi chạy `eval.py` để sinh kết quả cho hàng loạt câu hỏi, hệ thống liên tục văng lỗi từ phía API, chủ yếu là lỗi quá tải hoặc là hết token. Hậu quả là pipeline bị sập ngang giữa chừng, toàn bộ kết quả gen trước đó bị "bốc hơi" và nhóm phải cắn răng chạy lại từ đầu. 

>Trải nghiệm đau thương này mang lại một bài học đắt giá về thiết kế hệ thống thực chiến: Không bao giờ được tin tưởng tuyệt đối vào API bên thứ ba. Tôi nhận ra bắt buộc phải thiết kế cơ chế chịu lỗi (Fault Tolerance), cụ thể là thêm logic tự động thử lại (Exponential Backoff Retry) và lưu kết quả tạm (Checkpointing) sau mỗi câu hỏi để bảo toàn công sức chờ đợi.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** "Approval Matrix để cấp quyền hệ thống là tài liệu nào?" (ID: gq07 - Category: Insufficient Context)

**Phân tích:** Ở phiên bản Baseline, mô hình Dense Search tìm được chunk đích (do có chứa tên cũ "Approval Matrix"), nhưng lại kéo theo quá nhiều chunk rác (Section 1, 3) lên top đầu. Lỗi ở đây là sự thiếu tối ưu trong khâu Retrieval vì Dense Search chỉ tính khoảng cách vector tổng thể của đoạn văn, dẫn đến việc các đoạn mô tả chung chung có điểm số xấp xỉ và gây nhiễu ngữ cảnh cho LLM.

Khuyết điểm này được xử lý triệt để ở Variant (Dense + Cross-encoder Rerank). Ở bước Rerank, thuật toán tiến hành chấm điểm chéo (cross-attention) từng từ giữa câu hỏi và danh sách kết quả thô. Nó đánh giá cực kỳ chính xác mức độ liên quan trực tiếp của cụm "Approval Matrix" trong chunk đích, qua đó đẩy chunk chứa alias này lên vị trí Top 1 và gạt bỏ hoàn toàn các chunk nhiễu. Trường hợp này chứng minh Rerank là chốt chặn hoàn hảo để "lọc tinh" các kết quả tìm kiếm khi câu hỏi chứa các tên gọi tài liệu đặc thù.

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> Dựa trên cấu trúc dữ liệu và quá trình debug, tôi sẽ ưu tiên hai cải tiến:

1. Triển khai Hybrid Search (BM25 + Dense): Đặc thù tài liệu Helpdesk chứa nhiều mã định danh (ERR-403-AUTH). Mình dự đoán Vector Search dễ trượt các từ khóa cứng này, do đó cần thêm BM25 làm "mỏ neo" để đảm bảo truy xuất chính xác từ vựng chuyên ngành.

2. Xây dựng Checkpointing & Retry: Trong lúc test, API LLM rất hay văng lỗi Rate Limit. Mình muốn thêm cơ chế lưu kết quả tạm để pipeline đánh giá có thể tự động chạy tiếp khi sập API, thay vì phải làm lại từ đầu.
_________________
