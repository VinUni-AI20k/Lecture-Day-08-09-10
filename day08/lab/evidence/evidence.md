# RAG Evaluation Evidence
Generated: 2026-04-13 18:14

## BASELINE — baseline_dense

### q01 — SLA xử lý ticket P1 là bao lâu?

**Expected:** Ticket P1 có SLA phản hồi ban đầu 15 phút và thời gian xử lý (resolution) là 4 giờ.

**Answer:** Theo support/sla-p1-2026.pdf, SLA xử lý ticket P1 bao gồm phản hồi ban đầu trong vòng 15 phút kể từ khi ticket được tạo và thời gian xử lý và khắc phục là 4 giờ. Nếu không có phản hồi trong 10 phút, ticket sẽ tự động được escalate lên Senior Engineer.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q02 — Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?

**Expected:** Khách hàng có thể yêu cầu hoàn tiền trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.

**Answer:** Khách hàng có thể yêu cầu hoàn tiền trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng, theo quy định trong tài liệu "policy/refund-v4.pdf".

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q03 — Ai phải phê duyệt để cấp quyền Level 3?

**Expected:** Level 3 (Elevated Access) cần phê duyệt từ Line Manager, IT Admin, và IT Security.

**Answer:** Để cấp quyền Level 3 — Elevated Access, cần có sự phê duyệt của Line Manager, IT Admin và IT Security. Thời gian xử lý cho cấp quyền này là 3 ngày làm việc. Theo it/access-control-sop.md, quy trình này là một phần của quy trình cấp phép truy cập vào các hệ thống nội bộ của công ty.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q04 — Sản phẩm kỹ thuật số có được hoàn tiền không?

**Expected:** Không. Theo chính sách hoàn tiền, sản phẩm thuộc danh mục hàng kỹ thuật số (license key, subscription) là ngoại lệ không được hoàn tiền.

**Answer:** Theo policy/refund-v4.pdf, sản phẩm thuộc danh mục hàng kỹ thuật số (license key, subscription) không được hoàn tiền. Do đó, khách hàng không thể yêu cầu hoàn tiền cho các sản phẩm này.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q05 — Tài khoản bị khóa sau bao nhiêu lần đăng nhập sai?

**Expected:** Tài khoản bị khóa sau 5 lần đăng nhập sai liên tiếp.

**Answer:** Tài khoản bị khóa sau 5 lần đăng nhập sai liên tiếp. Để mở khóa, bạn có thể liên hệ IT Helpdesk hoặc tự reset qua portal SSO. Theo support/helpdesk-faq.md, thông tin này được nêu rõ.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q06 — Escalation trong sự cố P1 diễn ra như thế nào?

**Expected:** Ticket P1 tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút sau khi tạo ticket.

**Answer:** Trong sự cố P1, quy trình escalation diễn ra tự động khi không có phản hồi trong 10 phút kể từ khi ticket được tạo. Ticket sẽ được tự động escalate lên Senior Engineer để đảm bảo sự cố được xử lý kịp thời (Theo support/sla-p1-2026.pdf).

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q07 — Approval Matrix để cấp quyền hệ thống là tài liệu nào?

**Expected:** Tài liệu 'Approval Matrix for System Access' hiện tại có tên mới là 'Access Control SOP' (access-control-sop.md).

**Answer:** Tài liệu quy định Approval Matrix để cấp quyền hệ thống là "it/access-control-sop.md". Tài liệu này mô tả các cấp độ quyền truy cập và quy trình phê duyệt tương ứng cho từng cấp độ.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q08 — Nhân viên được làm remote tối đa mấy ngày mỗi tuần?

**Expected:** Nhân viên sau probation period có thể làm remote tối đa 2 ngày/tuần, với điều kiện được Team Lead phê duyệt.

**Answer:** Nhân viên sau probation period có thể làm remote tối đa 2 ngày/tuần. Tuy nhiên, lịch remote phải được Team Lead phê duyệt qua HR Portal. Ngày onsite bắt buộc là Thứ 3 và Thứ 5 theo lịch team. (Theo hr/leave-policy-2026.pdf)

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q09 — ERR-403-AUTH là lỗi gì và cách xử lý?

**Expected:** Không tìm thấy thông tin về ERR-403-AUTH trong tài liệu hiện có. Đây có thể là lỗi liên quan đến xác thực (authentication), hãy liên hệ IT Helpdesk.

**Answer:** Tài liệu không đề cập đến lỗi ERR-403-AUTH và cách xử lý của nó. Bạn có thể liên hệ với IT Helpdesk qua số máy nội bộ 9000 để được hỗ trợ thêm.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | None/5 | No expected sources defined |
| Completeness   | None/5 | judge_error |

---

### q10 — Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?

**Expected:** Tài liệu chính sách hoàn tiền không đề cập đến quy trình đặc biệt cho khách hàng VIP. Theo chính sách hiện hành, tất cả yêu cầu hoàn tiền đều theo cùng quy trình tiêu chuẩn trong 3-5 ngày làm việc.

**Answer:** Tài liệu không đề cập đến quy trình hoàn tiền khẩn cấp cho khách hàng VIP. Để biết thêm thông tin chi tiết, bạn có thể liên hệ với bộ phận hỗ trợ khách hàng hoặc Finance Team.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq01 — SLA xử lý ticket P1 đã thay đổi như thế nào so với phiên bản trước?

**Expected:** Phiên bản hiện tại (v2026.1, có hiệu lực từ 2026-01-15) đã cập nhật SLA P1 resolution từ 6 giờ xuống còn 4 giờ. Phiên bản trước (v2025.3) không thay đổi SLA này.

**Answer:** Theo support/sla-p1-2026.pdf, SLA xử lý ticket P1 đã được cập nhật từ 6 giờ xuống 4 giờ cho thời gian khắc phục (resolution). Ngoài ra, quy trình escalation tự động cũng đã được thêm vào trong phiên bản này.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq02 — Khi làm việc remote, tôi phải dùng VPN và được kết nối trên tối đa bao nhiêu thiết bị?

**Expected:** Khi làm việc remote và truy cập hệ thống nội bộ, VPN là bắt buộc (theo HR Leave Policy). Phần mềm VPN là Cisco AnyConnect và mỗi tài khoản được kết nối VPN trên tối đa 2 thiết bị cùng lúc (theo IT Helpdesk FAQ).

**Answer:** Khi làm việc remote, bạn phải sử dụng VPN và mỗi tài khoản được kết nối trên tối đa 2 thiết bị cùng lúc. Điều này được quy định trong chính sách làm việc từ xa của công ty. Theo hr/leave-policy-2026.pdf và support/helpdesk-faq.md.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 2/2 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq03 — Đơn hàng mua trong chương trình Flash Sale và đã kích hoạt sản phẩm có được hoàn tiền không?

**Expected:** Không được hoàn tiền. Đơn hàng rơi vào hai ngoại lệ cùng lúc: (1) đơn hàng áp dụng mã giảm giá chương trình Flash Sale và (2) sản phẩm đã được kích hoạt — cả hai đều thuộc danh sách ngoại lệ không được hoàn tiền theo Điều 3 của chính sách.

**Answer:** Theo refund-v4.pdf, đơn hàng đã áp dụng mã giảm giá đặc biệt theo chương trình khuyến mãi Flash Sale và sản phẩm đã được kích hoạt hoặc đăng ký tài khoản sẽ không được hoàn tiền.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq04 — Nếu chọn nhận store credit thay vì hoàn tiền, tôi được bao nhiêu phần trăm so với số tiền gốc?

**Expected:** Khách hàng có thể chọn nhận store credit (credit nội bộ) thay thế với giá trị 110% so với số tiền hoàn gốc. Đây là tùy chọn, không phải bắt buộc.

**Answer:** Nếu bạn chọn nhận store credit thay vì hoàn tiền, bạn sẽ nhận được giá trị 110% so với số tiền gốc. Theo tài liệu "policy/refund-v4.pdf", điều này áp dụng trong 100% trường hợp đủ điều kiện.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq05 — Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?

**Expected:** Có. Theo Access Control SOP, quy trình áp dụng cho tất cả nhân viên, contractor và third-party vendor. Admin Access (Level 4) cần phê duyệt từ IT Manager và CISO, thời gian xử lý 5 ngày làm việc, và có yêu cầu thêm: training bắt buộc về security policy.

**Answer:** Theo it/access-control-sop.md, contractor từ bên ngoài công ty không được đề cập cụ thể về việc cấp quyền Admin Access. Tài liệu chỉ nêu rõ quyền Admin Access áp dụng cho DevOps, SRE, và IT Admin. Do đó, bạn nên liên hệ với IT Helpdesk để biết thêm thông tin chi tiết về trường hợp này.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq06 — Lúc 2 giờ sáng xảy ra sự cố P1, on-call engineer cần cấp quyền tạm thời cho một engineer xử lý incident. Quy trình cụ thể như thế nào và quyền này tồn tại bao lâu?

**Expected:** On-call IT Admin có thể cấp quyền tạm thời (tối đa 24 giờ) sau khi được Tech Lead phê duyệt bằng lời. Sau 24 giờ, phải có ticket chính thức hoặc quyền bị thu hồi tự động. Mọi quyền tạm thời phải được ghi log vào hệ thống Security Audit. Liên hệ on-call qua hotline ext. 9999 (24/7) theo SLA P1.

**Answer:** Theo it/access-control-sop.md, trong trường hợp khẩn cấp P1, on-call IT Admin có thể cấp quyền tạm thời cho engineer sau khi được Tech Lead phê duyệt bằng lời. Quyền này chỉ tồn tại tối đa 24 giờ, sau đó phải có ticket chính thức hoặc quyền sẽ bị thu hồi tự động.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 2/2 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq07 — Công ty sẽ phạt bao nhiêu nếu team IT vi phạm cam kết SLA P1?

**Expected:** Tài liệu hiện có không quy định mức phạt hay hình thức xử lý khi vi phạm SLA P1. Tài liệu sla-p1-2026.pdf chỉ mô tả quy trình xử lý và SLA target, không có điều khoản về penalty.

**Answer:** Tài liệu không đề cập đến mức phạt cụ thể nếu team IT vi phạm cam kết SLA P1. Để biết thêm thông tin chi tiết về vấn đề này, bạn có thể liên hệ với bộ phận IT Helpdesk.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | None/5 | No expected sources defined |
| Completeness   | None/5 | judge_error |

---

### gq08 — Nhân viên phải báo trước bao nhiêu ngày để xin nghỉ phép năm? Con số này có giống với số ngày cần giấy tờ khi nghỉ ốm không?

**Expected:** Nghỉ phép năm cần báo trước ít nhất 3 ngày làm việc qua HR Portal. Nghỉ ốm cũng liên quan đến mốc 3 ngày: nếu nghỉ TRÊN 3 ngày liên tiếp thì cần giấy tờ y tế từ bệnh viện. Hai con số '3 ngày' này áp dụng cho hai tình huống khác nhau.

**Answer:** Nhân viên phải gửi yêu cầu nghỉ phép năm qua hệ thống HR Portal ít nhất 3 ngày làm việc trước ngày nghỉ (Theo hr/leave-policy-2026.pdf). Trong khi đó, khi nghỉ ốm trên 3 ngày liên tiếp, nhân viên cần có giấy tờ y tế từ bệnh viện, nhưng không có yêu cầu cụ thể về số ngày báo trước (Theo hr/leave-policy-2026.pdf). Do đó, con số này không giống nhau.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq09 — Mật khẩu tài khoản công ty cần đổi định kỳ không? Nếu có, hệ thống sẽ nhắc nhở trước bao nhiêu ngày và đổi qua đâu?

**Expected:** Có. Mật khẩu phải được thay đổi mỗi 90 ngày. Hệ thống sẽ nhắc nhở 7 ngày trước khi hết hạn. Để đổi mật khẩu, truy cập https://sso.company.internal/reset hoặc liên hệ Helpdesk qua ext. 9000.

**Answer:** Có, mật khẩu tài khoản công ty cần được thay đổi định kỳ mỗi 90 ngày. Hệ thống sẽ nhắc nhở 7 ngày trước khi mật khẩu hết hạn và người dùng có thể đổi mật khẩu qua portal SSO. Theo support/helpdesk-faq.md, thông tin này được nêu rõ.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq10 — Chính sách hoàn tiền hiện tại áp dụng cho đơn hàng đặt trước ngày 01/02/2026 không?

**Expected:** Không. Chính sách hoàn tiền phiên bản 4 có hiệu lực từ ngày 01/02/2026 và chỉ áp dụng cho các đơn hàng được đặt kể từ ngày đó. Các đơn hàng đặt trước ngày này sẽ áp dụng theo chính sách hoàn tiền phiên bản 3.

**Answer:** Theo policy/refund-v4.pdf, các đơn hàng đặt trước ngày 01/02/2026 sẽ áp dụng theo chính sách hoàn tiền phiên bản 3. Do đó, chính sách hoàn tiền hiện tại không áp dụng cho các đơn hàng này.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### 📊 BASELINE — baseline_dense — Summary

| Metric | Average | Câu |
|--------|:-------:|:---:|
| Faithfulness | N/A | 0 |
| Relevance | N/A | 0 |
| Context Recall | 5.00/5 | 18 |
| Completeness | N/A | 0 |

> **Total: 90/90 (100.0%)**

## VARIANT  — variant_hybrid

### q01 — SLA xử lý ticket P1 là bao lâu?

**Expected:** Ticket P1 có SLA phản hồi ban đầu 15 phút và thời gian xử lý (resolution) là 4 giờ.

**Answer:** Theo support/sla-p1-2026.pdf, SLA xử lý và khắc phục ticket P1 là 4 giờ. Phản hồi ban đầu phải được thực hiện trong vòng 15 phút kể từ khi ticket được tạo.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q02 — Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?

**Expected:** Khách hàng có thể yêu cầu hoàn tiền trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.

**Answer:** Khách hàng có thể yêu cầu hoàn tiền trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng, theo quy định trong tài liệu "policy/refund-v4.pdf".

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q03 — Ai phải phê duyệt để cấp quyền Level 3?

**Expected:** Level 3 (Elevated Access) cần phê duyệt từ Line Manager, IT Admin, và IT Security.

**Answer:** Để cấp quyền Level 3 — Elevated Access, yêu cầu phải được phê duyệt bởi Line Manager, IT Admin và IT Security. Thời gian xử lý cho cấp quyền này là 3 ngày làm việc. Theo it/access-control-sop.md, quy trình này áp dụng cho Team Lead, Senior Engineer và Manager.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q04 — Sản phẩm kỹ thuật số có được hoàn tiền không?

**Expected:** Không. Theo chính sách hoàn tiền, sản phẩm thuộc danh mục hàng kỹ thuật số (license key, subscription) là ngoại lệ không được hoàn tiền.

**Answer:** Theo policy/refund-v4.pdf, sản phẩm thuộc danh mục hàng kỹ thuật số (license key, subscription) không được hoàn tiền. Do đó, khách hàng không thể yêu cầu hoàn tiền cho các sản phẩm này.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q05 — Tài khoản bị khóa sau bao nhiêu lần đăng nhập sai?

**Expected:** Tài khoản bị khóa sau 5 lần đăng nhập sai liên tiếp.

**Answer:** Tài khoản bị khóa sau 5 lần đăng nhập sai liên tiếp. Để mở khóa, bạn có thể liên hệ IT Helpdesk hoặc tự reset qua portal SSO. Theo support/helpdesk-faq.md, đây là quy trình cần thực hiện.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q06 — Escalation trong sự cố P1 diễn ra như thế nào?

**Expected:** Ticket P1 tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút sau khi tạo ticket.

**Answer:** Theo support/sla-p1-2026.pdf, trong sự cố P1, quy trình escalation tự động diễn ra nếu không có phản hồi trong 10 phút. On-call engineer sẽ nhận alert hoặc ticket, xác nhận severity trong 5 phút và gửi thông báo tới Slack #incident-p1 và email incident@company.internal ngay lập tức. Nếu cần hỗ trợ thêm, engineer có thể escalate ngay trong quá trình xử lý.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q07 — Approval Matrix để cấp quyền hệ thống là tài liệu nào?

**Expected:** Tài liệu 'Approval Matrix for System Access' hiện tại có tên mới là 'Access Control SOP' (access-control-sop.md).

**Answer:** Tài liệu quy định quy trình cấp phép truy cập vào các hệ thống nội bộ của công ty không đề cập cụ thể đến Approval Matrix. Bạn có thể liên hệ với IT Helpdesk để biết thêm thông tin chi tiết về quy trình phê duyệt này. Theo it/access-control-sop.md, quy trình cấp quyền bao gồm việc tạo Access Request ticket và phê duyệt từ Line Manager.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q08 — Nhân viên được làm remote tối đa mấy ngày mỗi tuần?

**Expected:** Nhân viên sau probation period có thể làm remote tối đa 2 ngày/tuần, với điều kiện được Team Lead phê duyệt.

**Answer:** Nhân viên sau probation period có thể làm remote tối đa 2 ngày/tuần. Tuy nhiên, lịch remote phải được Team Lead phê duyệt qua HR Portal. Ngày onsite bắt buộc là Thứ 3 và Thứ 5 theo lịch team. (Theo hr/leave-policy-2026.pdf)

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### q09 — ERR-403-AUTH là lỗi gì và cách xử lý?

**Expected:** Không tìm thấy thông tin về ERR-403-AUTH trong tài liệu hiện có. Đây có thể là lỗi liên quan đến xác thực (authentication), hãy liên hệ IT Helpdesk.

**Answer:** Tài liệu không đề cập đến lỗi ERR-403-AUTH và cách xử lý. Bạn có thể liên hệ với IT Helpdesk qua số máy nội bộ 9000 để được hỗ trợ thêm.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | None/5 | No expected sources defined |
| Completeness   | None/5 | judge_error |

---

### q10 — Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?

**Expected:** Tài liệu chính sách hoàn tiền không đề cập đến quy trình đặc biệt cho khách hàng VIP. Theo chính sách hiện hành, tất cả yêu cầu hoàn tiền đều theo cùng quy trình tiêu chuẩn trong 3-5 ngày làm việc.

**Answer:** Tài liệu không đề cập đến quy trình hoàn tiền khẩn cấp cho khách hàng VIP. Để biết thêm thông tin chi tiết, bạn có thể liên hệ với bộ phận CS Agent hoặc Finance Team để được hỗ trợ. Theo policy/refund-v4.pdf, quy trình hoàn tiền thông thường yêu cầu khách hàng gửi yêu cầu qua hệ thống ticket nội bộ.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq01 — SLA xử lý ticket P1 đã thay đổi như thế nào so với phiên bản trước?

**Expected:** Phiên bản hiện tại (v2026.1, có hiệu lực từ 2026-01-15) đã cập nhật SLA P1 resolution từ 6 giờ xuống còn 4 giờ. Phiên bản trước (v2025.3) không thay đổi SLA này.

**Answer:** Theo support/sla-p1-2026.pdf, SLA xử lý ticket P1 đã được cập nhật từ 6 giờ xuống 4 giờ trong phiên bản v2026.1 (2026-01-15). Ngoài ra, quy trình escalation tự động cũng được thêm vào trong phiên bản v2025.3 (2025-09-01).

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq02 — Khi làm việc remote, tôi phải dùng VPN và được kết nối trên tối đa bao nhiêu thiết bị?

**Expected:** Khi làm việc remote và truy cập hệ thống nội bộ, VPN là bắt buộc (theo HR Leave Policy). Phần mềm VPN là Cisco AnyConnect và mỗi tài khoản được kết nối VPN trên tối đa 2 thiết bị cùng lúc (theo IT Helpdesk FAQ).

**Answer:** Khi làm việc remote, bạn phải sử dụng VPN và mỗi tài khoản được kết nối trên tối đa 2 thiết bị cùng lúc. Điều này được quy định trong chính sách làm việc từ xa của công ty. Theo hr/leave-policy-2026.pdf và support/helpdesk-faq.md.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 2/2 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq03 — Đơn hàng mua trong chương trình Flash Sale và đã kích hoạt sản phẩm có được hoàn tiền không?

**Expected:** Không được hoàn tiền. Đơn hàng rơi vào hai ngoại lệ cùng lúc: (1) đơn hàng áp dụng mã giảm giá chương trình Flash Sale và (2) sản phẩm đã được kích hoạt — cả hai đều thuộc danh sách ngoại lệ không được hoàn tiền theo Điều 3 của chính sách.

**Answer:** Theo refund-v4.pdf, đơn hàng đã áp dụng mã giảm giá đặc biệt theo chương trình khuyến mãi Flash Sale và sản phẩm đã được kích hoạt sẽ không được hoàn tiền.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq04 — Nếu chọn nhận store credit thay vì hoàn tiền, tôi được bao nhiêu phần trăm so với số tiền gốc?

**Expected:** Khách hàng có thể chọn nhận store credit (credit nội bộ) thay thế với giá trị 110% so với số tiền hoàn gốc. Đây là tùy chọn, không phải bắt buộc.

**Answer:** Nếu bạn chọn nhận store credit thay vì hoàn tiền, bạn sẽ nhận được giá trị 110% so với số tiền gốc. Theo tài liệu "policy/refund-v4.pdf", điều này áp dụng trong 100% trường hợp đủ điều kiện.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq05 — Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?

**Expected:** Có. Theo Access Control SOP, quy trình áp dụng cho tất cả nhân viên, contractor và third-party vendor. Admin Access (Level 4) cần phê duyệt từ IT Manager và CISO, thời gian xử lý 5 ngày làm việc, và có yêu cầu thêm: training bắt buộc về security policy.

**Answer:** Theo it/access-control-sop.md, contractor từ bên ngoài công ty có thể được cấp quyền Admin Access. Thời gian xử lý là 5 ngày làm việc và yêu cầu đặc biệt là phải hoàn thành training bắt buộc về security policy.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq06 — Lúc 2 giờ sáng xảy ra sự cố P1, on-call engineer cần cấp quyền tạm thời cho một engineer xử lý incident. Quy trình cụ thể như thế nào và quyền này tồn tại bao lâu?

**Expected:** On-call IT Admin có thể cấp quyền tạm thời (tối đa 24 giờ) sau khi được Tech Lead phê duyệt bằng lời. Sau 24 giờ, phải có ticket chính thức hoặc quyền bị thu hồi tự động. Mọi quyền tạm thời phải được ghi log vào hệ thống Security Audit. Liên hệ on-call qua hotline ext. 9999 (24/7) theo SLA P1.

**Answer:** Theo it/access-control-sop.md, trong trường hợp khẩn cấp như sự cố P1, on-call IT Admin có thể cấp quyền tạm thời cho engineer sau khi được Tech Lead phê duyệt bằng lời. Quyền này chỉ tồn tại tối đa 24 giờ, sau đó phải có ticket chính thức hoặc quyền sẽ bị thu hồi tự động.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 2/2 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq07 — Công ty sẽ phạt bao nhiêu nếu team IT vi phạm cam kết SLA P1?

**Expected:** Tài liệu hiện có không quy định mức phạt hay hình thức xử lý khi vi phạm SLA P1. Tài liệu sla-p1-2026.pdf chỉ mô tả quy trình xử lý và SLA target, không có điều khoản về penalty.

**Answer:** Tài liệu không đề cập đến việc công ty sẽ phạt bao nhiêu nếu team IT vi phạm cam kết SLA P1. Để biết thêm thông tin chi tiết, bạn có thể liên hệ với bộ phận quản lý hoặc IT Helpdesk.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | None/5 | No expected sources defined |
| Completeness   | None/5 | judge_error |

---

### gq08 — Nhân viên phải báo trước bao nhiêu ngày để xin nghỉ phép năm? Con số này có giống với số ngày cần giấy tờ khi nghỉ ốm không?

**Expected:** Nghỉ phép năm cần báo trước ít nhất 3 ngày làm việc qua HR Portal. Nghỉ ốm cũng liên quan đến mốc 3 ngày: nếu nghỉ TRÊN 3 ngày liên tiếp thì cần giấy tờ y tế từ bệnh viện. Hai con số '3 ngày' này áp dụng cho hai tình huống khác nhau.

**Answer:** Nhân viên phải gửi yêu cầu nghỉ phép năm qua hệ thống HR Portal ít nhất 3 ngày làm việc trước ngày nghỉ (Theo hr/leave-policy-2026.pdf). Trong khi đó, khi nghỉ ốm trên 3 ngày liên tiếp, nhân viên cần có giấy tờ y tế từ bệnh viện, không có số ngày cụ thể được đề cập (Theo hr/leave-policy-2026.pdf). Do đó, con số này không giống nhau.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq09 — Mật khẩu tài khoản công ty cần đổi định kỳ không? Nếu có, hệ thống sẽ nhắc nhở trước bao nhiêu ngày và đổi qua đâu?

**Expected:** Có. Mật khẩu phải được thay đổi mỗi 90 ngày. Hệ thống sẽ nhắc nhở 7 ngày trước khi hết hạn. Để đổi mật khẩu, truy cập https://sso.company.internal/reset hoặc liên hệ Helpdesk qua ext. 9000.

**Answer:** Có, mật khẩu tài khoản công ty cần được thay đổi định kỳ mỗi 90 ngày. Hệ thống sẽ nhắc nhở 7 ngày trước khi mật khẩu hết hạn và người dùng có thể đổi mật khẩu qua portal SSO. Theo support/helpdesk-faq.md, thông tin này được quy định rõ ràng.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### gq10 — Chính sách hoàn tiền hiện tại áp dụng cho đơn hàng đặt trước ngày 01/02/2026 không?

**Expected:** Không. Chính sách hoàn tiền phiên bản 4 có hiệu lực từ ngày 01/02/2026 và chỉ áp dụng cho các đơn hàng được đặt kể từ ngày đó. Các đơn hàng đặt trước ngày này sẽ áp dụng theo chính sách hoàn tiền phiên bản 3.

**Answer:** Chính sách hoàn tiền hiện tại không áp dụng cho các đơn hàng đặt trước ngày 01/02/2026, mà sẽ áp dụng theo chính sách hoàn tiền phiên bản 3. Theo tài liệu "policy/refund-v4.pdf", chính sách này chỉ có hiệu lực cho các đơn hàng được đặt từ ngày 01/02/2026 trở đi.

| Metric | Score | Notes |
|--------|:-----:|-------|
| Faithfulness   | None/5 | judge_error |
| Relevance      | None/5 | judge_error |
| Context Recall | 5/5 | Retrieved 1/1 expected sources |
| Completeness   | None/5 | judge_error |

---

### 📊 VARIANT  — variant_hybrid — Summary

| Metric | Average | Câu |
|--------|:-------:|:---:|
| Faithfulness | N/A | 0 |
| Relevance | N/A | 0 |
| Context Recall | 5.00/5 | 18 |
| Completeness | N/A | 0 |

> **Total: 90/90 (100.0%)**

## 🏆 Grand Total (cả 2 bộ)

> **180/180 (100.0%)**
