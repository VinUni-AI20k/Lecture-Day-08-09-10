# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** C401 - C5
**Thành viên:**

| Tên              | Vai trò            | Mã học viên |
| ---------------- | ------------------ | ----------- |
| Nguyễn Khánh Nam | Supervisor Owner   | \_\_\_      |
| Đỗ Minh Phúc     | Worker Owner       | 2A202600039 |
| Lê Tú Nam        | Worker Owner       | 2A202600109 |
| Lê Hữu Hưng      | Worker Owner       | 2A202600098 |
| Chu Minh Quân    | MCP Owner          | \_\_\_      |
| Nguyễn Minh Hiếu | Trace & Docs Owner | \_\_\_      |

**Ngày nộp:** 14/04/2026

**Repo:** https://github.com/nam-k-nguyen/Lecture-Day-08-09-10

---

## 1. Kiến trúc nhóm đã xây dựng

**Hệ thống tổng quan:**
Nhóm xây dựng hệ thống theo mô hình **Supervisor-Worker** với 1 Supervisor điều phối và 3 Workers chuyên biệt: `retrieval_worker` (dense retrieval từ ChromaDB), `policy_tool_worker` (kiểm tra luật nghiệp vụ + MCP), và `synthesis_worker` (tổng hợp câu trả lời với citation). Ngoài ra có node `human_review` (HITL) cho các trường hợp rủi ro cao. Graph được implement bằng Python thuần (không cần LangGraph), đủ để trace toàn bộ pipeline qua `AgentState` TypedDict dùng chung.

**Routing logic cốt lõi:**Supervisor dùng **keyword matching + regex** với 2 nhóm từ khóa độc lập:

- Policy keywords (`"hoàn tiền"`, `"refund"`, `"flash sale"`, `"license"`, `"cấp quyền"`, `"level 2/3"`, ...) → `policy_tool_worker`
- Retrieval keywords (`"p1"`, `"sla"`, `"ticket"`, `"escalat"`, `"mật khẩu"`, `"remote"`, ...) → `retrieval_worker`
- Regex `\berr-[a-z0-9\-]+\b` phát hiện mã lỗi lạ → `human_review` (HITL)
- Nếu câu hỏi chứa từ khóa của **cả hai nhóm** (VD: `"level 3"` + `"p1"`) → multi-hop, route sang `policy_tool_worker` và gọi tiếp `retrieval_worker`

Qua 15 trace (test set + 10 câu grading) lưu trong `artifacts/traces/`: ~**50% route sang `policy_tool_worker`**, ~**50% route sang `retrieval_worker`**, phản ánh đúng sự phân bổ đa dạng của test cases.

**Routing logic cốt lõi:**
Supervisor sử dụng **Keyword & Regex matching** để đưa ra quyết định routing. Các từ khóa về SLA/Ticket được route sang `retrieval_worker`. Các từ khóa về hoàn tiền/cấp quyền được route sang `policy_tool_worker`. Trường hợp câu hỏi multi-hop (vừa có access control + SLA) được nhận diện riêng và gọi cả 2 workers. Hệ thống nhận diện mã lỗi không xác định (`err-xxx`) để route sang `human_review` node — node này auto-approve trong lab mode rồi tiếp tục về `retrieval_worker`, đồng thời đặt `hitl_triggered = True` trong trace.

**MCP tools đã tích hợp:**

- `search_kb`: tìm kiếm thêm trong ChromaDB khi `needs_tool=True`
- `get_ticket_info`: tra cứu thông tin Jira ticket (mocked)
- `check_access_permission`: kiểm tra approval matrix Level 1/2/3
- `create_ticket`: tạo ticket mới (mock)

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định chính: Chấp nhận đánh đổi Latency để lấy Observability.**

**Bối cảnh vấn đề:**
Day 08 dùng Single Agent RAG — khi trả lời sai (VD: áp sai policy v3 thay vì v4), không có cách nào xác định lỗi nằm ở bước retrieval hay suy luận. Nhóm cần kiểm soát được từng chặng của pipeline.

**Các phương án đã cân nhắc:**

| Phương án                      | Ưu điểm                                                        | Nhược điểm                                         |
| ------------------------------ | -------------------------------------------------------------- | -------------------------------------------------- |
| Single Agent (Day 08)          | Nhanh (~1,850ms), ít LLM call                                  | "Hộp đen", không biết bước nào sai, dễ hallucinate |
| **Supervisor-Worker (Day 09)** | Trace rõ từng node, kiểm soát được output, multi-hop chính xác | Latency tăng (~16,315ms avg), nhiều LLM call hơn   |

**Phương án chọn:** Supervisor-Worker, vì bài toán IT Helpdesk doanh nghiệp cần **Governance** hơn là tốc độ.

**Quyết định phụ: Fail-loud trong `route_decision()` thay vì silent fallback.**
Khi `supervisor_route` rỗng hoặc không hợp lệ, hệ thống raise `ValueError` ngay lập tức thay vì fallback về default. Lý do: lỗi routing ẩn rất khó phát hiện khi chạy production.

```python
# graph.py — route_decision()
if not route:
    raise ValueError(
        f"[route_decision] supervisor_route is empty — "
        f"supervisor_node chưa chạy hoặc state bị corrupt. "
        f"run_id={state.get('run_id')}"
    )
if route not in VALID_ROUTES:
    raise ValueError(
        f"[route_decision] unknown route: '{route}'. "
        f"Expected one of {VALID_ROUTES}."
    )
```

**Bằng chứng từ trace:** Trong 15 trace đã lưu, không có lần nào bị silent wrong-route — tất cả đều có `route_reason` rõ ràng, ví dụ `"multi-hop: access control + SLA context | risk_high flagged"` cho câu `"Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp"`.

---

## 3. Kết quả test questions

Nhóm đã chạy pipeline trên test set + 10 câu grading, tổng 15 trace lưu trong `artifacts/traces/`:

**Routing Distribution:**

Nhóm đã chạy pipeline với **10 câu grading questions** (gq01–gq10) trong khung 17:00–18:00. Kết quả được lưu tại `artifacts/grading_run.jsonl`.

**Tổng quan kết quả:**

| Câu  | Supervisor Route   | Confidence | HITL | MCP Tool        | Latency (ms) |
| ---- | ------------------ | ---------- | ---- | --------------- | ------------ |
| gq01 | retrieval_worker   | 0.77       | ✗    | —               | 15,938       |
| gq02 | policy_tool_worker | 0.71       | ✗    | —               | 11,246       |
| gq03 | policy_tool_worker | 0.77       | ✗    | get_ticket_info | 10,639       |
| gq04 | policy_tool_worker | 0.72       | ✗    | —               | 7,853        |
| gq05 | retrieval_worker   | 0.80       | ✗    | —               | 8,360        |
| gq06 | retrieval_worker   | 0.79       | ✗    | —               | 10,074       |
| gq07 | retrieval_worker   | **0.30**   | ✅   | —               | 7,776        |
| gq08 | retrieval_worker   | 0.77       | ✗    | —               | 9,508        |
| gq09 | policy_tool_worker | 0.80       | ✗    | get_ticket_info | 14,504       |
| gq10 | policy_tool_worker | 0.74       | ✗    | —               | 8,727        |

**Điểm nổi bật:**

- **gq07 (anti-hallucination):** Pipeline trả lời đúng "Không đủ thông tin trong tài liệu nội bộ." với confidence = 0.30, kích hoạt HITL. Không bịa mức phạt tài chính — tránh được penalty −50%.
- **gq09 (multi-hop, 16 điểm):** Supervisor nhận diện đúng `"multi-hop: access control + SLA context | risk_high flagged"`, gọi cả 3 workers + MCP tool `get_ticket_info`. Câu trả lời nêu đủ cả 2 phần (SLA notification + Level 2 emergency access).
- **gq02 (temporal policy scoping):** Policy worker xác định đúng phiên bản chính sách v3 (đơn đặt trước 01/02/2026), không áp nhầm policy v4.
- **Avg confidence:** 0.717 (trên 10 câu grading).
- **Avg latency:** 10,467ms — cao hơn Day 08 nhưng đổi lại độ chính xác và traceability.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

**Bảng so sánh (số Day 08 lấy từ `day08/lab/results/scorecard_variant.md` — variant_dense_rerank, bản đã chọn nộp grading; số Day 09 lấy từ `artifacts/grading_run.jsonl` + 15 trace trong `artifacts/traces/`):**

| Metric                      | Day 08 (Single Agent RAG) | Day 09 (Multi-Agent)           | Ghi chú                          |
| --------------------------- | ------------------------- | ------------------------------ | -------------------------------- |
| Faithfulness (LLM-judge 1–5)| 4.30/5                    | N/A (chưa chấm LLM-judge)      | Day 09 dùng confidence heuristic |
| Relevance (LLM-judge 1–5)   | 4.50/5                    | N/A                            | —                                |
| Context Recall (1–5)        | 5.00/5                    | N/A                            | —                                |
| Completeness (1–5)          | 4.00/5                    | N/A                            | —                                |
| Avg confidence (0–1)        | N/A (không đo)            | 0.717 (10 câu grading)         | Metric riêng Day 09              |
| Avg latency                 | N/A (không log)           | 10,467ms (grading)             | Day 08 `run_grading.py` không đo |
| HITL / Abstain rate         | N/A (không có HITL)       | 10% (1/10 grading, gq07)       | Cơ chế mới của Day 09            |
| Multi-hop handling          | Không có routing riêng    | Có (gq09: retrieval + policy)  | Định tính                        |
| Routing visibility          | ✗ Không có                | ✓ `route_reason` mọi câu       | Định tính                        |

**Metric thay đổi rõ nhất:** Routing Visibility là cải thiện rõ rệt nhất về mặt vận hành. Trong khi Day 08 chỉ trả về 1 câu trả lời cuối cùng, Day 09 cung cấp `worker_io_logs` chi tiết từng node — cho phép nhóm xác định ngay lỗi ở `retrieval_worker` hay `synthesis_worker` mà không cần đọc lại toàn bộ prompt.

**Điều nhóm bất ngờ nhất khi chuyển sang multi-agent:**
Khả năng abstain (từ chối trả lời) của Multi-Agent tốt hơn hẳn. Cụ thể: câu **gq07** hỏi về mức phạt tài chính — thông tin **không có trong bất kỳ tài liệu nào**. Day 09 pipeline trả confidence = 0.30 và kích hoạt HITL, trả lời "Không đủ thông tin trong tài liệu nội bộ." thay vì bịa số liệu. Đây là hành vi mà Single Agent (Day 08) rất dễ mắc phải do không có cơ chế kiểm tra confidence theo ngưỡng.

**Trường hợp multi-agent KHÔNG giúp ích:**
Với các câu hỏi đơn giản như **gq08** ("Mật khẩu đổi sau bao nhiêu ngày?"), pipeline phải đi qua supervisor → retrieval_worker → synthesis_worker với latency = 9,508ms — trong khi Day 08 trả lời tương đương chỉ ~1,850ms. Với loại câu này, overhead của multi-agent không mang lại giá trị thêm.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên       | Phần đã làm                                                                                      | Sprint  |
| ---------------- | ------------------------------------------------------------------------------------------------ | ------- |
| Nguyễn Khánh Nam | Supervisor Owner, Graph Orchestrator, Routing logic                                              | 1       |
| Đỗ Minh Phúc     | Synthesis Worker Owner + Integrator (cross-worker review, refactor graph.py, run eval & grading) | 2, 3, 4 |
| Lê Tú Nam        | Worker Owner (Policy Tool Worker)                                                                | 2       |
| Lê Hữu Hưng      | Worker Owner (Retrieval Worker & ChromaDB)                                                       | 2       |
| Chu Minh Quân    | MCP Owner (MCP Server & Tool Implementation)                                                     | 3       |
| Nguyễn Minh Hiếu | Trace & Docs Owner, Eval Trace, Documentation                                                    | 4       |

**Điều nhóm làm tốt:**
Nhóm phối hợp rất tốt về những mặt sau:
**Interface Contract**. Nhờ thống nhất `AgentState` từ sớm, các Worker của các thành viên khác nhau khi lắp ghép vào `graph.py` hoạt động ngay lập tức mà không gặp lỗi tương thích dữ liệu. Việc phân chia 3 Worker Owner giúp chuyên môn hóa sâu vào từng khía cạnh: Retrieval, Policy và Suy luận, từ đó tối ưu hóa được chất lượng của từng module độc lập.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
Việc debug MCP tool call tốn nhiều thời gian hơn dự kiến do các thành viên ban đầu chưa nắm vững giao thức MCP, dẫn đến việc tích hợp ở Sprint 3 bị chậm so với timeline. Ngoài ra, việc đồng bộ giữa 3 Worker Owner đôi khi cần nhiều thời gian thảo luận để đảm bảo các cạnh nối trong graph hoạt động trơn tru.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

Nhóm sẽ thực hiện 2 cải tiến dựa trên trace thực tế:

1. **Async Orchestration:** `build_graph()` hiện chạy tuần tự — latency ~16s phần lớn là LLM wait time. Chuyển sang `asyncio.gather()` để `retrieval_worker` và `policy_tool_worker` chạy song song có thể giảm latency xuống ~8–10s. Bằng chứng: trace `run_20260414_174518.json` ghi 47,899ms cho câu Flash Sale — retrieval và policy chạy nối tiếp nhau không cần thiết.
2. **Semantic Supervisor:** Keyword matching hiện không phân biệt được câu như `"Mật khẩu Flash Sale"` (retrieval keyword `"mật khẩu"` override policy keyword `"flash sale"`). Thay bằng embedding-based intent classifier (BERT few-shot hoặc LLM zero-shot) sẽ xử lý chính xác hơn các câu chồng lấn domain.

---
