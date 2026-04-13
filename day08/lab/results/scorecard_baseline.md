# Scorecard — Baseline Dense
**Thời gian chạy:** 2026-04-13 16:57 

## RAGAS Metrics
| Metric | Score | Target | Status |
|---|---|---|---|---|
| Faithfulness | 0.84 | > 0.90 | ❌ |
| Relevance | 0.84 | > 0.85 | ❌ |
| Context Recall | 0.96 | > 0.80 | ✅ |
| Completeness | 0.66 | > 0.80 | ❌ |
| Abstain Accuracy | 0.00 | = 1.00 | ❌ |

## Per-question Results
| ID | Category | Expected | Got | Pass? |
|---|---|---|---|---|
| gq01 | SLA | Phiên bản hiện tại (v2026.1, có hiệu lực từ 2026-0... | SLA xử lý ticket P1 đã thay đổi như sau so với phi... | ✅ |
| gq02 | Cross-Document | Khi làm việc remote và truy cập hệ thống nội bộ, V... | Khi làm việc remote, bạn phải sử dụng VPN để kết n... | ✅ |
| gq03 | Refund | Không được hoàn tiền. Đơn hàng rơi vào hai ngoại l... | Đơn hàng mua trong chương trình Flash Sale không đ... | ✅ |
| gq04 | Refund | Khách hàng có thể chọn nhận store credit (credit n... | Nếu bạn chọn nhận store credit thay vì hoàn tiền, ... | ✅ |
| gq05 | Access Control | Có. Theo Access Control SOP, quy trình áp dụng cho... | Tôi không tìm thấy thông tin này trong tài liệu.... | ❌ |
| gq06 | Cross-Document | On-call IT Admin có thể cấp quyền tạm thời (tối đa... | Khi xảy ra sự cố P1 lúc 2 giờ sáng, quy trình cấp ... | ✅ |
| gq07 | Insufficient Context | Tài liệu hiện có không quy định mức phạt hay hình ... | Tôi không tìm thấy thông tin này trong tài liệu.... | ❌ |
| gq08 | HR Policy | Nghỉ phép năm cần báo trước ít nhất 3 ngày làm việ... | Nhân viên phải báo trước ít nhất 3 ngày làm việc đ... | ✅ |
| gq09 | IT Helpdesk | Có. Mật khẩu phải được thay đổi mỗi 90 ngày. Hệ th... | Có, mật khẩu tài khoản công ty cần được thay đổi đ... | ✅ |
| gq10 | Refund | Không. Chính sách hoàn tiền phiên bản 4 có hiệu lự... | Chính sách hoàn tiền hiện tại không áp dụng cho cá... | ✅ |
