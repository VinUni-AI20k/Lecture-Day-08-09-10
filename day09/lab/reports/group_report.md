# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** E402 — Nhóm 11  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Hà Hữu An | Supervisor Owner | ___ |
| Đỗ Văn Quyết | Worker Owner (Retrieval + Policy) | ___ |
| Hoàng Văn Kiên | Worker Owner (Synthesis) | ___ |
| Hồ Thị Tố Nhi | MCP Owner | ___ |
| Lê Hoàng Long | MCP Owner (get_ticket_info) | ___ |
| Lê Thị Phương | Trace & Docs Owner | ___ |

**Ngày nộp:** 14/04/2026  
**Repo:** E402_Nhom11_Day09  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

**Hệ thống tổng quan:**

Nhóm xây dựng hệ thống theo pattern **Supervisor-Worker** gồm 4 node chính: `supervisor_node`, `retrieval_worker`, `policy_tool_worker`, và `synthesis_worker`, cùng một `human_review_node` xử lý các trường hợp rủi ro cao. Hệ thống xử lý 3 loại câu hỏi: (1) tìm kiếm thông tin từ tài liệu nội bộ (SLA, FAQ, ticket), (2) kiểm tra chính sách rule-based (refund, access control), và (3) các trường hợp rủi ro cao cần HITL. MCP server được tích hợp với 4 tools để policy_tool_worker gọi khi cần.

**Routing logic cốt lõi:**

Supervisor dùng **keyword matching** để route. Nếu task chứa từ khoá policy/refund/access/hoàn tiền → `policy_tool_worker`. Nếu chứa SLA/ticket/escalation/FAQ → `retrieval_worker` (default). Nếu `risk_high=True` kết hợp mã lỗi `err-` → `human_review_node`. Flag `needs_tool=True` được set khi task liên quan access control.

**MCP tools đã tích hợp:**

- `search_kb`: Tìm kiếm knowledge base ChromaDB theo semantic query
- `get_ticket_info`: Lấy thông tin ticket theo ID từ mock DB (`tickets.json`)
- `tool_check_access_permission`: Kiểm tra quyền truy cập theo level và role
- `tool_create_ticket`: Tạo ticket mới, lưu vào `tickets.json`

Ví dụ trace gq09 (`run_20260414_165345.json`): `"workers_called": ["policy_tool_worker", "retrieval_worker", "synthesis_worker"]` — cả retrieval lẫn policy đều được gọi cho câu multi-hop.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Dùng **keyword-based routing** trong `supervisor_node` thay vì LLM classifier để phân loại câu hỏi.

**Bối cảnh vấn đề:**

Supervisor cần phân loại câu hỏi vào đúng worker trước khi xử lý. Nhóm phải chọn giữa hai hướng: gọi LLM để classify ý định (chính xác hơn nhưng chậm) hoặc dùng keyword matching (nhanh nhưng cần thiết kế keyword list tốt). Với domain hẹp gồm 3 loại câu hỏi rõ ràng (policy, SLA/ticket, risk), keyword matching đủ chính xác.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| LLM classifier | Hiểu ngữ cảnh, ít false positive | Tốn ~800ms/request, thêm API call, khó debug |
| Keyword matching | Nhanh (~5ms), zero latency, dễ trace | Cần maintain keyword list, dễ miss edge case |

**Phương án đã chọn và lý do:**

Nhóm chọn keyword matching vì domain đủ nhỏ và có tính cấu trúc. Keyword list phân chia rõ: `["hoàn tiền", "refund", "policy", "access", "quyền"]` → `policy_tool_worker`; `["sla", "ticket", "escalation", "p1", "p2"]` → `retrieval_worker`. Ngoài ra, keyword routing cho phép `route_reason` rõ ràng trong mỗi trace, giúp debug nhanh hơn khi routing sai.

**Bằng chứng từ trace/code:**

```json
// Trace gq01 — grading_run.jsonl
{
  "supervisor_route": "retrieval_worker",
  "route_reason": "sla / ticket query",
  "workers_called": ["retrieval_worker", "synthesis_worker"],
  "confidence": 0.80
}

// Trace gq02
{
  "supervisor_route": "policy_tool_worker",
  "route_reason": "policy / access task",
  "workers_called": ["policy_tool_worker", "retrieval_worker", "synthesis_worker"],
  "confidence": 0.90
}
```

---

## 3. Kết quả grading questions (150–200 từ)

**Tổng điểm raw ước tính:** ~70 / 96

**Câu pipeline xử lý tốt nhất:**

- **gq03** — `"Cần cấp Level 3 access"` → `policy_tool_worker`, confidence 0.95. Routing đúng, policy decision rõ ràng (`requires_approval`), kết hợp được cả SLA evidence và access control rule.
- **gq09** — câu multi-hop khó nhất: pipeline gọi đủ cả 3 workers (`policy_tool_worker → retrieval_worker → synthesis_worker`), confidence 0.95, trả về kết quả bao gồm cả SLA P1 notification lẫn điều kiện cấp Level 2 access.

**Câu pipeline fail hoặc partial:**

- **gq06** — `"Nhân viên mới probation muốn làm remote"` → route vào `retrieval_worker` nhưng không có document liên quan → trả về `fallback`, confidence 0.70. Root cause: thiếu document về remote work policy trong knowledge base.
- **gq08** — `"Đổi mật khẩu sau bao nhiêu ngày"` → tương tự gq06, không có document IT security policy → `fallback`, confidence 0.70.

**Câu gq07 (abstain):** Pipeline route vào `retrieval_worker` và trả về kết quả SLA P1 liên quan, confidence 0.80 — **chưa abstain đúng**. Hệ thống chưa detect được đây là câu hỏi về thông tin không có trong tài liệu (mức phạt tài chính cụ thể). Synthesis Worker có cơ chế abstain nhưng chưa đủ mạnh để override khi retrieval trả về chunk có liên quan mờ nhạt.

**Câu gq09 (multi-hop):** Trace ghi nhận đủ 2 workers chính (`policy_tool_worker` + `retrieval_worker`) cùng `synthesis_worker`. Kết quả hợp lệ.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

**Metric thay đổi rõ nhất (có số liệu):**

| Metric | Day 08 | Day 09 | Ghi chú |
|--------|--------|--------|---------|
| Avg confidence | 0.76 | 0.584 | Day 09 dùng mock workers |
| Avg latency (ms) | 7,448 | 20,587 | Day 09 overhead từ multi-node graph |
| Routing visibility | Không có | Có `route_reason` | Dễ debug hơn |
| Debuggability | Thấp | Cao | Test từng worker độc lập |

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**

Routing visibility là lợi ích thực tế nhất — mỗi trace đều có `route_reason` và `workers_called`, giúp xác định ngay câu hỏi nào bị route sai mà không cần đọc toàn bộ log. Với Day 08 single agent, khi answer sai không biết lỗi ở prompt hay retrieval hay context window.

Điều bất ngờ thứ hai: latency tăng mạnh (20,587ms vs 7,448ms) dù workers là mock (không gọi API thật). Overhead đến từ LangGraph state management và nhiều node transition, không phải từ LLM calls.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**

Câu gq06 và gq08 (information not in KB) — cả single agent lẫn multi-agent đều trả về fallback. Multi-agent thêm latency nhưng kết quả tương đương. Với những câu hỏi đơn giản chỉ cần retrieval 1 bước, pipeline 3-node (supervisor → retrieval → synthesis) chậm hơn single agent ~3x mà không cải thiện chất lượng.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Hà Hữu An | `graph.py` — supervisor_node, routing logic, HITL | Sprint 1–2 |
| Đỗ Văn Quyết | `workers/retrieval.py`, `workers/policy_tool.py`, `mcp_server.py` | Sprint 2–3 |
| Hoàng Văn Kiên | `workers/synthesis.py` — synthesize, confidence scoring | Sprint 2–3 |
| Hồ Thị Tố Nhi | `mcp_server.py` — Hybrid MCP dispatcher, FastAPI HTTP mode | Sprint 3 |
| Lê Hoàng Long | `mcp_server.py` — `get_ticket_info`, `TICKET_DB` | Sprint 3 |
| Lê Thị Phương | `eval_trace.py`, `docs/`, `artifacts/` — trace format, metrics | Sprint 3–4 |

**Điều nhóm làm tốt:**

Interface `run(state) -> state` được định nghĩa rõ trong contracts từ sớm, giúp các worker có thể develop độc lập và tích hợp không bị xung đột. Trace format chuẩn 12 field giúp debug nhanh.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**

Knowledge base thiếu documents về remote work policy và IT security (password policy) dẫn đến gq06, gq08 fallback. Abstain logic của synthesis_worker chưa đủ mạnh để xử lý gq07 đúng.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**

Bổ sung bước kiểm tra coverage của knowledge base ngay từ Sprint 1 — đọc tất cả grading question categories rồi đảm bảo có document tương ứng trước khi build worker.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ thực hiện 2 cải tiến:

1. **Bổ sung knowledge base** cho các topic bị fallback (remote work policy, IT security/password policy) — gq06 và gq08 hiện trả về `fallback` với confidence 0.70, cải thiện KB trực tiếp tăng điểm raw.

2. **Cải thiện abstain logic** trong `synthesis_worker` — hiện gq07 (mức phạt tài chính) không abstain đúng dù thông tin không có trong tài liệu. Cần bổ sung LLM-as-Judge để đánh giá relevance trước khi synthesis, hoặc threshold confidence thấp hơn cho retrieval kết quả mờ nhạt.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
