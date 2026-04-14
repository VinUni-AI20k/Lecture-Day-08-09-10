# Routing Decisions Log — Lab Day 09

**Nhóm:** E402_Nhom11  
**Ngày:** 2026-04-14

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1 — Retrieval (SLA Query)

**Task đầu vào:**
> "SLA xử lý ticket P1 là bao lâu?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `sla / ticket query`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer: `[Evidence] SLA P1: phản hồi 15 phút, xử lý 4 giờ. Escalation P1 cần notify team lead ngay lập tức.`
- confidence: 0.80
- Correct routing? **Yes** ✓

**Nhận xét:** Routing đúng — câu hỏi chứa keyword "SLA" và "ticket P1" → supervisor nhận diện đúng là retrieval task. Retrieval worker trả về 3 chunks liên quan từ SLA docs. Confidence 0.80 phù hợp vì có nhiều evidence support.

---

## Routing Decision #2 — Policy (Refund + Flash Sale Exception)

**Task đầu vào:**
> "Sản phẩm kỹ thuật số (license key) có được hoàn tiền không?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `policy / access task`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `policy_tool_worker → retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer: `[Policy Decision] refund_policy_v4 → allowed. Lý do: Refund tiêu chuẩn` + Evidence từ retrieval
- confidence: 0.90
- Correct routing? **Yes** ✓

**Nhận xét:** Routing đúng — keyword "license" match policy_keywords trong supervisor. Policy worker phát hiện đây là câu hỏi về digital product refund. Confidence cao (0.90) vì có cả policy result lẫn retrieved chunks. Tuy nhiên, mock policy worker chưa detect đúng exception "digital_product" ở graph.py level (chỉ detect ở workers/policy_tool.py thật).

---

## Routing Decision #3 — Human Review (Error Code + Risk)

**Task đầu vào:**
> "ERR-403-AUTH là lỗi gì và cách xử lý?"

**Worker được chọn:** `human_review` → (auto-approve) → `retrieval_worker`  
**Route reason (từ trace):** `error + risk_high → human review | human approved → retrieval`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `human_review → retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer: "Không tìm thấy dữ liệu phù hợp." (fallback)
- confidence: 0.70
- hitl_triggered: **true**
- Correct routing? **Yes** ✓

**Nhận xét:** Đây là trường hợp routing phức tạp nhất. Supervisor phát hiện cả `risk_high` (keyword "err-") lẫn error code → route sang `human_review`. Sau khi HITL auto-approve, pipeline chuyển về `retrieval_worker` nhưng không tìm thấy evidence → trả fallback. Routing logic đúng: câu hỏi chứa mã lỗi unknown cần human review trước khi xử lý.

---

## Routing Decision #4 — Multi-hop (Access Control + SLA)

**Task đầu vào:**
> "Contractor cần Admin Access (Level 3) để khắc phục sự cố P1 đang active. Quy trình cấp quyền tạm thời như thế nào?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `policy / access task`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**

Câu hỏi này yêu cầu cross-document reasoning: cần thông tin từ cả `access_control_sop.txt` (quy trình cấp quyền Level 3) và `sla_p1_2026.txt` (context P1 escalation). Supervisor chọn `policy_tool_worker` vì keyword "cấp quyền" + "access" + "level 3", sau đó policy worker cũng gọi `retrieval_worker` để lấy evidence → cả hai nguồn đều được sử dụng. Confidence đạt 0.95 — cao nhất trong tất cả câu hỏi.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 8 | 53% |
| policy_tool_worker | 7 | 47% |
| human_review | 1 (→ reroute về retrieval) | 7% |

### Routing Accuracy

> Trong số 15 câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: **13 / 15**
- Câu route sai: **2** — q02 ("hoàn tiền" → policy thay vì retrieval theo expected) và q04 ("đăng nhập sai" → retrieval đúng nhưng không match keyword nên dùng fallback retrieval). Đã không cần sửa vì fallback vẫn hoạt động.
- Câu trigger HITL: **1** (q09 — ERR-403-AUTH)

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?

1. **Keyword matching đủ tốt cho lab scope** — với 15 câu test, rule-based routing bằng keyword lists đạt 87% accuracy. Không cần LLM classifier cho use case này.
2. **Fallback về retrieval_worker là an toàn** — khi supervisor không tự tin về route, default retrieval luôn cho kết quả hợp lý (dù có thể không optimal). Tốt hơn là raise error.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?

Route reason hiện tại khá generic ("policy / access task", "sla / ticket query", "fallback retrieval"). Để cải thiện, nhóm sẽ:
- Thêm **matched keywords** vào route_reason: `"policy / access task [matched: 'cấp quyền', 'level 3']"`
- Thêm **confidence score của routing decision**: `"sla query (confidence=0.92, matched 2/3 keywords)"`
- Ghi rõ **tại sao không chọn route khác**: `"retrieval (not policy: no refund/access keyword)"`
