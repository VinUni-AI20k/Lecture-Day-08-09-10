# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Hoàng Nghĩa
**Vai trò trong nhóm:** Eval Owner
**Ngày nộp:** 13/04/2026
**Độ dài:** 500-800 từ

---

## 1. Tôi đã làm gì trong lab này? (100–150 từ)

Trong lab này, tôi đảm nhận vai trò Eval Owner và tập trung chủ yếu vào Sprint 4. Nhiệm vụ chính của tôi là xây dựng pipeline đánh giá cho hệ thống RAG, bao gồm việc thiết kế scorecard và implement các hàm chấm điểm theo 4 metrics: Faithfulness, Answer Relevance, Context Recall và Completeness. Tôi cũng tích hợp pipeline evaluation với output từ `rag_answer` để đảm bảo chạy end-to-end từ retrieval đến scoring. Ngoài ra, tôi thiết lập cấu hình baseline và variant để phục vụ so sánh A/B, đồng thời xuất kết quả ra file markdown và CSV. Công việc của tôi kết nối trực tiếp với phần retrieval (Sprint 2, 3) vì tôi cần sử dụng output chunks và answer để đánh giá chất lượng hệ thống.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100–150 từ)

Sau lab này, tôi hiểu rõ hơn về vòng lặp evaluation trong hệ thống RAG. Trước đây, tôi nghĩ chỉ cần cải thiện retrieval hoặc prompt là đủ, nhưng qua việc chấm điểm, tôi nhận ra rằng phải đo lường từng thành phần riêng biệt. Ví dụ, Context Recall phản ánh chất lượng retrieval, trong khi Faithfulness và Completeness lại liên quan đến generation. Ngoài ra, tôi cũng hiểu rõ hơn sự khác biệt giữa “relevant” và “faithful”: một câu trả lời có thể đúng câu hỏi nhưng vẫn không dựa trên context. Điều này giúp tôi nhìn hệ thống một cách có cấu trúc hơn thay vì đánh giá cảm tính.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100–150 từ)

Điều khiến tôi bất ngờ là việc chấm điểm không hề đơn giản như ban đầu nghĩ. Tôi gặp khó khăn khi phân biệt giữa Faithfulness và Completeness, vì có những trường hợp câu trả lời đúng một phần nhưng thiếu chi tiết quan trọng. Ngoài ra, việc parse JSON từ LLM khi thử LLM-as-judge cũng gây lỗi khá nhiều, khiến tôi chuyển sang chấm thủ công để đảm bảo ổn định cho demo. Một vấn đề khác là việc so khớp source trong Context Recall, do format đường dẫn không đồng nhất nên phải dùng partial matching. Ban đầu tôi nghĩ evaluation chỉ là bước phụ, nhưng thực tế đây là phần giúp phát hiện lỗi rõ nhất trong pipeline.

---

## 4. Phân tích một câu hỏi trong scorecard (150–200 từ)

**Câu hỏi:** q07 – “Approval Matrix để cấp quyền hệ thống là tài liệu nào?”

**Phân tích:**

Ở baseline, hệ thống retrieval đã lấy được đúng các chunk từ tài liệu access-control-sop.md. Trong đó, chunk đầu tiên chứa thông tin then chốt: tài liệu này trước đây được gọi là “Approval Matrix for System Access”, đóng vai trò như một alias để trả lời câu hỏi. Tuy nhiên, các chunk còn lại (Section 1, Section 3) chủ yếu mô tả phạm vi và quy trình chung, không trực tiếp phục vụ câu hỏi, dẫn đến việc xuất hiện nhiễu. Điều này cho thấy retrieval đúng nhưng chưa thực sự tối ưu. Đây là một dạng câu hỏi tương đối khó vì sử dụng tên cũ thay vì tên hiện tại của tài liệu. Dense retrieval vẫn có thể tìm được nhờ sự xuất hiện của cụm “Approval Matrix”, nhưng cách này không đảm bảo ổn định với các alias khác. Khi chuyển sang variant (hybrid retrieval), hệ thống có xu hướng ưu tiên match keyword “Approval Matrix” mạnh hơn, từ đó đưa chunk chứa alias lên vị trí cao hơn và giảm nhiễu. Trường hợp này cho thấy hybrid retrieval phù hợp hơn với các truy vấn có chứa alias hoặc tên gọi cũ

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm thời gian, tôi muốn thử thêm bước reranking sau hybrid retrieval để cải thiện thứ tự các chunks, vì một số trường hợp top-1 vẫn chưa phải chunk tốt nhất. Ngoài ra, tôi cũng muốn refine prompt để giảm trường hợp answer bị thiếu thông tin dù đã retrieve đúng context, vì kết quả evaluation cho thấy Completeness chưa luôn đạt mức cao.

---

