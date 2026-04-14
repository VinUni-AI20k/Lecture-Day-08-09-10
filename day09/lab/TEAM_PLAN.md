# Team Plan & Worklog — Lab Day 09

**Lab:** Multi-Agent Orchestration & MCP Integration
**Thời lượng:** 4 giờ (4 Sprint × 60′) + Grading window 17:00–18:00
**Hard cutoff code:** 18:00 — `artifacts/grading_run.jsonl` bắt buộc commit trước giờ này.
**Sau 18:00:** chỉ được nộp `reports/group_report.md` và `reports/individual/[ten].md`.

**Điểm tổng 100:** Nhóm 60 (Sprint 20 + Docs 10 + Grading 30) — Cá nhân 40 (Report 30 + Code contribution 10) — Bonus ≤ +5.

## 1. Phân vai nhóm (6 người)

| #   | Vai trò                          | Thành viên     | File/Deliverable phụ trách                                                              |
| --- | -------------------------------- | -------------- | --------------------------------------------------------------------------------------- |
| 1   | **Team Lead + Supervisor Owner** | **Phúc**       | `graph.py` (supervisor_node, route_decision, build_graph)                               |
| 2   | Retrieval Engineer               | \***\*\_\*\*** | `workers/retrieval.py` + build ChromaDB index từ 5 docs                                 |
| 3   | Policy + MCP Engineer            | \***\*\_\*\*** | `workers/policy_tool.py` + `mcp_server.py`                                              |
| 4   | Synthesis Engineer               | \***\*\_\*\*** | `workers/synthesis.py` (LLM, confidence, abstain)                                       |
| 5   | Evaluation Engineer              | \***\*\_\*\*** | `eval_trace.py` + `artifacts/grading_run.jsonl` + `docs/single_vs_multi_comparison.md`  |
| 6   | Docs + QA                        | \***\*\_\*\*** | `docs/system_architecture.md` + `docs/routing_decisions.md` + `reports/group_report.md` |

> **Quy tắc:** mỗi người chỉ sửa file của mình. Tránh merge conflict trên `graph.py` — chỉ Phúc sửa file này. Các thay đổi liên quan routing gửi qua Phúc.

---

## 2. Nguyên tắc chung (bắt buộc đọc)

1. **Không hallucinate** — bịa thông tin trong grading Q = −50% điểm câu đó. Thà abstain còn hơn bịa.
2. **`route_reason` không được để "unknown"** — mất −20% mỗi câu.
3. **Worker I/O phải khớp `contracts/worker_contracts.yaml`** — grader sẽ check.
4. **Stateless worker:** chỉ đọc `task` từ state, ghi đúng field output của mình.
5. **Log `worker_io_logs` cho mỗi worker** — dùng cho trace analysis.
6. **Mỗi người tự lưu evidence** (commit SHA, screenshot trace, comment review) để viết báo cáo cá nhân — **KHÔNG** thể viết lại sau khi merge.
7. **Commit thường xuyên** (sau mỗi checkpoint) — commit sau 18:00 không tính cho code.
8. **Không copy báo cáo cá nhân** — report giống nhau giữa các thành viên = **0/40 cho tất cả**.

---

## 3. Timeline tổng hợp

### Sprint 1 (0:00–1:00) — Skeleton song song

| Thành viên         | Công việc                                                                                                                             | DoD                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| **Phúc**           | Implement `supervisor_node` tại `graph.py:92-129` với keyword routing + risk flags. Viết `route_decision` + wrapper node placeholder. | `python graph.py` chạy ≥2 loại task, `route_reason` có ý nghĩa. |
| **TV2 Retrieval**  | Build ChromaDB index từ 5 docs trong `data/docs/`. Chuẩn bị `_get_embedding_fn` (SentenceTransformer `all-MiniLM-L6-v2`).             | Index query trả ra chunks với score hợp lệ.                     |
| **TV3 Policy+MCP** | Thiết kế JSON schema cho 4 MCP tool (search_kb, get_ticket_info, check_access_permission, create_ticket).                             | Schema draft trong `mcp_server.py`.                             |
| **TV4 Synthesis**  | Thiết kế prompt + rule abstain. Draft `SYSTEM_PROMPT` với yêu cầu citation `[1]`, no hallucination.                                   | Prompt review xong, sẵn sàng cắm LLM call.                      |
| **TV5 Eval**       | Viết loader cho `data/test_questions.json`. Chuẩn bị `run_test_questions` skeleton.                                                   | Loader parse được 15 câu, in ra console.                        |
| **TV6 Docs+QA**    | Draft skeleton 3 docs (`system_architecture`, `routing_decisions`, `single_vs_multi_comparison`) — chưa điền số liệu.                 | 3 file có section headers đúng template.                        |

✅ **CHECKPOINT 1 (1:00):** Graph chạy end-to-end với placeholder worker. Phúc merge `feat/supervisor` vào main.

---

### Sprint 2 (1:00–2:00) — Implement workers

| Thành viên         | Công việc                                                                                                                          | DoD                                                     |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **Phúc**           | Review PR theo thứ tự: retrieval → policy_tool → synthesis. Check contract compliance. Wire worker thật vào `graph.py:184-229`.    | 3 worker test độc lập pass; đã merge vào graph.         |
| **TV2 Retrieval**  | Implement `retrieve_dense(query, top_k)` tại `workers/retrieval.py:86`. Fallback `[]` nếu ChromaDB fail.                           | Query trả chunks {text, source, score∈[0,1], metadata}. |
| **TV3 Policy+MCP** | Implement `analyze_policy` rule-based: phát hiện flash_sale, digital_product, activated exceptions + temporal scoping.             | Test 3 câu có exception → phát hiện đúng.               |
| **TV4 Synthesis**  | Implement `_call_llm` (GPT-4o-mini, temp=0.1, max_tokens=500). Implement `_estimate_confidence` heuristic.                         | Trả answer có citation, abstain khi chunks=[].          |
| **TV5 Eval**       | Viết `run_test_questions()` gọi `graph.invoke()` từng câu, save trace JSON.                                                        | Chạy thử 1 câu → trace file xuất hiện.                  |
| **TV6 Docs+QA**    | Viết contract checker script (load YAML, verify worker output có đủ field). Bắt đầu điền bảng worker vào `system_architecture.md`. | Checker chạy OK trên 1 worker.                          |

✅ **CHECKPOINT 2 (2:00):** 3 worker hoạt động qua graph; trace có đủ field cơ bản.

---

### Sprint 3 (2:00–3:00) — MCP integration

| Thành viên         | Công việc                                                                                                                                                                 | DoD                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **Phúc**           | Test routing cho gq09 multi-hop (cần 2 doc: SLA + Access Control). Quyết định chain: retrieval → policy_tool hay policy_tool tự gọi MCP search_kb. Test abstain cho gq07. | Trace có ≥2 worker trong `workers_called` cho multi-hop.                  |
| **TV2 Retrieval**  | Hỗ trợ TV3 để MCP `search_kb` gọi được ChromaDB của retrieval.                                                                                                            | MCP search_kb trả kết quả giống retrieval worker.                         |
| **TV3 Policy+MCP** | Hoàn thiện `mcp_server.py` với ≥2 tool. Wire `policy_tool_worker` gọi MCP khi `needs_tool=True`. Log `mcp_tools_used` với timestamp.                                      | Trace chứa `mcp_tools_used` với ≥1 call.                                  |
| **TV4 Synthesis**  | Tune `_estimate_confidence`: penalty exception 0.05/ex, abstain → 0.1–0.3. Đảm bảo không hallucinate khi không có context.                                                | 3 test case: có chunks / không chunks / có exception → confidence hợp lý. |
| **TV5 Eval**       | Viết `analyze_traces()`: routing_distribution, avg_confidence, avg_latency_ms, mcp_usage_rate, hitl_rate.                                                                 | Chạy analyze ra dict metrics.                                             |
| **TV6 Docs+QA**    | Bắt đầu điền `routing_decisions.md` với 3 case từ trace thực tế của Sprint 1–2.                                                                                           | 3 routing case có đủ: task → worker → route_reason → correct? (Y/N).      |

✅ **CHECKPOINT 3 (3:00):** Trace đầy đủ 11 field; MCP log đúng; gq09 routing test OK.

---

### Sprint 4 (3:00–4:00) — Evaluation & Docs

| Thành viên         | Công việc                                                                                                                                        | DoD                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| **Phúc**           | Smoke test 15 test questions. Fix bug graph nếu có. Dress rehearsal `--grading` trên test_questions để đảm bảo JSONL format đúng.                | 15/15 câu không crash; JSONL format pass check.           |
| **TV2 Retrieval**  | Standby hỗ trợ debug. Tối ưu top_k nếu kết quả retrieval kém.                                                                                    | —                                                         |
| **TV3 Policy+MCP** | Standby hỗ trợ debug MCP. Kiểm tra log `mcp_tools_used` đầy đủ timestamp.                                                                        | —                                                         |
| **TV4 Synthesis**  | Fix các câu hallucinate (nếu có). Verify gq07 (abstain) hoạt động.                                                                               | Không câu nào bịa khi chunks=[].                          |
| **TV5 Eval**       | Chạy `run_test_questions` → save 15 traces. Chạy `analyze_traces` + `compare_single_vs_multi`. Viết số liệu vào `single_vs_multi_comparison.md`. | `artifacts/traces/` có 15 file; comparison có ≥2 metrics. |
| **TV6 Docs+QA**    | Hoàn thiện `system_architecture.md` (diagram + bảng worker) và `routing_decisions.md` (≥3 case thực). QA contract compliance toàn bộ trace.      | 3 docs hoàn chỉnh, không còn placeholder.                 |

✅ **CHECKPOINT 4 (4:00 / trước 17:00):** Mọi deliverable trừ `grading_run.jsonl` đã ready.

---

### Grading window (17:00–18:00) — CRITICAL

| Thời gian   | Hoạt động                                                                                                                        | Người      |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 17:00       | Nhận 10 grading questions →`data/grading_questions.json`                                                                         | TV5        |
| 17:05       | Start `python eval_trace.py --grading`                                                                                           | TV5        |
| 17:05–17:40 | Monitor log: route đúng? confidence hợp lý? hallucination?                                                                       | Phúc + TV4 |
| 17:40–17:50 | QA `grading_run.jsonl`: 10 dòng, đủ 11 field/dòng, `route_reason` ≠ unknown, confidence ∈ [0,1], gq07 abstain, gq09 có ≥2 worker | Phúc + TV6 |
| 17:55       | `git add artifacts/ && git commit && git push`                                                                                   | Phúc       |
| **18:00**   | **HARD CUTOFF — không commit code sau giờ này**                                                                                  | —          |

---

### Sau 18:00 — Báo cáo

| Deliverable                                           | Người                                      | Khung thời gian |
| ----------------------------------------------------- | ------------------------------------------ | --------------- |
| `reports/individual/[ten].md` (500–800 từ, 30đ/người) | **Mỗi người tự viết**                      | Tối             |
| `reports/group_report.md` (600–1000 từ) — 6 section   | TV6 tổng hợp, mỗi người đóng góp phần mình | Tối             |

---

## 4. Checklist deliverable (trước 18:00)

### Code

- [ ] `graph.py` — supervisor routing ≥2 loại task, `route_reason` có ý nghĩa
- [ ] `workers/retrieval.py` — test độc lập pass
- [ ] `workers/policy_tool.py` — phát hiện exception, log MCP
- [ ] `workers/synthesis.py` — citation + abstain, không hallucinate
- [ ] `mcp_server.py` — ≥2 tool, dispatch log đầy đủ
- [ ] `eval_trace.py` — chạy end-to-end

### Artifacts

- [ ] `artifacts/traces/` — 15 trace file cho test_questions
- [ ] `artifacts/grading_run.jsonl` — 10 dòng JSON hợp lệ ✅
- [ ] `contracts/worker_contracts.yaml` — cập nhật `actual_implementation: done`

### Docs (nhóm)

- [ ] `docs/system_architecture.md` — 4 điểm
- [ ] `docs/routing_decisions.md` — ≥3 case từ trace thực, 3 điểm
- [ ] `docs/single_vs_multi_comparison.md` — ≥2 metrics evidence, 3 điểm

---

## 5. Checklist báo cáo cá nhân (cho phép sau 18:00)

Mỗi thành viên viết `reports/individual/[ten].md` gồm 5 mục:

- [ ] **(7đ) Phần phụ trách** (100–150 từ): file/function/quyết định cụ thể + evidence commit
- [ ] **(8đ) 1 Technical decision**: what, alternatives, why chosen, trade-offs, trace evidence
- [ ] **(8đ) 1 Bug đã fix**: error → symptom → root cause → fix → before/after
- [ ] **(4đ) Self-assessment**: strengths, weaknesses, dependencies
- [ ] **(3đ, optional) +2h improvement**: ý tưởng cụ thể, trace-based

⚠️ **Penalty 0/40 nếu:** report không khớp code, khai công người khác, copy report, không giải thích được quyết định.

---

## 6. Rủi ro & mitigation

| Rủi ro                                          | Likelihood | Impact  | Mitigation                                | Owner      |
| ----------------------------------------------- | ---------- | ------- | ----------------------------------------- | ---------- |
| TV3 (MCP) chậm → graph không test được Sprint 3 | Med        | Cao     | Check mỗi 30′; fallback mock in-process   | Phúc       |
| Merge conflict trên `graph.py`                  | Low        | Cao     | Chỉ Phúc sửa; worker dev file riêng       | Phúc       |
| gq09 fail (16 điểm!)                            | Med        | Rất cao | Dress rehearsal multi-hop trước 17:00     | Phúc + TV3 |
| Hallucination trong grading → −50%              | Med        | Cao     | Synthesis abstain khi chunks=[]           | TV4        |
| ChromaDB index lỗi                              | Low        | Rất cao | Build index sớm từ Sprint 1               | TV2        |
| Quên commit trước 18:00                         | Low        | Fatal   | Alarm 17:50; commit sớm từng phần         | Phúc       |
| Report không match code → 0/40                  | Med        | Fatal   | Mỗi người lưu evidence ngay               | Mỗi người  |
| Copy báo cáo → 0/40 cho cả nhóm                 | Low        | Fatal   | Mỗi người viết độc lập, không share draft | Mỗi người  |

---

## 7. Điểm dễ ăn / dễ mất (ưu tiên cao)

**Dễ ăn (nhất định phải làm):**

- `route_reason` có ý nghĩa cho mọi câu → tránh mất −20%/câu.
- gq07 abstain đúng = 10/10; nếu bịa = −5 penalty → TV4 check kỹ.
- gq09 bonus +1 nếu trace log 2 worker → TV3 + Phúc design chain hợp lý.
- Contract compliance → TV6 dùng checker script.

**Dễ mất (cảnh giác):**

- Level 3 access **KHÔNG có emergency bypass** (chỉ Level 2 có) — gq13/q15 rất dễ sai.
- Temporal scoping (q12/gq02): đơn trước 01/02/2026 áp dụng v3, không phải v4 → abstain hoặc note version.
- Hallucination trong câu không có info → thà abstain.

**Bonus (≤+5) nếu rảnh:**

- Real MCP HTTP server (không mock class): +2Confidence scoring thật (không hard-coded): +1
- gq09 Full + trace đúng 2 worker: +2

---

## 8. Worklog chung (điền trong lúc làm)

### Sprint 1 (0:00–1:00)

- Bắt đầu thực tế: **:**
- Kết thúc thực tế: **:**
- Đã merge: [ ] Phúc [ ] TV2 [ ] TV3 [ ] TV4 [ ] TV5 [ ] TV6
- Ghi chú/blocker:

### Sprint 2 (1:00–2:00)

- Bắt đầu thực tế: **:**
- Kết thúc thực tế: **:**
- Đã merge: [ ] Phúc [ ] TV2 [ ] TV3 [ ] TV4 [ ] TV5 [ ] TV6
- Ghi chú/blocker:

### Sprint 3 (2:00–3:00)

- Bắt đầu thực tế: **:**
- Kết thúc thực tế: **:**
- Đã merge: [ ] Phúc [ ] TV2 [ ] TV3 [ ] TV4 [ ] TV5 [ ] TV6
- Ghi chú/blocker:

### Sprint 4 (3:00–4:00)

- Bắt đầu thực tế: **:**
- Kết thúc thực tế: **:**
- Đã merge: [ ] Phúc [ ] TV2 [ ] TV3 [ ] TV4 [ ] TV5 [ ] TV6
- Ghi chú/blocker:

### Grading run (17:00–18:00)

- Start: **:**
- Số câu chạy OK: \_\_/10
- Vấn đề phát sinh:
- Commit cuối lúc: **:**
- File `grading_run.jsonl` verify: [ ] 10 dòng [ ] đủ field [ ] route_reason OK [ ] gq07 abstain [ ] gq09 multi-worker

---

## 9. Liên kết nhanh

- [README.md](README.md) — mô tả lab
- [SCORING.md](SCORING.md) — rubric chấm điểm chi tiết
- [contracts/worker_contracts.yaml](contracts/worker_contracts.yaml) — I/O contract các worker
- [data/test_questions.json](data/test_questions.json) — 15 câu test nội bộ
- [reports/individual/template.md](reports/individual/template.md) — template báo cáo cá nhân
- [reports/group_report.md](reports/group_report.md) — template báo cáo nhóm

---

**Quy tắc vàng:**

> "Làm ít mà chắc, có trace/evidence rõ ràng" > "Làm nhiều mà không verify được".
> Abstain đúng = 10 điểm. Bịa thông tin = −5 điểm.
