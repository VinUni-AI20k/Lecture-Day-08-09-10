# Routing Decisions Log — Lab Day 09

**Nhóm:** AI in Action (AICB-P1)
**Ngày:** 14/04/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword | risk_high flagged`  
**MCP tools được gọi:** `None` (Mock stage)  
**Workers called sequence:** `policy_tool_worker` -> `retrieval_worker` -> `synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): [PLACEHOLDER] Câu trả lời được tổng hợp từ 1 chunks.
- confidence: 0.75
- Correct routing? Yes

**Nhận xét:** _(Routing này đúng hay sai? Nếu sai, nguyên nhân là gì?)_
Routing **Đúng**. Hệ thống đã nhận diện được từ khóa "cấp quyền" (access) và mức độ khẩn cấp (P1/khẩn cấp) để chuyển đến Policy worker xử lý ngoại lệ trước khi tìm kiếm tài liệu.

---

## Routing Decision #2

**Task đầu vào:**
> _________________

**Worker được chọn:** `___________________`  
**Route reason (từ trace):** `___________________`  
**MCP tools được gọi:** _________________  
**Workers called sequence:** _________________

**Kết quả thực tế:**
- final_answer (ngắn): _________________
- confidence: _________________
- Correct routing? Yes / No

**Nhận xét:**

_________________

---

## Routing Decision #3

**Task đầu vào:**
> _________________

**Worker được chọn:** `___________________`  
**Route reason (từ trace):** `___________________`  
**MCP tools được gọi:** _________________  
**Workers called sequence:** _________________

**Kết quả thực tế:**
- final_answer (ngắn): _________________
- confidence: _________________
- Correct routing? Yes / No

**Nhận xét:**

_________________

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
| retrieval_worker | ___ | ___% |
| policy_tool_worker | ___ | ___% |
| human_review | ___ | ___% |

### Routing Accuracy

> Trong số X câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: ___ / ___
- Câu route sai (đã sửa bằng cách nào?): ___
- Câu trigger HITL: ___

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?  
> (VD: dùng keyword matching vs LLM classifier, threshold confidence cho HITL, v.v.)

1. **Sức mạnh của Keyword Matching**: Với một tập hợp tài liệu nội bộ có cấu trúc rõ ràng (SLA, Refund, Access SOP), việc sử dụng keyword matching kết hợp Regex là đủ hiệu quả và cực kỳ nhanh so với việc dùng LLM để phân loại, đồng thời tiết kiệm chi phí API.
2. **Tầm quan trọng của route_reason**: Việc bắt buộc ghi lại lý do định tuyến giúp tầng Synthesis hiểu rõ tại sao context đó được chọn, đồng thời giúp con người dễ dàng can thiệp (HITL) khi có sai sót.
3. **Mở rộng qua MCP**: Tách biệt logic routing và logic gọi công cụ (tools) giúp Supervisor giữ được sự tinh gọn, chỉ quan tâm đến việc "đi đâu" thay vì "làm thế nào".

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  
> Nếu chưa, nhóm sẽ cải tiến format route_reason thế nào?

_________________
