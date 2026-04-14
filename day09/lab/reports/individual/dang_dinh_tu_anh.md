# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đặng Đinh Tú Anh
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 2026-04-14  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi chịu trách nhiệm chính cho **Supervisor Orchestrator** — tức là `graph.py` — file điều phối toàn bộ luồng xử lý trong pipeline multi-agent.

**Module/file tôi chịu trách nhiệm:**
- File chính: `day09/lab/graph.py`
- Functions tôi implement:
  - `supervisor_node` — phân tích task và quyết định route
  - `route_decision` — conditional edge, fallback an toàn khi route không hợp lệ
  - `policy_next_decision` — edge sau policy worker: đi retrieval hay thẳng synthesis
  - `build_graph` — chuyển từ Option A (Python thuần) sang LangGraph `StateGraph`
  - `AgentState`, `make_initial_state`, `run_graph`, `save_trace`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

`supervisor_node` là điểm đầu vào duy nhất — mọi request từ user phải đi qua đây trước. Routing decision của tôi quyết định worker nào được gọi: retrieval worker (do thành viên khác implement) hay policy_tool_worker (cần MCP). Nếu tôi route sai, toàn bộ pipeline downstream sẽ trả kết quả không đúng.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Chuyển `build_graph` từ Python function thuần (Option A) sang LangGraph `StateGraph` với conditional edges.

Template ban đầu để sẵn Option A — một hàm `run()` dùng if/else thủ công để gọi các worker. Tôi đánh giá hai lựa chọn:

- **Option A (Python thuần):** Đơn giản, không dependency. Nhược điểm: không có trace tự động, không mở rộng được HITL thật sự (phải mock toàn bộ), khó thêm edge mới khi pipeline phức tạp hơn.
- **Option B (LangGraph StateGraph):** Cần thêm dependency, nhưng mỗi node/edge được declare rõ ràng, runtime tự handle state passing, và sau này có thể dùng `interrupt_before` để implement HITL thật.

Tôi chọn LangGraph vì kiến trúc của lab rõ ràng cần conditional edges (supervisor → 3 nhánh, policy → 2 nhánh). Option A bằng if/else tốn 40+ dòng và dễ sai thứ tự gọi. LangGraph giảm về ~20 dòng `add_node` / `add_edge` và đảm bảo đúng flow.

**Trade-off đã chấp nhận:** Thêm `langgraph` vào `requirements.txt`, tăng install time. Với môi trường lab, trade-off này chấp nhận được.

**Bằng chứng từ code:**

```python
# Trước (Option A — commit gốc trước be827ed):
def run(state: AgentState) -> AgentState:
    state = supervisor_node(state)
    route = route_decision(state)
    if route == "human_review":
        state = human_review_node(state)
        state = retrieval_worker_node(state)
    elif route == "policy_tool_worker":
        state = policy_tool_worker_node(state)
        if not state["retrieved_chunks"]:
            state = retrieval_worker_node(state)
    else:
        state = retrieval_worker_node(state)
    state = synthesis_worker_node(state)
    return state

# Sau (Option B — commit be827ed):
graph = StateGraph(AgentState)
graph.add_node("supervisor", supervisor_node)
graph.add_node("retrieval_worker", retrieval_worker_node)
graph.add_node("policy_tool_worker", policy_tool_worker_node)
graph.add_node("human_review", human_review_node)
graph.add_node("synthesis_worker", synthesis_worker_node)
graph.set_entry_point("supervisor")
graph.add_conditional_edges("supervisor", route_decision, {...})
graph.add_conditional_edges("policy_tool_worker", policy_next_decision, {...})
graph.add_edge("human_review", "retrieval_worker")
graph.add_edge("retrieval_worker", "synthesis_worker")
graph.add_edge("synthesis_worker", END)
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `route_decision` trả về giá trị tùy ý từ `supervisor_route` mà không validate, gây LangGraph KeyError khi route không khớp tên node.

**Symptom:**

Khi chạy thử với query có từ khóa lạ, `supervisor_node` ghi một giá trị không hợp lệ vào `supervisor_route`. `route_decision` cũ trả thẳng giá trị đó ra (`return route  # type: ignore`). LangGraph tìm không thấy node tương ứng trong conditional edge map → runtime error.

**Root cause:**

`route_decision` tin tưởng hoàn toàn vào `supervisor_route` mà không kiểm tra xem giá trị đó có nằm trong tập hợp node hợp lệ hay không. Một thay đổi nhỏ trong `supervisor_node` (ví dụ typo "retrival_worker") sẽ khiến toàn bộ graph crash thay vì fallback.

**Cách sửa:**

Thêm whitelist validation trong `route_decision`: nếu `supervisor_route` không nằm trong `{"retrieval_worker", "policy_tool_worker", "human_review"}` thì fallback về `"retrieval_worker"` và ghi log vào `history`.

**Bằng chứng trước/sau:**

```python
# Trước (commit 0c464dc):
def route_decision(state):
    route = state.get("supervisor_route", "retrieval_worker")
    return route  # type: ignore  ← không validate

# Sau (commit be827ed):
def route_decision(state):
    route = state.get("supervisor_route", "retrieval_worker")
    if route in ("retrieval_worker", "policy_tool_worker", "human_review"):
        return route
    state["history"].append(
        f"[route_decision] invalid supervisor_route='{route}', fallback='retrieval_worker'"
    )
    return "retrieval_worker"
```

Trace `run_20260414_142641` sau fix: `supervisor_route=policy_tool_worker`, pipeline chạy đúng luồng policy → retrieval → synthesis trong 3891ms, không có crash.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Routing logic trong `supervisor_node` được thiết kế rõ ràng với 3 tầng keyword (policy, retrieval, risk), có `matched_policy` và `matched_risk` được log vào `route_reason` để trace sau dễ debug. Trace `run_20260414_142641` cho thấy `route_reason="policy/access keyword matched: ['hoàn tiền', 'flash sale']"` — đủ thông tin để hiểu tại sao route sang `policy_tool_worker`.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Routing hiện tại là keyword-based, dễ miss các câu hỏi không dùng đúng từ khóa. Ví dụ: câu hỏi về "license key đã kích hoạt" sẽ không route sang policy nếu user viết "phần mềm đã cài". Chưa có fallback LLM-classify khi keyword không match.

**Nhóm phụ thuộc vào tôi ở đâu?**

Tất cả workers (retrieval, policy, synthesis) đều chờ `supervisor_node` chạy trước. Nếu routing logic sai, workers nhận task đúng nhưng theo luồng sai.

**Phần tôi phụ thuộc vào thành viên khác:**

`synthesis_worker` do thành viên khác implement — nếu synthesis trả về `confidence=0.1` (như trace hiện tại do thiếu ChromaDB data), output cuối không có giá trị dù routing đúng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm LLM-classify fallback vào `supervisor_node`: nếu không có keyword nào match (route vẫn là `"retrieval_worker"` với `route_reason="default"`), gọi một LLM call nhỏ để classify task vào đúng category. Lý do: trace `run_20260414_142636` của query `"SLA xử lý ticket P1 là bao lâu?"` cho thấy `route_reason="default: general knowledge query → retrieval"` — câu này có thể được routing tốt hơn nếu LLM nhận ra "SLA" + "P1" là escalation context, không phải general query.

---

*File: `reports/individual/dang_dinh_tu_anh.md`*
