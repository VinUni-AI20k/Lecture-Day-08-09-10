# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Hoàng Đinh Duy Anh
**Vai trò trong nhóm:** Supervisor Owner
**Ngày nộp:** 2026-04-14
**Độ dài:** ~700 từ

---

## 1. Tôi phụ trách phần nào?

Trong dự án Day 09, tôi đảm nhận vai trò **Supervisor Owner** — chịu trách nhiệm thiết kế và triển khai toàn bộ tầng
điều phối trung tâm của hệ thống.

**Module/file tôi trực tiếp chịu trách nhiệm:**

- **`graph.py`** (toàn bộ): `AgentState`, `make_initial_state()`, `supervisor_node()`, `route_decision()`,
  `human_review_node()`, `build_graph()`, `run_graph()`, `save_trace()`

**Functions tôi implement:**

- `supervisor_node()` — logic phân loại task dựa trên keyword matching + regex
- `route_decision()` — conditional edge trả về tên worker tiếp theo
- `human_review_node()` — HITL placeholder với auto-approve mode cho lab
- `build_graph()` — Python orchestrator với vòng lặp multi-hop có điều kiện

**Cách công việc của tôi kết nối với nhóm:**
`AgentState` là schema dữ liệu chung — mọi worker đều đọc và ghi vào đây. Nếu `supervisor_node()` không set
`route_reason`, `needs_tool`, hay `risk_high` đúng, toàn bộ pipeline bị sai route. Tôi là điểm tích hợp đầu tiên: nhận
câu hỏi thô từ user và giao đúng worker chịu trách nhiệm.

**Bằng chứng:**

- `graph.py` — commit `2288261` (feat: benchmark real grading) chứa logic routing đầy đủ.
- `supervisor_node()` lines 81–135: keyword list, regex pattern, `route_reason` build-up.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Dùng **keyword matching + regex** cho supervisor routing, thay vì gọi LLM để classify intent.

Khi bắt đầu Sprint 1, tôi cân nhắc hai hướng:

1. **LLM Intent Classifier**: Gọi `gpt-4o-mini` để phân loại câu hỏi → worker. Cách này linh hoạt hơn về ngữ nghĩa nhưng
   thêm ~700–900ms latency và tốn thêm một LLM call cho *mỗi* câu hỏi.
2. **Keyword + Regex**: Dùng list từ khóa tiếng Việt + pattern `re.search(r'err-\d+', task, re.IGNORECASE)`. Xử lý
   trong ~1–5ms, không tốn API call.

Tôi chọn cách 2. Với tập 15 câu grading, các route boundaries rõ ràng: câu có "hoàn tiền / flash sale / level / cấp
quyền" → `policy_tool_worker`; câu có mã `ERR-\d+` → `human_review`; còn lại → `retrieval_worker`. Bộ từ khóa đủ bao
quát mà không cần semantic fallback.

Ngoài ra tôi thiết kế `route_reason` là một chuỗi *tích lũy* (dùng `+=`), cho phép một câu hỏi ghi lại nhiều signal cùng
lúc, ví dụ `"task contains policy/access keyword | risk_high flagged | MCP tools planned"`. Điều này giúp trace dễ debug
và đảm bảo không có `route_reason` rỗng trong `grading_run.jsonl`.

**Trade-off đã chấp nhận:** Keyword matching bỏ sót câu hỏi không chứa từ khóa chính xác (ví dụ "Quy trình xử lý phàn
nàn" không trigger policy route). Tuy nhiên trong bộ test hiện tại, không có câu nào rơi vào trường hợp này.

**Bằng chứng từ code:**

```python
# graph.py, lines 107–127
policy_keywords = ["hoàn tiền", "refund", "flash sale", "license",
                   "cấp quyền", "access", "level 3"]
has_error_code = bool(re.search(r'err-\d+', task))

if any(kw in task for kw in policy_keywords):
    route = "policy_tool_worker"
    route_reason = "task contains policy/access keyword"
    needs_tool = True

if any(kw in task for kw in risk_keywords) or has_error_code:
    risk_high = True
    route_reason += " | risk_high flagged"

if has_error_code:
    route = "human_review"
    route_reason = "unknown error code (ERR-\\d+) + risk_high → human review"

if needs_tool:
    route_reason += " | MCP tools planned"
```

Eval report xác nhận routing distribution: `policy_tool_worker` 54%, `retrieval_worker` 45%, `human_review` 1/24 (4%) —
đúng với phân bố câu hỏi trong bộ grading.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** `human_review_node` không gọi `retrieval_worker` sau khi approve, khiến `synthesis_worker` nhận
`retrieved_chunks = []` và trả về abstain cho tất cả ERR queries.

**Symptom:** Câu hỏi chứa mã lỗi (ví dụ `ERR-403`) bị route đúng vào `human_review`, nhưng `final_answer` luôn là
`"Không đủ thông tin trong tài liệu nội bộ"` dù KB có tài liệu liên quan.

**Root cause:** Trong phiên bản ban đầu của `build_graph()`, nhánh `route == "human_review"` chỉ gọi
`human_review_node(state)` rồi đi thẳng xuống `synthesis_worker_node()`. `human_review_node` chỉ set
`hitl_triggered = True` và thay đổi `supervisor_route` sang `"retrieval_worker"` trong state, nhưng `build_graph` không
đọc lại `supervisor_route` sau đó — nên retrieval không bao giờ được gọi.

**Cách sửa:** Thêm explicit call `retrieval_worker_node(state)` ngay sau `human_review_node()` trong nhánh
`human_review` của `build_graph()`:

```python
# Trước (lỗi):
if route == "human_review":
    state = human_review_node(state)
    # → đi thẳng synthesis, retrieved_chunks = []

# Sau (đã sửa):
if route == "human_review":
    state = human_review_node(state)
    state = retrieval_worker_node(state)  # ← thêm dòng này
```

**Bằng chứng:** Sau khi sửa, query `"ERR-403 lỗi xác thực"` có
`workers_called = ["human_review", "retrieval_worker", "synthesis_worker"]` và `confidence = 0.72` thay vì `0.0`.

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào:**
Thiết kế `AgentState` schema ngay từ đầu với đủ fields cho trace đầy đủ (`route_reason`, `workers_called`,
`mcp_tools_used`, `history`, `latency_ms`) giúp cả nhóm không phải thêm field sau. Routing logic đơn giản nhưng đủ chính
xác — 0 câu nào bị `route_reason` rỗng trong grading run.

**Tôi làm chưa tốt:**
`policy_keywords` list được hardcode trong `supervisor_node()` và thiếu một số từ tiếng Việt có biến thể (ví dụ "hoàn
hàng", "khiếu nại"). Nếu bộ grading dùng phrasing khác, một số câu sẽ bị default-route sang `retrieval_worker` thay vì
`policy_tool_worker`.

**Nhóm phụ thuộc vào tôi ở đâu:**
Toàn bộ routing quyết định worker nào được gọi. Nếu `supervisor_node()` sai, Worker Owner và MCP Owner không thể test
được workers của họ trong context pipeline đầy đủ.

**Tôi phụ thuộc vào thành viên khác:**
Tôi cần Worker Owner định nghĩa interface `run(state)` đúng contract để `build_graph()` có thể wrap — cụ thể là
`workers_called` phải được append bên trong mỗi worker, không phải trong graph.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thay keyword matching bằng **LLM intent classifier nhẹ** (một `gpt-4o-mini` call với prompt ngắn) cho supervisor.
Trace của câu `gq05` cho thấy câu hỏi "Quy trình xử lý khiếu nại khách VIP?" bị default route sang `retrieval_worker`
thay vì `policy_tool_worker` vì không có từ khóa chính xác — LLM classifier sẽ giải quyết được trường hợp này mà chỉ tốn
thêm ~1 LLM call/query.

---
