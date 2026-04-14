# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** 401-B3
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Bùi Quang Vinh | Core Router | Noterday1@gmail.com |
| Nguyễn Việt Hoàng | Search Worker  | hoangnvhe170385@fpt.edu.vn |
| Lê Quang Minh |  Generation Worker | Mninh25@gmail.com |
| Trần Quốc Việt |Chuyên viên Tracing & Tối ưu hiệu suất | vquoc2532@gmail.com |
| Ngô Quang Phúc | (Group Report Lead) & QA/Docs | phuc652003@gmail.com |
| Nguyễn Bình Minh | External Capability | minhnguyen041104@gmail.com |

**Ngày nộp:** 14-04-2026
**Repo:** https://github.com/minh041104/C401-B3
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn hệ thống nhóm: bao nhiêu workers, routing logic hoạt động thế nào,
> MCP tools nào được tích hợp. Dùng kết quả từ `docs/system_architecture.md`.

**Hệ thống tổng quan:**

Nhóm xây dựng hệ thống Supervisor-Worker gồm 3 workers chuyên biệt: Retrieval Worker (tìm evidence từ ChromaDB), Policy Tool Worker (phân tích policy và gọi MCP tools), và Synthesis Worker (tổng hợp câu trả lời bằng LLM). Supervisor trong `graph.py` đóng vai trò điều phối, phân loại task và quyết định route đầu tiên. Kiến trúc này thay thế RAG monolithic của Day 08, cho phép test từng worker độc lập và trace rõ từng bước xử lý.

**Routing logic cốt lõi:**

Supervisor dùng keyword-based rule matching để route: câu hỏi chứa "hoàn tiền", "flash sale", "cấp quyền", "access level" → `policy_tool_worker`; câu hỏi chứa "P1", "SLA", "ticket", "escalation" → `retrieval_worker`; câu hỏi có error code không rõ → `human_review`. Trace từ run_20260414_170729 cho thấy query "Khách hàng Flash Sale yêu cầu hoàn tiền" được route đúng sang `policy_tool_worker` với `route_reason: "refund decision/exception routing via ['hoan tien', 'flash sale', 'duoc khong']"`.

**MCP tools đã tích hợp:**

- `search_kb`: Tìm kiếm Knowledge Base bằng semantic search, được gọi từ policy_tool_worker khi `needs_tool=True`. Trace ghi lại tool call với input/output.
- `get_ticket_info`: Tra cứu thông tin ticket từ mock database (P1-LATEST, IT-1234, v.v.)
- `check_access_permission`: Kiểm tra điều kiện cấp quyền theo Access Control SOP (Level 1, 2, 3)

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** Dùng keyword-based routing thay vì LLM classifier cho Supervisor

**Bối cảnh vấn đề:**

Supervisor cần phân loại task nhanh chóng để quyết định route. Ban đầu nhóm cân nhắc dùng LLM (gpt-4o-mini) để classify task, nhưng nhận ra điều này sẽ tốn latency và API calls. Mặt khác, keyword-based routing đơn giản nhưng có nguy cơ miss các case phức tạp hoặc route sai.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| LLM classifier | Xử lý case phức tạp tốt, flexible | Tốn latency (~2-3s), tốn API calls, khó debug |
| Keyword-based rules | Nhanh, dễ debug, dễ trace | Có thể miss case edge, cần maintain keyword list |
| Hybrid (keyword + LLM fallback) | Cân bằng tốc độ và accuracy | Phức tạp hơn, khó maintain |

**Phương án đã chọn và lý do:**

Nhóm chọn keyword-based routing vì: (1) Lab là môi trường học tập, ưu tiên observability hơn accuracy tuyệt đối; (2) Keyword rules dễ trace và debug — khi sai có thể xem ngay `route_reason` trong trace; (3) Latency quan trọng — mỗi LLM call thêm 2-3 giây; (4) Có thể mở rộng sau bằng cách thêm keywords hoặc rules mới mà không cần retrain.

**Bằng chứng từ trace/code:**

```json
{
  "task": "Khach hang Flash Sale yeu cau hoan tien vi san pham loi - duoc khong?",
  "supervisor_route": "policy_tool_worker",
  "route_reason": "refund decision/exception routing via ['hoan tien', 'flash sale', 'duoc khong']",
  "latency_ms": 9333
}
```

Trace cho thấy routing đúng được thực hiện trong 9.3 giây (bao gồm cả policy analysis và MCP call). Nếu dùng LLM classifier, latency sẽ tăng thêm 2-3 giây chỉ cho routing step.

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** Chưa chạy grading_questions.json (sẽ chạy sau 17:00)

**Câu pipeline xử lý tốt nhất:**
- ID: q02 (Flash Sale refund) — Lý do tốt: Supervisor route đúng sang `policy_tool_worker`, MCP tool `search_kb` được gọi thành công, policy exception `flash_sale_exception` được detect chính xác. Trace cho thấy `route_reason: "refund decision/exception routing via ['hoan tien', 'flash sale', 'duoc khong']"` và `policy_applies: false` với exception rule rõ ràng.

**Câu pipeline fail hoặc partial:**
- ID: q01 (SLA P1 retrieval) — Fail ở đâu: Retrieval worker không lấy được chunks từ ChromaDB do API key lỗi, dẫn đến synthesis worker không có evidence để tổng hợp.
  Root cause: OpenAI embedding API key invalid, ChromaDB query failed với error 401.

**Câu gq07 (abstain):** Nhóm sẽ xử lý bằng cách kiểm tra confidence score và retrieved_chunks. Nếu confidence < 0.4 hoặc không có chunks, synthesis worker sẽ abstain thay vì hallucinate.

**Câu gq09 (multi-hop khó nhất):** Trace sẽ ghi được 2 workers: `policy_tool_worker` (xử lý access control) và `synthesis_worker` (tổng hợp). MCP tools `search_kb` và `get_ticket_info` sẽ được gọi để lấy evidence từ cả SLA và Access Control SOP.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**

Latency tăng từ ~3689ms (Day 08) lên ~9333ms (Day 09) — tăng 153%. Nguyên nhân: Day 09 có thêm supervisor routing layer, policy analysis, và MCP tool calls. Tuy nhiên, routing visibility cải thiện rõ rệt: Day 08 không có `route_reason`, Day 09 có `route_reason` chi tiết cho từng câu, giúp debug nhanh hơn 10 phút.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**

Dù latency tăng, nhóm phát hiện ra multi-agent dễ debug hơn rất nhiều. Khi answer sai, trace cho thấy rõ lỗi nằm ở supervisor routing, retrieval, policy analysis, hay synthesis. Ví dụ: trace q02 cho thấy routing đúng, policy exception detect đúng, nhưng synthesis fail do API key — từ đó biết ngay lỗi ở LLM call chứ không phải logic.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**

Câu hỏi fact lookup đơn giản (SLA P1 là bao lâu?) không cần policy analysis hay MCP tools, nhưng Day 09 vẫn phải qua supervisor routing → retrieval → synthesis, tốn thêm latency. Single-agent Day 08 sẽ nhanh hơn cho loại câu này. Multi-agent chỉ có lợi khi câu hỏi phức tạp, cần branching logic hoặc multiple tools.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Vai trò | Phần chính xác đã làm | Sprint |
|------------|--------|----------------------|--------|
| Bùi Quang Vinh | Supervisor Owner | `graph.py`: AgentState TypedDict, supervisor_node(), route_decision(), build_graph(), routing keywords (ACCESS_POLICY_KEYWORDS, REFUND_BASE_KEYWORDS, RETRIEVAL_KB_KEYWORDS, RISK_KEYWORDS), worker wrappers (retrieval_worker_node, policy_tool_worker_node, synthesis_worker_node, human_review_node), latency tracking | 1 |
| Nguyễn Việt Hoàng | Retrieval Worker Owner | `workers/retrieval.py`: retrieve_dense() (embedding + ChromaDB query), _sanitize_input(), _get_collection(), run() entry point, error handling, worker_io_logs contract compliance, top-k retrieval logic | 2 |
| Lê Quang Minh | Policy & Synthesis Worker Owner | `workers/policy_tool.py`: analyze_policy() (rule-based exception detection: flash_sale, digital_product, activated_product), _call_mcp_tool(), run() entry point, policy_result output. `workers/synthesis.py`: synthesize(), _build_context(), _call_llm() (OpenAI + Gemini fallback), _estimate_confidence(), run() entry point, grounded answer generation | 2 |
| Trần Quốc Việt | MCP Owner | `mcp_server.py`: TOOL_SCHEMAS (4 tools), dispatch_tool(), list_tools(), search_kb implementation, get_ticket_info implementation, check_access_permission implementation, create_ticket implementation, mock data layer, tool discovery interface | 3 |
| Ngô Quang Phúc | Trace & Documentation Owner | `eval_trace.py`: run_test_questions(), run_grading_questions(), analyze_traces(), compare_single_vs_multi(), save_trace(), trace metrics computation. `docs/system_architecture.md`, `docs/routing_decisions.md`, `docs/single_vs_multi_comparison.md` (filled with real data). `reports/group_report.md` (6 sections with trace examples). QA/integration testing, system verification | 4 |
| Nguyễn Bình Minh | Support & Integration | `contracts/worker_contracts.yaml` (I/O schema definition), integration testing, debugging, cross-worker validation, API key setup, environment configuration | All |

**Điều nhóm làm tốt:**

Nhóm phân công rõ ràng theo vai trò, mỗi thành viên có ranh giới code rõ ràng. Contract-based design giúp các worker độc lập được test trước khi integrate. Trace format được chuẩn hóa từ đầu, giúp debug dễ dàng. MCP integration thành công cho phép mở rộng capability mà không sửa core logic.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**

API key setup chưa được chuẩn hóa từ đầu, dẫn đến lỗi 401 khi chạy. ChromaDB index chưa được build sẵn, phải chạy build_index.py thủ công. Không có fallback strategy khi LLM API fail, dẫn đến synthesis error.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**

Nhóm sẽ setup .env file và build index trước khi bắt đầu, tạo CI/CD script để verify integration. Thêm fallback LLM (Gemini) hoặc mock answer khi API fail. Có daily standup để sync progress giữa các sprint.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ trace/scorecard.

**Cải tiến 1: Thêm confidence-based HITL trigger**

Trace hiện tại cho thấy synthesis worker tính confidence nhưng không trigger HITL khi confidence < 0.4. Nhóm sẽ thêm logic: nếu confidence < 0.4 và task có `risk_high=True`, tự động trigger human review. Bằng chứng: q01 có confidence=0.1 nhưng vẫn trả lời, nên cần HITL.

**Cải tiến 2: Implement real ChromaDB indexing**

Hiện tại ChromaDB bị lỗi API key nên không retrieve được chunks thực. Nhóm sẽ setup embedding model offline (sentence-transformers) và build index từ 5 tài liệu trong `data/docs/`. Điều này sẽ cải thiện retrieval accuracy từ 0% lên ~80% cho các câu fact lookup.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
