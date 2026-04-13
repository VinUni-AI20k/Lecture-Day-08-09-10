# Scorecard: baseline_dense
Generated: 2026-04-13 15:52

## Summary

| Metric | Average Score |
|--------|--------------|
| Faithfulness | 3.80/5 |
| Relevance | 3.80/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.90/5 |

## Per-Question Results

| ID | Category | Faithful | Relevant | Recall | Complete | Notes |
|----|----------|----------|----------|--------|----------|-------|
| q01 | SLA | 5 | 5 | 5 | 5 | Thông tin trong Answer hoàn toàn khớp với Context. Thời gian phản hồi ban đầu và khắc phục cho ticket P1 đều được xác nhận trong Chunk 1. |
| q02 | Refund | 5 | 5 | 5 | 5 | Thông tin trong Answer hoàn toàn trung thực, vì nó chỉ tái khẳng định điều kiện hoàn tiền trong vòng 7 ngày làm việc từ Context, mà không có bất kỳ thông tin nào bị bịa đặt. |
| q03 | Access Control | 5 | 5 | 5 | 5 | Mọi thông tin trong Answer đều chính xác và có thể tìm thấy trong Context, đặc biệt là yêu cầu phê duyệt của Line Manager, IT Admin và IT Security cho quyền Level 3. |
| q04 | Refund | 5 | 5 | 5 | 5 | Tất cả thông tin trong Answer đều có thể tìm thấy trong Context. Câu trả lời chính xác nêu rõ rằng sản phẩm kỹ thuật số không được hoàn tiền và đưa ra ví dụ cụ thể là license key và subscription, hoàn toàn phù hợp với thông tin được cung cấp trong các Chunk. |
| q05 | IT Helpdesk | 5 | 5 | 5 | 5 | Mọi thông tin trong Answer đều chính xác và có thể tìm thấy trong Context. Câu trả lời đúng với thông tin về việc tài khoản bị khóa sau 5 lần đăng nhập sai và cách mở khóa. |
| q06 | SLA | 5 | 5 | 5 | 5 | Mọi thông tin trong Answer đều có thể tìm thấy trong Context, tuân theo quy trình xử lý sự cố P1 và thông tin về escalation. |
| q07 | Access Control | 1 | 1 | 5 | 1 | Answer chứa thông tin bịa đặt vì nó khẳng định rằng thông tin không có trong tài liệu, trong khi tài liệu đã quy định chi tiết quy trình cấp phép và các cấp độ quyền truy cập. |
| q08 | HR Policy | 5 | 5 | 5 | 5 | Hoàn toàn trung thực, mọi ý đều có trong context. |
| q09 | Insufficient Context | 1 | 1 | None | 2 | Thông tin trong Answer không liên quan đến bất kỳ phần nào trong Context, dẫn đến việc cho rằng thông tin không có trong tài liệu nội bộ là không chính xác. |
| q10 | Refund | 1 | 1 | 5 | 1 | Answer tuyên bố rằng thông tin không có trong tài liệu nội bộ, trong khi thực tế có nhiều thông tin về quy trình hoàn tiền và điều kiện cần thiết được nêu rõ trong context. |
