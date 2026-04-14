# Routing Decisions Log — Lab Day 09

**Nhóm:** 2A202600292-TranDangQuangHuy  
**Ngày:** 2026-04-14

**Nguồn trace dùng để điền:**
- `artifacts/runs/sprint4_test_20260414_115500.jsonl`
- `artifacts/runs/sprint4_test_20260414_115500_summary.json`

---

## Routing Decision #1

**Task đầu vào:**
> SLA xử lý ticket P1 là bao lâu?

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `incident/SLA keywords matched (p1, sla, ticket); needs_tool=False; mcp_expected=False | mcp_used=False`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `retrieval_worker -> synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): Trả lời theo evidence từ `sla_p1_2026.txt`, có citation.
- confidence: `0.33`
- Correct routing? **Yes**

**Nhận xét:** Routing đúng với câu SLA/P1. Supervisor không gọi MCP và log rõ lý do.

---

## Routing Decision #2

**Task đầu vào:**
> Ai phải phê duyệt để cấp quyền Level 3?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `policy/access keywords matched (cấp quyền, level 3); needs_tool=True; mcp_expected=True | mcp_used=True`  
**MCP tools được gọi:** `search_kb`, `check_access_permission` (transport: `inprocess-real`)  
**Workers called sequence:** `policy_tool_worker -> synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): Trả về danh sách approver `Line Manager, IT Admin, IT Security`.
- confidence: `0.37`
- Correct routing? **Yes**

**Nhận xét:** Đây là case policy/access chuẩn, route và MCP usage đều đúng kỳ vọng.

---

## Routing Decision #3

**Task đầu vào:**
> ERR-403-AUTH là lỗi gì và cách xử lý?

**Worker được chọn:** `human_review`  
**Route reason (từ trace):** `ambiguous error code detected (err-403); human review required; needs_tool=False; mcp_expected=False | risk_high=True due to ambiguous error | mcp_used=False`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `human_review -> synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): `Không đủ thông tin trong tài liệu nội bộ để trả lời câu hỏi này.`
- confidence: `0.10`
- Correct routing? **No** (khác `expected_route` của test set, nhưng phù hợp với luật risk/human-review hiện tại)

**Nhận xét:** Route này cho thấy guardrail an toàn đang ưu tiên khi gặp mã lỗi mơ hồ.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> Ticket P1 lúc 2am... Cần Level 2 access tạm thời... notify stakeholders theo SLA.

**Worker được chọn:** `retrieval_worker`  
**Route reason:** `incident/SLA keywords matched ... policy keywords also present ..., but retrieval is prioritized ... | risk_high=True due to emergency, 2am | mcp_used=False`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**

Case này là multi-hop (SLA + access policy) nhưng rule hiện tại ưu tiên retrieval khi có tín hiệu P1/SLA, nên không kích hoạt policy worker/MCP như kỳ vọng test set.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 9 | 60.00% |
| policy_tool_worker | 5 | 33.33% |
| human_review | 1 | 6.67% |

### Routing Accuracy

- Câu route đúng: **11 / 15**
- Câu route sai theo expected_route test set: **4** (`q02`, `q09`, `q13`, `q15`)
- Câu trigger HITL: **13**

### Lesson Learned về Routing

1. Rule ưu tiên retrieval cho tín hiệu P1/SLA giúp phản hồi nhanh câu vận hành, nhưng làm yếu case multi-hop policy.
2. Cần thêm luật ưu tiên policy khi câu đồng thời chứa access-level + emergency để giảm sai lệch cho `q13`, `q15`.

### Route Reason Quality

`route_reason` hiện đã đủ để debug nhanh vì ghi:
- keyword nào match,
- có/không `needs_tool`,
- kỳ vọng MCP,
- và kết quả `mcp_used` sau audit.

Điểm cần cải tiến: thêm `decision_score` hoặc `route_confidence` để dễ đặt ngưỡng chuyển sang `human_review`.
