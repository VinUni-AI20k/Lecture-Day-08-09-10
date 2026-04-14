# Routing Decisions Log — Lab Day 09

<<<<<<< HEAD
**Nhóm:** 4, E402
**Ngày:** 2026-04-14

Tất cả trace files tại `artifacts/traces/`. Các quyết định dưới đây lấy từ run `eval_trace.py` ngày 2026-04-14 (15 câu,
15/15 thành công).

---

## Routing Decision #1 — SLA P1 đơn giản → `retrieval_worker`

**Task đầu vào:**
> "SLA xử lý ticket P1 là bao lâu?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `default route`  
**MCP tools được gọi:** không có  
**Workers called sequence:** `retrieval_worker` → `synthesis_worker`

**Kết quả thực tế:**

- final_answer: "SLA xử lý ticket P1: (1) Phản hồi ban đầu: 15 phút. (2) Xử lý và khắc phục: 4 giờ. (3) Escalation: tự
  động lên Senior Engineer nếu không phản hồi trong 10 phút."
- confidence: 0.86
- latency: 7 680 ms
- Correct routing? **Yes**

**Nhận xét:**  
Câu này không chứa policy keyword nào ("hoàn tiền", "cấp quyền"...) nên supervisor giữ default route →
`retrieval_worker`. Hybrid RRF tìm đúng chunk từ `sla_p1_2026.txt` với confidence cao (0.86). Đây là happy path — không
cần routing phức tạp.

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
`re.search(r'err-\d+', task)` khớp với "ERR-403" (có chữ số sau dấu gạch ngang) → supervisor route sang `human_review`,
đặt `risk_high=True`. Sau khi auto-approve, retrieval chạy nhưng không tìm thấy chunk nào liên quan đến mã lỗi cụ thể
này → synthesis abstain đúng với confidence 0.30. Đây là grading risk gq07/gq09 — hệ thống không hallucinate số liệu
phạt hay cách xử lý giả tạo.

---

## Routing Decision #3 — Level 2 P1 2am → `policy_tool_worker` + 3 MCP tools

**Task đầu vào:**
> "Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Đồng thời cần notify
> stakeholders theo SLA. Nêu đủ cả hai quy trình."

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword | risk_high flagged | MCP tools planned`  
**MCP tools được gọi:** `search_kb`, `get_ticket_info`, `check_access_permission`  
**Workers called sequence:** `policy_tool_worker` → `synthesis_worker`

**Kết quả thực tế:**

- final_answer: "Hai quy trình song song: (1) SLA P1: gửi Slack #incident-p1, email incident@..., PagerDuty on-call.
  Escalate lên Senior Engineer nếu không phản hồi trong 10 phút. (2) Level 2 emergency: CÓ bypass — cấp tạm thời với
  approval đồng thời của Line Manager và IT Admin on-call. Không cần IT Security cho Level 2 emergency."
- confidence: 0.77
- latency: 7 774 ms
- Correct routing? **Yes**

**Nhận xét:**  
Task chứa "level 2" + "2am" (risk keyword) + "emergency" → supervisor route đúng sang `policy_tool_worker` với
`needs_tool=True` và `risk_high=True`. Policy worker gọi đủ 3 MCP tools:

- `search_kb`: fallback KB search — sau khi fix, gọi `retrieve_hybrid()` thay vì `retrieve_dense()` (fix 2026-04-14)
- `get_ticket_info("P1-LATEST")`: lấy context ticket đang active
- `check_access_permission(2, "contractor", is_emergency=True)`: lấy rule Level 2 emergency bypass

MCP tool outputs cũng được đưa vào synthesis context (fix 2026-04-14) — synthesis có thể cite `check_access_permission`
result trực tiếp thay vì chỉ dựa vào KB chunks.

Tương đương với **gq06** trong grading set (P1 2am emergency access + SLA notification), đạt C=5, F=5.

---

## Routing Decision #4 — Level 3 contractor P1 → MCP xác nhận không có emergency bypass

**Task đầu vào:**
> "Contractor cần Admin Access (Level 3) để khắc phục sự cố P1 đang active. Quy trình cấp quyền tạm thời như thế nào?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `task contains policy/access keyword | MCP tools planned`  
**MCP tools được gọi:** `search_kb`, `get_ticket_info`, `check_access_permission`

**Kết quả thực tế:**

- final_answer: "Level 3 (Admin Access) KHÔNG có emergency bypass. Dù đang có P1, vẫn phải có approval đủ 3 bên: Line
  Manager, IT Admin, IT Security. Không thể cấp tạm thời."
- confidence: 0.77
- latency: 8 671 ms
- Correct routing? **Yes**

**Nhận xét:** Đây là trường hợp routing khó nhất vì trả lời đúng đòi hỏi biết rằng Level 3 **không** có bypass — thông
tin tiêu cực. `check_access_permission(3, "contractor", is_emergency=True)` trả về `emergency_override: False` và note "
Phải follow quy trình chuẩn". Synthesis kết hợp MCP output + KB chunks để khẳng định điều này mà không hallucinate một
quy trình bypass giả tạo.

Tương đương với **gq05** trong grading set (contractor Admin Access Level 4), đạt C=5 — mặc dù faithfulness bị judge
đánh sai (1/5) do judge nhầm scope clause.

---

## Tổng kết

### Routing Distribution

**15-question eval run (eval_trace.py, 2026-04-14):**

| Worker               | Số câu được route | % tổng |
|----------------------|-------------------|--------|
| `retrieval_worker`   | 7                 | 47%    |
| `policy_tool_worker` | 7                 | 47%    |
| `human_review`       | 1                 | 6%     |

**10-question grading run (score_grading.py, gq01–gq10, 2026-04-14):**

| Worker               | Số câu được route | % tổng |
|----------------------|-------------------|--------|
| `retrieval_worker`   | 5                 | 50%    |
| `policy_tool_worker` | 5                 | 50%    |
| `human_review`       | 0                 | 0%     |

Không có ERR-\d+ pattern trong grading set → HITL không trigger. Grading set thiên về refund/policy (gq03, gq04, gq05,
gq06, gq10) và retrieval (gq01, gq02, gq07, gq08, gq09).

### Routing Accuracy (grading run)

- Câu route đúng: **10 / 10** — tất cả grading questions được route hợp lý
- Câu trigger HITL: **0** (grading set không có ERR-\d+ pattern)
- Câu có MCP tool được gọi: **5 / 10** (gq03, gq04, gq05, gq06, gq10 — tất cả policy route)
- Câu abstain đúng: **1** (gq07 — SLA penalty, confidence 0.30, không hallucinate số phạt)

### Lesson Learned về Routing

1. **Regex > substring cho error codes:** Dùng `re.search(r'err-\d+', task)` thay vì `"err-" in task` tránh false
   positive trên các câu chứa "err-" trong ngữ cảnh khác (e.g., "error message"). Chỉ match khi có chữ số sau dấu gạch
   ngang.
2. **`needs_tool` phải được append vào `route_reason`:** Khi `needs_tool=True`, supervisor append
   `"| MCP tools planned"` vào `route_reason`. Điều này giúp trace log tự documenting — reviewer biết ngay MCP sẽ được
   gọi mà không cần đọc code policy_tool.
3. **`search_kb` phải dùng hybrid, không phải dense:** Khi policy_tool gọi `search_kb` MCP tool, phải dùng
   `retrieve_hybrid()` để BM25 vẫn có tác dụng với các keyword chính xác (Level 4, contractor). Dùng `retrieve_dense()`
   như trước có thể bỏ sót chunk quan trọng. Fix áp dụng 2026-04-14.
4. **`top_k` phải nhất quán giữa MCP và retrieval worker:** `policy_tool_worker` gọi `search_kb` với `top_k` lấy từ
   `state.get("retrieval_top_k", 3)` thay vì hardcode. Điều này đảm bảo grading run với `top_k=5` được áp dụng nhất quán
   cho cả hai paths.

### Route Reason Quality

Các `route_reason` trong trace đủ thông tin debug:

- `default route` — biết ngay không có keyword match
- `task contains policy/access keyword | risk_high flagged | MCP tools planned` — biết route lý do gì, risk từ đâu, và
  MCP có chạy không
- `unknown error code (ERR-\d+) + risk_high → human review | human approved → retrieval` — thể hiện cả HITL flow

Điểm cần cải tiến: `route_reason` chưa ghi keyword cụ thể nào triggered (e.g., "keyword='level 3'"). Nếu routing sai,
phải đoán keyword nào match. Cải tiến: log keyword đầu tiên match vào `route_reason`.
=======
**Nhóm:** 04 
**Ngày:** 2026-04-14

## Mục tiêu tài liệu

- Ghi ít nhất 3 quyết định routing từ trace thật trong `artifacts/traces/` hoặc `artifacts/grading_run.jsonl`.
- Mỗi quyết định phải đủ 4 ý: `task` -> `supervisor_route` -> `route_reason` -> `kết quả`.
- Bám đúng code hiện tại trong `graph.py` (rule-based route + worker thật).

## Cách trích evidence nhanh

1. Chọn 3-5 câu đại diện từ run gần nhất.
2. Copy nguyên văn các field sau từ trace:
   - `task` hoặc `question`
   - `supervisor_route`
   - `route_reason`
   - `workers_called`
   - `mcp_tools_used`
   - `confidence`
3. Đánh giá routing đúng/sai theo mục tiêu câu hỏi, không theo cảm tính.

## Routing Decision #1

**Trace file / id:** `artifacts/traces/run_20260414_165615.json`  
**Task đầu vào:** `SLA xử lý ticket P1 là bao lâu?`  
**Supervisor route:** `retrieval_worker`  
**Route reason (raw):** `task contains retrieval keyword (P1/SLA/ticket/escalation)`

**Execution evidence**
- workers_called: `["retrieval_worker", "synthesis_worker"]`
- mcp_tools_used: `[]`
- confidence: `0.76`
- final_answer (rút gọn): `Ticket P1 phản hồi 15 phút, xử lý 4 giờ, có citation nguồn SLA.`

**Đánh giá**
- Correct routing? `Yes`
- Lý do: câu hỏi SLA/P1 đúng domain retrieval.
- Nếu sai, sửa ở đâu trong `graph.py`: `supervisor_node()` (không cần sửa cho case này).

## Routing Decision #2

**Trace file / id:** `artifacts/traces/run_20260414_165651.json`  
**Task đầu vào:** `Store credit khi hoàn tiền có giá trị bao nhiêu so với tiền gốc?`  
**Supervisor route:** `policy_tool_worker`  
**Route reason (raw):** `task contains policy/access keyword -> policy_tool_worker + MCP allowed`

**Execution evidence**
- workers_called: `["policy_tool_worker", "synthesis_worker"]`
- mcp_tools_used: `["search_kb"]`
- confidence: `0.75`
- final_answer (rút gọn): `Store credit = 110% giá trị hoàn tiền, có citation policy/refund-v4.pdf.`

**Đánh giá**
- Correct routing? `Yes`
- Lý do: câu policy hoàn tiền nên route sang policy worker + MCP là hợp lý.
- Nếu sai, sửa ở đâu trong `graph.py`: không sai route; cải thiện thêm ở policy rules/synthesis formatting.

## Routing Decision #3

**Trace file / id:** `artifacts/traces/run_20260414_165705.json`  
**Task đầu vào:** `Ticket P1 lúc 2am... cấp Level 2 access... notify stakeholders...`  
**Supervisor route:** `retrieval_worker`  
**Route reason (raw):** `task contains retrieval keyword (P1/SLA/ticket/escalation) | risk_high flagged`

**Execution evidence**
- workers_called: `["retrieval_worker", "synthesis_worker"]`
- mcp_tools_used: `[]`
- confidence: `0.77`
- final_answer (rút gọn): `Có cả quy trình emergency access và notify stakeholders theo SLA, cite 2 nguồn.`

**Đánh giá**
- Correct routing? `Yes (thực dụng)`
- Lý do: retrieval đã trả đủ chunks từ cả `it/access-control-sop.md` và `support/sla-p1-2026.pdf`.
- Nếu sai, sửa ở đâu trong `graph.py`: có thể tối ưu thêm multi-hop chain, nhưng hiện tại đã trả đủ evidence.

## Routing Decision #4 (bonus cho gq09 hoặc case khó)

**Trace file / id:** `artifacts/traces/run_20260414_165705.json`  
**Task đầu vào:** `q15 multi-hop (P1 + access level + emergency + notify)`  
**Supervisor route:** `retrieval_worker`  
**Route reason (raw):** `...retrieval keyword... | risk_high flagged`

**Vì sao case này khó?**  
Do câu hỏi yêu cầu đồng thời 2 domain (SLA + access control) và cần trả đầy đủ theo timeline. Case này kiểm tra khả năng retrieve multi-source + synthesis không bỏ sót ý.

## Tổng kết định lượng

| Worker | Số câu được route | Tỉ lệ |
|---|---:|---:|
| retrieval_worker | 10 | 66% |
| policy_tool_worker | 5 | 33% |
| human_review | 0 | 0% |

| Chỉ số | Giá trị |
|---|---|
| Câu route đúng (ước lượng thủ công) | 13 / 15 |
| Câu route sai/partial (ước lượng thủ công) | 2 |
| Câu có `route_reason` hữu ích để debug | 15 / 15 |
| Câu trigger HITL (`hitl_triggered=true`) | 1 |

## Lesson learned cho vòng sau

1. Quy tắc route SLA/P1 -> retrieval giữ lại vì đơn giản, dễ debug.
2. Quy tắc cho multi-hop cần nâng cấp để gọi cả policy_tool + retrieval theo chain.
3. `route_reason` nên thêm `matched_keywords=[...]` để audit rõ hơn.
>>>>>>> NhatVi
