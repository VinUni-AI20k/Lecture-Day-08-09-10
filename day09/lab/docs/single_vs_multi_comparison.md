# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** Team 62  
**Ngày:** 2026-04-14

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | ~0.70 (ước tính) | 0.54 | −0.16 | Day 09 thực tế hơn — low confidence khi KB thiếu |
| Avg latency (ms) | ~1,500 | 4,821 | +3,321ms | Day 09 có LLM call trong synthesis |
| Abstain rate (%) | ~0% | ~23% (3/13 traces) | +23% | Day 09 nói rõ "không đủ thông tin" |
| Multi-hop accuracy | Thấp | Cao hơn | ↑ | Day 09 có policy_tool + MCP cross-doc |
| Routing visibility | ✗ Không có | ✓ `route_reason` mọi trace | N/A | |
| Debuggability | Khó | Dễ hơn | ↑ | Test từng worker độc lập được |
| MCP extensibility | ✗ Không có | ✓ 4 tools | N/A | |

> **Nguồn Day 09:** Tính từ 4 traces có latency thực trong `artifacts/traces/`: 5655ms, 3468ms, 5211ms, 4950ms → avg = **4,821ms**.

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Cao | Cao |
| Latency | ~1,500ms | ~5,655ms |
| Observation | Đủ với 1 LLM call | Overhead do multi-step |

**Kết luận:** Multi-agent **không cải thiện** câu hỏi đơn giản — chậm hơn ~3.8× do thêm bước retrieval worker + synthesis worker riêng. Với câu "SLA xử lý ticket P1 là bao lâu?", cả hai đều trả lời đúng nhưng Day 09 mất 5,655ms.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Thấp — chỉ retrieve 1 doc | Cao hơn — policy_tool + MCP |
| Routing visible? | ✗ | ✓ |
| Observation | Không có cơ chế ưu tiên 2 doc | MCP gọi `search_kb` + `check_access_permission` |

**Kết luận:** Multi-agent **cải thiện rõ** với câu hỏi multi-hop. Câu "Level 3 + P1 khẩn cấp" cần cross-reference `access_control_sop.txt` và `sla_p1_2026.txt`. Day 09 gọi 3 MCP tools và trả lời đầy đủ cả hai phần trong 5,211ms.

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | ~0% | ~23% |
| Hallucination risk | Cao | Thấp hơn — confidence + HITL |
| Observation | Không có cơ chế abstain rõ | confidence 0.30, HITL triggered |

**Kết luận:** Multi-agent **tốt hơn rõ** về abstain. Với câu ERR-9999, Day 09 trigger HITL (risk_high), confidence 0.30, answer ghi rõ "Không đủ thông tin trong tài liệu nội bộ". Day 08 không có cơ chế này.

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Khi answer sai → đọc toàn bộ RAG pipeline (1 file)
→ không biết lỗi ở embedding / retrieval / prompt / generation
→ không có trace để xem lại
Thời gian ước tính: 15–20 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace JSON trong artifacts/traces/
→ xem supervisor_route: route đúng chưa?
  → route sai: sửa keyword trong route_decision() (graph.py)
  → retrieval sai: python workers/retrieval.py (test độc lập)
  → policy sai: python workers/policy_tool.py (test độc lập)
  → synthesis sai: xem retrieved_sources đúng tài liệu chưa?
Thời gian ước tính: 5–8 phút
```

**Ví dụ debug thực tế trong lab:**  
Sprint 3 phát hiện `mcp_tools_used` luôn rỗng dù route là `policy_tool_worker`. Đọc trace thấy `workers_called: ["retrieval_worker", "policy_tool_worker", "synthesis_worker"]` — retrieval đã fill chunks trước → điều kiện `if not chunks and needs_tool` không trigger. Fix: đổi sang `if needs_tool:`. Thời gian debug: ~5 phút nhờ trace rõ ràng.

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa prompt + re-test toàn pipeline | Thêm function trong `mcp_server.py` |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới, không ảnh hưởng cũ |
| Thay đổi retrieval | Sửa trực tiếp pipeline | Sửa `retrieval_worker` độc lập |
| A/B test một phần | Phải clone toàn pipeline | Swap worker hoặc MCP tool |

**Nhận xét:** Thực tế trong lab, MCP Owner (Sprint 3) thêm `check_access_permission` tool mà không cần các thành viên khác sửa file. Đây là lợi ích rõ nhất của kiến trúc modular.

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 LLM calls | Day 09 LLM calls |
|---------|-----------------|-----------------|
| Simple query (SLA P1) | 1 | 1 (synthesis) |
| Policy query (Flash Sale) | 1 | 1 (policy) + 1 (synthesis) = 2 |
| Multi-hop (Level 3 + P1) | 1 | 2 LLM + 3 MCP calls |

Day 09 tốn 2× LLM calls với câu hỏi phức tạp nhưng mỗi call nhỏ hơn và focused hơn. Trade-off chấp nhận được vì accuracy và debuggability tăng đáng kể.

---

## 6. Kết luận

**Multi-agent tốt hơn ở:**

1. **Debuggability**: Trace ghi `route_reason`, `workers_called`, `mcp_tools_used` → tìm lỗi nhanh hơn ~3×
2. **Multi-hop accuracy**: Policy worker + MCP xử lý câu hỏi cross-document tốt hơn
3. **Abstain quality**: Confidence score + HITL → giảm hallucination
4. **Extensibility**: Thêm MCP tool hoặc worker mới không ảnh hưởng toàn hệ thống

**Multi-agent kém hơn ở:**

1. **Latency**: Chậm hơn ~3× với câu đơn giản (overhead multi-step)
2. **Cost**: 2× LLM calls với câu policy phức tạp

**Khi nào KHÔNG nên dùng multi-agent:** Câu hỏi đơn giản, latency-sensitive, hoặc KB nhỏ domain hẹp.
**Nếu tiếp tục phát triển:** Thêm LLM-based router thay keyword matching, implement confidence-based retry, và thêm `hr_worker` riêng cho HR policy queries.
