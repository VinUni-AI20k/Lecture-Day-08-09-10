# Scorecard: variant_hybrid
Generated: 2026-04-13 15:54

## Summary

| Metric | Average Score |
|--------|--------------|
| Faithfulness | 3.80/5 |
| Relevance | 3.80/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.60/5 |

## Per-Question Results

| ID | Category | Faithful | Relevant | Recall | Complete | Notes |
|----|----------|----------|----------|--------|----------|-------|
| q01 | SLA | 5 | 5 | 5 | 5 | Mọi thông tin trong Answer đều có thể tìm thấy hoàn toàn trong Context Chunk 1, không có bất kỳ thông tin bịa đặt nào. |
| q02 | Refund | 5 | 5 | 5 | 5 | Tất cả thông tin trong Answer đều phù hợp và có thể tìm thấy trong Context. Yêu cầu hoàn tiền trong vòng 7 ngày, điều kiện sản phẩm bị lỗi do nhà sản xuất, và điều kiện đơn hàng chưa được sử dụng hoặc chưa mở seal đều được xác nhận từ các Chunk trong Context. |
| q03 | Access Control | 5 | 5 | 5 | 5 | Mọi thông tin trong câu trả lời đều đúng và có thể tìm thấy trong context, chi tiết phê duyệt cho quyền Level 3 được nêu rõ trong chunk 2. |
| q04 | Refund | 5 | 5 | 5 | 5 | Mọi thông tin trong Answer đều có thể tìm thấy trong Context, cụ thể là thông tin về sản phẩm kỹ thuật số và các ngoại lệ không được hoàn tiền. |
| q05 | IT Helpdesk | 5 | 5 | 5 | 5 | Mọi thông tin trong Answer đều phù hợp và có thể tìm thấy trong Context, cụ thể là thông tin về số lần đăng nhập sai và các phương thức mở khóa tài khoản. |
| q06 | SLA | 5 | 5 | 5 | 2 | Mọi thông tin trong Answer đều có thể tìm thấy dữ liệu bổ trợ trong Context. Cụ thể, Answer đã trình bày đúng quy trình escalation được mô tả trong Chunk 1, không thiếu sót hay thông tin bịa đặt nào. |
| q07 | Access Control | 1 | 1 | 5 | 1 | Answer không cung cấp thông tin nào trong context và hoàn toàn không đáp ứng yêu cầu, do đó, đây là một trường hợp bịa đặt. |
| q08 | HR Policy | 5 | 5 | 5 | 5 | Tất cả thông tin trong Answer đều có thể tìm thấy trong Context, cụ thể là về điều kiện làm remote và ngày onsite bắt buộc. |
| q09 | Insufficient Context | 1 | 1 | None | 2 | Answer không cung cấp thông tin nào từ Context và khẳng định rằng thông tin không có trong tài liệu nội bộ, điều này dẫn đến sự không trung thực vì câu hỏi có thể có thông tin liên quan trong Context. |
| q10 | Refund | 1 | 1 | 5 | 1 | Answer không có thông tin nào trong Context. Nó khẳng định rằng thông tin không có trong tài liệu nội bộ, nhưng không chỉ rõ loại thông tin mà người hỏi đang tìm kiếm, điều này dẫn đến sự không rõ ràng và không thể đánh giá tính trung thực. |
