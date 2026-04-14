# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Day09-Lab-Team  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| ___ | Supervisor Owner | ___ |
| 2A202600497 Trần Nhật Vĩ | Worker Owner | vitrannhat@gmail.com |
| ___ | MCP Owner | ___ |
| ___ | Trace & Docs Owner | ___ |

**Ngày nộp:** 2026-04-14  
**Repo:** `day09/lab`  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

## Checklist nộp nhanh (theo rubric Group 60)

- [ ] Nêu rõ kiến trúc + routing logic + MCP tools đã dùng.
- [ ] Có số liệu grading (raw/96) và nhận xét gq07 + gq09.
- [ ] Có ít nhất 2 metric so sánh Day08 vs Day09 với nguồn dữ liệu.
- [ ] Có bảng phân công khớp thực tế code/trace.
- [ ] Không có claim vượt quá hiện trạng code chạy.

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn hệ thống nhóm: bao nhiêu workers, routing logic hoạt động thế nào,
> MCP tools nào được tích hợp. Dùng kết quả từ `docs/system_architecture.md`.

**Hệ thống tổng quan:**

Nhóm triển khai kiến trúc Supervisor-Worker bằng Python thuần trong `graph.py`. Supervisor chịu trách nhiệm route theo keyword và gắn `route_reason`, còn domain logic tách sang 3 worker: `retrieval.py`, `policy_tool.py`, `synthesis.py`. `policy_tool` gọi `mcp_server.dispatch_tool()` để dùng tool bên ngoài theo pattern MCP mock (`search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket`). `eval_trace.py` chạy batch câu hỏi, lưu trace và tổng hợp metric giúp debug từng bước.

**Routing logic cốt lõi:**
> Mô tả logic supervisor dùng để quyết định route (keyword matching, LLM classifier, rule-based, v.v.)

Routing đang dùng rule-based keyword: câu SLA/P1/ticket/escalation ưu tiên `retrieval_worker`; câu refund/access/license ưu tiên `policy_tool_worker` và bật `needs_tool=True`; câu có tín hiệu rủi ro (`emergency`, `err-`) gắn `risk_high`. Mô hình này giúp trace dễ đọc, nhưng hiện còn điểm yếu ở câu multi-hop vì chưa có dual-route chain chính thức.

**MCP tools đã tích hợp:**
> Liệt kê tools đã implement và 1 ví dụ trace có gọi MCP tool.

- `search_kb`: được gọi khi policy worker thiếu chunks.
- `get_ticket_info`: được gọi cho task có ticket/P1/Jira.
- `check_access_permission`: được gọi cho task access level/emergency.

**Bằng chứng bắt buộc cho mục 1:**
- File code: `graph.py`, `workers/*.py`, `mcp_server.py`
- Trace file/id: `artifacts/traces/run_20260414_165651.json`

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** Dùng supervisor rule-based + route_reason chi tiết thay vì classifier LLM cho sprint đầu.

**Bối cảnh vấn đề:**

Trong lab timebox ngắn, nhóm cần ưu tiên hệ thống chạy ổn, trace rõ và sửa lỗi nhanh. Nếu dùng classifier LLM cho routing từ đầu sẽ phụ thuộc API/key và tăng độ biến thiên, khó debug khi output sai.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Rule-based keyword route | Nhanh, ổn định, dễ audit trace | Không bắt được ngữ nghĩa multi-hop phức tạp |
| LLM classifier route | Linh hoạt hơn với câu mơ hồ | Phụ thuộc API, khó kiểm soát trong lab |

**Phương án đã chọn và lý do:**

Nhóm chọn rule-based ở sprint hiện tại để đảm bảo có thể chạy end-to-end và có trace minh bạch. Đánh đổi là một số câu đa domain (P1 + access) chưa route đủ hai nhánh.

**Bằng chứng từ trace/code:**
> Dẫn chứng cụ thể (VD: route_reason trong trace, đoạn code, v.v.)

```
route_reason: "task contains policy/access keyword -> policy_tool_worker + MCP allowed"
workers_called: ["policy_tool_worker", "synthesis_worker"]
mcp_tools_used: [{"tool": "search_kb", ...}]
```

**Nguồn dẫn chứng:**
- File: `graph.py`, `workers/policy_tool.py`
- Trace id/run id: `run_20260414_165651`

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** `92.0/96` (chấm lại theo rubric Day09 trong `SCORING.md`)
**Quy đổi điểm nhóm (gợi ý):** `28.75/30` (theo tỉ lệ `raw/96 * 30`)

**Câu pipeline xử lý tốt nhất:**
- ID: gq09 — Lý do tốt: đạt đủ 2 domain (SLA notification + Level 2 emergency access), full `5/5` criteria, điểm `16/16`.

**Câu pipeline fail hoặc partial:**
- ID: gq08 — Hiện là partial `4/8` (`2/3` criteria).  
  Root cause: cần trả lời đúng tuyệt đối cả chu kỳ đổi mật khẩu và số ngày cảnh báo trước theo đúng nguồn FAQ.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?

Ở `gq07`, hệ thống đã chuyển sang abstain rõ: xác nhận không có mức phạt tài chính trong tài liệu và gợi ý liên hệ legal/finance, nên đang đạt full theo bản chấm Day09.

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?

`gq09` đã chạy thật: route `policy_tool_worker` theo nhánh multi-hop, workers có cả retrieval + policy + synthesis, và bản chấm Day09 hiện cho full `16/16`.

**Bằng chứng bắt buộc cho mục 3:**
- File: `artifacts/grading_run.jsonl`
- Dòng/ID đã dùng để phân tích: `artifacts/grading_run.jsonl` với `gq04`, `gq07`, `gq09`, `gq10`
- File chấm điểm: `artifacts/day09_scoring.json`

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**

MCP usage rate và confidence là hai metric nổi bật: `mcp_usage_rate=5/15 (33%)`, `avg_confidence=0.739`, `avg_latency_ms=3494`, `hitl_rate=1/15 (6%)`.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**

Điểm bất ngờ là chỉ cần đồng bộ đúng embedding provider giữa indexing và retrieval, chất lượng câu trả lời tăng rõ mà không phải đổi kiến trúc.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**

Multi-agent vẫn chậm hơn single-agent tiềm năng ở case đơn giản nếu worker chain dài, và hiện chưa có số liệu Day08 để kết luận delta tuyệt đối.

**Nguồn metric:**
- `docs/single_vs_multi_comparison.md`
- `artifacts/eval_report.json` hoặc `eval_trace.py --analyze`

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Hien | graph routing + docs + eval | 1,4 |
| Phong | retrieval/policy/synthesis worker wiring | 2,3 |
| ___ | MCP kiểm thử + validate traces | 3,4 |
| ___ | Report tổng hợp + đối chiếu rubric | 4 |

**Điều nhóm làm tốt:**

Nhóm chia module rõ, mỗi sprint có output kiểm thử độc lập, nên debug nhanh và không block toàn pipeline.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**

Ban đầu chưa khóa sớm chuẩn embedding cho Chroma nên tốn thời gian debug; sau khi đồng bộ Vertex embedding thì pipeline ổn định lại.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**

Nếu làm lại, nhóm sẽ chốt "index + embedding model contract" ngay đầu Sprint 2 và thêm smoke test provider trước khi chạy batch 15 câu.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ trace/scorecard.

1) Tinh chỉnh abstain logic cho câu dạng gq07 (không có số liệu phạt trong tài liệu). 2) Viết script đối chiếu auto theo rubric để ước tính raw/96 trước khi nộp.

---

## Self-check trước khi nộp

- [ ] Mọi nhận định đều có evidence tương ứng (trace/code/metric).
- [ ] Không mâu thuẫn với `docs/system_architecture.md`.
- [ ] Không mâu thuẫn với `docs/routing_decisions.md`.
- [ ] Không mâu thuẫn với `docs/single_vs_multi_comparison.md`.

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
