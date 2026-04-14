# CLAUDE.md — Lab Day 09: Multi-Agent Orchestration

## Project Overview
Vietnamese IT Helpdesk assistant, refactored from Day 08 monolithic RAG into a
Supervisor-Worker graph with MCP tool integration and full trace observability.

## Tech Stack
- **Graph:** Pure Python supervisor-worker (LangGraph optional)
- **Embeddings:** Sentence-Transformers `all-MiniLM-L6-v2` (offline) or OpenAI `text-embedding-3-small`
- **LLM:** OpenAI `gpt-4o-mini` (temperature=0) for synthesis & policy analysis
- **Vector Store:** ChromaDB PersistentClient, collection `day09_docs`
- **Retrieval (inherited from Day 08):** Dense (ChromaDB cosine) + Sparse (BM25 via `rank-bm25`) + Hybrid (RRF fusion). Day 08 chose **hybrid** as the winning variant — keep that as the retrieval worker default.
- **Eval harness (inherited from Day 08):** LLM-as-Judge for faithfulness / relevance / completeness + programmatic context_recall. Reusable inside `eval_trace.py` to score multi-agent traces.
- **MCP:** In-process mock dispatcher (`mcp_server.py`), 4 tools

## Carryover from Day 08

Day 08 built a single-agent RAG pipeline. Day 09 reuses its retrieval primitives and eval knowledge; the change is **orchestration + observability**, not retrieval quality.

| Day 08 concept | How it maps into Day 09 |
|----------------|-------------------------|
| `index.py` (chunk → embed → upsert) | Run once to build `chroma_db/day09_docs`. Port the chunker into `scripts/build_index.py`. |
| `retrieve_dense()` | Already in `workers/retrieval.py` — keep. |
| `retrieve_sparse()` BM25 | **Port into `workers/retrieval.py`** — load corpus from ChromaDB, tokenise, `BM25Okapi.get_scores(query)`. |
| `retrieve_hybrid()` RRF | **Port + make it the default in `workers/retrieval.py`** — hybrid was the Day 08 winning config (best faithfulness on edge cases). |
| Day 08 grounded prompt (cite `[n]`, abstain when unsure) | Copy into `workers/synthesis.py` verbatim — it already passes Day 08's faithfulness rubric. |
| LLM-as-Judge (`score_faithfulness`, `score_answer_relevance`, `score_completeness`) | Optional: import into `eval_trace.py` to produce auto-graded comparison numbers for `docs/single_vs_multi_comparison.md`. |
| Abstain behaviour (q09 "Không đủ dữ liệu") | Matches Day 09 gq07 requirement — reuse the same prompt guard so gq07 doesn't hallucinate a penalty number. |

**Borrowed artifacts (already copied):**
- `artifacts/day08_baseline/ab_comparison.csv` — 10-question A/B table (baseline_dense vs variant_hybrid)
- `artifacts/day08_baseline/scorecard_baseline.md` — dense-only scores
- `artifacts/day08_baseline/scorecard_variant.md` — hybrid scores

### Day 08 benchmark numbers (anchors for Day 09 comparison)

| Metric | baseline_dense | variant_hybrid | Day 09 target |
|--------|---------------|----------------|---------------|
| Faithfulness (avg/5) | 4.60 | **5.00** | ≥ 5.00 (multi-agent should not regress grounding) |
| Relevance (avg/5) | 5.00 | 5.00 | 5.00 |
| Context Recall | 5.00 | 5.00 | 5.00 |
| Completeness | 4.29 | 3.00 | **beat 4.29** (supervisor routing + policy worker should improve multi-hop completeness — this is our hypothesis) |

> Day 08 hybrid sacrificed completeness (3.00) for faithfulness (5.00). Day 09's policy worker + cross-worker state should recover completeness without losing faithfulness — prove this in `docs/single_vs_multi_comparison.md`.

## Deadlines
- **17:00** — `grading_questions.json` published
- **18:00** — hard lock for all `.py`, `contracts/`, `docs/`, `artifacts/grading_run.jsonl`
- **After 18:00** — only `reports/group_report.md` and `reports/individual/*.md` may be committed

---

## Current state of the scaffold

**Already working:**
- `graph.py` — AgentState, supervisor routing keyword logic, HITL placeholder — but worker nodes are placeholders, not wired to real workers.
- `workers/retrieval.py` — dense ChromaDB retrieval complete.
- `workers/policy_tool.py` — rule-based exception detection + MCP `search_kb` call complete.
- `workers/synthesis.py` — skeleton present, LLM grounded call is TODO.
- `mcp_server.py` — 4 tools fully implemented: `search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket`, with schemas + dispatch.
- `eval_trace.py` — run/grading/analyze/compare all implemented.
- `contracts/worker_contracts.yaml` — present.
- `docs/` and `reports/` — templates only, empty.

**Blocking gaps:**
1. ~~ChromaDB index `chroma_db/` not built~~ — **DONE** (29 chunks, Vertex AI)
2. ~~`graph.py` placeholder nodes~~ — **DONE** (wired to real workers)
3. ~~`workers/synthesis.py` missing grounded LLM call~~ — **DONE** (temperature=0, dynamic confidence)
4. ~~`workers/retrieval.py` missing BM25 + hybrid retrieval~~ — **DONE** (RRF default)
5. Docs (partial — breakdown.md done) + reports blank.

---

## Plan by Sprint

### Sprint 1 — Wire the graph (~30 min)
- [x] Port Day 08's `index.py` chunker → `scripts/build_index.py`. **DONE** — 29 chunks indexed (sla:5, access:7, refund:6, faq:6, hr:5), 0 missing metadata. Vertex AI `text-multilingual-embedding-002`, collection `day09_docs`. See `docs/breakdown.md`.
- [ ] Extend supervisor `risk_keywords` to match `ERR-\d+` pattern, route unknown error codes → `human_review`.
- [ ] Smoke test: `python graph.py` runs 3 built-in queries without error.

**DoD:** supervisor routes 2+ task types correctly, every route logs a non-"unknown" `route_reason`, state has `task`, `route_reason`, `history`, `risk_high`.

### Sprint 2 — Swap placeholders for real workers (~45 min) ✅ DONE
- [x] `graph.py` wired to real workers — imports uncommented, placeholder nodes replaced.
- [x] `workers/retrieval.py` — `retrieve_sparse()` (BM25Okapi) + `retrieve_hybrid()` (RRF k=60) added; `run()` defaults to hybrid.
- [x] `workers/synthesis.py` — grounded LLM call (gpt-4o-mini, temperature=0); dynamic confidence from normalised RRF scores.
- [x] Smoke test passed — 3 queries, correct routing, real answers with citations. See `docs/breakdown.md`.

**DoD:** workers I/O match `contracts/worker_contracts.yaml`; policy worker flags Flash Sale exception; synthesis produces `[1]` citations without hallucination.

### Sprint 3 — MCP deeper wiring (~20 min)
- [ ] `policy_tool.py` already calls `dispatch_tool("search_kb", ...)`. Add:
  - Task contains "P1" + ticket context → `get_ticket_info("P1-LATEST")`
  - Task contains "Level N" + "emergency"/"khẩn cấp" → `check_access_permission(level, role, is_emergency=True)`
- [ ] Supervisor: when `needs_tool=True`, append `"MCP tools planned"` to `route_reason`.
- [ ] Confirm `state["mcp_tools_used"]` entries contain `{tool, input, output, timestamp}`.

**DoD:** ≥2 MCP tools implemented & called from a worker; trace records `mcp_tool_called` + `mcp_result`; supervisor `route_reason` mentions MCP decision.

### Sprint 4 — Traces, docs, reports (~45 min)
- [ ] `python eval_trace.py` → 15 trace files in `artifacts/traces/` + `eval_report.json`.
- [ ] `docs/system_architecture.md`: Mermaid diagram `Supervisor → {retrieval | policy_tool | human_review} → synthesis → END`; worker responsibility table; rationale.
- [ ] `docs/routing_decisions.md`: pick 3+ real traces (SLA P1 → retrieval; Flash Sale refund → policy_tool; ERR-XXX emergency → human_review). Each: task, route, route_reason, outcome.
- [ ] `docs/single_vs_multi_comparison.md`: use `artifacts/day08_baseline/` as the Day 08 anchor. Report ≥2 metrics side-by-side, e.g.:
  - **Faithfulness** — Day 08 hybrid 5.00 vs Day 09 (re-run judge on 10 trace answers)
  - **Completeness** — Day 08 hybrid 3.00 vs Day 09 (expected improvement from policy worker + multi-hop routing)
  - **Debuggability** — Day 08 monolithic trace vs Day 09 per-worker `worker_io_logs` (qualitative)
  - **Latency** — Day 08 ~1 LLM call/q vs Day 09 ~2 (retrieval + synthesis, sometimes + policy). Expect 1.5–2× slower; acceptable trade for observability.
  - **Abstain rate** — compare gq07-type behaviour between the two systems.
- [ ] **At 17:00**: `python eval_trace.py --grading` → `artifacts/grading_run.jsonl`.
- [ ] **Before 18:00**: commit code + docs + grading log.
- [ ] **After 18:00**: write `reports/group_report.md` and `reports/individual/[name].md` (500–800 words, 5-section rubric).

---

## Grading risk register

| Risk | Mitigation |
|------|-----------|
| **gq07** (penalty SLA) hallucinates a number → −50% | Synthesis prompt must explicitly permit abstain; no fallback number |
| **gq09** (multi-hop, 16 pts) only hits one doc → 8/16 | Route contains "P1" AND "Level"/"access" → call both retrieval + policy_tool; synthesis must cite both sources |
| Missing `route_reason` on any graded question → −20% | Verify every `grading_run.jsonl` record has non-empty `route_reason` |
| MCP trace not recorded → lose 2 Sprint 3 points | Confirm `mcp_tools_used` populated on gq01/gq03/gq09 |
| Commit after 18:00 | Push code before 17:45; leave only reports for later |

## Bonus targets (+5 max)
- [ ] +2: real MCP HTTP server (skip unless time)
- [ ] +1: dynamic confidence score (plan includes this)
- [ ] +2: gq09 full marks + trace shows 2 workers called

---

## Running Order
```bash
# Sprint 1 setup
uv run python scripts/build_index.py       # build ChromaDB
uv run python graph.py                     # smoke test

# Sprint 2/3 verification
uv run python workers/retrieval.py
uv run python workers/policy_tool.py
uv run python workers/synthesis.py
uv run python mcp_server.py

# Sprint 4
uv run python eval_trace.py                # 15 test questions
uv run python eval_trace.py --analyze
uv run python eval_trace.py --grading      # after 17:00
```

## Key Files
- `graph.py` — supervisor orchestrator
- `workers/{retrieval,policy_tool,synthesis}.py` — worker nodes
- `mcp_server.py` — tool registry + dispatcher
- `eval_trace.py` — trace runner + metrics
- `contracts/worker_contracts.yaml` — I/O contracts
- `data/docs/` — 5 source documents (identical to Day 08)
- `artifacts/traces/` — per-question traces (generated)
- `artifacts/grading_run.jsonl` — grading log (generated at 17:00–18:00)

## Notes
- OPENAI_API_KEY lives in `.env`
- Day 08 docs and ChromaDB index are content-identical — can be reused (see "Reusing Day 08" below)
- Abstain behavior mandatory on gq07; grounded citation mandatory on all answers
