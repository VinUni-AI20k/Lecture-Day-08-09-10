# Routing Decisions Log — Lab Day 09

**Nhóm:** Team 62  
**Ngày:** 2026-04-14  

> Ghi lại 4 quyết định routing thực tế từ trace của nhóm.  
> Nguồn: `artifacts/traces/` — tất cả dữ liệu dưới đây lấy từ trace JSON thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> "SLA xử lý ticket P1 là bao lâu?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `task contains SLA/ticket keywords: p1, sla | MCP disabled: direct retrieval sufficient`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer: "SLA xử lý ticket P1 là như sau: Phản hồi ban đầu: 15 phút. Xử lý và khắc phục: 4 giờ. Escalation: Tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút."
- confidence: 0.62
- latency: 5655ms
- Correct routing? **Yes**

**Nhận xét:** Routing đúng. Task chứa cả "p1" và "sla" — hai keyword SLA rõ ràng. Retrieval trả về chunk chính xác từ `sla_p1_2026.txt` với score 0.64. MCP không cần thiết vì câu hỏi đơn giản — retrieval trực tiếp đủ.

---

## Routing Decision #2

**Task đầu vào:**
> "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keywords: hoàn tiền, flash sale | MCP enabled: search_kb + check_access_permission`  
**MCP tools được gọi:** `search_kb`  
**Workers called sequence:** `retrieval_worker → policy_tool_worker → synthesis_worker`

**Kết quả thực tế:**
- policy_result: `policy_applies=False`, exception: `flash_sale_exception` — "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4)"
- final_answer: "Khách hàng yêu cầu hoàn tiền cho sản phẩm lỗi trong chương trình Flash Sale sẽ không được chấp nhận."
- confidence: 0.55
- latency: 3468ms
- Correct routing? **Yes**

**Nhận xét:** Routing đúng. Keywords "hoàn tiền" và "flash sale" trigger policy route. Policy worker phát hiện đúng `flash_sale_exception` từ `policy_refund_v4.txt`. MCP `search_kb` được gọi để bổ sung evidence (Sprint 3). Đây là loại câu hỏi cần policy check — không chỉ retrieval thuần túy.

---

## Routing Decision #3

**Task đầu vào:**
> "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keywords: cấp quyền, level 3 | MCP enabled: search_kb + check_access_permission | risk_high: emergency context detected`  
**MCP tools được gọi:** `search_kb`, `check_access_permission`, `get_ticket_info`
**Workers called sequence:** `retrieval_worker → policy_tool_worker → synthesis_worker`

**Kết quả thực tế:**
- MCP `get_ticket_info("P1-LATEST")` trả về: ticket IT-9847, P1, in_progress, SLA deadline 02:47
- MCP `check_access_permission(level=3, emergency=True)` trả về: `can_grant=True`, approvers: [Line Manager, IT Admin, IT Security], `emergency_override=False`
- final_answer: "Quy trình cấp quyền Level 3 khẩn cấp: On-call IT Admin cấp tạm thời max 24h sau khi Tech Lead phê duyệt bằng lời. Sau 24h phải có ticket chính thức hoặc quyền bị thu hồi."
- confidence: 0.52
- latency: 5211ms
- Correct routing? **Yes**

**Nhận xét:** Đây là câu hỏi phức tạp nhất — vừa có "cấp quyền" (policy route), vừa có "level 3" (access control keyword), vừa có "khẩn cấp" (risk_high). Pipeline gọi đúng 3 MCP tools: `search_kb` để tìm policy, `check_access_permission` để kiểm tra điều kiện level 3, `get_ticket_info` để lấy context ticket P1 hiện tại. Multi-hop cross-document thành công giữa `access_control_sop.txt` và context ticket.

---

## Routing Decision #4 — HITL Case

**Task đầu vào:**
> "Hệ thống báo lỗi ERR-9999 không rõ nguyên nhân, khẩn cấp cần xử lý"

**Worker được chọn:** `human_review`  
**Route reason (từ trace):** `unknown error code with risk_high context → human review required | human approved → retrieval`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `human_review → retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- `hitl_triggered: true`
- Lab mode: auto-approve, pipeline tiếp tục với retrieval
- confidence: 0.30 (thấp — KB không có thông tin về ERR-9999)
- latency: 4950ms
- Correct routing? **Yes** (đúng khi không rõ error code)

**Nhận xét: Đây là trường hợp routing khó nhất trong lab.**  
Error code "ERR-9999" không nằm trong bất kỳ tài liệu nào → KB không có evidence → confidence thấp (0.30). Supervisor nhận diện đúng: unknown error code + "khẩn cấp" = risk_high → cần human_review thay vì tự đoán. Điều này quan trọng để tránh hallucinate. Trong production, HITL sẽ pause pipeline cho đến khi on-call engineer xác nhận. Câu trả lời cuối ghi rõ "không đủ thông tin trong tài liệu nội bộ".

---

## Tổng kết

### Routing Distribution (từ 13 traces trong artifacts/traces/)

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| `retrieval_worker` | 3 | 23% |
| `policy_tool_worker` | 5 | 38% |
| `human_review` | 5 | 38% |

> Lưu ý: nhiều trace là cùng 1 câu hỏi được chạy nhiều lần ở các sprint khác nhau (trước khi routing logic hoàn thiện). Sau Sprint 3, human_review chỉ trigger đúng với ERR-9999 pattern.

### Routing Accuracy (trên 4 câu hỏi đặc trưng)
- Câu route đúng: 4 / 4
- Câu trigger HITL: 1 (ERR-9999 — đúng)
- Câu có MCP tools được gọi: 2 (Decision #2 và #3)

### Lesson Learned về Routing

1. **Keyword matching đủ cho lab nhưng không scale**: Từ khóa "access" cũng xuất hiện trong câu hỏi IT FAQ ("truy cập hệ thống") — dễ false positive vào `policy_tool_worker`. Giải pháp: thêm negative keywords hoặc dùng embedding-based classifier.
2. **`route_reason` phải ghi cả MCP intent**: Từ Sprint 3, `route_reason` ghi `"MCP enabled: search_kb + check_access_permission"` — giúp debug trace nhanh hơn vì biết ngay worker đó sẽ gọi tool gì.

### Route Reason Quality

`route_reason` trong trace rõ ràng và đủ thông tin để debug sau Sprint 3:
- Ghi rõ keyword nào trigger route
- Ghi rõ MCP enabled/disabled và tools nào sẽ được gọi
- Ghi risk_high nếu có

Cải tiến tiếp theo: thêm confidence score của routing decision vào `route_reason` (ví dụ: "keyword match confidence: 3/5 keywords matched").