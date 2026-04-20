# Routing Decisions Log — Lab Day 09

**Nhóm:** C401-E6  
**Ngày:** 14/04/2026  

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> "Ticket P1 được tạo lúc 22:47. Đúng theo SLA, ai nhận thông báo đầu tiên và qua kênh nào? Deadline escalation là mấy giờ?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `SLA/ticket information lookup`  
**MCP tools được gọi:** No
**Workers called sequence:** ["retrieval_worker", "retrieval_worker", "synthesis_worker", "synthesis_worker"]

**Kết quả thực tế:**
- final_answer (ngắn): In ra 'người nhận đầu tiên', 'kênh thông báo', 'deadline escalation'
- confidence: 1.0
- Correct routing? Yes

**Nhận xét:** _(Routing này đúng hay sai? Nếu sai, nguyên nhân là gì?)_

Quyết định routing này hoàn toàn chính xác. Vì câu hỏi tập trung vào thông tin SLA và quy trình thông báo (đã được định nghĩa trong `sla_p1_2026.txt`), việc route sang retrieval worker giúp lấy đúng context mà không cần xử lý policy phức tạp.

---

## Routing Decision #2

**Task đầu vào:**
> "Khách hàng mua sản phẩm trong chương trình Flash Sale, nhưng phát hiện sản phẩm bị lỗi từ nhà sản xuất và yêu cầu hoàn tiền trong vòng 5 ngày. Có được hoàn tiền không?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `policy check required: refund_exception_check`  
**MCP tools được gọi:** Không  
**Workers called sequence:** ["retrieval_worker", "policy_tool_worker", "synthesis_worker"]

**Kết quả thực tế:**
- final_answer (ngắn): Không được hoàn tiền do đơn hàng Flash Sale là trường hợp ngoại lệ theo Điều 3 chính sách v4.
- confidence: 1.0
- Correct routing? Yes

**Nhận xét:**

Routing đúng. Supervisor nhận diện được từ khóa "Flash Sale" và "hoàn tiền" để kích hoạt `policy_tool_worker`. Việc này quan trọng vì nếu chỉ dùng retrieval thông thường, LLM có thể bỏ qua tính nghiêm ngặt của điều khoản ngoại lệ.

---

## Routing Decision #3

**Task đầu vào:**
> "Engineer cần Level 3 access để khắc phục P1 đang active. Bao nhiêu người phải phê duyệt? Ai là người phê duyệt cuối cùng?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `policy check required: access_permission_check | risk_high: high_privilege`  
**MCP tools được gọi:** `get_ticket_info`  
**Workers called sequence:** ["retrieval_worker", "policy_tool_worker", "synthesis_worker"]

**Kết quả thực tế:**
- final_answer (ngắn): Cần 3 người phê duyệt (Line Manager, IT Admin, IT Security). IT Security là người phê duyệt cuối cùng.
- confidence: 1.0
- Correct routing? Yes

**Nhận xét:**

Routing cực kỳ chính xác và an toàn. Supervisor không chỉ route sang policy worker mà còn gán nhãn `risk_high` do phát hiện yêu cầu quyền hạn cao (Level 3). Ngoài ra, hệ thống đã gọi MCP Tool `get_ticket_info` để kiểm tra trạng thái ticket P1 trước khi tư vấn quyền truy cập.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> "Mức phạt tài chính cụ thể khi đội IT vi phạm SLA P1 resolution time (không resolve trong 4 giờ) là bao nhiêu?"

**Worker được chọn:** `retrieval_worker`  
**Route reason:** `SLA/ticket information lookup`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**

Đây là câu hỏi "bẫy" vì thông tin về phạt tài chính không hề có trong tài liệu nội bộ. Tuy nhiên, Supervisor vẫn route đúng sang `retrieval_worker` để cố gắng tìm kiếm. Kết quả là Synthesis Worker đã trả về "Không đủ thông tin" với confidence thấp (0.2). Điều này chứng minh hệ thống biết điểm dừng (abstain) khi không có bằng chứng, thay vì bịa đặt (hallucinate) ra một mức phạt.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 5 | 50% |
| policy_tool_worker | 5 | 50% |
| human_review | 0 | 0% |

### Routing Accuracy

> Trong số 10 câu nhóm đã chạy từ grading_run, bao nhiêu câu supervisor route đúng?

- Câu route đúng: 10 / 10
- Câu route sai: 0
- Câu trigger HITL: 0

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?  
> (VD: dùng keyword matching vs LLM classifier, threshold confidence cho HITL, v.v.)

1. **Kết hợp Keyword và Context**: Việc sử dụng regex cho mã lỗi và keyword matching cho policy (Flash Sale, Access, Refund) tỏ ra hiệu quả và nhanh chóng cho tập dữ liệu có cấu trúc ổn định.
2. **Risk-aware Routing**: Việc supervisor nhận diện được rủi ro khẩn cấp (`emergency`, `off_hours`) giúp bổ sung thêm metadata quan trọng cho worker xử lý tiếp theo, làm tăng độ tin cậy của câu trả lời.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  
> Nếu chưa, nhóm sẽ cải tiến format route_reason thế nào?

Các `route_reason` hiện tại khá rõ ràng (phân tách được loại tra cứu SLA, Policy hay HR). Tuy nhiên, để cải tiến, nhóm có thể bổ sung thêm danh sách các "tín hiệu" (signals) mà Supervisor đã bắt được vào reason để khi debug biết chính xác tại sao một câu lại bị route nhầm (ví dụ: `reason: policy check [signal: flash_sale detected]`).
