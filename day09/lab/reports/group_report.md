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

**Tổng kết quả grading (10 câu):** 10/10 câu được xử lý thành công (100% completion rate). Confidence score trung bình là 0.10 do ChromaDB trống (chưa build index) và LLM fallback trả "Không đủ thông tin trong tài liệu nội bộ." Latency trung bình: 5,056ms (từ 1,344ms đến 10,490ms).

**Routing accuracy:** 10/10 câu được route đúng (100% routing accuracy):
- 5 câu route sang `retrieval_worker` (gq01, gq05, gq06, gq07, gq08) — latency trung bình: 2,134ms
- 5 câu route sang `policy_tool_worker` (gq02, gq03, gq04, gq09, gq10) — latency trung bình: 7,978ms

**Câu pipeline xử lý tốt nhất:**
- ID: gq10 (Flash Sale refund) — Supervisor route đúng sang `policy_tool_worker`, MCP tool `search_kb` được gọi, policy exception `flash_sale_exception` được detect. Answer: "Khách hàng không được hoàn tiền cho sản phẩm mua trong chương trình Flash Sale, ngay cả khi sản phẩm bị lỗi từ nhà sản xuất. Điều này được quy định rõ trong chính sách: 'Đơn hàng Flash Sale không được hoàn tiền' [chính sách v4]." Trace: `route_reason: "refund decision/exception routing via ['hoan tien', 'flash sale']"`, `latency_ms: 6198`, `confidence: 0.10` (thấp vì ChromaDB trống nhưng routing logic và policy analysis đúng). Answer length: 289 ký tự (dài nhất trong 10 câu).

**Câu pipeline fail hoặc partial:**
- ID: gq01, gq05, gq06, gq07, gq08 (retrieval-based) — Fail ở retrieval stage: ChromaDB collection 'day09_docs' trống, không retrieve được chunks. Synthesis worker fallback trả "Không đủ thông tin" với confidence=0.10. Root cause: Chưa chạy `python build_index.py` để populate ChromaDB từ 5 tài liệu trong `data/docs/`. Latency ngắn nhất: gq07 (1,344ms), gq08 (1,373ms), gq06 (1,473ms).

**Câu gq09 (multi-hop khó nhất):** Route đúng sang `policy_tool_worker`, MCP tools `search_kb` và `get_ticket_info` được gọi (latency: 10,341ms — cao thứ 2). Answer fallback do ChromaDB trống. Tuy nhiên, routing logic đã đúng — supervisor detect cross-domain query (`cross-domain query detected`) và route sang policy_tool_worker thay vì retrieval_worker. Nếu ChromaDB có data, câu này sẽ được xử lý tốt.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**

Latency tăng từ ~3,689ms (Day 08) lên ~5,056ms (Day 09 grading average) — tăng 37%. Nguyên nhân: Day 09 có thêm supervisor routing layer, policy analysis, và MCP tool calls. Cụ thể: retrieval-only queries (gq01, gq05-08) mất 2,134ms trung bình, nhưng policy queries (gq02-04, gq09-10) mất 7,978ms trung bình do MCP tool calls. Tuy nhiên, routing visibility cải thiện rõ rệt: Day 08 không có `route_reason`, Day 09 có `route_reason` chi tiết cho từng câu (ví dụ: `"refund decision/exception routing via ['hoan tien', 'flash sale']"`), giúp debug nhanh hơn.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**

Dù latency tăng, nhóm phát hiện ra multi-agent dễ debug hơn rất nhiều. Khi answer sai, trace cho thấy rõ lỗi nằm ở supervisor routing, retrieval, policy analysis, hay synthesis. Ví dụ: trace gq10 cho thấy routing đúng (`policy_tool_worker`), MCP tool `search_kb` được gọi, policy exception detect đúng (`flash_sale_exception`), nhưng synthesis fail do ChromaDB trống — từ đó biết ngay lỗi ở data layer chứ không phải logic.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**

Câu hỏi fact lookup đơn giản (gq01: "SLA P1 ai nhận thông báo?") không cần policy analysis hay MCP tools, nhưng Day 09 vẫn phải qua supervisor routing → retrieval → synthesis, tốn 4,010ms. Single-agent Day 08 sẽ nhanh hơn cho loại câu này. Multi-agent chỉ có lợi khi câu hỏi phức tạp (gq09: multi-hop P1 + access control, latency 10,341ms), cần branching logic hoặc multiple tools.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Vai trò | Trách nhiệm chính | Chi tiết công việc |
|------------|--------|-------------------|-------------------|
| Bùi Quang Vinh | Kiến trúc sư & Supervisor Agent (Core Router) | Xây dựng file kiến trúc cốt lõi và Supervisor | `graph.py`: AgentState TypedDict, supervisor_node(), route_decision(), build_graph(), routing keywords (ACCESS_POLICY_KEYWORDS, REFUND_BASE_KEYWORDS, RETRIEVAL_KB_KEYWORDS, RISK_KEYWORDS), worker wrappers, latency tracking. Thiết kế logic routing để phân phối công việc cho các Workers. Cùng thành viên 2 & 3 thiết kế "Hợp đồng rõ ràng" (Contract) quy định đầu vào/đầu ra chung. |
| Nguyễn Việt Hoàng | Kỹ sư Worker 1 (Retrieval/Search Worker) | Xây dựng Worker đầu tiên chuyên tìm kiếm/trích xuất thông tin | `workers/retrieval.py`: retrieve_dense() (embedding + ChromaDB query), _sanitize_input(), _get_collection(), run() entry point, error handling, worker_io_logs contract compliance, top-k retrieval logic. Đảm bảo Worker tuân thủ đúng hợp đồng giao tiếp với Supervisor. Viết logic xử lý lỗi riêng cho luồng tìm kiếm. |
| Lê Quang Minh | Kỹ sư Worker 2 & 3 (Synthesis/Generation Worker) | Xây dựng Worker thứ 2 & 3 chuyên tổng hợp thông tin và sinh câu trả lời | `workers/policy_tool.py`: analyze_policy() (rule-based exception detection: flash_sale, digital_product, activated_product), _call_mcp_tool(), run() entry point. `workers/synthesis.py`: synthesize(), _build_context(), _call_llm() (OpenAI + Gemini fallback), _estimate_confidence(), run() entry point, grounded answer generation. Đảm bảo giao tiếp chuẩn xác với Supervisor. Xử lý lỗi trong quá trình sinh text. |
| Nguyễn Bình Minh | Chuyên viên Tích hợp MCP (External Capability) | Tích hợp Model Context Protocol (MCP) vào hệ thống | `mcp_server.py`: TOOL_SCHEMAS (4 tools: search_kb, get_ticket_info, check_access_permission, create_ticket), dispatch_tool(), list_tools(), mock data layer, tool discovery interface. Nghiên cứu setup capability bên ngoài bằng MCP. Viết code kết nối MCP vào hệ thống. Parse dữ liệu từ công cụ bên ngoài. |
| Trần Quốc Việt | Chuyên viên Tracing & Tối ưu hiệu suất | Theo dõi (Tracing) và So sánh hiệu năng | Thiết lập công cụ logging và tracing xuyên suốt luồng routing. Chạy các kịch bản test để thu thập dữ liệu về hiệu suất. So sánh hiệu năng giữa single-agent (Day 08) và multi-agent (Day 09). Cấu hình Tracing, các hàm middleware để đo lường thời gian xử lý. `contracts/worker_contracts.yaml` (I/O schema definition), integration testing, debugging, cross-worker validation. |
| Ngô Quang Phúc | Trưởng nhóm Báo cáo (Group Report Lead) & QA/Docs | Viết báo cáo nhóm và kiểm thử tích hợp | `eval_trace.py`: run_test_questions(), run_grading_questions(), analyze_traces(), compare_single_vs_multi(), save_trace(), trace metrics computation. Đóng vai trò QA: Ghép nối code của 5 người, chạy thử pipeline để đảm bảo luồng chạy trơn tru. Cập nhật tài liệu kiến trúc hệ thống. Soạn thảo `reports/group_report.md`: Tổng hợp các quyết định kỹ thuật cấp nhóm, nhặt ví dụ code/traces để đưa vào báo cáo. |

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

Trace hiện tại cho thấy synthesis worker tính confidence nhưng không trigger HITL khi confidence < 0.4. Nhóm sẽ thêm logic: nếu confidence < 0.4 và task có `risk_high=True`, tự động trigger human review. Bằng chứng: gq01 có confidence=0.1 và risk_high=True nhưng vẫn trả lời "Không đủ thông tin", nên cần HITL để escalate.

**Cải tiến 2: Implement real ChromaDB indexing**

Hiện tại ChromaDB trống nên không retrieve được chunks thực. Nhóm sẽ setup embedding model offline (sentence-transformers) và build index từ 5 tài liệu trong `data/docs/`. Điều này sẽ cải thiện retrieval accuracy từ 0% lên ~80% cho các câu fact lookup (gq01, gq05-08). Bằng chứng: gq10 có answer length 289 ký tự (dài nhất) vì policy logic hoạt động, nhưng gq01-08 chỉ có 53 ký tự (fallback message) vì ChromaDB trống.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
