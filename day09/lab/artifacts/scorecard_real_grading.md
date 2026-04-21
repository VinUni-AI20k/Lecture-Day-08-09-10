# Day 09 Scorecard — Real Grading Questions

Generated: 2026-04-14 17:14

## Summary

| Metric         | Score |
|----------------|-------|
| Faithfulness   | 4.4/5 |
| Relevance      | 5.0/5 |
| Criteria Score | 3.9/5 |

## Per-Question Results

| ID   | Pts | F | R | Crit | Met | Route              | Conf | Criteria Notes                                                                   |
|------|-----|---|---|------|-----|--------------------|------|----------------------------------------------------------------------------------|
| gq01 | 10  | 5 | 5 | 3    | 2/3 | retrieval_worker   | 0.75 | ✓ Kênh thông báo; ✓ Deadline escalation; ✗ Đối tượng escalation                  |
| gq02 | 10  | 5 | 5 | 2    | 1/3 | policy_tool_worker | 0.88 | ✗ Nhận ra rằng đơn đặt trước 01/02/2026 áp; ✗ Nêu rõ rằng tài liệu hiện có chỉ c |
| gq03 | 10  | 5 | 5 | 5    | 3/3 | policy_tool_worker | 0.83 | ✓ Nêu đúng số người phê duyệt; ✓ Nêu đúng tên 3 người; ✓ Nêu đúng người cuối cùn |
| gq04 | 6   | 5 | 5 | 3    | 1/2 | policy_tool_worker | 0.84 | ✓ Nêu đúng con số: 110%; ✗ Giải thích đúng: thêm 10% bonus so với h              |
| gq05 | 8   | 5 | 5 | 5    | 3/3 | retrieval_worker   | 0.82 | ✓ Nêu đúng hành động: tự động escalate; ✓ Nêu đúng đối tượng: Senior Engineer; ✓ |
| gq06 | 8   | 5 | 5 | 5    | 3/3 | retrieval_worker   | 0.74 | ✓ Kết luận đúng: nhân viên trong probation; ✓ Nêu điều kiện đúng: phải qua proba |
| gq07 | 10  | 5 | 5 | 5    | 3/3 | retrieval_worker   | 0.30 | Correct abstain — no penalty number invented                                     |
| gq08 | 8   | 5 | 5 | 5    | 3/3 | retrieval_worker   | 0.82 | ✓ Nêu đúng chu kỳ đổi mật khẩu (số ngày cụ; ✓ Nêu đúng số ngày cảnh báo trước; ✓ |
| gq09 | 16  | 3 | 5 | 2    | 2/5 | policy_tool_worker | 0.66 | ✗ SLA P1: nêu đủ 3 kênh notification (Slac; ✓ SLA P1: nêu đúng escalation deadli |
| gq10 | 10  | 1 | 5 | 4    | 3/4 | policy_tool_worker | 0.92 | ✓ Kết luận đúng: KHÔNG được hoàn tiền; ✓ Nêu đúng lý do: đơn Flash Sale là ngoại |

## Answers

### gq01 — SLA detail retrieval — multi-detail extraction

**Question:** Ticket P1 được tạo lúc 22:47. Đúng theo SLA, ai nhận thông báo đầu tiên và qua kênh nào? Deadline
escalation là mấy giờ?

**Answer:**
> 1. **Người nhận thông báo đầu tiên**: On-call engineer nhận alert hoặc ticket và gửi thông báo tới Slack #incident-p1
     và email incident@company.internal ngay lập tức sau khi ticket được tạo [4].

2. **Kênh thông báo**: Thông báo được gửi qua Slack #incident-p1 và email incident@company.internal [5].

3. **Deadline escalation**: Escalation sẽ tự động diễn ra sau 10 phút nếu không có phản hồi [1].

Tóm lại:

- Người nhận thông báo đầu tiên: On-call engineer.
- Kênh thông báo: Slack #incident-p1 và email incident@company.internal.
- Deadline escalation: 10 phút.

**Criteria (2/3 met):** ✓ Kênh thông báo; ✓ Deadline escalation; ✗ Đối tượng escalation

---

### gq02 — Temporal policy scoping — abstain khi thiếu version history

**Question:** Khách hàng đặt đơn ngày 31/01/2026 và gửi yêu cầu hoàn tiền ngày 07/02/2026 vì lỗi nhà sản xuất. Sản phẩm
chưa kích hoạt, không phải Flash Sale, không phải kỹ thuật số. Chính sách nào áp dụng và có được hoàn tiền không?

**Answer:**
> Khách hàng có thể yêu cầu hoàn tiền vì sản phẩm bị lỗi do nhà sản xuất và chưa được kích hoạt. Tuy nhiên, yêu cầu hoàn
> tiền phải được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.

Trong trường hợp này, khách hàng đã gửi yêu cầu hoàn tiền sau 7 ngày làm việc (từ ngày 31/01/2026 đến ngày 07/02/2026),
do đó không đủ điều kiện để được hoàn tiền theo chính sách.

Chính sách hoàn tiền áp dụng cho đơn hàng này là phiên bản 4, nhưng yêu cầu không được chấp nhận do không đáp ứng thời
hạn gửi yêu cầu hoàn tiền. [1], [2], [3]

**Criteria (1/3 met):** ✗ Nhận ra rằng đơn đặt trước 01/02/2026 áp; ✗ Nêu rõ rằng tài liệu hiện có chỉ có chín; ✓ KHÔNG
tự bịa nội dung của chính sách v3

---

### gq03 — Multi-section access control retrieval

**Question:** Engineer cần Level 3 access để khắc phục P1 đang active. Bao nhiêu người phải phê duyệt? Ai là người phê
duyệt cuối cùng (người phê duyệt có thẩm quyền cao nhất)?

**Answer:**
> Để khắc phục sự cố P1 đang active, Engineer cần Level 3 access. Số người phải phê duyệt là 3, bao gồm: Line Manager,
> IT Admin và IT Security. Người phê duyệt cuối cùng (người có thẩm quyền cao nhất) là IT Security [3].

**Criteria (3/3 met):** ✓ Nêu đúng số người phê duyệt; ✓ Nêu đúng tên 3 người; ✓ Nêu đúng người cuối cùng/cao nhất

---

### gq04 — Specific numeric fact extraction

**Question:** Khi khách hàng chọn nhận store credit thay vì hoàn tiền, họ nhận được bao nhiêu phần trăm so với số tiền
gốc cần hoàn?

**Answer:**
> Khách hàng chọn nhận store credit thay vì hoàn tiền sẽ nhận được giá trị 110% so với số tiền gốc cần hoàn. [1]

**Criteria (1/2 met):** ✓ Nêu đúng con số: 110%; ✗ Giải thích đúng: thêm 10% bonus so với h

---

### gq05 — SLA escalation rule — triggered condition

**Question:** Ticket P1 được tạo và on-call engineer không phản hồi sau 10 phút. Theo đúng SLA, hệ thống sẽ làm gì tiếp
theo?

**Answer:**
> Theo đúng SLA, nếu ticket P1 được tạo và on-call engineer không phản hồi sau 10 phút, hệ thống sẽ tự động escalate lên
> Senior Engineer. [1]

**Criteria (3/3 met):** ✓ Nêu đúng hành động: tự động escalate; ✓ Nêu đúng đối tượng: Senior Engineer; ✓ Không nêu sai
thời gian hoặc đối tượng e

---

### gq06 — HR policy — eligibility condition with negative case

**Question:** Một nhân viên mới đang trong probation period muốn làm remote vì lý do cá nhân. Yêu cầu này có được chấp
thuận không? Điều kiện để được làm remote là gì?

**Answer:**
> Yêu cầu làm remote của nhân viên mới trong probation period không được chấp thuận. Điều kiện để làm remote là nhân
> viên phải hoàn thành probation period và được phê duyệt lịch remote bởi Team Lead qua HR Portal. Nhân viên sau probation
> period có thể làm remote tối đa 2 ngày/tuần, với ngày onsite bắt buộc vào thứ 3 và thứ 5 theo lịch team [1].

**Criteria (3/3 met):** ✓ Kết luận đúng: nhân viên trong probation; ✓ Nêu điều kiện đúng: phải qua probation p; ✓ Nêu
giới hạn đúng: tối đa 2 ngày/tuần và

---

### gq07 — Anti-hallucination / abstain — thông tin không có trong tài liệu

**Question:** Mức phạt tài chính cụ thể khi đội IT vi phạm SLA P1 resolution time (không resolve trong 4 giờ) là bao
nhiêu?

**Answer:**
> Không đủ thông tin trong tài liệu nội bộ.

**Criteria (3/3 met):** Correct abstain — no penalty number invented

---

### gq08 — Multi-detail FAQ retrieval

**Question:** Theo quy định IT nội bộ, nhân viên phải đổi mật khẩu sau bao nhiêu ngày? Và hệ thống cảnh báo trước bao
nhiêu ngày?

**Answer:**
> Nhân viên phải đổi mật khẩu mỗi 90 ngày. Hệ thống sẽ nhắc nhở 7 ngày trước khi mật khẩu hết hạn [1].

**Criteria (3/3 met):** ✓ Nêu đúng chu kỳ đổi mật khẩu (số ngày cụ; ✓ Nêu đúng số ngày cảnh báo trước; ✓ Cite đúng
nguồn: it_helpdesk_faq.txt

---

### gq09 — Cross-doc multi-hop — SLA + Access Control, 2 tài liệu

**Question:** Sự cố P1 xảy ra lúc 2am. Đồng thời cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency
fix. Hãy nêu đầy đủ: (1) các bước SLA P1 notification phải làm ngay, và (2) điều kiện để cấp Level 2 emergency access.

**Answer:**
> ### (1) Các bước SLA P1 notification phải làm ngay:

1. **Tiếp nhận**: On-call engineer nhận alert hoặc ticket, xác nhận severity trong 5 phút.
2. **Thông báo**: Gửi thông báo tới Slack #incident-p1 và email incident@company.internal ngay lập tức.
3. **Triage và phân công**: Lead Engineer phân công engineer xử lý trong 10 phút.
4. **Xử lý**: Engineer cập nhật tiến độ lên ticket mỗi 30 phút. Nếu cần hỗ trợ thêm, escalate ngay.
5. **Resolution**: Sau khi khắc phục, viết incident report trong vòng 24 giờ. [3][5]

### (2) Điều kiện để cấp Level 2 emergency access:

- Cần có sự phê duyệt đồng thời của Line Manager và IT Admin on-call.
- Quyền cấp tạm thời có thể được cấp tối đa trong 24 giờ. [1][2]

**Criteria (2/5 met):** ✗ SLA P1: nêu đủ 3 kênh notification (Slac; ✓ SLA P1: nêu đúng escalation deadline nếu; ✗ Level
2 access: nêu đúng rằng Level 2 CÓ; ✓ Level 2 access: nêu đúng điều kiện emerg; ✗ Level 2 access: nêu đúng rằng KHÔNG
cần

---

### gq10 — Policy exception completeness — exception override normal condition

**Question:** Khách hàng mua sản phẩm trong chương trình Flash Sale, nhưng phát hiện sản phẩm bị lỗi từ nhà sản xuất và
yêu cầu hoàn tiền trong vòng 5 ngày. Có được hoàn tiền không? Giải thích theo đúng chính sách.

**Answer:**
> Khách hàng không được hoàn tiền cho sản phẩm mua trong chương trình Flash Sale, ngay cả khi sản phẩm bị lỗi do nhà sản
> xuất. Điều này được quy định rõ trong chính sách hoàn tiền: "Đơn hàng Flash Sale không được hoàn tiền" [3].

Ngoài ra, khách hàng cần lưu ý rằng yêu cầu hoàn tiền phải được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận
đơn hàng, nhưng điều này không áp dụng cho đơn hàng Flash Sale [2].

**Criteria (3/4 met):** ✓ Kết luận đúng: KHÔNG được hoàn tiền; ✓ Nêu đúng lý do: đơn Flash Sale là ngoại ; ✓ Không bị
đánh lừa bởi 'lỗi nhà sản xuất'; ✗ Cite đúng nguồn: policy_refund_v4.txt

---

