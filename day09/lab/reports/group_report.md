# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** C401-E3  
**Ngày nộp:** 14/04/2026  
**Repo:** https://github.com/jot2003/Lab8-Lab9-Lab10_C401_E3

## Thành viên và vai trò

| Tên | Vai trò |
|-----|---------|
| Đặng Đình Tú Anh | Supervisor Owner |
| Phạm Quốc Dũng | Retrieval + MCP Owner |
| Quách Gia Được | Policy Worker Owner |
| Hoàng Kim Trí Thành | Synthesis + Eval Owner |
| Nguyễn Thành Nam | Trace + Docs Owner |

---

## 1) Kiến trúc hệ thống

Nhóm triển khai kiến trúc Supervisor-Worker gồm `graph.py` (router), `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py` và `mcp_server.py`.

- Supervisor quyết định route và ghi `supervisor_route`, `route_reason`.
- Retrieval lấy bằng chứng từ ChromaDB.
- Policy worker gọi MCP tools (`search_kb`, `get_ticket_info`, `check_access_permission`) cho các case policy/access.
- Synthesis tạo câu trả lời grounded, trả `answer`, `sources`, `confidence`.

Hệ thống chạy đủ ba nhánh chính: `retrieval_worker`, `policy_tool_worker`, `multi_hop`.

---

## 2) Quyết định kỹ thuật chính

**Quyết định:** dùng rule-based routing theo thứ tự ưu tiên (`multi_hop` -> `sla` -> `policy` -> fallback) thay vì LLM router.

**Lý do chọn:**
- deterministic và dễ debug bằng trace;
- giữ được độ ổn định giữa các lần chạy grading;
- phù hợp rubric Day 09 yêu cầu giải thích route.

---

## 3) Kết quả grading ở phiên bản hiện tại

Nhóm chốt theo file `artifacts/grading_run.jsonl` mới nhất ở local sau lần chạy lại với bộ câu custom.

- **Điểm ước lượng nội bộ:** `88/96` raw (~`27.5/30`).
- **Các câu ổn định:** `gq01`, `gq03`, `gq04`, `gq05`, `gq06`, `gq07`, `gq08`, `gq10`.
- **Điểm nghẽn chính:** `gq09` còn thiếu đủ bộ notification channels trong một số lần sinh câu trả lời (đặc biệt thiếu PagerDuty), nên dễ bị chấm Partial.

Ghi chú: kết quả có dao động giữa các run do bước synthesis vẫn dùng LLM generation.

---

## 4) So sánh Day 08 vs Day 09

- Day 09 mạnh hơn ở **debuggability**: trace có `route_reason`, `workers_called`, `mcp_tools_used`.
- Day 09 mạnh hơn ở câu **multi-hop/policy** nhờ tách worker và MCP boundary.
- Day 09 chậm hơn Day 08 do thêm bước route + orchestration.

Day 08 baseline trong repo (`day08/lab/results/grading_auto.json`) có projected ~`25.41/30`; Day 09 hiện đạt mức ~`27.5/30` theo run mới nhất.

---

## 5) Phân công công việc

| Thành viên | Phần chính |
|------------|------------|
| Tú Anh | `graph.py`, routing, state contracts |
| Quốc Dũng | `retrieval.py`, MCP integration core |
| Gia Được | `policy_tool.py`, exception path |
| Trí Thành | `synthesis.py`, `eval_trace.py`, grading loop |
| Thành Nam | docs/report tổng hợp |

---

## 6) Nếu có thêm 1 ngày

1. Thêm post-check deterministic cho `gq09` để bắt buộc đủ 3 kênh SLA notification.
2. Thêm auto-grader script bám `grading_criteria` để giảm sai số chấm tay giữa các lần run.
