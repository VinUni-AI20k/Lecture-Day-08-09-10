# New Test Questions — RAG Pipeline (Day 08 Lab)

> 10 câu hỏi mới, dựa hoàn toàn trên nội dung 5 tài liệu trong `data/docs/`.  
> Mỗi câu ghi rõ: nguồn, độ khó, mục tiêu kiểm tra, expected answer.

---

## Q11 — Overtime cuối tuần được tính lương thế nào?

| Trường | Giá trị |
|--------|---------|
| **Source** | `hr/leave-policy-2026.pdf` — Phần 3 |
| **Difficulty** | easy |
| **Test target** | retrieval + factual answer |

**Expected answer:**  
Làm thêm giờ vào ngày cuối tuần được tính với hệ số **200%** lương giờ tiêu chuẩn. Ngày lễ là 300%, ngày thường là 150%. Yêu cầu: phải được Line Manager phê duyệt trước bằng văn bản.

---

## Q12 — Nhân viên mới vào có được cấp laptop ngay không?

| Trường | Giá trị |
|--------|---------|
| **Source** | `support/helpdesk-faq.md` — Section 4 |
| **Difficulty** | easy |
| **Test target** | factual retrieval từ FAQ |

**Expected answer:**  
Có. Laptop được cấp trong ngày onboarding đầu tiên. Nếu có vấn đề, liên hệ HR hoặc IT Admin.

---

## Q13 — Level 4 Access khác Level 3 Access ở điểm nào?

| Trường | Giá trị |
|--------|---------|
| **Source** | `it/access-control-sop.md` — Section 2 |
| **Difficulty** | medium |
| **Test target** | comparison / same-or-different — kiểm tra citation hai snippet |

**Expected answer:**  
Level 3 (Elevated Access) áp dụng cho Team Lead, Senior Engineer, Manager; cần phê duyệt từ Line Manager + IT Admin + IT Security; xử lý trong 3 ngày làm việc.  
Level 4 (Admin Access) áp dụng cho DevOps, SRE, IT Admin; cần phê duyệt từ IT Manager + CISO; xử lý trong 5 ngày làm việc và **bắt buộc training security policy** — điều Level 3 không yêu cầu.

---

## Q14 — Khi nhân viên nghỉ ốm hơn 3 ngày liên tiếp cần làm gì?

| Trường | Giá trị |
|--------|---------|
| **Source** | `hr/leave-policy-2026.pdf` — Phần 1.2 |
| **Difficulty** | easy |
| **Test target** | điều kiện cụ thể trong chính sách |

**Expected answer:**  
Nếu nghỉ ốm trên 3 ngày liên tiếp, nhân viên cần cung cấp **giấy tờ y tế từ bệnh viện**. Ngoài ra phải thông báo cho Line Manager trước 9:00 sáng ngày nghỉ đầu tiên.

---

## Q15 — Ticket P2 có SLA phản hồi và xử lý là bao lâu?

| Trường | Giá trị |
|--------|---------|
| **Source** | `support/sla-p1-2026.pdf` — Phần 2 |
| **Difficulty** | medium |
| **Test target** | retrieval multi-level — phân biệt P1 vs P2 |

**Expected answer:**  
Ticket P2 (HIGH): phản hồi ban đầu **2 giờ**, xử lý và khắc phục **1 ngày làm việc**, escalation tự động sau **90 phút** không có phản hồi. (Khác P1: first response 15 phút, resolution 4 giờ, escalation sau 10 phút.)

---

## Q16 — Đơn hàng dùng mã Flash Sale có được hoàn tiền không?

| Trường | Giá trị |
|--------|---------|
| **Source** | `policy/refund-v4.pdf` — Điều 3 |
| **Difficulty** | medium |
| **Test target** | ngoại lệ chính sách — kiểm tra model không bỏ sót điều khoản ẩn |

**Expected answer:**  
Không. Đơn hàng đã áp dụng **mã giảm giá đặc biệt theo chương trình Flash Sale** là một trong các ngoại lệ không được hoàn tiền, theo Điều 3 chính sách hoàn tiền v4.

---

## Q17 — Quyền truy cập bị thu hồi như thế nào khi nhân viên chuyển bộ phận?

| Trường | Giá trị |
|--------|---------|
| **Source** | `it/access-control-sop.md` — Section 5 |
| **Difficulty** | medium |
| **Test target** | retrieval điều kiện thu hồi — phân biệt 3 tình huống |

**Expected answer:**  
Khi nhân viên chuyển bộ phận, quyền truy cập sẽ được **điều chỉnh trong 3 ngày làm việc**. Các trường hợp khác: nghỉ việc → thu hồi ngay trong ngày cuối; hết hạn contract → thu hồi đúng ngày hết hạn.

---

## Q18 — Muốn đặt mật khẩu mới, nhân viên cần làm gì?

| Trường | Giá trị |
|--------|---------|
| **Source** | `support/helpdesk-faq.md` — Section 1 |
| **Difficulty** | easy |
| **Test target** | FAQ retrieval + thông tin URL/ext cụ thể |

**Expected answer:**  
Truy cập `https://sso.company.internal/reset` hoặc liên hệ IT Helpdesk qua **ext. 9000**. Mật khẩu mới sẽ được gửi qua email công ty trong vòng **5 phút**. Lưu ý: mật khẩu phải được đổi định kỳ mỗi **90 ngày**; hệ thống nhắc trước 7 ngày khi sắp hết hạn.

---

## Q19 — Khi yêu cầu hoàn tiền được phê duyệt, khách hàng nhận tiền qua hình thức nào?

| Trường | Giá trị |
|--------|---------|
| **Source** | `policy/refund-v4.pdf` — Điều 5 |
| **Difficulty** | medium |
| **Test target** | multi-option answer — kiểm tra citation cả hai hình thức |

**Expected answer:**  
Có hai hình thức: (1) **Hoàn tiền qua phương thức thanh toán gốc** — áp dụng 100% trường hợp đủ điều kiện; (2) **Store credit nội bộ** — khách hàng có thể chọn nhận với giá trị **110%** so với số tiền hoàn gốc. Finance Team xử lý trong 3–5 ngày làm việc.

---

## Q20 — Nhân viên có bao nhiêu ngày phép năm nếu đã làm việc được 4 năm?

| Trường | Giá trị |
|--------|---------|
| **Source** | `hr/leave-policy-2026.pdf` — Phần 1.1 |
| **Difficulty** | medium |
| **Test target** | retrieval điều kiện dải số — kiểm tra model chọn đúng bracket (3–5 năm) |

**Expected answer:**  
Nhân viên từ **3 đến 5 năm kinh nghiệm** được **15 ngày phép năm**. Ngoài ra tối đa **5 ngày phép chưa dùng** có thể được chuyển sang năm tiếp theo. (Dưới 3 năm: 12 ngày; trên 5 năm: 18 ngày.)

---

## Tổng quan

| ID | Nguồn | Độ khó | Mục tiêu kiểm tra |
|----|-------|--------|-------------------|
| Q11 | hr/leave-policy | easy | overtime rate retrieval |
| Q12 | helpdesk-faq | easy | onboarding FAQ |
| Q13 | access-control-sop | medium | comparison Level 3 vs 4 |
| Q14 | hr/leave-policy | easy | sick leave condition |
| Q15 | sla-p1-2026 | medium | P2 SLA + phân biệt P1/P2 |
| Q16 | policy/refund-v4 | medium | Flash Sale exception |
| Q17 | access-control-sop | medium | access revocation 3 cases |
| Q18 | helpdesk-faq | easy | password reset FAQ |
| Q19 | policy/refund-v4 | medium | dual refund options |
| Q20 | hr/leave-policy | medium | leave days bracket lookup |
