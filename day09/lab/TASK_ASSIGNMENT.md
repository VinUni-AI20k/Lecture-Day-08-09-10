# Day 09 Lab — Phân Công Công Việc (7 Người)

**Thời gian:** 4 giờ × 4 sprints (60 phút/sprint)  
**Nhóm:** Quang, Tuấn, Hải, Dũng, Huy, Long, Thuận

---

## Tổng Quan Vai Trò

| Vai trò | Sprint | Người | Trách nhiệm chính |
|---------|--------|-------|------------------|
| **Supervisor Owner** | 1 | Quang | `graph.py`, routing logic, state management |
| **Retrieval Worker** | 2 | Tuấn | `workers/retrieval.py` |
| **Policy Tool Worker** | 2 | Hải | `workers/policy_tool.py`, MCP integration |
| **Synthesis Worker** | 2 | Dũng | `workers/synthesis.py` |
| **MCP Owner** | 3 | Huy | `mcp_server.py`, 2+ tools |
| **Trace & Eval Owner** | 4 | Long | `eval_trace.py`, tracing & metrics |
| **Docs & Reports Owner** | 4 | Thuận | Architecture, routing decisions, group/individual reports |

---

## Phân Công Chi Tiết

### 📍 **Quang — Supervisor Owner (Sprint 1)**

**Mục tiêu:** Implement orchestrator coordinator, routing logic, state management.

**Deliverables:**
- [ ] **`graph.py`** — Supervisor-Worker graph
  - Implement `AgentState` class (fields: task, route_reason, history, risk_high, etc.)
  - Implement `supervisor_node()` — entry point, init state
  - Implement `route_decision()` — routing logic based on task keywords
  - Connect graph: `supervisor → route → [workers] → synthesis → END`
  - Test with 2 sample queries
- [ ] **Routing Logic** (implement based on this guideline):
  ```
  if "hoàn tiền", "refund", "policy" → policy_tool_worker
  elif "cấp quyền", "access", "emergency", "contractor" → policy_tool_worker  
  elif "P1", "escalation", "ticket" → retrieval_worker (ưu tiên)
  elif mã lỗi không rõ → human_review
  else → retrieval_worker
  ```
- [ ] **Logging:** Mỗi routing decision phải log `route_reason`
- [ ] **Test:** `python graph.py` chạy không lỗi

**Dependencies:**
- Chờ Tuấn, Hải, Dũng viết workers xong (sprint 2) → nối graph lại

**Deadline:** Cuối Sprint 1 (60 phút)

---

### 📍 **Tuấn — Retrieval Worker (Sprint 2)**

**Mục tiêu:** Implement retrieval module, ChromaDB integration, document fetch.

**Deliverables:**
- [ ] **`workers/retrieval.py`**
  - Implement `run(state)` function
  - Query ChromaDB với `state["task"]`
  - Trả về top-k chunks với sources
  - Store `retrieved_chunks`, `worker_io_log` vào state
- [ ] **Test ngoài graph:**
  ```python
  from workers.retrieval import run
  test_state = {"task": "SLA ticket P1 là bao lâu?", "history": []}
  result = run(test_state)
  # Check result["retrieved_chunks"]
  ```
- [ ] **Input/Output** khớp với `contracts/worker_contracts.yaml` (cùng Long viết)
- [ ] **Metrics:** Top-k retrieval accuracy (chứng minh trả lại chunks liên quan)

**Thân thiện làm việc với:**
- **Hải** (Policy Tool Worker) — Hải sẽ dùng chunks từ Tuấn để check policy
- **Dũng** (Synthesis Worker) — Dũng sẽ dùng chunks để tổng hợp answer
- **Long** (Trace Owner) — Long sẽ track `retrieved_chunks` trong trace

**Deadline:** Cuối Sprint 2 (60 phút)

---

### 📍 **Hải — Policy Tool Worker (Sprint 2)**

**Mục tiêu:** Implement policy checking, exception handling, MCP integration.

**Deliverables:**
- [ ] **`workers/policy_tool.py`**
  - Implement `run(state)` function
  - Nhận `retrieved_chunks` từ state
  - Check policy dựa trên chunks (e.g., refund limits, access rules)
  - Handle ít nhất 1 exception case:
    - Flash Sale refund (special policy)
    - Digital Product (không hoàn lại)
    - Contractor emergency access (escalation)
  - Store `policy_result`, `worker_io_log` vào state
- [ ] **MCP Client Integration** (Sprint 3)
  - Call `mcp.search_kb(query, top_k)` thay vì direct ChromaDB (khi MCP ready)
  - Call `mcp.get_ticket_info(ticket_id)` để lấy ticket metadata
  - Log `mcp_tools_used`, `mcp_result` vào state
- [ ] **Test ngoài graph:**
  ```python
  from workers.policy_tool import run
  test_state = {"task": "Flash Sale refund", "retrieved_chunks": [...]}
  result = run(test_state)
  # Check result["policy_result"]
  ```
- [ ] **Input/Output** khớp với contract

**Thân thiện làm việc với:**
- **Tuấn** (Retrieval) — dùng chunks từ Tuấn
- **Huy** (MCP Owner) — gọi MCP tools từ Huy
- **Dũng** (Synthesis) — trả policy kết quả cho Dũng

**Deadline:** Cuối Sprint 2 (60 phút), update MCP calls lúc Sprint 3

---

### 📍 **Dũng — Synthesis Worker (Sprint 2)**

**Mục tiêu:** Implement answer synthesis, grounding, citation generation.

**Deliverables:**
- [ ] **`workers/synthesis.py`**
  - Implement `run(state)` function
  - Nhận `retrieved_chunks`, `policy_result` từ state
  - Gọi LLM (GPT-4 / Claude) với grounded prompt
  - Prompt phải chứa: "Answer only based on provided context"
  - Output format:
    ```python
    {
      "answer": "...",
      "sources": ["sla_p1_2026.txt", "access_control_sop.txt"],
      "confidence": 0.85,
      "hitl_flag": False  # True nếu confidence thấp
    }
    ```
  - Store vào state
- [ ] **Test ngoài graph:**
  ```python
  from workers.synthesis import run
  test_state = {
    "task": "...",
    "retrieved_chunks": [...],
    "policy_result": {...}
  }
  result = run(test_state)
  # Check result["answer"], sources, confidence
  ```
- [ ] **Citation check:** Answer không hallucinate, chỉ dùng evidence từ state
- [ ] **HITL trigger:** Nếu confidence < 0.6, set `hitl_flag=True`

**Thân thiện làm việc với:**
- **Tuấn**, **Hải** — nhận kết quả từ hai worker này
- **Long** (Trace Owner) — Long sẽ track confidence, HITL decision

**Deadline:** Cuối Sprint 2 (60 phút)

---

### 📍 **Huy — MCP Owner (Sprint 3)**

**Mục tiêu:** Implement MCP server, 2+ tools, client integration.

**Deliverables:**
- [ ] **`mcp_server.py`** — Mock MCP Server
  - Tool 1: `search_kb(query: str, top_k: int)` → return chunks từ ChromaDB
  - Tool 2: `get_ticket_info(ticket_id: str)` → return mock ticket data
  - Optional Tool 3: `check_access_policy(user_role: str, resource: str)` → return access decision
  - MCP response format (JSON):
    ```json
    {
      "tool": "search_kb",
      "input": {"query": "...", "top_k": 3},
      "output": {"chunks": [...], "sources": [...]},
      "timestamp": "2026-04-14T..."
    }
    ```
- [ ] **Mức độ implement (chọn 1):**
  - **Standard:** Mock class trong Python, call qua function
  - **Advanced:** Real MCP server dùng `mcp` library hoặc HTTP (bonus +2)
- [ ] **Integration checklist:**
  - [ ] Update `workers/policy_tool.py` để gọi MCP client
  - [ ] Test MCP tools độc lập
  - [ ] Verify trace ghi được `mcp_tool_called`, `mcp_result`
- [ ] **Test:**
  ```python
  from mcp_server import MCPServer
  server = MCPServer()
  result = server.search_kb("refund policy", top_k=3)
  print(result)
  ```

**Thân thiện làm việc với:**
- **Hải** (Policy Tool Worker) — Hải sẽ call MCP tools từ policy_tool.py
- **Long** (Trace Owner) — Long sẽ ghi MCP calls trong trace

**Deadline:** Cuối Sprint 3 (60 phút)

---

### 📍 **Long — Trace & Evaluation Owner (Sprint 4)**

**Mục tiêu:** Implement tracing, metrics calculation, single vs multi comparison.

**Deliverables:**
- [ ] **`eval_trace.py`**
  - Implement `run_evaluation(test_questions_file)` — chạy pipeline với 15 test questions
  - Output format (required fields):
    ```json
    {
      "run_id": "run_2026-04-14_0000",
      "task": "câu hỏi đầu vào",
      "supervisor_route": "retrieval_worker",
      "route_reason": "task contains SLA keyword",
      "workers_called": ["retrieval_worker", "synthesis_worker"],
      "mcp_tools_used": ["search_kb"],
      "retrieved_sources": ["sla_p1_2026.txt"],
      "final_answer": "...",
      "confidence": 0.88,
      "hitl_triggered": false,
      "latency_ms": 1230,
      "timestamp": "2026-04-14T..."
    }
    ```
  - Save to `artifacts/traces/run_*.jsonl`
  - Log mỗi query thành 1 line JSON (JSONL format)
- [ ] **Metrics calculation:**
  - Routing accuracy (supervisor route đúng không?)
  - Answer quality (manual check 5-10 answers, confidence calibration)
  - Latency distribution (mean, p95, p99)
  - HITL trigger rate
- [ ] **Comparison: Single vs Multi**
  - Compare Day 08 baseline vs Day 09 multi-agent
  - Metrics to compare:
    - Accuracy (answer correctness)
    - Latency (single-pass vs multi-worker)
    - Explainability (routing trace vs black box)
  - Write comparison in `docs/single_vs_multi_comparison.md`
- [ ] **Grading run:**
  - Chạy tất cả grading questions → save to `artifacts/grading_run.jsonl`

**Dependencies:**
- Quang phải hoàn thành graph.py (Sprint 1)
- Tuấn, Hải, Dũng phải hoàn thành workers (Sprint 2)
- Huy phải hoàn thành & integrate MCP (Sprint 3)

**Deadline:** Cuối Sprint 4 (60 phút)

---

### 📍 **Thuận — Documentation & Reports Owner (Sprint 4)**

**Mục tiêu:** Document architecture, decisions, generate group & individual reports.

**Deliverables:**
- [ ] **`docs/system_architecture.md`** (template provided)
  - Mô tả kiến trúc Supervisor-Worker graph
  - Diagram (ASCII hoặc link to image)
  - Component roles & interactions
  - Data flow từ input → supervisor → workers → output
- [ ] **`docs/routing_decisions.md`** (template provided)
  - Ghi lại ít nhất **3 quyết định routing thực tế** từ test run
  - Format:
    ```
    ## Decision 1: SLA P1 Question
    - **Input task:** "Ticket P1 lúc 2am — escalation xảy ra thế nào?"
    - **Supervisor route:** retrieval_worker
    - **Route reason:** task contains P1 + escalation keywords
    - **Outcome:** Retrieved SLA policy, answer = "Escalation procedure in sla_p1_2026.txt"
    ```
- [ ] **`docs/single_vs_multi_comparison.md`** (collaborate with Long)
  - Compare Day 08 (single RAG) vs Day 09 (multi-agent)
  - Metrics: accuracy, latency, explainability
  - Pro/con của từng approach
- [ ] **`reports/group_report.md`** (template provided)
  - Tóm tắt nhóm: gì thành công, gì khó khăn
  - Phân công & trách nhiệm
  - Kết quả chính (metrics summary)
  - 500–800 từ
- [ ] **`reports/individual/[tên].md`** × 7
  - Mỗi người viết báo cáo cá nhân (500–800 từ)
  - Template: 
    ```markdown
    # Báo cáo cá nhân — [Tên]
    
    ## Vai trò
    [Supervisor Owner / Retrieval Worker / ...]
    
    ## Nhiệm vụ chính
    - [ ] Task 1
    - [ ] Task 2
    
    ## Kết quả
    (Mô tả kết quả & metrics)
    
    ## Học được gì
    (Insights & lessons learned)
    
    ## Khó khăn & giải pháp
    (Obstacles & how to overcome)
    ```

**Dependencies:**
- Long phải hoàn thành eval_trace.py → có metrics data
- Cả team phải submit code trước → có material để wrote docs

**Deadline:** Cuối Sprint 4 (60 phút) — **LAST DELIVERABLE**

---

## Worker Contracts (Shared between Tuấn, Hải, Dũng + Long)

**File:** `contracts/worker_contracts.yaml`

**Điền vào:**
```yaml
retrieval_worker:
  input:
    - name: task
      type: string
      description: "User query"
    - name: history
      type: list[dict]
      description: "Previous turns"
  output:
    - name: retrieved_chunks
      type: list[dict]
      fields: [text, source, similarity]
    - name: worker_io_log
      type: dict

policy_tool_worker:
  input:
    - name: retrieved_chunks
      type: list[dict]
  output:
    - name: policy_result
      type: dict
      fields: [applicable_policy, exception_flag, notes]

synthesis_worker:
  input:
    - name: retrieved_chunks
      type: list[dict]
    - name: policy_result
      type: dict
  output:
    - name: answer
      type: string
    - name: sources
      type: list[string]
    - name: confidence
      type: float
    - name: hitl_flag
      type: bool
```

**Owner:** **Tuấn + Hải + Dũng** (mỗi người định nghĩa I/O cho worker của mình)

---

## Sprint Checklist

### Sprint 1 — Quang (60')
- [ ] `graph.py` + routing logic
- [ ] Test with 2 sample queries
- [x] **Status:** ✅ Ready for Sprint 2

### Sprint 2 — Tuấn + Hải + Dũng (60')
- [ ] `workers/retrieval.py` (Tuấn)
- [ ] `workers/policy_tool.py` (Hải)
- [ ] `workers/synthesis.py` (Dũng)
- [ ] `contracts/worker_contracts.yaml` (All)
- [ ] Test workers independently
- [x] **Status:** ✅ Ready for Sprint 3

### Sprint 3 — Huy (60')
- [ ] `mcp_server.py` with 2+ tools
- [ ] MCP client integration into policy_tool.py
- [ ] Trace includes MCP tool calls
- [x] **Status:** ✅ Ready for Sprint 4

### Sprint 4 — Long + Thuận (60')
- [ ] `eval_trace.py` + run 15 test questions
- [ ] `artifacts/traces/` + metrics
- [ ] `docs/system_architecture.md` (Thuận)
- [ ] `docs/routing_decisions.md` (Thuận)
- [ ] `docs/single_vs_multi_comparison.md` (Long + Thuận)
- [ ] `reports/group_report.md` (Thuận)
- [ ] `reports/individual/[name].md` × 7 (Everyone)
- [ ] `artifacts/grading_run.jsonl` (Long)
- [x] **Status:** ✅ DONE

---

## Tài liệu tham khảo

| Tài liệu | Link |
|----------|------|
| Lab README | `./README.md` |
| Day 08 baseline | `../../day08/lab/` |
| LangGraph docs | https://langchain-ai.github.io/langgraph/ |
| MCP spec | https://modelcontextprotocol.io/docs |
| ChromaDB API | https://docs.trychroma.com |
| OpenAI Function Calling | https://platform.openai.com/docs/guides/function-calling |

---

## Quy tắc làm việc

1. **Daily standup** (bắt đầu mỗi sprint): ai làm gì, blocker nào
2. **Test độc lập:** Mỗi worker test ngoài graph trước khi nối lại
3. **Logging:** Tất cả routing & tool calls phải có timestamp + traceability
4. **Git workflow:**
   ```bash
   git checkout -b sprint-X-[role]
   # commit changes
   git push origin sprint-X-[role]
   # create PR, review before merge
   ```
5. **Handoff checklist:** Sau mỗi sprint, người tiếp theo gửi tin nhắn "xác nhận sẵn sàng"

---

## Contact & Support

- **Issue?** → Post in team channel với tag `@Quang` (team lead)
- **Blocker?** → Escalate immediately, không đợi
- **Deadline?** → 4 giờ từ 14:00 → 18:00 (hoặc thời gian team agreement)

---

**Generated:** 2026-04-14  
**Version:** 1.0
