# Routing Decisions Log — Lab Day 09

**Nhóm:** 67  
**Ngày:** 14/04/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).

---

## Routing Decision #1

**Task đầu vào:**
> "SLA xử lý ticket P1 là bao lâu?" (q01)

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `default route`  
**MCP tools được gọi:** `[]` (Không có)  
**Workers called sequence:** `['retrieval_worker', 'synthesis_worker']`

**Kết quả thực tế:**
- final_answer (ngắn): Nêu rõ các bước phản hồi ban đầu 15 phút, xử lý 4 giờ.
- confidence: 0.55
- Correct routing? Yes

**Nhận xét:** 
Routing chính xác dù reason là `default_route` (nghĩa là task không chứa các từ khóa policy đặc biệt hay lỗi mã code nên trôi thẳng về máy nhánh tra cứu thông thường).

---

## Routing Decision #2

**Task đầu vào:**
> "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?" (q02)

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword`  
**MCP tools được gọi:** `['search_kb']`  
**Workers called sequence:** `['policy_tool_worker', 'synthesis_worker']`

**Kết quả thực tế:**
- final_answer (ngắn): Trong vòng 7 ngày làm việc... Các ngoại lệ không được hoàn tiền.
- confidence: 0.66
- Correct routing? Yes

**Nhận xét:**
Lệnh if-else trong Supervisor đã bắt trúng chữ "hoàn tiền" và gán cờ `needs_tool = True`. Worker tương ứng đã kết nối MCP tool `search_kb` thành công để lấy file policy phân tích.

---

## Routing Decision #3

**Task đầu vào:**
> "ERR-403-AUTH là lỗi gì và cách xử lý?" (q09)

**Worker được chọn:** `human_review`  
**Route reason (từ trace):** `unknown error code + risk_high → human review | human approved → retrieval`  
**MCP tools được gọi:** `[]`
**Workers called sequence:** `['human_review', 'retrieval_worker', 'synthesis_worker']`

**Kết quả thực tế:**
- final_answer (ngắn): Tổng hợp thông tin liên quan từ access-control-sop.
- confidence: 0.3
- Correct routing? Yes

**Nhận xét:**
Lấy được Risk Keyword "err-", đẩy cờ Risk High lên True và chuyển node sang `human_review_node` thành công (Trong lab giả lập auto_approve). Routing logic hoạt động đúng với kỳ vọng giới hạn bảo mật.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 8 / 15 | 53% |
| policy_tool_worker | 7 / 15 | 46% |
| human_review | 1 / 15 | 6% |

### Routing Accuracy

> Trong số 15 câu test nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: 15 / 15
- Câu route sai (đã sửa bằng cách nào?): 0
- Câu trigger HITL: 1 (Câu q09)

### Lesson Learned về Routing

1. Sử dụng Keyword matching tĩnh khá nhẹ nhưng thô (brittle). Khi gặp các câu chữ đồng nghĩa mà chưa khai báo (như "hoàn trả" thay vì "hoàn tiền") có thể nó sẽ bay vào `default route`.
2. Flow human review (HITL) có thể được móc nối trực tiếp bằng cách ghi đè lộ trình `supervisor_route = "retrieval_worker"` sau lệnh Resume, cách này dễ lập trình thay vì ngắt StateGraph phức tạp.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  
> Nếu chưa, nhóm sẽ cải tiến format route_reason thế nào?

Trace có đủ thông tin cơ bản để debug (ví dụ `unknown error code + risk_high → human review`). Tuy nhiên, `default route` lại chưa mô tả rõ tại sao nó chọn. Nhóm sẽ cải tiến bằng cách bổ sung thêm cờ log từ chối (Vd: `no policy keywords matched => defaulting to basic retrieval`).
