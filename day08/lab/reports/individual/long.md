# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** _Nguyen Viet Long_ 
**Vai trò trong nhóm:** Eval Owner / Documentation Owner  
**Ngày nộp:** _13/4/2026_
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi đảm nhiệm phần evaluation cho pipeline RAG. Tôi chủ yếu làm việc vào giai đoạn cuối của sprint, khi pipeline đã có index và retrieval cơ bản. Công việc của tôi bao gồm sửa lỗi `eval.py` và `rag_answer.py`, đảm bảo đánh giá hoạt động end-to-end, tạo log chạy grading theo yêu cầu trong `logs/grading_run.json` và cập nhật phần tài liệu tuning-log. Tôi cũng phối hợp với phần xây dựng index và prompt để kiểm chứng rằng kết quả trả lời và scorecard phản ánh đúng chiến lược retrieval và rerank.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn về evaluation loop và vai trò của logging trong đánh giá mô hình. Việc triển khai `grading_run.json` cho thấy rằng không chỉ output cuối cùng quan trọng, mà còn cần có log chi tiết để minh bạch quá trình truy xuất và rerank. Tôi cũng nắm rõ hơn cách đánh giá A/B giữa baseline và variant, và cách các mặt điểm như faithfulness, relevance, context recall, completeness giúp phân tích lỗi của hệ thống.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều bất ngờ nhất là pipeline ban đầu chạy chưa bị lỗi ở phần mô hình, mà gặp khó khăn ở khâu code và logging. Lỗi mất nhiều thời gian debug nhất là sự không khớp giữa index/retrieval và phần đánh giá, khiến `eval.py` không sinh được log grading đúng định dạng. Ban đầu tôi nghĩ vấn đề do prompt hoặc rerank, nhưng thực tế cần sửa logic trong `rag_answer.py` để trả về response an toàn và bổ sung đoạn ghi log cho `grading_questions.json`.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** Escalation trong sự cố P1 diễn ra như thế nào?

**Phân tích:** Câu hỏi này là ví dụ rõ ràng cho thấy lỗi không phải do indexing, bởi cả baseline và variant đều truy xuất được nguồn tài liệu đúng (context recall = 5). Baseline trả lời đã mang đủ ý chính, nhưng điểm relevance và completeness thấp hơn do trình bày chưa tập trung vào câu hỏi chính. Variant dense+rerrank cải thiện completeness từ 2 lên 3, nghĩa là mặc dù cùng thông tin, câu trả lời variant đã cấu trúc lại tốt hơn và giảm bớt phần không cần thiết. Do đó, lỗi chính ở khâu generation/phần prompt chứ không phải retrieval.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ tinh chỉnh prompt generation để ép mô hình trả lời ngắn gọn và chỉ tập trung vào bước escalation. Tôi cũng muốn thử thêm hybrid retrieval hoặc rerank theo query-specific score, vì kết quả eval cho thấy retrieval đúng nguồn nhưng generation vẫn cần cải thiện tính đầy đủ và liên quan.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
