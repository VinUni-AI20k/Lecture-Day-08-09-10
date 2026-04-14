# Routing Decisions Log — Lab Day 09

**Nhóm:** C401-A4  
**Ngày:** 14/04/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> SLA xu ly ticket P1 la bao lau?

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `SLA/ticket/escalation signal detected | risk_high flagged`  
**MCP tools được gọi:** (Trống - Hệ thống dùng search engine nội bộ của worker thay vì gọi công cụ MCP ngoài)  
**Workers called sequence:** supervisor -> retrieval_worker -> synthesis_worker

**Kết quả thực tế:**
- final_answer (ngắn): SLA P1 resolution là 4 giờ (cập nhật từ 6 giờ); Stakeholder cần được update mỗi 30 phút.
- confidence: 0.95
- Correct routing? Yes

**Nhận xét:** _(Routing này đúng hay sai? Nếu sai, nguyên nhân là gì?)_

> Routing này đúng. Supervisor đã nhận diện chính xác các từ khóa nhạy cảm ("SLA", "P1") để gắn flag risk_high: true và điều hướng về retrieval_worker để truy xuất tài liệu sla_p1_2026.txt. Hệ thống cũng loại bỏ được nhiễu từ chunk số 3 (về sprint cycle 2-4 tuần - vốn dành cho các task thông thường) để đưa ra con số 4 giờ chính xác nhất cho P1.

---

## Routing Decision #2

**Task đầu vào:**
> Khach hang Flash Sale yeu cau hoan tien vi san pham loi - duoc khong?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `refund/policy signal detected | MCP lookup enabled for policy worker`  
**MCP tools được gọi:** search_kb (để truy vấn cơ sở tri thức về chính sách)  
**Workers called sequence:** supervisor -> policy_tool_worker -> synthesis_worker

**Kết quả thực tế:**
- final_answer (ngắn): Không được hoàn tiền. Mặc dù sản phẩm lỗi là điều kiện đủ, nhưng đơn hàng thuộc chương trình Flash Sale là ngoại lệ không áp dụng hoàn trả theo `policy_refund_v4.txt`.
- confidence: 0.6
- Correct routing? Yes 

**Nhận xét:**

> Routing này đúng về mặt kỹ thuật vì Supervisor đã nhận diện được ý định hỏi về "chính sách hoàn tiền" (refund policy) và chuyển cho policy_tool_worker xử lý thay vì chỉ tìm kiếm thông tin đơn thuần.
> Tuy nhiên, có 2 điểm cần lưu ý để debug:

+ Độ tin cậy (Confidence) thấp (0.6): Do hệ thống tìm thấy cả điều kiện cho phép (sản phẩm lỗi) và điều kiện từ chối (Flash Sale), gây ra sự xung đột trong bước tổng hợp.

+ Nhiễu dữ liệu: synthesis_worker đã lấy cả nguồn từ access_control_sop.txt và sla_p1_2026.txt vào câu trả lời cuối cùng dù chúng không liên quan đến việc hoàn tiền cho khách hàng. Điều này cho thấy bước lọc source sau khi retrieve cần được cải thiện.
---

## Routing Decision #3

**Task đầu vào:**
> Can cap quyen Level 3 de khac phuc P1 khan cap. Quy trinh la gi?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `access-control signal detected | incident/SLA context also detected | MCP lookup enabled for policy worker | risk_high flagged`  
**MCP tools được gọi:** search_kb, check_access_permission, get_ticket_info  
**Workers called sequence:** supervisor -> policy_tool_worker -> synthesis_worker
**Kết quả thực tế:**
- final_answer (ngắn): Quyền Level 3 thông thường cần chuỗi phê duyệt (Manager, IT Admin, Security). Tuy nhiên, trong sự cố P1, có thể sử dụng Escalation khẩn cấp: On-call IT Admin cấp quyền tạm thời (max 24h) sau khi Tech Lead phê duyệt bằng lời.
- confidence: 0.75
- Correct routing? Yes

**Nhận xét:**

> Routing này rất chính xác và hiệu quả.
> Điểm sáng: Supervisor không chỉ route dựa trên từ khóa "quyền Level 3" mà còn nhận diện được bối cảnh "P1 khẩn cấp", từ đó kích hoạt flag risk_high và gọi cùng lúc 3 công cụ MCP để kiểm tra cả chính sách lẫn trạng thái ticket thực tế (IT-9847).
> Vấn đề cần cải thiện: Mặc dù trả kết quả đúng, nhưng synthesis_worker vẫn bị nhiễu thông tin từ hr_leave_policy.txt (chính sách nghỉ phép), dẫn đến độ tự tin chỉ đạt 0.75.
---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> _________________

**Worker được chọn:** `___________________`  
**Route reason:** `___________________`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**

_________________

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 1 | 33% |
| policy_tool_worker | 2 | 67% |
| human_review | 0 | 0% |

### Routing Accuracy

> Trong số X câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: 3 / 3
- Câu route sai (đã sửa bằng cách nào?): 0
- Câu trigger HITL: 0 (Mặc dù có câu P1 rủi ro cao nhưng Agent đã tự xử lý được qua các tool MCP).

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?  
> (VD: dùng keyword matching vs LLM classifier, threshold confidence cho HITL, v.v.)

1. Sức mạnh của Flag rủi ro (Risk Flagging): Việc Supervisor tự động gắn risk_high: true cho các task liên quan đến SLA và Access Control giúp hệ thống ưu tiên gọi các tool kiểm tra quyền hạn (check_access_permission) thay vì chỉ trả lời lý thuyết.
2. Xử lý nhiễu dữ liệu (Noise Reduction): Các tài liệu HR thường có score trung bình (0.5) dễ lọt vào context. Nhóm cần thiết lập Hard Threshold cho Retrieval (ví dụ: chỉ lấy score > 0.6) để tránh làm loãng câu trả lời khẩn cấp.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  
> Nếu chưa, nhóm sẽ cải tiến format route_reason thế nào?

> Khá tốt. Format hiện tại đã chỉ ra được các "signals" (tín hiệu) mà Supervisor bắt được (ví dụ: access-control signal). Tuy nhiên, nhóm sẽ cải tiến để ghi rõ Supervisor có nhận diện được Ticket ID cụ thể hay không để debug phần MCP tốt hơn.
