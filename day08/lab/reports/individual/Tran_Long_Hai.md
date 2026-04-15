# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Thành Viên 5  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)
> Mô tả cụ thể phần bạn đóng góp vào pipeline:
- **Sprint chủ yếu làm**: Sprint 4 (Evaluation & Scorecard).
- **Cụ thể thực hiện**: Tôi đã thiết kế và triển khai logic chấm điểm tự động cho pipeline dựa trên khung đánh giá RAGAS (RAG Assessment) thông qua phương pháp LLM-as-a-Judge. Cụ thể, tôi viết các hàm để gọi OpenAI đánh giá độ trung thực (Faithfulness), độ liên quan (Answer Relevance), và độ đầy đủ (Completeness) theo thang điểm 1-5. Ngoài ra, tôi triển khai logic tính Context Recall bằng việc so khớp chính xác chuỗi `expected_sources` với `source` trong `metadata` của tài liệu thu hồi. Cuối cùng, tôi xây dựng tính năng xuất toàn bộ kết quả chấm điểm ra file JSON (`logs/grading_run.json`).
- **Liên kết với nhóm**: Điểm số và log format mà tôi xuất ra giúp Person 4 (Tuning Variant) định lượng chính xác sự thay đổi khi thử nghiệm Hybrid hoặc Rerank so với Dense Baseline của Person 2.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)
Sau bài lab này, tôi đã hiểu sâu sắc về khái niệm **LLM-as-a-Judge (Dùng LLM để làm giám khảo)** trong quy trình Evaluation của RAG. 
Trước đây, tôi cứ nghĩ rằng để đánh giá hệ thống tạo văn bản, bắt buộc phải dùng sức người hoặc các nhãn từ khớp rập khuôn như ROUGE hay BLEU (vốn rất cứng nhắc và không hiểu ý nghĩa đoạn văn). Việc sử dụng một Prompt cố định hướng dẫn LLM khác đóng vai trò như một "chuyên gia bóc tách" (ví dụ: yêu cầu LLM chấm điểm từ 1-5 xem câu trả lời có hoàn toàn dựa vào context không – Faithfulness) đem lại tính quy mô lớn. LLM Judge xử lý rất tinh tế các từ đồng nghĩa và cách diễn đạt khác nhau, giúp quy trình A/B Testing giữa Baseline và Variant được tự động hoá gần như 100%.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)
Sự cố khó khăn nhất là **cách xử lý các câu hỏi Abstain (hệ thống cần từ chối trả lời do thiếu dữ liệu)**. Trong `test_questions.json`, câu Q09 có trường `expected_sources: []`. 
Lúc đầu, logic đếm Context Recall của tôi chia cho độ dài mảng `expected_sources` (số 0), dẫn tới lỗi chia cho 0. Tương tự, nếu `chunks_used` trả về rỗng nhưng LLM hệ thống chính vẫn xin lỗi và báo là "không có thông tin", thì LLM Judge ban đầu lại chấm Faithfulness là 1/5 do cho rằng câu trả lời "không khớp với bất kỳ Context nào"! Tôi đã phải tinh chỉnh lại logic: nếu hệ thống trả lời là "không thấy dữ liệu" dựa trên context rỗng, thì đó là biểu hiện của độ trung thực tuyệt đối (Faithfulness = 5) và Recall = hoàn hảo. Đây là một bài học đắt giá về việc đánh giá các trường hợp ngoại lệ.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)
**Câu hỏi:** Q09 - "ERR-403-AUTH là lỗi gì và cách xử lý?"

**Phân tích:**
- **Baseline (Dense Retrieval)**: Khi chạy bằng chiến lược Baseline, vì "ERR-403-AUTH" không hề tồn tại trong kho dữ liệu, Retriever (của Person 2) có xu hướng đem về một vài đoạn FAQ không liên quan (noise) chỉ vì chúng có khoảng cách vector gần nhất một cách ngẫu nhiên. Sau đó ở bước Generation (Person 3), nếu prompt không đủ nghiêm ngặt về grounded rules, model sẽ tự bịa ra kiến thức chung chung (hallucination) về cách sửa lỗi 403.
- **Điểm số**: Context Recall là trọn vẹn do mình quy định expected là rỗng, tuy nhiên **Faithfulness sẽ rớt rất thảm hại (1/5)** vì câu trả lời vay mượn thông tin ngoài context. 
- **Lỗi nằm ở đâu**: Lỗi nằm ở bước Generation (thiết kế Prompt chưa chặn được Hallucination) kết hợp với Retrieval (truy xuất các noise vô nghĩa khi query nằm ngoài tập dữ liệu).
- **Variant cải thiện**: Việc Person 4 tích hợp Threshold Score để gạt bỏ các kết quả retrieval kém chất lượng, kết hợp với Prompt generation chặt chẽ ("Answer only from context") chắc chắn sẽ giải quyết triệt để lỗi này.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)
Nếu có thêm thời gian, tôi sẽ bổ sung **Few-shot Examples** vào bên trong LLM-as-Judge Prompt của các hàm chấm điểm. 
Hiện tại sử dụng Zero-shot, đôi khi LLM-as-Judge khá nhân nhượng và cho điểm 4 thay vì 5 mà không có lý luận (notes) thật sự rõ ràng. Đưa ví dụ cụ thể về câu nào đáng bị trừ điểm (VD: penalty nặng khi trích xuất sai ngày) sẽ giúp điểm số của RAGAS ổn định, nhất quán và đáng tin cậy hơn qua nhiều lần chạy thử nghiệm.
