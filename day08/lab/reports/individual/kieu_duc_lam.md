# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Kiều Đức Lâm  
**Vai trò trong nhóm:** Retrieval Owner
**Ngày nộp:** 13.04.2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi phụ trách phần Sprint 3 với vai trò chính liên quan đến retrieval tuning. Cụ thể, tôi triển khai các hướng cải tiến gồm hybrid retrieval, retrieve_sparse, rerank và transform question/query. Sau khi nhóm hoàn thành pipeline cơ bản với LLM và dense retrieval, nhiệm vụ của tôi là bổ sung các biến thể nhằm tối ưu khả năng truy xuất thông tin trước khi đưa sang bước đánh giá mô hình. Tôi đã xây dựng cơ chế hybrid bằng cách kết hợp dense retrieval và sparse retrieval theo hướng Reciprocal Rank Fusion để tận dụng cả semantic matching lẫn keyword matching. Ngoài ra, tôi cũng thử rerank lại các candidate chunks để chọn ra các đoạn thật sự liên quan nhất, đồng thời thêm bước transform query để tăng recall với các câu hỏi diễn đạt khác nhau. Phần tôi làm đóng vai trò cầu nối giữa baseline RAG và giai đoạn evaluation sau đó.

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

au lab này, tôi hiểu rõ hơn hai khái niệm là hybrid retrieval và evaluation loop. Trước đây tôi thường nghĩ retrieval chỉ cần dense search là đủ, vì embedding có thể nắm được ngữ nghĩa câu hỏi. Tuy nhiên khi làm lab, tôi nhận ra dense retrieval mạnh ở việc hiểu ý, nhưng đôi khi lại bỏ sót các từ khóa chính xác như mã lỗi, tên tài liệu, hoặc các cụm có tính quy ước. Ngược lại, sparse/BM25 rất hiệu quả với exact match nhưng lại kém hơn khi câu hỏi bị paraphrase. Vì vậy hybrid retrieval giúp cân bằng hai điểm mạnh này. Tôi cũng hiểu rõ hơn evaluation loop là quá trình không chỉ đo điểm cuối cùng, mà còn dùng kết quả eval để xác định lỗi nằm ở retrieval hay generation. Nhờ vậy, việc cải tiến mô hình trở nên có cơ sở hơn thay vì chỉnh sửa theo cảm giác.

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến tôi ngạc nhiên là việc thêm nhiều kỹ thuật hơn không đồng nghĩa với việc kết quả luôn tốt hơn ngay lập tức. Ban đầu tôi giả thuyết rằng chỉ cần thêm hybrid retrieval hoặc rerank thì chất lượng trả lời sẽ tăng rõ rệt. Nhưng trong thực tế, hiệu quả còn phụ thuộc vào chất lượng candidate chunks ban đầu, cách trộn điểm, và số lượng chunks được chọn đưa vào prompt. Phần mất thời gian debug nhất là kiểm tra xem lỗi đến từ retrieve sai tài liệu, rerank chọn sai chunk, hay LLM sinh câu trả lời chưa bám sát context. Ngoài ra, với bước transform query, tôi cũng nhận ra rằng mở rộng câu hỏi quá nhiều đôi khi làm tăng nhiễu thay vì tăng recall. Khó khăn lớn nhất không phải là viết hàm, mà là xác định chính xác mỗi thay đổi đang cải thiện hay làm hỏng mắt xích nào trong pipeline.

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
>
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:**
Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?

**Phân tích:**

Với câu hỏi này, baseline trả lời đúng nhưng điểm số chưa tối ưu (1 | 5 | 5 | 4). Điều này cho thấy hệ thống đã nắm được ý chính của câu hỏi (có/không được cấp quyền), nhưng thiếu một phần quan trọng liên quan đến chi tiết như thời gian xử lý hoặc các yêu cầu đặc biệt đi kèm. Điểm thấp ở tiêu chí đầu tiên nhiều khả năng phản ánh việc câu trả lời chưa đầy đủ hoặc chưa bám sát hoàn toàn vào yêu cầu multi-part của câu hỏi.

Xét về nguyên nhân, lỗi chủ yếu nằm ở retrieval thay vì generation. Cụ thể, dense retrieval có thể đã lấy được các chunk liên quan đến “Admin Access” nhưng chưa ưu tiên đúng các đoạn có chứa thông tin về contractor bên ngoài hoặc các điều kiện đặc biệt. Ngoài ra, việc giới hạn số lượng chunk (top-k) đưa vào prompt cũng có thể khiến một số thông tin quan trọng bị bỏ sót. LLM sau đó chỉ tổng hợp từ context hiện có nên không thể bổ sung phần thiếu.

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi muốn thử tinh chỉnh lại cách kết hợp điểm trong hybrid retrieval, ví dụ thay đổi trọng số giữa dense và sparse cho từng loại câu hỏi thay vì dùng cố định. Tôi cũng muốn làm một bảng eval chi tiết hơn để phân nhóm lỗi theo retrieval failure và generation failure. Lý do là kết quả hiện tại cho thấy có những câu baseline đã tốt, nên cần phân tích sâu hơn để biết variant thật sự giúp ở nhóm câu hỏi nào và tránh tối ưu dàn trải

_Lưu file này với tên: `reports/individual/[ten_ban].md`_
_Ví dụ: `reports/individual/nguyen_van_a.md`_
