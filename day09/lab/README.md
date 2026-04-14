# Lab Day 09 — Multi-Agent Orchestration

**Môn:** AI in Action (AICB-P1)  
**Chủ đề:** Supervisor-Worker Pattern · MCP · Trace & Observability  
**Thời gian:** 4 giờ (4 sprints x 60 phút)  
**Tiếp nối:** Day 08 — RAG Pipeline → Day 09 — Orchestration Layer

---

## Bối cảnh

Cùng bài toán **trợ lý nội bộ CS + IT Helpdesk** từ Day 08, nhưng RAG pipeline đã bắt đầu quá tải:

- Một agent vừa retrieve, vừa kiểm tra policy, vừa tổng hợp, vừa xử lý retry
- Khi pipeline trả lời sai, không rõ lỗi nằm ở retrieval, policy check, hay generation
- Không thể thay thế từng phần mà không ảnh hưởng toàn hệ

**Nhiệm vụ hôm nay:** Refactor RAG pipeline (Day 08) thành hệ **Supervisor + Workers** rõ vai, dễ trace, dễ mở rộng.

**Câu hỏi hệ thống mới phải xử lý được:**
- "Ticket P1 lúc 2am — escalation xảy ra thế nào và ai nhận thông báo?"
- "Contractor cần Admin Access để sửa P1 khẩn cấp — quy trình tạm thời là gì?"
- "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — policy nào áp dụng?"

---

## Mục tiêu học tập

| Mục tiêu | Sprint liên quan |
|-----------|----------------|
| Refactor pipeline sang Supervisor-Worker graph | Sprint 1 |
| Implement 2–3 workers với contract rõ ràng | Sprint 2 |
| Nối 1 external capability qua MCP (thật hoặc mock) | Sprint 3 |
| Trace toàn bộ routing flow + so sánh single vs multi | Sprint 4 |

---

## Cấu trúc repo

```
lab/
├── graph.py               # Sprint 1: Supervisor orchestrator (main entry)
│
├── workers/
│   ├── retrieval.py       # Sprint 2: Retrieval Worker — tìm chunks bằng chứng
│   ├── policy_tool.py     # Sprint 2: Policy/Tool Worker — kiểm tra policy + MCP tools
│   └── synthesis.py       # Sprint 2: Synthesis Worker — tổng hợp answer có citation
│
├── mcp_server.py          # Sprint 3: MCP Server (HTTP + in-process dispatch)
├── mcp_config.json        # MCP endpoint + tool registry for the lab
├── eval_trace.py          # Sprint 4: Đọc trace, tính metrics, so sánh single vs multi
│
├── contracts/
│   └── worker_contracts.yaml  # I/O contract cho từng worker
│
├── data/
│   ├── docs/              # 5 tài liệu nội bộ (kế thừa từ Day 08)
│   │   ├── policy_refund_v4.txt
│   │   ├── sla_p1_2026.txt
│   │   ├── access_control_sop.txt
│   │   ├── it_helpdesk_faq.txt
│   │   └── hr_leave_policy.txt
│   ├── test_questions.json    # 15 test questions (single + multi-hop)
│   └── grading_questions.json # Câu hỏi chấm điểm (public lúc 17:00)
│
├── artifacts/
│   └── traces/            # Output trace files (.jsonl)
│
├── docs/
│   ├── system_architecture.md       # Template: mô tả kiến trúc multi-agent
│   ├── routing_decisions.md         # Template: ghi lại quyết định routing
│   ├── single_vs_multi_comparison.md # Template: so sánh Day 08 vs Day 09
│   └── commit_plan.md               # Kế hoạch commit / push an toàn
│
├── reports/
│   ├── group_report.md              # Báo cáo nhóm (template)
│   └── individual/
│       └── template.md              # Báo cáo cá nhân (500–800 từ)
│
├── requirements.txt
└── .env.example
```

---

## Setup

### 1. Cài dependencies
```bash
pip install -r requirements.txt
```

### 2. Tạo file .env
```bash
cp .env.example .env
# Điền GROQ_API_KEY để chạy synthesis
# (tuỳ chọn) điền OPENAI_API_KEY nếu muốn bật OpenAI embeddings cho retrieval
```

> Nếu bạn muốn demo MCP HTTP, giữ `MCP_SERVER_MODE=http` và chạy `mcp_server.py`.
> Nếu chỉ cần test nhanh không qua network, đổi sang `mock-only` hoặc `hybrid`.

### 3. Build index từ Day 08 (nếu chưa có)
```bash
# Copy ChromaDB index từ Day 08, hoặc chạy lại:
python -c "
import chromadb, os
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path='./chroma_db')
col = client.get_or_create_collection('day09_docs')
model = SentenceTransformer('all-MiniLM-L6-v2')

docs_dir = './data/docs'
for fname in os.listdir(docs_dir):
    with open(os.path.join(docs_dir, fname)) as f:
        content = f.read()
    print(f'Indexed: {fname}')
print('Index ready.')
"
```

### 4. Kiểm tra setup
```bash
python graph.py  # Chạy 1 test query cơ bản
```

---

## 4 Sprints

### Sprint 1 (60') — Refactor Graph

**File:** `graph.py`

**Bối cảnh:** RAG pipeline Day 08 là một "monolith" — retrieve → generate trong một hàm. Sprint này tách nó thành graph với Supervisor điều phối.

**Việc phải làm:**
1. Implement `AgentState` — shared state của toàn graph
2. Implement `supervisor_node()` — đọc task, quyết định route
3. Implement `route_decision()` — routing logic dựa vào task type và risk flag
4. Kết nối graph: `supervisor → route → [retrieval | policy_tool | human_review] → synthesis → END`
5. Chạy `graph.invoke()` với 2 test queries khác nhau

**Definition of Done:**
- [ ] `python graph.py` chạy không lỗi
- [ ] Supervisor route đúng cho ít nhất 2 loại câu hỏi khác nhau (retrieval vs policy)
- [ ] Mỗi bước routing được log với `route_reason`
- [ ] State object có: `task`, `route_reason`, `history`, `risk_high`

**Gợi ý routing logic:**
```
task chứa "hoàn tiền", "refund", "policy" → policy_tool_worker
task chứa "cấp quyền", "access", "emergency" → policy_tool_worker  
task chứa "P1", "escalation", "ticket" → retrieval_worker (ưu tiên)
task chứa mã lỗi không rõ → human_review
còn lại → retrieval_worker
```

---

### Sprint 2 (60') — Build Workers

**Files:** `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py`

**Việc phải làm:**

**Retrieval Worker** (`workers/retrieval.py`):
1. Implement `run(state)` — nhận query từ state, gọi ChromaDB, trả về chunks
2. Ghi `retrieved_chunks` và `worker_io_log` vào state

**Policy Tool Worker** (`workers/policy_tool.py`):
1. Implement `run(state)` — kiểm tra policy dựa trên retrieved chunks
2. Phân tích exception/edge case nếu có (e.g., Flash Sale, Digital Product)
3. Ghi `policy_result` và `worker_io_log` vào state

**Synthesis Worker** (`workers/synthesis.py`):
1. Implement `run(state)` — tổng hợp answer từ chunks + policy_result
2. Gọi LLM với grounded prompt (chỉ dùng evidence từ state)
3. Output có `answer`, `sources`, `confidence`

**Kiểm tra từng worker độc lập:**
```python
# Test retrieval worker độc lập
from workers.retrieval import run as retrieval_run
test_state = {"task": "SLA ticket P1 là bao lâu?", "history": []}
result = retrieval_run(test_state)
print(result["retrieved_chunks"])
```

**Definition of Done:**
- [ ] Mỗi worker test độc lập được (không cần graph)
- [ ] Input/output của từng worker khớp với `contracts/worker_contracts.yaml`
- [ ] Policy worker xử lý đúng ít nhất 1 exception case (Flash Sale hoặc digital product)
- [ ] Synthesis worker trả về answer có citation `[1]`, không hallucinate

---

### Sprint 3 (60') — Thêm MCP

**File:** `mcp_server.py`

**Bối cảnh:** Tool worker cần gọi external capability. Thay vì hard-code từng API, dùng MCP interface.

**Việc phải làm:**
1. Implement mock MCP Server với ít nhất **2 tools**:
   - `search_kb(query, top_k)` — search Knowledge Base (dùng ChromaDB)
   - `get_ticket_info(ticket_id)` — tra cứu thông tin ticket (mock data)
2. Trong `workers/policy_tool.py`: gọi MCP client để lấy kết quả thay vì truy cập ChromaDB trực tiếp
3. Ghi lại `mcp_tool_called` và `mcp_result` vào trace

**Format MCP tool call (JSON):**
```json
{
  "tool": "search_kb",
  "input": {"query": "refund policy flash sale", "top_k": 3},
  "output": {"chunks": [...], "sources": [...]},
  "timestamp": "2026-04-13T14:32:11"
}
```

**Chọn 1 trong 2 mức độ:**

| Mức | Làm gì | Điểm |
|-----|--------|------|
| **Standard** | Mock MCP class trong Python, gọi qua function call | Full credit |
| **Advanced** | MCP server thật dùng `mcp` library hoặc HTTP server | Bonus +2 |

**Definition of Done:**
- [ ] `mcp_server.py` có ít nhất 2 tools implement
- [ ] Policy worker gọi MCP client, không direct call ChromaDB
- [ ] Trace ghi được `mcp_tool_called` cho từng lần gọi
- [ ] Supervisor ghi log "chọn MCP vs không chọn MCP" vào `route_reason`

---

### Sprint 4 (60') — Trace & Docs & Report

**File:** `eval_trace.py`

**Việc phải làm:**
1. Chạy pipeline với 15 test questions, lưu trace vào `artifacts/traces/`
2. Implement `analyze_trace()` — đọc trace, tính metrics
3. Implement `compare_single_vs_multi()` — so sánh với Day 08 baseline
4. Điền vào 3 docs templates
5. Viết báo cáo nhóm và báo cáo cá nhân

**Trace format bắt buộc:**
```json
{
  "run_id": "run_2026-04-13_1432",
  "task": "câu hỏi đầu vào",
  "supervisor_route": "retrieval_worker",
  "route_reason": "task contains SLA keyword",
  "workers_called": ["retrieval_worker", "synthesis_worker"],
  "mcp_tools_used": [],
  "retrieved_sources": ["sla_p1_2026.txt"],
  "final_answer": "...",
  "confidence": 0.88,
  "hitl_triggered": false,
  "latency_ms": 1230,
  "timestamp": "2026-04-13T14:32:11"
}
```

**Definition of Done:**
- [ ] `python eval_trace.py` chạy end-to-end với 15 test questions
- [ ] Trace file có đủ các fields bắt buộc
- [ ] `docs/routing_decisions.md` điền xong với ít nhất 3 quyết định routing thực tế
- [ ] `docs/single_vs_multi_comparison.md` điền xong với ít nhất 2 metrics
- [ ] Mỗi người có file báo cáo cá nhân trong `reports/individual/`
- [ ] Nhóm có `reports/group_report.md` hoàn chỉnh

---

## Deliverables (Nộp bài)

| Item | File | Owner |
|------|------|-------|
| Orchestrator | `graph.py` | Supervisor Owner |
| Workers | `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py` | Worker Owners |
| MCP Server | `mcp_server.py` | MCP Owner |
| Worker contracts | `contracts/worker_contracts.yaml` | Worker Owners |
| Trace + eval | `eval_trace.py`, `artifacts/traces/` | Trace Owner |
| System architecture | `docs/system_architecture.md` | Documentation Owner |
| Routing decisions | `docs/routing_decisions.md` | Documentation Owner |
| Single vs Multi comparison | `docs/single_vs_multi_comparison.md` | Documentation Owner |
| Grading run log | `artifacts/grading_run.jsonl` | Trace Owner |
| Báo cáo nhóm | `reports/group_report.md` | Documentation Owner |
| Báo cáo cá nhân | `reports/individual/[ten].md` | Từng người |

---

## Phân vai (Giao ngay phút đầu)

| Vai trò | Trách nhiệm chính | Sprint lead |
|---------|------------------|------------|
| **Supervisor Owner** | graph.py, routing logic, state management | 1 |
| **Worker Owner** | retrieval.py, policy_tool.py, synthesis.py, contracts | 2 |
| **MCP Owner** | mcp_server.py, MCP integration trong policy_tool | 3 |
| **Trace & Docs Owner** | eval_trace.py, 3 doc templates, group_report | 4 |

> Một người có thể giữ nhiều vai nếu nhóm < 4 người. Mỗi vai phải có **ít nhất 1 người** khai báo và chứng minh được.

---

## Câu hỏi debug (Routing Error Tree)

Nếu pipeline trả lời sai, kiểm tra lần lượt:

```
1. Routing sai?
   → Xem trace: supervisor_route có đúng không?
   → Xem route_reason: logic routing có dựa vào signal đúng không?

2. Worker sai?
   → Test worker độc lập với cùng input
   → Xem worker_io_log: input/output có đúng contract không?

3. MCP sai?
   → Xem mcp_tools_used và mcp_result trong trace
   → Thử gọi MCP tool trực tiếp

4. Synthesis sai?
   → Xem retrieved_sources: đúng tài liệu chưa?
   → Kiểm tra prompt: có "Answer only from context" không?
   → Confidence thấp → có nên trigger HITL không?
```

---

## Tài nguyên tham khảo

- Slide Day 09: `../lecture-09.html`
- Lab Day 08 (baseline): `../../day08/lab/`
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- MCP spec: https://modelcontextprotocol.io/docs
- ChromaDB: https://docs.trychroma.com
- OpenAI Function Calling: https://platform.openai.com/docs/guides/function-calling
