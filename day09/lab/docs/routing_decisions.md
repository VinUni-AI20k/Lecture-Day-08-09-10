# Routing Decisions Log — Lab Day 09

**Nhóm:** A20C1E402G4  
**Ngày:** 2026-04-14

Tất cả trace files tại `artifacts/traces/`. Các quyết định dưới đây lấy từ run `eval_trace.py` ngày 2026-04-14 (15 câu, 15/15 thành công).

---

## Routing Decision #1 — SLA P1 đơn giản → `retrieval_worker`

**Task đầu vào:**
> "SLA xử lý ticket P1 là bao lâu?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `default route`  
**MCP tools được gọi:** không có  
**Workers called sequence:** `retrieval_worker` → `synthesis_worker`

**Kết quả thực tế:**
- final_answer: "SLA xử lý ticket P1: (1) Phản hồi ban đầu: 15 phút. (2) Xử lý và khắc phục: 4 giờ. (3) Escalation: tự động lên Senior Engineer nếu không phản hồi trong 10 phút."
- confidence: 0.86
- latency: 7 680 ms
- Correct routing? **Yes**

**Nhận xét:**  
Câu này không chứa policy keyword nào ("hoàn tiền", "cấp quyền"...) nên supervisor giữ default route → `retrieval_worker`. Hybrid RRF tìm đúng chunk từ `sla_p1_2026.txt` với confidence cao (0.86). Đây là happy path — không cần routing phức tạp.

---

## Routing Decision #2 — ERR-403-AUTH không rõ → `human_review` → abstain

**Task đầu vào:**
> "ERR-403-AUTH là lỗi gì và cách xử lý?"

**Worker được chọn:** `human_review` (sau đó auto-approve → `retrieval_worker`)  
**Route reason (từ trace):** `unknown error code (ERR-\d+) + risk_high → human review | human approved → retrieval`  
**MCP tools được gọi:** không có  
**Workers called sequence:** `human_review` → `retrieval_worker` → `synthesis_worker`

**Kết quả thực tế:**
- final_answer: "Không đủ thông tin trong tài liệu nội bộ."
- confidence: 0.30
- hitl_triggered: True
- latency: 4 000 ms
- Correct routing? **Yes**

**Nhận xét:**  
`re.search(r'err-\d+', task)` khớp với "ERR-403" (có chữ số sau dấu gạch ngang) → supervisor route sang `human_review`, đặt `risk_high=True`. Sau khi auto-approve, retrieval chạy nhưng không tìm thấy chunk nào liên quan đến mã lỗi cụ thể này → synthesis abstain đúng với confidence 0.30. Đây là grading risk gq07/gq09 — hệ thống không hallucinate số liệu phạt hay cách xử lý giả tạo.

---

## Routing Decision #3 — Level 2 P1 2am → `policy_tool_worker` + 3 MCP tools

**Task đầu vào:**
> "Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Đồng thời cần notify stakeholders theo SLA. Nêu đủ cả hai quy trình."

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword | risk_high flagged | MCP tools planned`  
**MCP tools được gọi:** `search_kb`, `get_ticket_info`, `check_access_permission`  
**Workers called sequence:** `policy_tool_worker` → `synthesis_worker`

**Kết quả thực tế:**
- final_answer: "Hai quy trình song song: (1) SLA P1: gửi Slack #incident-p1, email incident@..., PagerDuty on-call. Escalate lên Senior Engineer nếu không phản hồi trong 10 phút. (2) Level 2 emergency: CÓ bypass — cấp tạm thời với approval đồng thời của Line Manager và IT Admin on-call. Không cần IT Security cho Level 2 emergency."
- confidence: 0.77
- latency: 7 774 ms
- Correct routing? **Yes**

**Nhận xét:**  
Task chứa "level 2" + "2am" (risk keyword) + "emergency" → supervisor route đúng sang `policy_tool_worker` với `needs_tool=True` và `risk_high=True`. Policy worker gọi đủ 3 MCP tools:
- `search_kb`: fallback KB search vì retrieval chưa chạy trước
- `get_ticket_info("P1-LATEST")`: lấy context ticket đang active
- `check_access_permission(2, "contractor", is_emergency=True)`: lấy rule Level 2 emergency bypass

Synthesis tổng hợp đủ cả hai quy trình từ 3 nguồn evidence → đây là câu multi-hop khó nhất (q15).

---

## Routing Decision #4 — Level 3 contractor P1 → MCP xác nhận không có emergency bypass

**Task đầu vào:**
> "Contractor cần Admin Access (Level 3) để khắc phục sự cố P1 đang active. Quy trình cấp quyền tạm thời như thế nào?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `task contains policy/access keyword | MCP tools planned`  
**MCP tools được gọi:** `search_kb`, `get_ticket_info`, `check_access_permission`

**Kết quả thực tế:**
- final_answer: "Level 3 (Admin Access) KHÔNG có emergency bypass. Dù đang có P1, vẫn phải có approval đủ 3 bên: Line Manager, IT Admin, IT Security. Không thể cấp tạm thời."
- confidence: 0.77
- latency: 8 671 ms
- Correct routing? **Yes**

**Nhận xét:** Đây là trường hợp routing khó nhất vì trả lời đúng đòi hỏi biết rằng Level 3 **không** có bypass — thông tin tiêu cực. `check_access_permission(3, "contractor", is_emergency=True)` trả về `emergency_override: False` và note "Phải follow quy trình chuẩn". Synthesis kết hợp MCP output + KB chunks để khẳng định điều này mà không hallucinate một quy trình bypass giả tạo.

---

## Tổng kết

### Routing Distribution (15 câu, eval run 2026-04-14)

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| `retrieval_worker` | 7 | 47% |
| `policy_tool_worker` | 7 | 47% |
| `human_review` | 1 | 6% |

### Routing Accuracy

- Câu route đúng theo `expected_route`: **14 / 15** (q02 route vào `policy_tool_worker` thay vì `retrieval_worker` — hợp lý vì câu hỏi về refund policy)
- Câu trigger HITL: **1** (q09 — ERR-403-AUTH)
- Câu có MCP tool được gọi: **7 / 15** (tất cả đều đúng trigger condition)
- Câu abstain đúng: **1** (q09 — confidence 0.30, không hallucinate)

### Lesson Learned về Routing

1. **Regex > substring cho error codes:** Dùng `re.search(r'err-\d+', task)` thay vì `"err-" in task` tránh false positive trên các câu chứa "err-" trong ngữ cảnh khác (e.g., "error message"). Chỉ match khi có chữ số sau dấu gạch ngang.
2. **`needs_tool` phải được append vào `route_reason`:** Khi `needs_tool=True`, supervisor append `"| MCP tools planned"` vào `route_reason`. Điều này giúp trace log tự documenting — reviewer biết ngay MCP sẽ được gọi mà không cần đọc code policy_tool.

### Route Reason Quality

Các `route_reason` trong trace đủ thông tin debug:
- `default route` — biết ngay không có keyword match
- `task contains policy/access keyword | risk_high flagged | MCP tools planned` — biết route lý do gì, risk từ đâu, và MCP có chạy không
- `unknown error code (ERR-\d+) + risk_high → human review | human approved → retrieval` — thể hiện cả HITL flow

Điểm cần cải tiến: `route_reason` chưa ghi keyword cụ thể nào triggered (e.g., "keyword='level 3'"). Nếu routing sai, phải đoán keyword nào match. Cải tiến: log keyword đầu tiên match vào `route_reason`.
