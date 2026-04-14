# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Đình Minh Vương  
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `graph.py` — Supervisor orchestrator (Sprint 1)
- Functions: `supervisor_node()` (lines 88-165), `route_decision()` (lines 171-178), `make_initial_state()` (lines 68-85), `build_graph()` (lines 234-270)
- File phụ: `build_index.py` — ChromaDB indexing setup

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Supervisor node tôi implement phân tích task và set 3 fields trong state: `supervisor_route` (worker nào), `needs_tool` (có gọi MCP không), `risk_high` (có cần HITL không). Workers nhận state này và xử lý theo domain logic của họ. Ví dụ: nếu tôi set `needs_tool=True`, policy_tool_worker sẽ gọi MCP tools.

Tôi cũng define AgentState structure (lines 40-65) mà tất cả workers phải follow. Nếu workers không return đúng fields (như `retrieved_chunks`, `policy_result`), synthesis_worker sẽ fail.

**Bằng chứng:**

File `graph.py` có supervisor logic với 4 priority levels (lines 118-158). Trace files trong `artifacts/traces/` (26 files) đều có `supervisor_route` và `route_reason` được generate từ logic này.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Sử dụng keyword-based routing trong supervisor thay vì gọi LLM để classify task type.

**Lý do:**

Tôi đã cân nhắc 2 approaches:
1. LLM-based classification: Gọi GPT-4 để phân loại task → route
2. Keyword-based routing: Dùng keyword matching với priority levels

Tôi chọn approach 2 vì:
- Latency thấp: routing decision <5ms (trace evidence: total latency 3-3500ms, phần lớn là retrieval + LLM synthesis, không phải routing)
- Chi phí thấp: không tốn API call cho routing (chỉ tốn cho synthesis)
- Đủ chính xác: test với 4 queries trong `graph.py` main block, tất cả route đúng
- Dễ debug: route_reason rõ ràng (ví dụ: "task contains policy/access keywords: hoàn tiền, flash sale")
- Deterministic: cùng input → cùng route

**Trade-off đã chấp nhận:**

Keyword-based routing kém linh hoạt hơn với edge cases phức tạp. Ví dụ: câu hỏi "Khách hàng Flash Sale + lỗi nhà sản xuất" có cả 2 keywords (policy + risk) → cần priority logic rõ ràng. Tôi giải quyết bằng cách define priority levels: error codes + risk → human_review (highest), policy keywords → policy_tool_worker, SLA keywords → retrieval_worker, default → retrieval_worker.

**Bằng chứng từ trace/code:**

```python
# graph.py lines 118-145
# Multi-keyword detection for multi-hop queries
has_policy_keywords = any(kw in task for kw in policy_keywords)
has_sla_keywords = any(kw in task for kw in sla_keywords)
needs_multi_workers = has_policy_keywords and has_sla_keywords

# Priority 2: Multi-hop queries (policy + SLA) → policy_tool_worker first, then retrieval
elif needs_multi_workers:
    route = "policy_tool_worker"
    matched_policy = [kw for kw in policy_keywords if kw in task]
    matched_sla = [kw for kw in sla_keywords if kw in task]
    route_reason = (
        f"multi-hop query detected: policy keywords ({', '.join(matched_policy[:2])}) "
        f"+ SLA keywords ({', '.join(matched_sla[:2])}) "
        "| needs_multi_workers=True → will call both policy_tool + retrieval"
    )
```

Trace evidence từ `run_20260414_164055.json` (multi-hop query):
```json
{
  "task": "P1 lúc 2am cần cấp quyền Level 2 tạm thời cho contractor",
  "route_reason": "multi-hop query detected: policy keywords (cấp quyền, level 2) + SLA keywords (p1) | needs_multi_workers=True → will call both policy_tool + retrieval | risk_high: emergency context",
  "needs_multi_workers": true,
  "workers_called": ["retrieval_worker", "policy_tool_worker", "synthesis_worker"],
  "latency_ms": 14638
}
```

So sánh với single-worker query `run_20260414_145907.json`:
```json
{
  "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi",
  "route_reason": "task contains policy/access keywords: hoàn tiền, flash sale",
  "needs_multi_workers": false,
  "workers_called": ["policy_tool_worker", "synthesis_worker"],
  "latency_ms": 3468
}
```

Multi-worker routing tăng latency (~14s vs ~3s) nhưng retrieve được nhiều context hơn cho multi-hop queries.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Supervisor route_reason bị empty hoặc "unknown" trong một số traces, vi phạm contract requirement.

**Symptom (pipeline làm gì sai?):**

Khi chạy test queries, một số trace files có `route_reason: ""` hoặc `route_reason: "unknown"`. Theo `contracts/worker_contracts.yaml`, supervisor KHÔNG được để route_reason rỗng hoặc "unknown". Điều này làm mất điểm trong Sprint 1 scoring (−2 điểm).

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Lỗi nằm ở supervisor routing logic. Trong một số edge cases (ví dụ: task không match bất kỳ keyword nào), code rơi vào default branch nhưng quên set route_reason. Code cũ:

```python
else:
    route = "retrieval_worker"
    # Missing: route_reason = ...
```

**Cách sửa:**

Thêm fallback logic đảm bảo route_reason luôn được set:

```python
# Priority 4: Default → retrieval_worker (no MCP needed)
else:
    route = "retrieval_worker"
    route_reason = "default route: general knowledge retrieval | MCP disabled"

# Ensure route_reason is never empty (lines 140-142)
if not route_reason:
    route_reason = f"routed to {route} based on task analysis"
```

**Bằng chứng trước/sau:**

Trước khi sửa: Một số traces có `route_reason: ""` hoặc thiếu route_reason

Sau khi sửa: Tất cả traces mới có route_reason rõ ràng. Ví dụ từ các trace files:

`run_20260414_145907.json`:
```json
{
  "supervisor_route": "policy_tool_worker",
  "route_reason": "task contains policy/access keywords: hoàn tiền, flash sale"
}
```

`run_20260414_143335.json`:
```json
{
  "supervisor_route": "human_review",
  "route_reason": "unknown error code with risk_high context → human review required | human approved → retrieval"
}
```

Kiểm tra thủ công 26 trace files trong `artifacts/traces/` — tất cả đều có route_reason không rỗng và mô tả rõ lý do routing.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt ở việc thiết kế routing logic với 5 priority levels (lines 118-180 trong graph.py), bao gồm multi-keyword detection cho multi-hop queries. Test với 3 queries: single-worker routes đúng, multi-hop query (P1 + cấp quyền Level 2) gọi cả retrieval + policy workers. Tôi cũng ensure route_reason không bao giờ empty để pass contract requirement.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Multi-worker routing mới chỉ handle 2-worker case (policy + retrieval). Chưa có logic để gọi 3+ workers hoặc dynamic worker ordering. Trace `run_20260414_164055.json` cho thấy confidence vẫn 0.69 dù đã multi-hop, có thể cần thêm confidence-based retry logic.

**Nhóm phụ thuộc vào tôi ở đâu?**

Nhóm phụ thuộc vào tôi để có AgentState structure đúng và routing logic hoạt động. Nếu supervisor routing sai, toàn bộ pipeline trả lời sai. Workers không thể test integration nếu graph chưa xong.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi phụ thuộc vào Worker Owners để implement đúng contract (input/output format). Nếu workers không return đúng fields trong state (ví dụ: thiếu `retrieved_chunks`), synthesis worker sẽ fail.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

**Cải tiến cụ thể:**

Tôi sẽ thêm confidence-based routing fallback. Hiện tại supervisor chỉ route 1 lần dựa vào keywords. Nếu synthesis_worker trả về `confidence < 0.3`, supervisor nên tự động retry với worker khác hoặc route sang human_review.

Lý do: Trace `run_20260414_164055.json` (multi-hop query) có `confidence: 0.69` - vẫn khá thấp dù đã gọi cả retrieval + policy workers. Nếu có confidence-based fallback, pipeline sẽ tự động escalate câu hỏi khó sang human review thay vì trả lời với confidence thấp, giảm risk hallucination cho câu gq07 (abstain test) và improve accuracy cho gq09 (multi-hop hardest).

---

*Lưu file này với tên: `reports/individual/trandinhminhvuong.md`*
