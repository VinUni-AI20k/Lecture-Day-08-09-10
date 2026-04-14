# Routing Decisions Log — Lab Day 09

**Nhóm:** E402_Nhom11  
**Ngày:** 2026-04-14

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Đồng thời cần notify stakeholders theo SLA. Nêu đủ cả hai quy trình.

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `policy / access task`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** policy_tool_worker → retrieval_worker → synthesis_worker  

**Kết quả thực tế:**
- final_answer (ngắn): Yêu cầu cấp quyền Level 2 cần approval theo policy access_control_v2, đồng thời cung cấp SLA và escalation P1  
- confidence: 0.95  
- Correct routing? Yes  

**Nhận xét:**  
Routing đúng vì task liên quan trực tiếp đến cấp quyền (access control) và policy. Supervisor đã ưu tiên policy_tool_worker là hợp lý. Kết quả đầy đủ cả policy + SLA evidence.

---

## Routing Decision #2

**Task đầu vào:**
> Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword | risk_high flagged`  
**MCP tools được gọi:** search_kb, get_ticket_info  
**Workers called sequence:** policy_tool_worker → synthesis_worker  

**Kết quả thực tế:**
- final_answer (ngắn): Cho phép cấp quyền tạm thời 24h sau khi Tech Lead approve, cần log audit và tạo ticket sau đó  
- confidence: 0.53  
- Correct routing? Yes  

**Nhận xét:**  
Routing đúng vì đây là case high-risk liên quan đến quyền Level 3. Tuy nhiên confidence thấp do retrieval chưa mạnh và nội dung phụ thuộc nhiều vào policy chunk. Có thể cải thiện bằng retrieval tốt hơn.

---

## Routing Decision #3

**Task đầu vào:**
> Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword`  
**MCP tools được gọi:** search_kb  
**Workers called sequence:** policy_tool_worker → synthesis_worker  

**Kết quả thực tế:**
- final_answer (ngắn): Không được hoàn tiền do thuộc Flash Sale exception  
- confidence: 0.56  
- Correct routing? Yes  

**Nhận xét:**  
Routing đúng vì đây là bài toán policy (refund policy). Policy_tool_worker xử lý exception chính xác. Tuy nhiên confidence trung bình do phụ thuộc vào chunk retrieval.


---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> SLA xử lý ticket P1 là bao lâu?

**Worker được chọn:** `retrieval_worker`  
**Route reason:** `default route`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**  
Đây là case đơn giản nhưng dễ bị nhầm sang policy_worker nếu logic keyword không tốt. Supervisor đã route đúng sang retrieval_worker vì không cần policy reasoning, chỉ cần lookup thông tin.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 2 | 15% |
| policy_tool_worker | 13 | 86% |
| human_review | 1 (→ reroute về retrieval) | 7% |

### Routing Accuracy

> Trong số 15 câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: **13 / 15**
- Câu route sai: **2** — q02 ("hoàn tiền" → policy thay vì retrieval theo expected) và q04 ("đăng nhập sai" → retrieval đúng nhưng không match keyword nên dùng fallback retrieval). Đã không cần sửa vì fallback vẫn hoạt động.
- Câu trigger HITL: **1** (q09 — ERR-403-AUTH)

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?

1. Sử dụng keyword-based routing kết hợp flag `risk_high` để ưu tiên policy_tool_worker  
2. Không route sang retrieval_worker nếu task có yếu tố access control hoặc policy critical  

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  
> Nếu chưa, nhóm sẽ cải tiến format route_reason thế nào?

Route_reason hiện tại còn khá ngắn (vd: "default route", "policy/access task"), chưa đủ để debug sâu.  
Cần cải tiến theo format:

- Bao gồm: keyword match + risk flag + decision logic  
- Ví dụ tốt hơn:  
  `matched_keywords=[access, level3] | risk_high=True → route=policy_tool_worker`