# Chấm tự động — grading questions

> LLM-as-judge: **ước lượng** để benchmark nội bộ. Điểm chính thức do GV chấm theo [SCORING.md](SCORING.md).

- **Tổng raw (ước lượng):** 70.00 / 0
- **Quy đổi kiểu 30 điểm phần grading nhóm:** **0.00 / 30**

## Chi tiết

| ID | Verdict | Điểm | Max | Lý do (rút gọn) |
|----|---------|------|-----|-----------------|
| gq01 | Full | 10.0 | 10.0 | Câu trả lời nêu đúng giá trị hiện tại và cũ của SLA. Ngoài ra, có citation về phiên bản và không bịa |
| gq02 | Partial | 5.0 | 10.0 | Câu trả lời xác nhận VPN là bắt buộc và nêu đúng giới hạn 2 thiết bị. Tuy nhiên, không có citation t |
| gq03 | Full | 10.0 | 10.0 | Câu trả lời rõ ràng và chính xác về việc không được hoàn tiền. Đã nêu đúng các ngoại lệ liên quan đế |
| gq04 | Partial | 5.0 | 10.0 | Câu trả lời nêu đúng con số 110% và nhấn mạnh đây là tùy chọn. Tuy nhiên, không có citation từ polic |
| gq05 | Zero | 0.0 | 10.0 | Câu trả lời không cung cấp thông tin nào liên quan đến yêu cầu. Không có dữ liệu để xác nhận các tiê |
| gq06 | Partial | 5.0 | 10.0 | Câu trả lời đạt 4/5 tiêu chí. Không đề cập hotline on-call ext. 9999 từ SLA P1. |
| gq07 | Full | 10.0 | 10.0 | Câu trả lời nêu rõ rằng không có đủ dữ liệu trong tài liệu để trả lời câu hỏi. Không có thông tin nà |
| gq08 | Full | 10.0 | 10.0 | Câu trả lời nêu đúng số ngày báo trước cho nghỉ phép năm và quy định về nghỉ ốm. Hai ngữ cảnh được p |
| gq09 | Partial | 5.0 | 10.0 | Câu trả lời xác nhận mật khẩu cần đổi định kỳ, nêu đúng chu kỳ và thời gian nhắc nhở. Tuy nhiên, khô |
| gq10 | Full | 10.0 | 10.0 | Câu trả lời rõ ràng và chính xác về chính sách hoàn tiền. Tất cả các tiêu chí đều được đáp ứng đầy đ |

---

## So sánh với nhóm khác (gợi ý)

1. Dùng **cùng script + cùng bản rubric** (`grading_questions.json`) và so sánh `projected_grading_30pts`.
2. Theo [SCORING.md](SCORING.md): bonus +2 nếu **gq06** đạt Full; tránh **Penalty** ở **gq07** (bịa mức phạt).
3. Cải thiện **gq08** (phân biệt loại phép) thường cần prompt + retrieval tốt hơn, không chỉ tăng top_k.

## File 10 câu grading ở đâu?

- Đề + rubric: [`data/grading_questions.json`](data/grading_questions.json)
- Log pipeline: [`logs/grading_run.json`](logs/grading_run.json) (tạo bằng `python eval.py grading`)
