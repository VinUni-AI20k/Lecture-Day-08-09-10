# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Quang Minh  
**Vai trò trong nhóm:** Quality & Reports  
**Ngày nộp:** 13-04-2026  

---

## 1. Tôi đã làm gì trong lab này?

Trong đợt thực hành Lab Day 08 lần này, tôi đảm nhận vai trò chốt chặn cuối cùng của dự án ở Sprint 4. Nhiệm vụ chính của tôi là vận hành hệ thống đánh giá, xuất báo cáo Scorecard và tổng hợp dữ liệu cho Group Report. 

Cụ thể, tôi đã thực hiện việc đồng bộ mã nguồn từ các thành viên khác, xử lý các lỗi phát sinh về môi trường như xung đột kích thước vector trong ChromaDB và dọn dẹp các tệp tin rác trong workspace để đảm bảo kết quả đánh giá là khách quan nhất. Sau khi các pipeline RAG gồm bản Baseline và bản Hybrid được hoàn thiện, tôi trực tiếp chạy các kịch bản kiểm thử, thu thập dữ liệu từ Terminal và chuyển hóa những con số khô khan đó thành các phân tích có giá trị. Tôi đóng vai trò là cầu nối giữa kết quả kỹ thuật và tài liệu báo cáo, giúp nhóm nhìn ra được hiệu quả thực tế của những thay đổi mà nhóm đã triển khai.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Sau khi trực tiếp tham gia vào quy trình này, tôi đã hiểu sâu sắc hơn về vòng lặp đánh giá trong hệ thống RAG. Trước đây, tôi thường lầm tưởng rằng chỉ cần hệ thống lấy đúng được tài liệu là câu trả lời sẽ mặc định chính xác. Tuy nhiên, thực tế từ Scorecard đã dạy cho tôi một bài học khác.

Tôi nhận ra sự khác biệt rõ rệt giữa hai chỉ số Context Recall và Faithfulness. Hệ thống có thể đạt điểm Recall tuyệt đối 5/5 nhưng điểm Faithfulness vẫn thấp nếu mô hình ngôn ngữ lớn tự ý thêm thắt thông tin nằm ngoài ngữ cảnh được cung cấp. Việc hiểu rõ sự tương tác này giúp tôi biết cách tinh chỉnh lại niềm tin vào mô hình và hiểu tại sao chúng ta cần các chiến lược truy xuất kết hợp như Hybrid Retrieval để "buộc" mô hình phải bám sát vào dữ kiện thực tế hơn.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Khó khăn lớn nhất mà tôi phải đối mặt chính là việc tổng hợp và xử lý khối lượng thông tin khổng lồ từ các tệp log. Khi nhìn vào hàng loạt tệp báo cáo với hàng chục câu hỏi, mỗi câu lại đi kèm 4 tiêu chí điểm khác nhau, tôi thực sự cảm thấy bị ngợp. Việc phải xâu chuỗi xem tại sao câu hỏi này ở bản Baseline bị thấp điểm nhưng sang bản Hybrid lại cải thiện, hay ngược lại, đòi hỏi sự tập trung cực kỳ cao độ.

Tôi đã mất rất nhiều thời gian để "thẩm thấu" hết đống dữ liệu đó nhằm tìm ra quy luật chung thay vì chỉ liệt kê các con số. Việc phải đóng vai một điều tra viên để truy ngược lại xem lỗi nằm ở khâu nạp dữ liệu hay khâu sinh văn bản là một thử thách thực sự về mặt tư duy logic. Bên cạnh đó, tôi cũng khá bất ngờ khi những lỗi nhỏ về môi trường như cache của database cũ lại có thể làm sai lệch hoàn toàn kết quả của cả một quá trình đánh giá nếu không được dọn dẹp kỹ lưỡng.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** [gq07] Công ty sẽ phạt bao nhiêu nếu team IT vi phạm cam kết SLA P1?

**Phân tích:**
Đây là một tình huống rất thú vị mà nhóm tôi đã thảo luận kỹ. Trong kịch bản này, cả hai phiên bản Baseline và Hybrid đều nhận điểm số rất thấp 1/1/None/1 cho các tiêu chí Faithful/Relevant/Recall/Complete dù hệ thống đã hoạt động đúng logic.

Dữ liệu về hình phạt không hề tồn tại trong các tài liệu mà nhóm được cung cấp. Về mặt kỹ thuật, hệ thống đã thực hiện chính xác việc không tìm thấy tài liệu liên quan nên điểm Recall bằng None. LLM cũng đã tuân thủ yêu cầu không bịa đặt thông tin khi trả lời là "Tôi không biết". Tuy nhiên, dưới góc độ của bộ chấm điểm tự động, câu trả lời này bị coi là thiếu chuyên nghiệp và không đầy đủ về mặt thông tin phản hồi cho người dùng. 

Lỗi ở đây không nằm ở khâu truy xuất dữ liệu mà nằm ở khâu thiết kế câu lệnh hướng dẫn. Điều này giúp tôi nhận ra rằng, trong các hệ thống thực tế, việc biết cách từ chối một cách khéo léo và cung cấp lý do tại sao không có thông tin cũng quan trọng tương đương với việc đưa ra câu trả lời đúng.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Nếu có thêm thời gian, tôi sẽ tập trung vào hai cải tiến cụ thể để nâng cao chất lượng báo cáo và hiệu suất hệ thống. Thứ nhất, tôi muốn thiết kế lại toàn bộ System Prompt cho các trường hợp không tìm thấy thông tin, yêu cầu LLM phản hồi theo cấu trúc chuyên nghiệp hơn để cải thiện điểm số ở các câu hỏi bẫy. 

Thứ hai, tôi sẽ xây dựng một công cụ tự động bằng Python để trích xuất dữ liệu từ các file CSV kết quả và vẽ biểu đồ so sánh trực quan. Việc này không chỉ giúp tôi giảm bớt sự mệt mỏi khi phải tổng hợp dữ liệu thủ công bằng mắt thường mà còn giúp nhóm có cái nhìn trực diện, nhanh chóng hơn về xu hướng thay đổi của hệ thống sau mỗi lần điều chỉnh tham số.

---