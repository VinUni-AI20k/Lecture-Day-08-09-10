# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phan Văn Tấn  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong dự án này, tôi đảm nhận vai trò **Eval Owner**, chịu trách nhiệm xây dựng hệ thống giám sát và đánh giá chất lượng của toàn bộ pipeline RAG. Ở Sprint 1, tôi thiết lập cấu trúc cho file `eval.py` và phân tích bộ dữ liệu 10 câu hỏi kiểm thử để xác định các trường hợp đặc biệt như "Abstain" (câu hỏi không có trong dữ liệu). Sang Sprint 2 và 4, tôi trực tiếp triển khai các hàm chấm điểm tự động sử dụng phương pháp **LLM-as-Judge** để đo lường 4 chỉ số: `Faithfulness`, `Relevance`, `Context Recall` và `Completeness`. Công việc của tôi đóng vai trò là "chốt chặn" cuối cùng, giúp nhóm nhận diện được các lỗi về ảo giác (hallucination) và đánh giá khách quan hiệu quả của việc cải tiến từ bản Baseline (chỉ dùng Vector Search) sang bản Variant (kết hợp Hybrid và Rerank).

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu sâu sắc về concept **Evaluation Loop** và **Abstain Logic**. Trước đây, tôi nghĩ đơn giản AI cứ trả lời là xong, nhưng thực tế trong hệ thống RAG nội bộ, việc AI biết nói "Tôi không tìm thấy thông tin" khi dữ liệu không có trong tài liệu (Abstain) quan trọng hơn việc cố gắng suy luận bừa bãi gây ra lỗi ảo giác. Ngoài ra, việc sử dụng LLM làm "giám khảo" giúp tôi hiểu cách viết prompt để ép model đánh giá tính trung thực (Faithfulness) dựa trên bằng chứng (Context) thay vì đánh giá dựa trên cảm tính. Quy trình này giúp việc phát triển RAG trở nên khoa học hơn nhờ các con số cụ thể để so sánh giữa các phiên bản thay vì chỉ phán đoán cảm tính.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất tôi gặp phải là lỗi **mismatch hạ tầng** và **đồng bộ dữ liệu**. Ban đầu, file `eval.py` của tôi chạy tốt nhưng kết quả Recall luôn bằng 0. Qua quá trình debug, tôi phát hiện lỗi `Errno 2` do thiếu file Index BM25 cho bản Variant và sự sai lệch về model Embedding giữa bước Indexing và bước Evaluation. Điều làm tôi ngạc nhiên nhất là dù code pipeline đã xong, nhưng chỉ cần một sai sót nhỏ ở đường dẫn thư mục lưu trữ (`chroma_db` hoặc `bm25_index`) là toàn bộ hệ thống đánh giá sẽ báo lỗi ngay lập tức. Bài học rút ra là Eval Owner cần phối hợp cực kỳ chặt chẽ với team Indexing và Retrieval để đảm bảo môi trường chạy dữ liệu luôn đồng nhất.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 - "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**
Đây là một câu hỏi rất tiêu biểu để kiểm tra khả năng tìm kiếm nâng cao vì nó chứa từ khóa mang tính "bí danh" (Alias). Trong tài liệu thực tế, thông tin nằm trong file `access-control-sop.md`, nhưng người dùng lại hỏi bằng thuật ngữ cũ là "Approval Matrix". 

- **Ở bản Baseline (Dense Retrieval):** Hệ thống trả về kết quả rất tệ với Recall = 0. Nguyên nhân là do Embedding của câu hỏi và tài liệu không đủ gần nhau về mặt ngữ nghĩa để model tìm thấy nhau trong không gian vector. AI đã trả lời: "Không tìm thấy thông tin", dẫn đến điểm Faithfulness cao (không nói dối) nhưng Relevance và Recall bằng 0.
- **Ở bản Variant (Hybrid Search):** Nhờ sự kết hợp giữa BM25 (tìm kiếm từ khóa chính xác) và Vector Search, hệ thống đã bắt được cụm từ "Approval Matrix" có trong nội dung tài liệu. Điểm Recall của câu này đã cải thiện rõ rệt (nhảy từ 0 lên 5/5). 
- **Kết luận:** Qua trường hợp này, tôi thấy rõ giá trị của Hybrid Search trong việc giải quyết các bài toán tìm kiếm dựa trên từ khóa chuyên ngành mà Vector Search đơn thuần thường bỏ lỡ.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử nghiệm thêm chỉ số **Context Precision** để đánh giá độ nhiễu của tài liệu lấy về. Hiện tại hệ thống lấy 3 chunks (top-k=3), tôi muốn kiểm tra xem liệu việc giảm xuống 1 chunk chất lượng nhất có giúp câu trả lời ngắn gọn và chính xác hơn không. Ngoài ra, tôi muốn thử thêm **Reranker (Cross-Encoder)** để sắp xếp lại thứ tự ưu tiên của các đoạn văn bản trước khi đưa vào Prompt, nhằm nâng cao tối đa điểm Relevance.

---