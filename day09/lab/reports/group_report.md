# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Team 62  
**Thành viên:**
| Tên | Vai trò | Sprint |
|-----|---------|--------|
| Trần Đình Minh Vương | Supervisor Owner + Integrator | Sprint 1 |
| Phan Thanh Sang | Worker Owner A (Retrieval) | Sprint 2 |
| Trần Tiến Dũng | Worker Owner B (Policy + Contracts) | Sprint 2 |
| Ngô Hải Văn | MCP Owner | Sprint 3 |
| Đỗ Minh Khiêm | Trace & Docs Owner + QA Release | Sprint 4 |

**Ngày nộp:** 2026-04-14  
**Repo:** https://github.com/hvan128/team62-lecture-Day-08-09-10

---

## 1. Kiến trúc nhóm đã xây dựng

Nhóm xây dựng hệ thống **Supervisor-Worker** gồm 4 thành phần chính: Supervisor (`graph.py`), 3 Workers (`retrieval.py`, `policy_tool.py`, `synthesis.py`), và MCP Server (`mcp_server.py`).

**Hệ thống tổng quan:** Supervisor nhận câu hỏi từ user, phân tích keyword và quyết định route sang 1 trong 3 nhánh: `retrieval_worker` (câu hỏi SLA/ticket), `policy_tool_worker` (câu hỏi policy/access control), hoặc `human_review` (error code không rõ + risk cao). Sau đó tất cả hội tụ về `synthesis_worker` để tổng hợp câu trả lời có citation. Toàn bộ luồng được ghi vào trace JSON với đầy đủ `route_reason`, `workers_called`, `mcp_tools_used`, và `confidence`.

**Routing logic cốt lõi:** Keyword matching 3 nhóm — (1) policy/access keywords ("hoàn tiền", "refund", "cấp quyền", "level 2/3") → `policy_tool_worker` + `needs_tool=True`; (2) SLA/ticket keywords ("p1", "sla", "escalation") → `retrieval_worker`; (3) error code pattern (ERR-xxx) + risk keyword ("khẩn cấp") → `human_review`. `route_reason` ghi rõ keyword nào trigger và MCP có enabled không.

**MCP tools đã tích hợp:**
- `search_kb`: Semantic search KB qua sentence-transformers + ChromaDB — gọi mỗi khi `needs_tool=True`
- `get_ticket_info`: Tra cứu ticket P1 (mock data) — gọi khi task chứa "ticket/p1/jira"
- `check_access_permission`: Kiểm tra điều kiện cấp quyền theo level — gọi khi task chứa "access/quyền/level"
- `create_ticket`: Tạo ticket mới (mock) — available nhưng chưa trigger trong lab

Ví dụ trace có MCP: `run_20260414_145911.json` — task "Cần cấp quyền Level 3 khẩn cấp", gọi 3 tools: `search_kb` + `check_access_permission` + `get_ticket_info`.

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:** Khi nào policy_tool_worker gọi MCP — `if not chunks` hay `if needs_tool`?
- **gq09** (P1 lúc 2am + cấp quyền Level 2 cho contractor): Multi-hop cần cả `sla_p1_2026.txt` và `access_control_sop.txt`. Policy route + MCP có thể xử lý được nhưng cần synthesis tổng hợp đúng 2 phần.

**Câu gq07 (abstain):** Pipeline route sang `retrieval_worker` (task không có policy keyword rõ), retrieve `sla_p1_2026.txt`. Nếu chunk không mention "mức phạt tài chính", synthesis worker sẽ trả về confidence thấp và answer nêu rõ "không có thông tin trong tài liệu" → đúng hướng abstain.

**Câu gq09 (multi-hop):** Task chứa "2am" (risk), "cấp quyền", "Level 2", "contractor" → route sang `policy_tool_worker` + `needs_tool=True`. MCP gọi `search_kb`, `check_access_permission(level=2, is_emergency=True)`, `get_ticket_info`. Trace ghi đủ 2+ workers — đủ điều kiện nhận trace bonus +1.

---

## 4. So sánh Day 08 vs Day 09

**Metric thay đổi rõ nhất:** Latency tăng từ ~1,500ms lên 4,821ms (+221%) — chi phí của multi-step pipeline. Tuy nhiên abstain rate tăng từ ~0% lên 23%, cho thấy Day 09 trả lời cẩn thận hơn thay vì hallucinate.

**Điều nhóm bất ngờ nhất:** MCP integration phức tạp hơn dự kiến không phải ở code mà ở thứ tự gọi. `policy_tool_worker_node` gọi `retrieval_run` trước → fill chunks → MCP `search_kb` không trigger dù đã viết đúng. Cần đọc trace mới phát hiện được. Đây là lý do trace rõ ràng quan trọng hơn việc code chạy được.

**Trường hợp multi-agent không giúp ích:** Câu hỏi đơn giản 1 tài liệu (VD: "SLA P1 là bao lâu?") — pipeline mất 5,655ms trong khi Day 08 ước tính ~1,500ms. Không có thêm accuracy nhưng tốn gấp 3.8× thời gian. Single agent đủ và tốt hơn cho loại câu này.

---

## 5. Phân công và đánh giá nhóm

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Trần Đình Minh Vương | `graph.py`: AgentState, supervisor_node, route_decision, LangGraph wiring, HITL flow | Sprint 1 |
| Phan Thanh Sang | `workers/retrieval.py`: run(), retrieve_dense(), ChromaDB integration, build_index.py | Sprint 2 |
| Trần Tiến Dũng | `workers/policy_tool.py`: analyze_policy(), LLM analysis, `workers/synthesis.py`, `contracts/worker_contracts.yaml` | Sprint 2 |
| Ngô Hải Văn | `mcp_server.py`: 4 tools, dispatch_tool(); fix retrieval embedding (sentence-transformers); fix MCP trigger logic trong policy_tool; route_reason MCP logging | Sprint 3 |
| Đỗ Minh Khiêm | `eval_trace.py`, 3 docs templates, group_report, individual report | Sprint 4 |

**Điều nhóm làm tốt:** Phân vai rõ ràng từ đầu — mỗi sprint có owner cụ thể. Commit message có prefix `sprint1/sprint2/sprint3(Van)` giúp trace được ai làm gì. Pipeline hoạt động end-to-end trước 17:00.
**Điều nhóm làm chưa tốt:** Không có integration test sớm giữa Sprint 1 và Sprint 2 — phát hiện bug `mcp_tools_used` rỗng muộn ở Sprint 3. Thứ tự gọi worker trong `policy_tool_worker_node` cần được thống nhất sớm hơn.

**Nếu làm lại:** Viết integration test sau Sprint 1 xong — chạy `graph.py` với mock workers ngay để xác nhận state flow đúng trước khi Sprint 2 implement workers thật.

---

## 6. Nếu có thêm 1 ngày

1. **LLM-based router thay keyword matching**: Trace cho thấy routing đôi khi sai với câu mơ hồ (ví dụ "truy cập hệ thống" trigger policy route thay vì retrieval). Một LLM classifier nhỏ (gpt-4o-mini, 1 call) sẽ chính xác hơn. Bằng chứng: 2/13 traces có route_reason không khớp với loại câu hỏi thực tế.

2. **Confidence-based retry**: Khi `confidence < 0.4`, supervisor retry với worker khác hoặc mở rộng top_k. Hiện tại ERR-9999 cho confidence 0.30 nhưng pipeline không có cơ chế tự cải thiện. Bằng chứng từ trace: 3 traces có confidence ≤ 0.52, tất cả đều có thể cải thiện với retry strategy.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
