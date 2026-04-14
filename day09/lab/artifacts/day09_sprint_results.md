## Day09 — Results by sprint

Generated: 2026-04-14

### Sprint 1 — Build index (`build_index.py`)

- **Command**:
  - `python build_index.py`
- **Result**:
  - Indexed 5 docs into ChromaDB collection `day09_docs`
  - Output DB: `day09/lab/chroma_db/`

### Sprint 2 — Supervisor graph + retrieval (`graph.py`, `workers/retrieval.py`)

- **Commands**:
  - `python graph.py`
  - `python workers/retrieval.py`
- **Result**:
  - `graph.py` executed 3 demo queries and wrote traces to `day09/lab/artifacts/traces/`
  - `retrieval_worker` standalone test retrieved chunks and sources successfully

### Sprint 3 — Workers + MCP (`workers/policy_tool.py`, `workers/synthesis.py`, `mcp_server.py`)

- **Commands**:
  - `python workers/policy_tool.py`
  - `python workers/synthesis.py`
  - MCP dispatch smoke test:
    - `python -X utf8 -c "from mcp_server import dispatch_tool; ..."`
- **Result**:
  - `policy_tool_worker` ran (note: its `analyze_policy()` behavior depends on `LLM_PROVIDER`; with `openai/gemini` it returns text, so the demo prints `policy_applies: None`)
  - `synthesis_worker` generated grounded answers with citations in the standalone tests
  - Mock MCP tools worked:
    - `get_ticket_info` returned a mock P1 ticket record
    - `search_kb` executed (returned empty `sources` in the smoke test run)

### Sprint 4 — Trace & evaluation (`eval_trace.py`)

- **Commands**:
  - `python eval_trace.py`
  - `python eval_trace.py --analyze`
  - `python eval_trace.py --grading` (not available because `data/grading_questions.json` is missing)
- **Outputs**:
  - **Eval report**: `day09/lab/artifacts/eval_report.json`
  - **Traces**: `day09/lab/artifacts/traces/` (count: 100)
- **Key metrics** (from `artifacts/eval_report.json`):
  - `total_traces`: 100
  - `routing_distribution`: policy_tool_worker 50%, retrieval_worker 50%
  - `avg_confidence`: 0.655
  - `avg_latency_ms`: 14004
  - `mcp_usage_rate`: 7%
  - `hitl_rate`: 6%
  - `top_sources`: `sla_p1_2026.txt` (91), `it_helpdesk_faq.txt` (15), `access_control_sop.txt` (11), `policy_refund_v4.txt` (8), `hr_leave_policy.txt` (5)

