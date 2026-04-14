# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** E402_Nhom11  
**Ngày:** 2026-04-14

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Số liệu lấy từ:
> - Day 08: `python eval.py` → results/day08_baseline_metrics.json
> - Day 09: `python eval_trace.py` → artifacts/eval_report.json

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.76 | 0.827 | +0.067 | Day 09 cao hơn nhờ policy checking |
| Avg latency (ms) | 7448 | ~0 (mock workers) | -7448 | Day 09 dùng mock, không so sánh công bằng |
| Abstain rate (%) | 0% | 60% | +60% | Day 09 abstain nhiều hơn do mock KB nhỏ |
| Multi-hop accuracy | 0.4 | 0.95 (q13, q15) | +0.55 | Multi-agent xử lý multi-hop tốt hơn |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Day 09 giải thích được tại sao chọn worker |
| Debug time (estimate) | ~15 phút | ~3 phút | -12 phút | Trace + worker isolation giúp debug nhanh |
| HITL support | ✗ Không có | ✓ 6% câu trigger HITL | N/A | Day 09 nhận biết câu hỏi rủi ro cao |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Cao (LLM grounded tốt) | Tương đương (mock KB hạn chế) |
| Latency | ~7448ms (gọi LLM) | ~0ms (mock workers) |
| Observation | Pipeline đơn giản, 1 LLM call | Supervisor → Retrieval → Synthesis, 3 steps |

**Kết luận:** Với câu hỏi đơn giản (q01, q04, q05), multi-agent **không cải thiện đáng kể** so với single-agent. Thêm overhead routing nhưng kết quả tương tự. Single-agent pipeline đơn giản hơn cho use case này.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | 0.4 (khó reasoning cross-doc) | 0.95 (q13, q15) |
| Routing visible? | ✗ | ✓ route_reason giải thích tại sao chọn worker |
| Observation | LLM phải tự reasoning qua nhiều docs | Policy Worker + Retrieval Worker phối hợp |

**Kết luận:** Multi-agent **tốt hơn rõ rệt** cho câu hỏi multi-hop. Ví dụ q15 (SLA + Access Control) — Day 09 route sang `policy_tool_worker` rồi tự gọi `retrieval_worker` để lấy cả hai nguồn evidence, confidence đạt 0.95. Day 08 phải nhờ LLM tự suy luận cross-document.

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | 0% (LLM có xu hướng trả lời mọi thứ) | 60% (mock KB trả fallback) |
| Hallucination cases | Có thể xảy ra khi LLM tự tin trả lời | Ít hơn vì bám vào retrieved chunks |
| Observation | Single-agent không biết khi nào nên abstain | Multi-agent: retrieval trả về fallback → synthesis nhận ra |

**Kết luận:** Day 08 có abstain_rate = 0% — LLM luôn trả lời, kể cả khi không có đủ evidence. Day 09 abstain_rate cao hơn (60%) nhưng phần lớn do mock KB nhỏ. Tuy nhiên, cơ chế abstain đúng hơn: khi retrieval không tìm thấy → confidence thấp → synthesis trả lời "Không tìm thấy..." thay vì hallucinate.

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: ~15 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic (keyword lists)
  → Nếu retrieval sai → test retrieval_worker độc lập: python workers/retrieval.py
  → Nếu synthesis sai → test synthesis_worker độc lập: python workers/synthesis.py
  → Nếu policy sai → test policy_tool_worker độc lập: python workers/policy_tool.py
Thời gian ước tính: ~3 phút
```

**Câu cụ thể nhóm đã debug:**

Câu q09 ("ERR-403-AUTH") — pipeline trả lời "Không tìm thấy dữ liệu phù hợp" với confidence 0.70. Nhờ trace, nhóm thấy ngay:
1. `supervisor_route = human_review` → HITL triggered (đúng vì có error code)
2. Sau auto-approve → `retrieval_worker` → không tìm thấy keyword match → fallback
3. **Root cause:** Mock KB không có tài liệu về error codes → abstain đúng

Nếu dùng Day 08 pipeline, nhóm sẽ phải đọc toàn bộ code từ indexing → retrieval → generation để hiểu tại sao LLM trả lời sai.

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt + logic code | Thêm MCP tool trong `mcp_server.py` + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt + sửa retrieval | Thêm 1 worker mới + routing keyword |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline monolithic | Sửa `retrieval_worker` độc lập, test riêng |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker, giữ nguyên graph |

**Nhận xét:**

Multi-agent architecture có extensibility vượt trội. Ví dụ: thêm tool `check_access_permission` chỉ cần:
1. Định nghĩa schema trong `mcp_server.py` TOOL_SCHEMAS
2. Implement function trong `mcp_server.py`
3. Gọi từ `policy_tool_worker` khi `needs_tool=True`

Không cần sửa `graph.py`, `supervisor_node`, hay bất kỳ worker nào khác.

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query (q01) | 1 LLM call (embedding + generation) | 0 LLM calls (mock workers) |
| Complex query (q15) | 1 LLM call | 0 LLM calls (mock) |
| MCP tool call | N/A | 0 (chưa tích hợp MCP thật) |

> **Lưu ý:** Day 09 lab hiện dùng mock workers (không gọi LLM thật) nên latency ~0ms. Trong production:

| Scenario thực tế (ước tính) | Day 08 | Day 09 |
|-----|--------|--------|
| Simple query | 1 embedding + 1 generation = ~2s | 1 embedding + 1 generation + routing overhead = ~2.5s |
| Complex query (multi-hop) | 1 embedding + 1 generation = ~2s | 2 embeddings + 1 policy LLM + 1 synthesis LLM = ~5s |

**Nhận xét về cost-benefit:**

Multi-agent tốn nhiều LLM calls hơn (~2-3x cho complex queries) nhưng đổi lại:
- **Câu trả lời chính xác hơn** cho multi-hop queries (confidence 0.95 vs 0.4)
- **Dễ debug** khi có lỗi (3 phút vs 15 phút)
- **Extensible** — thêm tool/domain mới không cần sửa core
- **Trace có trách nhiệm giải trình** (route_reason, workers_called, confidence)

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. **Multi-hop reasoning**: Confidence 0.95 vs 0.4 — multi-agent phối hợp policy_worker + retrieval_worker cho kết quả cross-document tốt hơn rõ rệt.
2. **Debuggability & Observability**: Trace file ghi lại toàn bộ routing decision, workers called, confidence → debug nhanh gấp 5x (3 phút vs 15 phút).
3. **HITL (Human-in-the-Loop)**: Tự động nhận biết câu hỏi rủi ro cao (ERR codes, emergency) → trigger human review. Single-agent không có khả năng này.

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. **Câu hỏi đơn giản**: Thêm overhead routing không mang lại cải thiện, single-agent pipeline đơn giản hơn và nhanh hơn.
2. **Latency cao hơn trong production**: Nhiều LLM calls → tốn thêm ~2-3 giây cho complex queries.

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi domain đơn giản, chỉ có 1 loại câu hỏi, không cần policy checking hay multi-hop reasoning. Ví dụ: FAQ bot đơn giản với 50 câu hỏi và 1 knowledge base nhỏ → single-agent RAG đủ tốt và nhanh hơn.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

1. **Thay mock workers bằng real workers** gọi ChromaDB thật + LLM synthesis (đã implement trong `workers/` nhưng chưa tích hợp vào `graph.py`)
2. **LLM-based supervisor** thay vì keyword matching → xử lý câu hỏi ambiguous tốt hơn
3. **MCP HTTP server** thật (FastAPI) thay vì in-process mock → extensible cho external tools
4. **Confidence-based HITL** — nếu confidence < 0.4 tự động trigger human review thay vì chỉ dựa vào error codes
