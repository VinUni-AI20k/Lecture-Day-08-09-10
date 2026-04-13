# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Minh Quân 
**Vai trò trong nhóm:** Eval Owner
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Trong dự án RAG này, tôi chịu trách nhiệm chính về khâu hậu kiểm và phân tích hiệu năng thông qua việc xây dựng bộ công cụ A/B Comparison và Report Generator. Sau khi hệ thống vận hành trên hai cấu hình Baseline (Dense Retrieval) và Variant (Hybrid Retrieval), tôi đã thiết lập quy trình đối chiếu định lượng dựa trên bốn chỉ số tiêu chuẩn: Faithfulness, Relevance, Recall và Completeness.

> Công việc cụ thể của tôi bao gồm việc lập trình logic tính toán sự biến thiên (Delta) giữa các phiên bản và tự động hóa việc xuất báo cáo dưới định dạng Markdown và CSV. Thay vì chỉ dừng lại ở việc liệt kê điểm số, tôi đã xây dựng trình xử lý để nhận diện các câu hỏi có biến động điểm số lớn nhất, từ đó cung cấp bằng chứng thực nghiệm giúp nhóm đưa ra các quyết định điều chỉnh cấu hình hệ thống dựa trên dữ liệu khách quan.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Thông qua việc trực tiếp xây dựng bộ chỉ số đánh giá, tôi đã hiểu sâu sắc về vòng lặp phản hồi (Evaluation Loop) trong phát triển hệ thống AI. Tôi nhận ra rằng việc tối ưu hóa một thành phần (như thêm Hybrid Search) không phải lúc nào cũng mang lại kết quả tích cực đồng bộ.

> Cụ thể, kết quả thực nghiệm với mức Delta âm ở chỉ số Faithfulness (-0.50) đã giúp tôi hiểu rõ về hiện tượng "nhiễu thông tin" trong RAG. Khi kết hợp Sparse Search (BM25), hệ thống có thể truy xuất được nhiều đoạn văn bản chứa từ khóa trùng lặp nhưng lại không mang tính ngữ cảnh cao, dẫn đến việc làm loãng dữ liệu đầu vào của LLM. Bài học lớn nhất tôi rút ra là việc cân bằng giữa Precision (Độ chính xác) và Recall (Độ phủ) trong truy xuất thông tin là một thách thức kỹ thuật cần được tinh chỉnh thông qua nhiều lần thử nghiệm scorecard.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều khiến tôi ngạc nhiên nhất trong quá trình thực hiện là hiện tượng nghịch lý điểm số giữa Baseline và Variant. Mặc dù lý thuyết cho rằng Hybrid Search ưu việt hơn, nhưng thực tế kết quả scorecard cho thấy Baseline (Dense Search) lại có độ ổn định cao hơn ở các câu hỏi phức tạp về quy trình (như câu q06 và q10). Điều này bác bỏ giả thuyết ban đầu của nhóm và buộc tôi phải kiểm tra lại tính chất của bộ dữ liệu nguồn.

> Khó khăn kỹ thuật lớn nhất nằm ở việc thiết kế logic chấm điểm tự động (Automated Grading) sao cho công bằng. Việc xử lý các câu trả lời dạng "Không đủ dữ liệu" (như câu q09) đòi hỏi logic phân tích phức tạp để không đánh đồng việc "hệ thống trung thực" với việc "hệ thống trả lời thiếu ý". Tôi đã phải dành nhiều thời gian để hiệu chỉnh System Prompt cho AI Judge nhằm đảm bảo các nhận xét trong báo cáo là khách quan và có tính đóng góp cho việc debug.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)
**Câu hỏi:** [q06] "Escalation trong sự cố P1 diễn ra như thế nào?"

**Phân tích:**
> Đây là trường hợp điển hình minh chứng cho giá trị của việc phân tích A/B Comparison. Ở phiên bản Baseline (Dense Search), hệ thống đạt điểm tối đa 5/5 trên tất cả các metrics nhờ truy xuất đúng quy trình tự động hóa sau 10 phút. Tuy nhiên, ở phiên bản Variant (Hybrid Search), điểm Faithfulness đã sụt giảm nghiêm trọng từ 5 xuống 2 và Completeness giảm từ 5 xuống 2.

> Qua báo cáo đối chiếu, tôi phát hiện ra rằng khi sử dụng Hybrid Search, việc ưu tiên các từ khóa rời rạc đã khiến hệ thống truy xuất nhầm các đoạn văn bản về "quyền hạn của On-call IT Admin" thay vì "quy trình thời gian escalation". Điều này tạo ra sự nhiễu loạn thông tin cho LLM, dẫn đến một câu trả lời lạc đề. Việc phân tích Delta sâu ở câu hỏi này giúp nhóm nhận ra rằng thuật toán Dense Search có khả năng hiểu các truy vấn mang tính trình tự tốt hơn so với việc kết hợp từ khóa đơn thuần. Đây là dữ liệu quan trọng để chúng tôi xem xét lại trọng số (weighting) giữa các phương thức tìm kiếm trong các bước phát triển kế tiếp.
_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> Tôi dự định sẽ mở rộng trình Report Generator để tích hợp thêm tính năng Error Categorization. Thay vì chỉ báo cáo điểm số, hệ thống sẽ tự động phân loại lỗi thuộc về khâu Retrieval (truy xuất sai) hay khâu Generation (LLM diễn đạt sai). Điều này sẽ giúp quy trình tối ưu hóa hệ thống trở nên chuyên nghiệp và nhanh chóng hơn, thay vì phải kiểm tra thủ công từng câu có điểm Delta âm như hiện tại.

_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
