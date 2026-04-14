# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** 2A202600292-TranDangQuangHuy  
**Thành viên:** *(ẩn thông tin theo yêu cầu; nhóm 5 người)*  
**Ngày nộp:** 2026-04-14  
**Repo:** `Lecture-Day-08-09-10/day09/lab`

---

## 1. Kiến trúc nhóm đã xây dựng

Nhóm triển khai kiến trúc **Supervisor-Worker** bằng LangGraph với các node: `supervisor -> retrieval_worker/policy_tool_worker/human_review -> synthesis_worker -> supervisor_audit -> END`. Mỗi worker xử lý đúng domain riêng: retrieval lấy evidence, policy xử lý rule + MCP, synthesis tạo câu trả lời grounded và citation. `supervisor_audit` là bước cuối để ghi `mcp_used` và `latency_ms` cho toàn run.

Routing hiện tại là rule-based theo keyword. Nếu task có tín hiệu `P1/SLA/ticket` thì ưu tiên retrieval; nếu có `refund/access/level` thì route policy; nếu có mã lỗi mơ hồ (`ERR-*`) thì chuyển `human_review`. Route reason được log chi tiết trong trace.
Routing hiện tại là rule-based theo keyword nhưng có scoring ưu tiên cho case lai:
- `access/level/contractor` được ưu tiên route policy kể cả có `P1/SLA` (multi-hop).
- refund fact query đơn giản (ví dụ hỏi “bao nhiêu ngày”) route retrieval.
- mã lỗi `ERR-*` route retrieval trước để hỗ trợ abstain có căn cứ; chỉ đẩy `human_review` nếu có high-risk context.

MCP tools đã tích hợp và dùng trong run:
- `search_kb`: gọi ở các query policy như `q03`, `q07`, `q10`, `q12`, `q13`, `q15`.
- `check_access_permission`: gọi ở `q03` (Level 3 approval).
- `get_ticket_info`: có tích hợp trong worker, chỉ kích hoạt theo điều kiện task/ticket.
- `create_ticket`: có trong server nhưng đang bị safeguard chặn mặc định nếu không bật explicit side-effect.

**Bằng chứng:** run `sprint4_test_latencyopt_20260414`, file `artifacts/runs/sprint4_test_latencyopt_20260414.jsonl`.

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:** Ưu tiên route `policy_tool_worker` khi task chứa signal access-control rõ ràng (`access/level/contractor`), kể cả có `P1/SLA`.

**Bối cảnh vấn đề:**
Nhóm cần chọn ưu tiên route khi gặp câu “pha trộn” giữa vận hành sự cố và chính sách quyền truy cập (multi-hop). Ở vòng đầu nhóm ưu tiên retrieval và bị lệch route ở `q13`, `q15`. Sau đó nhóm đổi quyết định sang access-first policy route.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Ưu tiên retrieval khi có `P1/SLA` | Nhanh, ổn định cho câu incident thuần | Lệch route ở multi-hop cần policy/access |
| Ưu tiên policy khi có `access/level/contractor` | Đúng intent multi-hop, MCP đầy đủ | Tăng latency ở case policy path |

**Phương án đã chọn và lý do:**
Nhóm chọn access-first policy route cho case multi-hop, đồng thời giữ retrieval cho incident thuần. Sau đó nhóm tối ưu policy-path để giảm MCP round-trip thừa. Kết quả vừa đạt route accuracy 100% vừa giữ latency thấp.

**Bằng chứng từ trace/code:**

```
q15 route_reason:
access-control keywords matched (access, level 2, contractor, emergency);
incident/SLA keywords also present (p1, sla, ticket), policy is prioritized for multi-hop;
... | mcp_used=True
```
Kết quả: `q13`, `q15` được route đúng expected route ở run mới.

---

## 3. Kết quả grading questions

Trong phiên làm việc này, nhóm **chưa chạy `grading_questions.json` của Day09** nên không ghi điểm raw để tránh khai sai dữ liệu. Nhóm chỉ có số liệu xác thực từ test set (`data/test_questions.json`) ở Sprint 4.

**Trạng thái hiện có (test set Day09):**
- 15/15 chạy thành công.
- Route accuracy theo expected route: `15/15` (100.0%).
- Routing distribution: retrieval 9, policy 6.

**Câu xử lý tốt (test set):**
- `q03` — route đúng vào policy, gọi đủ `search_kb` + `check_access_permission`, answer nêu đúng approver chain.

**Câu fail/partial (test set):**
- Không có fail route trong run mới. Case `q09` vẫn trigger low-confidence abstain như thiết kế.

> Ghi chú: mục grading (`gq07`, `gq09`) sẽ được cập nhật sau khi nhóm chạy đúng file Day09 grading trong phiên riêng.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được

Nguồn số liệu so sánh:
- Day08 test questions: `day08/lab/results/ab_comparison.csv` (không dùng grading logs).
- Day09 test questions: `artifacts/runs/sprint4_test_latencyopt_20260414_summary.json`.

**Day08 (test questions) — baseline_dense:**
- Avg faithfulness: `3.6/5`
- Avg relevance: `4.6/5`
- Avg completeness: `2.8/5`
- Avg latency: `3977.624 ms`
- Heuristic abstain rate: `30%`

**Day09 (test questions):**
- Avg confidence: `0.851` *(thang 0-1, sau confidence + route + latency pass)*
- Avg latency: `1078.47 ms`
- Route visibility: có `route_reason`, `workers_called`, `mcp_tools_used`
- MCP usage rate: `40.0%`
- Abstain rate: `6.67%` (1/15)
- HITL usage rate: `6.67%` (1/15)
- Route accuracy: `100.0%` (15/15)

**Metric thay đổi rõ nhất:** route accuracy tăng từ `73.33%` lên `100.0%` sau route pass; đồng thời confidence giữ mức cao (`0.851`) so với baseline (`0.295`).

**Điều bất ngờ:** Day09 latency trung bình sau latency-pass còn thấp hơn Day08 baseline đáng kể (~ -2899ms).

**Trường hợp multi-agent chưa giúp tốt:** numeric fidelity vẫn chưa cao (40% theo heuristic test).

---

## 5. Phân công và đánh giá nhóm

### Phân công thực tế cuối cùng

| Thành viên | Vai trò chính | Phần phụ trách | Ghi chú |
|--------|-------------|-------------|--------|
| Trần Đăng Quang Huy | Supervisor Owner + Trace & Docs Owner | `graph.py`, `eval_trace.py`, trace files, docs/report | Quản lý, thực hiện eval, implement cross_eval để so sánh day08 và day09
| `member_1` | Retrieval Owner | `workers/retrieval.py`, chunk scoring, fallback hints, numeric grounding | Tập trung grounding và source recall |
| `member_2` | Policy/MCP Owner | `workers/policy_tool.py`, `mcp_server.py`, `mcp_mock_server.py`, `mcp_config.json` | Thêm guardrails + tool calling |
| `member_3` | Synthesis/Confidence Owner | `workers/synthesis.py`, confidence tuning, citation enforcement, `eval_cross_day.py` | Bảo đảm answer thật grounded |
| `member_4` | UI/UX + Demo + Setup Owner | `static/`, `templates/`, `README.md`, `.env.example`, `requirements.txt`, `docs/pitch_guide.md` | Chịu phần demo project và clone/setup polish |

**Nguyên tắc chia việc:**
- Mỗi người giữ một miền trách nhiệm chính để tránh đụng nhau khi commit.
- `member_4` phụ trách phần demo/UI/UX và polish setup để người khác clone repo là chạy được ngay.
- Huy giữ nguyên contribution hiện tại, chỉ chốt integration và report cuối cùng sau khi các phần còn lại ổn định.

**Điều nhóm làm tốt:**
- Hoàn thành đầy đủ luồng sprint, có artifacts thật cho Sprint 4.
- Tách mock và real MCP rõ ràng.
- Báo cáo có dẫn chứng trace theo từng case.

**Điều nhóm làm chưa tốt:**
- Numeric fidelity chưa cao ở nhóm câu có nhiều mốc số.

**Nếu làm lại:**
- Chốt tiêu chí route scorer sớm cho case pha trộn SLA + access.
- Chạy thêm vòng tuning trước khi đóng report.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

1. Cải thiện retrieval quality + numeric grounding để tăng độ chính xác số liệu trong câu trả lời.
2. Chuẩn hoá benchmark warm-up vs steady-state để theo dõi latency ổn định hơn qua nhiều lần chạy.

---

## 7. Error Tree (Debug Decision Tree)

```text
Start: Answer sai / thiếu / route không đúng
│
├─ 1) Kiểm tra supervisor routing
│   ├─ Xem supervisor_route + route_reason trong trace
│   ├─ Nếu route sai theo expected intent
│   │   └─ Sửa routing rules (ưu tiên policy cho case multi-hop)
│   └─ Nếu route đúng
│       └─ Sang bước 2
│
├─ 2) Kiểm tra retrieval quality
│   ├─ Xem retrieved_chunks, retrieved_sources, score
│   ├─ Nếu chunks nhiễu hoặc thiếu nguồn chính
│   │   └─ Tuning retrieval (top_k, filtering, fallback strategy)
│   └─ Nếu retrieval ổn
│       └─ Sang bước 3
│
├─ 3) Kiểm tra policy & MCP
│   ├─ Xem mcp_tools_used có được gọi chưa
│   ├─ Nếu cần policy mà mcp_used=False
│   │   └─ Xem lại needs_tool/routing condition
│   ├─ Nếu MCP gọi lỗi
│   │   └─ Kiểm tra transport + server guardrails + input schema
│   └─ Nếu policy/MCP ổn
│       └─ Sang bước 4
│
└─ 4) Kiểm tra synthesis & confidence
    ├─ Nếu final_answer thiếu citation hoặc lệch evidence
    │   └─ Rà prompt grounding + citation enforcement
    ├─ Nếu confidence quá thấp hàng loạt
    │   └─ Kiểm tra score distribution đầu vào từ retrieval
    └─ Nếu vẫn không đạt
        └─ Trigger HITL + ghi issue vào trace để iterate
```

---

## 8. Kế hoạch commit an toàn

Xem chi tiết trong `docs/commit_plan.md`. Tóm tắt ngắn:
- commit theo từng branch nhỏ,
- review xong mới merge,
- Huy là người chốt integration cuối cùng,
- không push `.env`, `chroma_db/`, hay file grading trước khi đến đúng thời điểm công bố.

---

*File này lưu tại: `reports/group_report.md`*