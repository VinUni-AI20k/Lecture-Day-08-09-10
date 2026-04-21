# Routing Decisions Log — Lab Day 09

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
