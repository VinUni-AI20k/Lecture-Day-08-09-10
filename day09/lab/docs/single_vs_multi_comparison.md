# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** Y3  
**Ngày:** 14/4/2026

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Điền vào bảng sau. Lấy số liệu từ:
> - Day 08: chạy `python eval.py` từ Day 08 lab
> - Day 09: chạy `python eval_trace.py` từ lab này

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.568 | 0.55 | -0.018 | Multi-agent thấp hơn nhẹ do có abstain cases |
| Avg latency (ms) | 2203 | 4378 | +2175ms | Day 09 thêm LLM supervisor + MCP calls |
| Abstain rate (%) | 10% | 15% | +5% | Day 09 HITL triggered 9/57 câu |
| Multi-hop accuracy | 6/10 (60%) | N/A | N/A | Day 09 chưa có grading kết quả |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Day 09 trace rõ từng bước |
| Debug time (estimate) | ~15–20 phút | ~5–8 phút | -12 phút | Day 09 có trace + test worker độc lập |
| MCP usage rate | N/A | 31% (18/57) | N/A | Day 08 không có MCP capability |


---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | ~60% | Tương đương | 
| Latency | 2203ms | 4378ms |
| Observation | Nhanh, 1 LLM call | Chậm hơn 2x vì thêm supervisor call |

Kết luận: Multi-agent KHÔNG cải thiện với câu đơn giản — latency tăng gấp đôi

_________________

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | 6/10 | N/A (chờ grading) |
| Routing visible? | ✗ | ✓ |
| Observation | Không biết bước nào sai | route_reason giải thích rõ tại sao chọn worker |

Kết luận: Day 09 route đúng loại câu — policy câu hỏi về hoàn tiền/quyền truy cập
→ policy_tool_worker (42%), câu tra cứu → retrieval_worker (57%).

_________________

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | 10% | 15% (HITL triggered) |
| Hallucination cases | Có | Giảm — synthesis abstain khi chunks rỗng |
| Observation | Không có cơ chế dừng | HITL 9/57 câu, confidence < 0.4 flag warning |

Kết luận: Day 09 an toàn hơn — có abstain condition rõ ràng và HITL flag.

_________________

---

## 3. Debuggability Analysis

Day 08: ~15–20 phút
→ Phải đọc toàn bộ pipeline, không có trace, không biết bắt đầu từ đâu

Day 09: ~5–8 phút  
→ Đọc trace → xem supervisor_route + route_reason
→ Route sai → sửa supervisor
→ Retrieval sai → test workers/retrieval.py độc lập
→ Synthesis sai → test workers/synthesis.py độc lập

Câu debug thực tế: Phát hiện qua trace rằng 9/57 câu trigger HITL —
xem route_reason xác định supervisor đang flag risk_high cho những câu
nào, từ đó điều chỉnh ngưỡng risk trong system prompt supervisor.

### Day 08 — Debug workflow
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 15–20 phút

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: 5–8 phút
```

**Câu cụ thể nhóm đã debug:**

Task: "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?"

Vấn đề: Pipeline trả về answer thiếu thông tin về emergency bypass.

Quá trình debug qua trace:
1. Xem supervisor_route → đúng: policy_tool_worker
2. Xem route_reason → "task contains access/emergency keyword"
3. Xem mcp_tools_used → phát hiện get_ticket_info trả về error dict
   vì tool không có trong TOOL_REGISTRY (bị comment out)
4. Xem retrieved_chunks → chunks từ access_control_sop.txt có điểm score thấp
5. Kết luận: lỗi ở MCP layer, không phải supervisor hay synthesis

Fix: Gọi trực tiếp check_access_permission thay vì get_ticket_info
→ answer có đủ thông tin required_approvers và emergency_override.

Thời gian debug: ~6 phút nhờ trace rõ từng bước.

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker |

**Nhận xét:**

Day 09 dễ extend hơn rõ rệt nhờ kiến trúc modular:
- Thêm MCP tool mới chỉ cần thêm function vào `mcp_server.py` và đăng ký vào
  `TOOL_REGISTRY` — không động vào logic supervisor hay workers khác.
- Trong lab, `check_access_permission` được thêm độc lập mà không ảnh hưởng
  `search_kb` đang chạy.
- 31% queries (18/57) đã dùng MCP thành công, chứng minh extension hoạt động
  trong thực tế mà không cần sửa core pipeline.

Day 08 bị tightly coupled — mọi thay đổi đều phải sửa toàn bộ prompt và
re-test toàn pipeline, không thể isolate từng phần.

_________________

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 2 LLM calls (supervisor + synthesis) + 1 embedding |
| Complex query | 1 LLM call | 2 LLM calls + 1 embedding + MCP dispatch |
| MCP tool call | N/A | 18/57 queries (31%) dùng MCP |

Nhận xét: Day 09 latency cao gấp đôi (2203ms → 4378ms). 
Cost hợp lý cho câu phức tạp cần routing chính xác và MCP tool.
Không đáng với câu đơn giản — nên dùng hybrid: keyword match trước,
LLM supervisor chỉ khi không match rõ.

_________________

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

Multi-agent tốt hơn:
1. Debuggability — trace rõ từng bước (supervisor_route, route_reason,
   workers_called), test từng worker độc lập không cần chạy toàn pipeline
2. Extensibility — thêm MCP tool mới không cần sửa core logic;
   31% queries đã dùng MCP thành công (18/57)

Multi-agent kém hơn/không khác biệt:
1. Latency tăng gấp đôi (2203ms → 4378ms) và confidence giảm nhẹ
   (0.568 → 0.55) — overhead supervisor không đáng với câu đơn giản

Khi nào KHÔNG nên dùng multi-agent:
Câu hỏi đơn giản, single-document, không cần policy check — single
agent RAG đủ dùng, nhanh hơn 2x và confidence cao hơn.

Nếu tiếp tục phát triển:
Thêm Evaluator Worker tự đánh giá chất lượng answer trước khi trả về,
implement HITL thực sự thay vì auto-approve, và dùng hybrid routing
(keyword match + LLM fallback) để giảm latency với câu đơn giản.
