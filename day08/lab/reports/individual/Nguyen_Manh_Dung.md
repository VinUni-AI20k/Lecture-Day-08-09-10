# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Mạnh Dũng 
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)


Với vai trò Tech Lead ghép cặp cùng Quang, tôi tập trung chủ yếu vào Sprint 1 và Sprint 2 để xây dựng khung xương cốt lõi cho pipeline. Cụ thể, tôi chịu trách nhiệm thiết lập môi trường, viết hàm get_embedding(), và cấu hình ChromaDB để lưu trữ vector. Tiếp đó, tôi implement hàm retrieve_dense() và call_llm() để tạo ra luồng Baseline hoạt động end-to-end.
Công việc của tôi đóng vai trò là "chất keo" kết dính dự án: tôi nhận logic chia chunk và bóc tách metadata từ team Retrieval (Tuấn, Hải) để lắp ráp vào file index.py. Trong Sprint 3, tôi cấu trúc lại file rag_answer.py để dễ dàng switch qua lại giữa Baseline và các Variant (như Hybrid/Rerank). Tôi cũng làm cầu nối liên lạc giữa team Eval và team Retrieval cũng như hiểu hệ thống để quá trình eval được suôn sẻ.
_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Concept tôi hiểu sâu sắc nhất sau lab này là tư duy A/B Testing và quy trình tinh chỉnh (tuning) thông số RAG. Ban đầu, khi muốn chatbot trả lời tốt hơn, tôi thường sửa prompt hoặc đổi thuật toán một cách cảm tính và chỉ "đọc lướt" vài câu để đoán xem nó có ổn hơn không. Tuy nhiên, lab này giúp tôi nhận ra RAG tuning đòi hỏi một vòng lặp đánh giá (evaluation loop) cực kỳ khắt khe.
Tôi thực sự thấm nhuần nguyên tắc cốt lõi của A/B test: chỉ thay đổi đúng MỘT biến số mỗi lần (ví dụ: giữ nguyên Baseline là Dense Search nhưng thêm module Rerank vào Variant, hoặc giữ nguyên Retrieval nhưng đổi chiến lược Chunking). Việc đóng gói hai cấu hình này để chạy đối chiếu qua scorecard giúp team đo lường rõ ràng "delta" (độ chênh lệch).

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến tôi thực sự ngạc nhiên là số lượng parameters cần tinh chỉnh trong một pipeline RAG. Hệ thống có các biến số: chunk_size, overlap, top_k của luồng Dense/Sparse, trọng số RRF, cho đến số lượng chunk giữ lại sau Rerank, và tất cả chúng đeeuf liên quan đến nhau.
Khó khăn lớn nhất là tôi nhận ra việc tuning RAG đòi hỏi "độ nhạy" và kinh nghiệm thực chiến cao hơn tôi tưởng rất nhiều. Khi LLM trả lời sai, rất khó để chẩn đoán ngay lỗi nằm ở đâu. Các thông số này tương tác chéo với nhau: đổi chunk_size sẽ lập tức làm top_k cũ mất tác dụng. Việc thiếu kinh nghiệm kiến trúc hệ thống khiến tôi lúc đầu tinh chỉnh khá cảm tính, dẫn đến tình trạng sửa được test case này lại vô tình làm hỏng kết quả của câu hỏi khác.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**
Đây là câu hỏi khó nhất trong bộ test vì người dùng truy vấn bằng tên cũ của tài liệu ("Approval Matrix"), trong khi file hiện hành đã được đổi tên thành "Access Control SOP".
Khi chạy trên luồng Baseline (Dense Search), hệ thống trả lời sai. Về mặt toán học, embedding của cụm từ "Approval Matrix" không nằm gần "Access Control SOP" trong không gian vector, khiến thuật toán bỏ lỡ hoàn toàn tài liệu đích (context_recall = 0).
Tuy nhiên, khi nhóm áp dụng Variant (Hybrid Search), hệ thống trả lời đúng. Thành phần tìm kiếm từ khóa (BM25) đã phát huy sức mạnh khi nắm được chính xác keyword "Approval Matrix" nằm ẩn trong dòng ghi chú lịch sử của file. Qua đây, tôi xác định rõ root cause của việc fail nằm thuần túy ở khâu Retrieval do Dense search bị trôi dạt ngữ nghĩa, hoàn toàn không phải do lỗi Indexing hay Generation. Với các bộ dữ liệu nội bộ có nhiều tên gọi lóng/tên cũ, Hybrid Search hoặc Query Expansion là giải pháp bắt buộc.

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử nghiệm Semantic Chunking (chia chunk theo ngữ nghĩa/tiêu đề) thay vì cắt theo số lượng ký tự cố định. Qua quá trình eval, tôi thấy một số chunk bị cắt làm đôi ngay giữa một điều khoản dài, khiến context bị cụt.

_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
