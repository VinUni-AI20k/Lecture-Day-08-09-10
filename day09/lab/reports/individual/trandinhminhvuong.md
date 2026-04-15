# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Đình Minh Vương  
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `graph.py` — Supervisor orchestrator (Sprint 1)
- Functions: `supervisor_node()` (lines 90-203), `route_decision()` (lines 206-213), `make_initial_state()` (lines 62-85), `build_graph()` (lines 280-325)
- File phụ: `build_index.py` — ChromaDB indexing setup

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Supervisor node tôi implement phân tích task và set 3 fields trong state: `supervisor_route` (worker nào), `needs_tool` (có gọi MCP không), `risk_high` (có cần HITL không). Workers nhận state này và xử lý theo domain logic. Tôi cũng define AgentState structure (lines 40-65) mà tất cả workers phải follow.

**Bằng chứng:** File `graph.py` có supervisor logic với 4 priority levels (lines 118-180). Trace files trong `artifacts/traces/` (26 files) đều có `supervisor_route` và `route_reason` được generate từ logic này.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Sử dụng keyword-based routing trong supervisor thay vì gọi LLM để classify task type.

**Lý do và trade-off:**

Tôi đã cân nhắc 2 approaches: (1) LLM-based classification gọi GPT-4 để phân loại task, (2) Keyword-based routing với priority levels. Tôi chọn approach 2 vì latency thấp (<5ms routing), chi phí thấp (không tốn API call cho routing), đủ chính xác (test với 4 queries đều route đúng), dễ debug, và deterministic.

Trade-off: Keyword-based kém linh hoạt với edge cases phức tạp. Tôi giải quyết bằng priority levels: error codes + risk → human_review (highest), policy keywords → policy_tool_worker, SLA keywords → retrieval_worker, default → retrieval_worker.

**Bằng chứng từ code (graph.py lines 118-180):**

```python
has_policy_keywords = any(kw in task for kw in policy_keywords)
has_sla_keywords = any(kw in task for kw in sla_keywords)
needs_multi_workers = has_policy_keywords and has_sla_keywords

elif needs_multi_workers:
    route = "policy_tool_worker"
    route_reason = f"multi-hop query detected: policy + SLA keywords"
```

**Trace evidence:** `run_20260414_164055.json` (multi-hop: P1 + cấp quyền Level 2) gọi cả retrieval + policy workers với latency 14638ms. So sánh `run_20260414_145907.json` (single-worker: Flash Sale) latency 3468ms. Multi-worker routing tăng latency nhưng retrieve nhiều context hơn.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Supervisor route_reason bị empty hoặc "unknown" trong một số traces, vi phạm contract requirement.

**Symptom:** Khi chạy test queries, một số trace files có `route_reason: ""` hoặc `route_reason: "unknown"`. Theo `contracts/worker_contracts.yaml`, supervisor KHÔNG được để route_reason rỗng hoặc "unknown". Điều này làm mất điểm trong Sprint 1 scoring (−2 điểm).

**Root cause:** Lỗi nằm ở supervisor routing logic. Trong một số edge cases (task không match bất kỳ keyword nào), code rơi vào default branch nhưng quên set route_reason.

**Cách sửa:** Thêm fallback logic:

```python
else:
    route = "retrieval_worker"
    route_reason = "default route: general knowledge retrieval | MCP disabled"

if not route_reason:
    route_reason = f"routed to {route} based on task analysis"
```

**Bằng chứng:** Sau khi sửa, kiểm tra 26 trace files trong `artifacts/traces/` — tất cả đều có route_reason rõ ràng như `"task contains policy/access keywords: hoàn tiền, flash sale"` hoặc `"unknown error code with risk_high context → human review required"`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt ở việc thiết kế routing logic với 5 priority levels (lines 118-180 trong graph.py), bao gồm multi-keyword detection cho multi-hop queries. Test với 3 queries: single-worker routes đúng, multi-hop query (P1 + cấp quyền Level 2) gọi cả retrieval + policy workers. Tôi cũng ensure route_reason không bao giờ empty để pass contract requirement.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Multi-worker routing mới chỉ handle 2-worker case (policy + retrieval). Chưa có logic để gọi 3+ workers hoặc dynamic worker ordering. Trace `run_20260414_164055.json` cho thấy confidence 0.69 dù đã multi-hop, cần thêm confidence-based retry logic.

**Nhóm phụ thuộc vào tôi ở đâu?**

Nhóm phụ thuộc vào AgentState structure và routing logic. Nếu supervisor routing sai, toàn bộ pipeline trả lời sai. Tôi phụ thuộc vào Worker Owners implement đúng contract — nếu workers không return đúng fields, synthesis_worker sẽ fail.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

**Cải tiến cụ thể:** Thêm confidence-based routing fallback. Hiện tại supervisor chỉ route 1 lần dựa vào keywords. Nếu synthesis_worker trả về `confidence < 0.3`, supervisor nên tự động retry với worker khác hoặc route sang human_review.

**Lý do từ trace:** `run_20260414_164055.json` có `confidence: 0.69` dù đã multi-hop. Confidence-based fallback sẽ escalate câu hỏi khó sang human review, giảm risk hallucination cho gq07 (abstain test) và improve accuracy cho gq09 (multi-hop hardest).

---

*Lưu file này với tên: `reports/individual/trandinhminhvuong.md`*
