# Test: hybrid + rerank
Generated: 2026-04-13T16:20:58

Config:
```
retrieval_mode = hybrid
top_k_search = 20
top_k_select = 3
use_rerank = True
label = test_hybrid_rerank
```

| ID | Sources | Answer (preview) |
|----|---------|------------------|
| q01 | support/helpdesk-faq.md, support/sla-p1-2026.pdf | SLA xử lý ticket P1 là 15 phút cho phản hồi ban đầu và 4 giờ cho xử lý và khắc phục [1]. |
| q02 | policy/refund-v4.pdf | Khách hàng có thể yêu cầu hoàn tiền trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng [1]. |
| q03 | it/access-control-sop.md | Để cấp quyền Level 3, cần có sự phê duyệt của Line Manager, IT Admin và IT Security [2]. |
| q04 | policy/refund-v4.pdf | Sản phẩm kỹ thuật số không được hoàn tiền, trừ khi có lỗi do nhà sản xuất và đáp ứng các điều kiện khác [1]. |
| q05 | policy/refund-v4.pdf, support/helpdesk-faq.md | Tài khoản bị khóa sau 5 lần đăng nhập sai liên tiếp. Để mở khóa, bạn cần liên hệ IT Helpdesk hoặc tự reset qua portal SSO [1]. |
| q06 | it/access-control-sop.md, support/sla-p1-2026.pdf | Escalation trong sự cố P1 diễn ra tự động lên Senior Engineer nếu không có phản hồi trong 10 phút. Ngoài ra, trong trường hợp khẩn cấp, On-c... |
| q07 | it/access-control-sop.md, policy/refund-v4.pdf | Tài liệu quy định quy trình cấp phép truy cập vào các hệ thống nội bộ của công ty là "Approval Matrix để cấp quyền hệ thống" [1]. |
| q08 | it/access-control-sop.md, hr/leave-policy-2026.pdf | Nhân viên được làm remote tối đa 2 ngày mỗi tuần sau khi đã qua probation period, và lịch remote phải được phê duyệt bởi Team Lead qua HR Po... |
| q09 | policy/refund-v4.pdf, support/sla-p1-2026.pdf | Tôi không biết. |
| q10 | it/access-control-sop.md, policy/refund-v4.pdf | Không có thông tin cụ thể nào trong bối cảnh về quy trình hoàn tiền khẩn cấp cho khách hàng VIP. Do đó, tôi không biết. |
