# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** A20C1E402G4  
**Ngày:** 2026-04-14

Baseline Day 08 lấy từ `artifacts/day08_baseline/` (10 câu, chạy 2026-04-13).  
Day 09 lấy từ `eval_trace.py` run 2026-04-14 (15 câu, tất cả pass).

---

## 1. Metrics Comparison

| Metric | Day 08 dense | Day 08 hybrid | Day 09 multi-agent | Ghi chú |
|--------|-------------|--------------|-------------------|---------|
| **Faithfulness** (avg/5) | 4.60 | **5.00** | pending LLM-Judge re-run | Day 09 dùng same grounded prompt — không kỳ vọng regress |
| **Relevance** (avg/5) | 5.00 | 5.00 | pending | |
| **Context Recall** | 5.00 | 5.00 | pending | |
| **Completeness** (avg/5) | 4.29 | 3.00 | pending | Kỳ vọng > 3.00 nhờ policy worker + MCP |
| Avg confidence | N/A | N/A | **0.75** | Đo trực tiếp từ 15 traces Day 09 |
| Avg latency | ~2–3 s | ~2–3 s | **~6.0 s** | +2–3× do thêm Vertex AI embed |
| Abstain rate | 0/10 (0%) | 0/10 (0%) | **1/15 (7%)** | q09 ERR-403-AUTH abstain đúng |
| MCP usage rate | N/A | N/A | **7/15 (47%)** | Câu policy/access trigger MCP |
| HITL rate | N/A | N/A | **1/15 (7%)** | q09 ERR-\d+ pattern |
| Routing visibility | ✗ | ✗ | **✓ route_reason** | Mọi trace đều có lý do route |
| Test worker độc lập | ✗ | ✗ | **✓** | `python workers/retrieval.py` |

*LLM-as-Judge re-run trên Day 09 traces cần chạy sau khi có `grading_questions.json` (17:00).*

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

Ví dụ: q01 (SLA P1), q04 (account lock), q05 (remote policy), q06 (P1 escalation)

| Nhận xét | Day 08 hybrid | Day 09 multi-agent |
|---------|--------------|-------------------|
| Retrieval quality | High (faithfulness 5.00) | High (same hybrid RRF) |
| Latency | ~2–3 s | ~5–7 s (+2–4 s Vertex embed) |
| Routing overhead | N/A | Minimal — "default route" |

**Kết luận:** Với câu đơn giản, multi-agent không cải thiện chất lượng trả lời (retrieval và synthesis giống nhau), nhưng tốn thêm ~4 s latency do Vertex AI embedding. Đây là trade-off chấp nhận được vì câu đơn giản không phải mục tiêu tối ưu hoá.

### 2.2 Câu hỏi multi-hop (cross-document)

Ví dụ: q13 (Level 3 contractor P1), q15 (Level 2 + SLA 2am)

| Nhận xét | Day 08 hybrid | Day 09 multi-agent |
|---------|--------------|-------------------|
| Coverage | 1 retrieval pass duy nhất | policy_tool + retrieval + 3 MCP tools |
| Routing visible? | ✗ | ✓ `route_reason` ghi rõ keyword triggered |
| MCP context | Không có | `get_ticket_info` + `check_access_permission` bổ sung live context |
| Completeness (q13, q15) | Phụ thuộc chunk overlap | Policy worker cung cấp exception + MCP rule → synthesis có đủ evidence |

**Kết luận:** Day 09 rõ ràng hơn trên multi-hop nhờ policy worker tách biệt exception detection và MCP tools cung cấp context chính xác (Level 2 có emergency bypass, Level 3 không). Day 08 hybrid phụ thuộc hoàn toàn vào retrieval — nếu chunk không chứa đủ negative condition (Level 3 không bypass) thì synthesis có thể hallucinate.

### 2.3 Câu hỏi cần abstain

Ví dụ: q09 (ERR-403-AUTH — không có trong docs)

| Nhận xét | Day 08 hybrid | Day 09 multi-agent |
|---------|--------------|-------------------|
| q09 answer | "Không biết thông tin..." (abstain) | "Không đủ thông tin trong tài liệu nội bộ." (abstain) |
| Confidence | N/A | 0.30 |
| HITL triggered | ✗ | ✓ (auto-approve lab mode) |
| Hallucination risk | Phụ thuộc prompt | Thấp hơn — HITL gate + low confidence |

**Kết luận:** Cả hai hệ thống abstain đúng trên q09. Day 09 có thêm `hitl_triggered=True` và `confidence=0.30` làm tín hiệu rõ ràng hơn cho downstream system. Grading risk gq07 (penalty SLA không có trong docs) được kiểm soát tốt.

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Answer sai → phải đọc toàn bộ rag_answer.py
→ tìm lỗi: indexing? chunking? retrieval? prompt? không rõ
→ không có trace → không biết chunk nào đã retrieve
→ Ước tính: 15–20 phút để tìm nguyên nhân
```

### Day 09 — Debug workflow
```
Answer sai → mở artifacts/traces/{run_id}.json
→ đọc route_reason: biết ngay route đúng chưa
→ đọc retrieved_chunks: biết retrieval trả về gì
→ đọc mcp_tools_used: biết MCP output
→ đọc worker_io_logs: biết từng worker nhận và trả gì
→ Nếu route sai: sửa supervisor keyword list
→ Nếu retrieval sai: uv run python workers/retrieval.py
→ Nếu synthesis sai: uv run python workers/synthesis.py
→ Ước tính: 3–5 phút để tìm nguyên nhân
```

**Ví dụ debug thực tế trong lab:**  
Trong quá trình implement Sprint 2, synthesis trả về confidence 0.02 thay vì 0.7+ cho câu retrieval bình thường. Nguyên nhân: RRF scores (~0.008) nhỏ hơn 0.1, nhưng max normalisation logic có bug (`max_score=0` branch). Phát hiện bằng cách đọc `worker_io_logs[synthesis_worker].output.confidence` trong trace → sửa `_estimate_confidence()` trong 5 phút. Không cần trace mà tìm bug này trong monolith sẽ mất rất lâu.

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool mới (e.g., HR API) | Phải sửa prompt + retrieval | Thêm 1 tool vào `mcp_server.py` + 1 trigger rule trong `policy_tool.py` |
| Thêm 1 domain mới (e.g., Finance) | Phải re-index và re-tune prompt | Thêm 1 worker `finance_worker.py` + route rule trong supervisor |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline code | Sửa `retrieve_hybrid()` trong `workers/retrieval.py` độc lập |
| A/B test retrieval (dense vs hybrid) | Phải clone toàn pipeline | Thay `retrieve_hybrid` → `retrieve_dense` trong `run()` của retrieval_worker |
| Thêm LLM intent classifier cho supervisor | Cần refactor lớn | Chỉ sửa `supervisor_node()` trong `graph.py` |

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 LLM calls | Day 09 LLM calls | Day 09 latency |
|---------|-----------------|-----------------|----------------|
| Simple query (retrieval only) | 1 (synthesis) | 1 (synthesis) | ~5–7 s |
| Policy query (no MCP) | 1 (synthesis) | 1 (synthesis) | ~5–7 s |
| Policy query + MCP tools | 1 (synthesis) | 1 (synthesis) + 3 in-process MCP | ~7–9 s |
| Human review + retrieval | 1 (synthesis) | 1 (synthesis) | ~4–5 s |

**Ghi chú về latency:**  
Day 09 chậm hơn Day 08 chủ yếu do Vertex AI embedding (~2–3 s/query, cả indexing và retrieval time) chứ không phải do multi-agent overhead. Số lượng LLM calls vẫn là 1 per run — synthesis worker. MCP tools là in-process Python function calls, latency không đáng kể (<10 ms).

**Cost-benefit:**  
Thêm ~4 s latency để đổi lấy routing visibility, MCP context, và debuggable traces là trade-off hợp lý cho enterprise helpdesk (không cần real-time sub-second response). Nếu cần giảm latency, thay Vertex AI → OpenAI `text-embedding-3-small` (faster, lower cost).

---

## 6. Kết luận

**Multi-agent tốt hơn single agent ở:**
1. **Debuggability** — trace có `route_reason`, `worker_io_logs`, `mcp_tools_used` → tìm bug nhanh hơn 3–5×
2. **Multi-hop completeness** — policy worker tách exception detection; MCP tools cung cấp context live (ticket status, access rules) mà pure retrieval không có
3. **Extensibility** — thêm tool hoặc domain không cần sửa core pipeline; chỉ thêm worker hoặc MCP tool

**Multi-agent kém hơn hoặc không khác biệt:**
1. **Latency** — Day 09 chậm hơn ~2–3× do Vertex AI embedding (không phải do multi-agent pattern)
2. **Simple queries** — câu đơn giản (SLA, HR policy) không hưởng lợi từ routing; chất lượng trả lời giống nhau

**Khi nào KHÔNG nên dùng multi-agent:**  
Khi corpus đơn giản, câu hỏi không có multi-hop, latency là yêu cầu quan trọng, và đội ngũ nhỏ không có resource để maintain nhiều worker. Single-agent RAG đơn giản hơn nhiều và dễ onboard hơn.

**Nếu tiếp tục phát triển:**  
- Thay keyword routing trong supervisor bằng LLM intent classifier (giải quyết false positive "hoàn tiền" → policy_tool cho câu retrieval đơn giản)
- Implement real HTTP MCP server với FastAPI để test network boundary
- Thêm LLM-as-Judge tích hợp vào `eval_trace.py` để tự động tính faithfulness/completeness trên mọi run, không chỉ Day 08 baseline
