# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Hà Việt Khánh - 2A202600055
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab Day 08, tôi tập trung chính ở Sprint 1: Indexing và Metadata, vì đây là nền tảng quyết định chất lượng retrieval ở các sprint sau. Phần tôi trực tiếp implement nằm trong `index.py`, gồm thiết kế các chiến lược chunking theo từng loại tài liệu thay vì dùng một kiểu chia chung. Ví dụ, với FAQ tôi tách theo cặp hỏi - đáp để tăng precision cho truy vấn ngắn; với SLA tôi nhóm theo mức ưu tiên để giữ ngữ cảnh định nghĩa + cam kết dịch vụ trong cùng một chunk. Tôi cũng chuẩn hóa metadata cho từng chunk (doc_id, chunk_id, section_title, department, effective_date, prev/next chunk, aliases, char_count) và cấu hình lưu vector vào ChromaDB bằng cosine similarity. Công việc của tôi kết nối trực tiếp với phần retrieval và evaluation của các bạn khác vì toàn bộ truy xuất sau này phụ thuộc vào chất lượng index và metadata từ Sprint 1.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu sâu hơn hai khái niệm: chunking theo ngữ nghĩa và vai trò của metadata trong retrieval. Trước đây tôi nghĩ chunking chủ yếu là cắt đều theo số ký tự, nhưng khi làm thực tế tôi thấy nếu cắt không theo cấu trúc nghiệp vụ thì retriever dễ lấy trúng đoạn “gần đúng” nhưng thiếu ý quan trọng. Việc chunk theo loại tài liệu giúp giảm nhiễu rõ rệt. Khái niệm thứ hai là metadata không chỉ để “ghi chú”, mà là tín hiệu điều hướng retrieval. Ví dụ `department`, `section_title`, hoặc `aliases` cho phép lọc và mở rộng ngữ cảnh đúng hướng, đặc biệt khi người dùng hỏi bằng tên cũ hoặc thuật ngữ nội bộ. Tôi cũng thấy `prev_chunk_id/next_chunk_id` hữu ích cho sliding window, giúp câu trả lời ít bị cụt thông tin khi ý nghĩa nằm ở hai đoạn liền kề.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi ngạc nhiên là cùng một mô hình embedding nhưng chất lượng truy hồi có thể chênh nhiều chỉ vì cách chunking. Ban đầu tôi giả thuyết rằng dùng model tốt là đủ, còn cách chia đoạn chỉ ảnh hưởng nhẹ. Thực tế ngược lại: khi chunk chưa đúng ranh giới ngữ nghĩa, kết quả retrieval thường “na ná” nhưng thiếu điều kiện quan trọng (ngoại lệ, phạm vi áp dụng, mốc thời gian). Khó khăn tốn thời gian nhất là xử lý dữ liệu tài liệu không đồng nhất định dạng: tiêu đề, đánh số mục và cách xuống dòng mỗi file khác nhau. Tôi phải chỉnh parser và quy tắc tách nhiều lần để tránh chunk bị đứt mạch. Ngoài ra, tôi cũng gặp vấn đề hiển thị ký tự trong terminal khi kiểm tra metadata, sau đó khắc phục bằng chuẩn hóa đầu ra để quá trình verify ổn định hơn.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** “Trong Refund Policy v4, các trường hợp ngoại lệ ở Article 3 có được hoàn tiền không và có điều kiện gì đi kèm?”

**Phân tích:**

Đây là câu hỏi thú vị vì nó kiểm tra đúng điểm yếu hay gặp của baseline: trả lời theo “quy tắc chung” nhưng bỏ qua ngoại lệ. Ở baseline, câu trả lời chỉ đúng một phần, thường nêu điều kiện hoàn tiền chung ở các điều khoản đầu và thiếu hoặc lẫn thông tin của Article 3. Điểm scorecard vì vậy ở mức trung bình (đúng ý chính nhưng thiếu điều kiện quan trọng nên bị trừ factual completeness). Theo tôi, lỗi gốc nằm nhiều ở retrieval hơn generation: retriever chưa ưu tiên chunk chứa đúng Article 3, hoặc chunk chứa Article 3 bị trộn với phần khác nên tín hiệu semantic yếu. Khi chuyển sang variant với chunking theo điều khoản và tách riêng ngoại lệ, chất lượng cải thiện rõ: top-k thường có chunk đúng ngay từ đầu, nên model trả lời đầy đủ hơn về phạm vi áp dụng và điều kiện kèm theo. Điều này cho thấy cải thiện indexing/retrieval đã tạo khác biệt lớn trước cả khi tinh chỉnh prompt generation.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử metadata-aware retrieval theo hai bước: lọc mềm theo `doc_id/section_title` rồi mới tính similarity để giảm khả năng kéo nhầm ngữ cảnh. Tôi cũng muốn thử dynamic top-k theo loại câu hỏi (factoid, policy, exception) vì kết quả eval cho thấy câu hỏi về “ngoại lệ” cần ngữ cảnh tập trung hơn. Mục tiêu là tăng factual completeness mà không làm tăng hallucination.
