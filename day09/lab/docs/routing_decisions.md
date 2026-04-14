# Routing Decisions Log — Lab Day 09

**Nhóm:** ___________  
**Ngày:** ___________

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

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

**Nhận xét:** _(Routing này đúng hay sai? Nếu sai, nguyên nhân là gì?)_

_________________

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

1. ___________________
2. ___________________

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  
> Nếu chưa, nhóm sẽ cải tiến format route_reason thế nào?

_________________
