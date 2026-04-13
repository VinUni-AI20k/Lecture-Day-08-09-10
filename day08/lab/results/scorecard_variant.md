# Scorecard — Variant Hybrid
**Thời gian chạy:** 2026-04-13 17:34 

## RAGAS Metrics
| Metric | Score | Target | Status |
|---|---|---|---|---|
| Faithfulness | 0.84 | > 0.90 | ❌ |
| Relevance | 0.84 | > 0.85 | ❌ |
| Context Recall | 0.96 | > 0.80 | ✅ |
| Completeness | 0.82 | > 0.80 | ✅ |
| Abstain Accuracy | 1.00 | = 1.00 | ✅ |

## Per-question Results
| ID | Category | Expected | Got | Pass? |
|---|---|---|---|---|
| q01 | SLA | Ticket P1 có SLA phản hồi ban đầu 15 phút và thời ... | SLA xử lý ticket P1 bao gồm các thời gian như sau:... | ✅ |
| q02 | Refund | Khách hàng có thể yêu cầu hoàn tiền trong vòng 7 n... | Khách hàng có thể yêu cầu hoàn tiền trong vòng 7 n... | ✅ |
| q03 | Access Control | Level 3 (Elevated Access) cần phê duyệt từ Line Ma... | Để cấp quyền Level 3 (Elevated Access), yêu cầu ph... | ✅ |
| q04 | Refund | Không. Theo chính sách hoàn tiền, sản phẩm thuộc d... | Sản phẩm thuộc danh mục hàng kỹ thuật số (như lice... | ✅ |
| q05 | IT Helpdesk | Tài khoản bị khóa sau 5 lần đăng nhập sai liên tiế... | Tài khoản bị khóa sau 5 lần đăng nhập sai liên tiế... | ✅ |
| q06 | SLA | Ticket P1 tự động escalate lên Senior Engineer nếu... | Escalation trong sự cố P1 diễn ra theo quy trình s... | ✅ |
| q07 | Access Control | Tài liệu 'Approval Matrix for System Access' hiện ... | Approval Matrix để cấp quyền hệ thống là tài liệu ... | ✅ |
| q08 | HR Policy | Nhân viên sau probation period có thể làm remote t... | Nhân viên sau probation period có thể làm remote t... | ✅ |
| q09 | Insufficient Context | Không tìm thấy thông tin về ERR-403-AUTH trong tài... | Tôi không tìm thấy thông tin này trong tài liệu.... | ❌ |
| q10 | Refund | Tài liệu chính sách hoàn tiền không đề cập đến quy... | Tôi không tìm thấy thông tin này trong tài liệu.... | ❌ |
