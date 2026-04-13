# Chấm tự động — grading questions

> LLM-as-judge: **ước lượng** để benchmark nội bộ. Điểm chính thức do GV chấm theo [SCORING.md](SCORING.md).

- **Tổng raw (ước lượng):** 98.00 / 98
- **Quy đổi kiểu 30 điểm phần grading nhóm:** **30.00 / 30**

## Chi tiết

| ID | Verdict | Điểm | Max | Lý do (rút gọn) |
|----|---------|------|-----|-----------------|
| gq01 | Full | 10.0 | 10.0 | Câu trả lời đã nêu rõ thời gian xử lý/khắc phục của P1 và có căn cứ từ tài liệu SLA. Không có thông  |
| gq02 | Full | 10.0 | 10.0 | Câu trả lời nêu rõ nhân viên remote cần VPN khi làm việc với hệ thống nội bộ và giới hạn tối đa 2 th |
| gq03 | Full | 10.0 | 10.0 | Câu trả lời đúng với chính sách hoàn tiền và không bỏ sót điều kiện nào. Thông tin được cung cấp chí |
| gq04 | Full | 8.0 | 8.0 | Câu trả lời nêu đúng 110% giá trị so với số tiền hoàn khi chọn store credit. Không có thông tin nào  |
| gq05 | Full | 10.0 | 10.0 | Câu trả lời đáp ứng đầy đủ các tiêu chí yêu cầu. Không có thông tin nào bị bịa đặt. |
| gq06 | Full | 12.0 | 12.0 | Câu trả lời đã đáp ứng đầy đủ tất cả các tiêu chí yêu cầu. Không có thông tin nào bị bịa đặt. |
| gq07 | Full | 10.0 | 10.0 | Câu trả lời rõ ràng nêu không có thông tin về mức phạt trong tài liệu. Không có bất kỳ con số hay qu |
| gq08 | Full | 10.0 | 10.0 | Câu trả lời đã phân biệt rõ ràng giữa nghỉ phép năm và nghỉ ốm, đồng thời nêu rõ điều kiện cần có gi |
| gq09 | Full | 8.0 | 8.0 | Câu trả lời đúng với cả hai tiêu chí đã đề ra. Không có thông tin nào bị bịa đặt. |
| gq10 | Full | 10.0 | 10.0 | Câu trả lời đúng với nội dung chính sách hoàn tiền v4. Không có thông tin nào bị bịa đặt. |

---

## So sánh với nhóm khác (gợi ý)

1. Dùng **cùng script + cùng bản rubric** (`grading_questions.json`) và so sánh `projected_grading_30pts`.
2. Theo [SCORING.md](SCORING.md): bonus +2 nếu **gq06** đạt Full; tránh **Penalty** ở **gq07** (bịa mức phạt).
3. Cải thiện **gq08** (phân biệt loại phép) thường cần prompt + retrieval tốt hơn, không chỉ tăng top_k.

## File 10 câu grading ở đâu?

- Đề + rubric: [`data/grading_questions.json`](data/grading_questions.json)
- Log pipeline: [`logs/grading_run.json`](logs/grading_run.json) (tạo bằng `python eval.py grading`)
