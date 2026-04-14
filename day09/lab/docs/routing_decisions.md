# Routing Decisions Log — Lab Day 09

**Nhóm:** E403_Team61  
**Ngày:** 14/04/2026

---

## Routing Decision #1

**Task đầu vào:**
> "Ticket P1 lúc 2am — escalation xảy ra thế nào và ai nhận thông báo?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `task contains P1 and ticket keyword`  
**MCP tools được gọi:** `None`  
**Workers called sequence:** `supervisor -> retrieval_worker -> synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): "The L1 team must respond within 15 minutes. If no response, escalate to L2 and alert Manager."
- confidence: `0.92`
- Correct routing? Yes

**Nhận xét:** 
Routing này chính xác. Việc query thông tin quy định chung về Ticket và P1 không cần truy vấn user data hoặc check policy động nên route trực tiếp cho Retrieval là tối ưu nhất.

---

## Routing Decision #2

**Task đầu vào:**
> "Khách hàng mua hàng Flash Sale trên app di động và muốn hoàn tiền vì sản phẩm lỗi — policy nào áp dụng?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains Flash Sale and policy keyword`  
**MCP tools được gọi:** `search_kb`  
**Workers called sequence:** `supervisor -> policy_tool_worker -> MCP_search_kb -> synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): "Hàng hóa mua trong dịp Flash sale không được apply chính sách refund thông thường."
- confidence: `0.85`
- Correct routing? Yes

**Nhận xét:**
Đúng hướng đi. Supervisor detect được term "Flash Sale" yêu cầu check policy đặc biệt nên đưa cho policy_tool_worker. Worker này tự list ra logic exception case mà không cần LLM hallucinate answer.

---

## Routing Decision #3

**Task đầu vào:**
> "User ID 15201 có vi phạm điều khoản công ty vì nghỉ quá 2 tuần liên tiếp hay không?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains HR policy keyword or specific ID`  
**MCP tools được gọi:** `get_ticket_info`, `search_kb`  
**Workers called sequence:** `supervisor -> policy_tool_worker -> MCP_get_ticket_info -> synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): "Tôi không thể verify ID nhân viên này vì insufficient clearance."
- confidence: `0.10`
- Correct routing? Yes

**Nhận xét:**
Route đúng vì câu hỏi có dính đến thông tin định danh HR specific ID cần móc nối với MCP để phân quyền tra cứu. Việc tool tự động deny/abstain là mong muốn an toàn hệ thống thay vì tự suy diễn.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 9 | 60% |
| policy_tool_worker | 5 | 33% |
| human_review | 1 | 7% |

### Routing Accuracy

- Câu route đúng: 13 / 15
- Câu route sai (đã sửa bằng cách nào?): 2 (Đã sửa bằng cách thêm condition keyword fallback từ LLM router)
- Câu trigger HITL: 2

### Lesson Learned về Routing

1. Keyword matching chạy cực nhanh và bao trọn được 80% use case.
2. Với mảng câu hỏi "lập lờ", mix giữa 2 tool, cần thêm config thứ tự ưu tiên (Risk/Policy/Security ưu tiên route hơn so với General retrieval)

### Route Reason Quality

Các `route_reason` được set rạch ròi bằng log tracing giúp nhận diện nhầm lẫn phân cấp ngay từ giây đầu tiên thay vì phải debug toàn Pipeline. Sắp tới nhóm sẽ format `route_reason` bằng JSON chứa tag rõ ràng hơn như `{"tag": "SECURITY_POLICY", "confidence": 0.88}` để trace tools đọc được thống kê.
