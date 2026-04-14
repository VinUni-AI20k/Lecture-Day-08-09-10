# Routing Decisions Log — Lab Day 09

Tài liệu này ghi lại 3 quyết định route lấy trực tiếp từ run grading mới nhất (`artifacts/grading_run.jsonl`).

---

## Decision #1 — SLA question -> `retrieval_worker`

**Input task:** `gq01` (P1 lúc 22:47, hỏi kênh thông báo + deadline escalation).  
**Chosen worker:** `retrieval_worker`  
**Route reason:** `SLA / P1 / IT ops keywords — retrieval + synthesis`  
**Workers called:** `retrieval_worker` -> `synthesis_worker`  
**MCP tools used:** none

**Observed outcome:** câu trả lời nêu đủ escalation và các kênh notification từ tài liệu SLA (bao gồm Slack/email, và một số run có PagerDuty).

---

## Decision #2 — Refund/policy exception -> `policy_tool_worker`

**Input task:** `gq10` (Flash Sale + lỗi nhà sản xuất + yêu cầu hoàn tiền).  
**Chosen worker:** `policy_tool_worker`  
**Route reason:** `policy/access/refund exception keywords — policy_tool uses MCP search_kb (not direct Chroma)`  
**Workers called:** `policy_tool_worker` -> `synthesis_worker`  
**MCP tools used:** `search_kb`

**Observed outcome:** trả lời đúng hướng chính sách ngoại lệ Flash Sale (không hoàn tiền), có dẫn nguồn `policy_refund_v4.txt`.

---

## Decision #3 — Cross-doc incident + access -> `multi_hop`

**Input task:** `gq09` (P1 lúc 2am + cấp Level 2 emergency cho contractor).  
**Chosen worker:** `multi_hop`  
**Route reason:** `multi-hop: task mentions incident/SLA/P1/ticket AND access/level/contractor — run retrieval then policy (+ MCP tools)`  
**Workers called:** `retrieval_worker` -> `policy_tool_worker` -> `synthesis_worker`  
**MCP tools used:** `get_ticket_info`, `check_access_permission`

**Observed outcome:** hệ thống kết hợp được cả hai phần SLA và access trong một câu trả lời; đây là case khó nhất và là điểm cần ổn định thêm để luôn đạt Full.

---

## Lessons Learned

1. Thứ tự routing rule có ảnh hưởng lớn đến khả năng giữ đủ ý ở câu multi-hop.
2. `route_reason` rõ ràng giúp debug nhanh khi câu trả lời thiếu một phần criteria.
3. Cần thêm hậu kiểm deterministic sau synthesis cho `gq09` để tránh bỏ sót PagerDuty.
