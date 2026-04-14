# Plan & Worklog — Phúc (Team Lead / Supervisor Owner)

**Lab:** Day 09 — Multi-Agent Orchestration & MCP
**Vai trò:** Team Lead + Supervisor/Graph Owner
**File phụ trách chính:** `graph.py` (supervisor_node, route_decision, build_graph)
**Deadline code:** 18:00 (hard cutoff) — `artifacts/grading_run.jsonl` phải commit trước giờ này.

---

## 1. Mục tiêu cá nhân

- Hoàn thành **orchestrator** (`graph.py`) làm xương sống để 3 worker cắm vào.
- Điều phối 5 thành viên còn lại, review PR, chống merge conflict.
- Đảm bảo grading run 17:00–18:00 chạy trơn tru, `grading_run.jsonl` hợp lệ.
- Thu thập evidence (commit SHA, comment, screenshot trace) cho **báo cáo cá nhân 30 điểm**.

---

## 2. Phân vai nhóm (6 người)

| # | Vai trò | Người | File chính |
|---|---------|-------|-----------|
| 1 | **Team Lead + Supervisor** | **Phúc (tôi)** | `graph.py` |
| 2 | Retrieval Engineer | TV2 | `workers/retrieval.py` + ChromaDB index |
| 3 | Policy + MCP Engineer | TV3 | `workers/policy_tool.py` + `mcp_server.py` |
| 4 | Synthesis Engineer | TV4 | `workers/synthesis.py` |
| 5 | Evaluation Engineer | TV5 | `eval_trace.py` + `grading_run.jsonl` + `single_vs_multi_comparison.md` |
| 6 | Docs + QA | TV6 | `system_architecture.md` + `routing_decisions.md` + `group_report.md` |

---

## 3. Timeline cá nhân theo giờ

### Sprint 1 (0:00–1:00) — Supervisor & Graph skeleton

- [ ] **0:00–0:10** Setup: clone repo, copy `.env.example` → `.env`, cài `requirements.txt`, tạo branch `feat/supervisor`.
- [ ] **0:10–0:15** Kickoff nhóm 5 phút: phân vai, thống nhất naming contract, tạo channel liên lạc.
- [ ] **0:15–0:45** Implement `supervisor_node(state)` tại `graph.py:92-129`:
  - Từ khóa policy: `hoàn tiền, refund, flash sale, license, cấp quyền, access, level 3` → `policy_tool_worker`.
  - Từ khóa risk: `emergency, 2am, không rõ, err-` → set `risk_high=True`.
  - Nếu `risk_high` + mã lỗi lạ → `supervisor_route = human_review`.
  - Luôn set `route_reason` có ý nghĩa (KHÔNG để "unknown" — mất −20%/câu).
- [ ] **0:45–0:55** Implement `route_decision(state)` + wrapper node (placeholder worker trả dict rỗng).
- [ ] **0:55–1:00** Smoke test: `python graph.py` với 1 câu mẫu → verify trace có `supervisor_route` + `route_reason`.
- ✅ **CHECKPOINT 1:** Graph chạy end-to-end với ≥2 loại task; commit `feat/supervisor`.

### Sprint 2 (1:00–2:00) — Review + tích hợp worker

- [ ] **1:00–1:30** Review PR của TV2/TV3/TV4 theo thứ tự merge: retrieval → policy_tool → synthesis.
  - Check contract compliance với `contracts/worker_contracts.yaml`.
  - Check stateless, không fake data, có `worker_io_logs`.
- [ ] **1:30–1:50** Wire worker thật vào `graph.py:184-229` (uncomment import, thay placeholder).
- [ ] **1:50–2:00** Chạy thử 3 câu (1 retrieval, 1 policy, 1 abstain) → log trace.
- ✅ **CHECKPOINT 2:** Cả 3 worker hoạt động qua graph; đã merge vào `main`.

### Sprint 3 (2:00–3:00) — MCP integration

- [ ] **2:00–2:15** Đồng hành TV3 wire MCP vào policy_tool; verify `mcp_tools_used` có trong trace.
- [ ] **2:15–2:45** Tinh chỉnh routing cho các câu khó:
  - **gq09 (16pt multi-hop):** route phải gọi được **cả** retrieval + policy (vì cần 2 doc: `sla_p1_2026.txt` + `access_control_sop.txt`). Cân nhắc: route sang policy_tool rồi policy_tool tự gọi MCP `search_kb`, hoặc chain retrieval → policy.
  - **gq07 (abstain):** đảm bảo khi `retrieved_chunks=[]` → synthesis abstain, không hallucinate.
- [ ] **2:45–3:00** Test 5 câu đại diện trên graph hoàn chỉnh.
- ✅ **CHECKPOINT 3:** Trace có đủ `supervisor_route, route_reason, workers_called, mcp_tools_used, confidence, hitl_triggered`.

### Sprint 4 (3:00–4:00) — Smoke test & chuẩn bị grading

- [ ] **3:00–3:30** Hỗ trợ TV5 chạy `eval_trace.py` trên 15 test_questions; fix bug graph nếu có.
- [ ] **3:30–3:45** Verify metrics hợp lý: routing_distribution ≠ 100% một worker, avg_confidence > 0.3, không có câu nào crash.
- [ ] **3:45–4:00** Dress rehearsal grading run: giả lập `--grading` trên test_questions để đảm bảo JSONL format đúng.

### Grading window (17:00–18:00)

- [ ] **17:00** Nhận 10 grading questions, đưa vào `data/grading_questions.json`.
- [ ] **17:05–17:40** TV5 chạy `python eval_trace.py --grading`; tôi monitor log, sẵn sàng fix bug graph.
- [ ] **17:40–17:50** QA lần cuối `artifacts/grading_run.jsonl`:
  - Đúng 10 dòng JSON.
  - Mỗi dòng có đủ 11 field.
  - `route_reason` không rỗng/unknown.
  - `confidence` ∈ [0,1]; không có NaN.
  - gq07 phải abstain (không hallucinate).
  - gq09 trace có ≥2 worker trong `workers_called` (nhắm +1 bonus).
- [ ] **17:55** `git add artifacts/ && git commit -m "grading run" && git push`.
- [ ] **18:00** HARD CUTOFF — không commit code sau giờ này.

### Sau 18:00 — Báo cáo cá nhân + phần group_report của tôi

- [ ] Viết `reports/individual/phuc.md` (500–800 từ, **30 điểm**).
- [ ] Đóng góp mục "Architecture summary" cho `reports/group_report.md` (phối hợp với TV6).

---

## 4. Báo cáo cá nhân — chuẩn bị sẵn evidence

**File:** `reports/individual/phuc.md` (500–800 từ)

### (1) Phần phụ trách (100–150 từ, 7 điểm)
- File: `graph.py` — `supervisor_node`, `route_decision`, `build_graph`, wrapper node.
- Quyết định: chọn keyword-based routing thay vì LLM-based (lý do: latency + debuggability).
- Kết nối với các thành viên: định nghĩa AgentState schema để 3 worker tuân theo; review PR retrieval/policy/synthesis.
- **Evidence cần lưu:** commit SHA của PR `feat/supervisor`, link comment review trên PR của TV2–TV4.

### (2) Technical decision (150–200 từ, 8 điểm)
Ứng viên (chọn 1 khi viết):
- **A.** Keyword routing vs LLM-based router — trade-off latency/cost vs flexibility.
- **B.** Cho phép policy_tool gọi retrieval qua MCP (để xử lý gq09 multi-hop) thay vì chain retrieval → policy.
- **C.** Quy tắc set `risk_high` + điều kiện trigger `human_review`.
- **Evidence cần lưu:** 2–3 trace entries minh hoạ quyết định hoạt động đúng.

### (3) Bug đã fix (150–200 từ, 8 điểm)
Dự kiến bug có thể gặp (ghi lại ngay khi gặp):
- Supervisor route sai khi task có cả keyword policy lẫn keyword retrieval → giải quyết bằng priority order.
- `route_reason` rỗng vì quên set trước khi return state delta.
- Graph infinite loop do conditional edge sai.
- **Evidence cần lưu:** before trace (lỗi) + after trace (đã fix) + diff commit.

### (4) Self-assessment (100–150 từ, 4 điểm)
- **Strengths:** orchestration, code review, điều phối timeline.
- **Weaknesses:** chưa deep về ChromaDB embedding; phụ thuộc TV2 cho retrieval quality.
- **Dependencies:** TV3 (MCP) là critical path — nếu TV3 chậm, graph không test được.

### (5) Improvement +2h (50–100 từ, 3 điểm)
Ý tưởng cụ thể:
- Thay keyword routing bằng small classifier LLM với few-shot prompt → đo improvement trên 15 test Q.
- HOẶC: thêm retry logic khi worker fail + circuit breaker cho MCP.
- **Evidence cần lưu:** trace cụ thể câu nào hiện đang route sai mà improvement sẽ fix.

---

## 5. Rủi ro & mitigation

| Rủi ro | Likelihood | Impact | Mitigation |
|--------|-----------|--------|-----------|
| TV3 (MCP) chậm → graph không test được Sprint 3 | Med | Cao | Check TV3 mỗi 30′; có fallback mock in-process |
| Merge conflict trên `graph.py` | Low | Cao | Chỉ tôi sửa `graph.py`; các worker dev trong file riêng |
| gq09 fail (16 điểm!) | Med | Rất cao | Dress rehearsal multi-hop trước 17:00; đảm bảo trace log 2 worker |
| Hallucination trong grading → −50% | Med | Cao | Synthesis phải abstain khi `retrieved_chunks=[]`; TV4 check |
| Quên commit trước 18:00 | Low | Fatal | Set alarm 17:50; commit từng phần sớm |
| Báo cáo cá nhân không match code | Low | Fatal (0/40) | Ghi chép evidence ngay khi làm; không viết claim mơ hồ |

---

## 6. Checklist commit theo giờ

- [ ] 1:00 — `feat/supervisor` merge
- [ ] 2:00 — workers wired vào graph
- [ ] 3:00 — MCP integrated, trace đầy đủ field
- [ ] 4:00 — eval chạy thành công trên 15 test Q
- [ ] 17:55 — `grading_run.jsonl` committed
- [ ] Sau 18:00 — `reports/individual/phuc.md` + phần architecture của `group_report.md`

---

## 7. Worklog (điền trong lúc làm)

### Sprint 1
- Thời gian thực tế: __:__ – __:__
- Đã làm: 
- Bug gặp: 
- Commit SHA: 

### Sprint 2
- Thời gian thực tế: __:__ – __:__
- Đã làm: 
- Bug gặp: 
- Commit SHA: 

### Sprint 3
- Thời gian thực tế: __:__ – __:__
- Đã làm: 
- Bug gặp: 
- Commit SHA: 

### Sprint 4
- Thời gian thực tế: __:__ – __:__
- Đã làm: 
- Bug gặp: 
- Commit SHA: 

### Grading run
- Thời gian bắt đầu: __:__
- Số câu chạy thành công: __/10
- Vấn đề phát sinh: 
- Commit cuối: 

---

## 8. Liên kết nhanh

- [graph.py](graph.py) — file tôi phụ trách
- [contracts/worker_contracts.yaml](contracts/worker_contracts.yaml) — contract các worker phải tuân
- [SCORING.md](SCORING.md) — rubric chấm điểm
- [data/test_questions.json](data/test_questions.json) — 15 câu test nội bộ
- [reports/individual/template.md](reports/individual/template.md) — template báo cáo cá nhân
