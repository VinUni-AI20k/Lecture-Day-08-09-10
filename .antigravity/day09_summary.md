# Tổng hợp Review Repo Day 09: Multi-Agent Orchestration

**Bối cảnh:**
Lab chia làm 4 Sprints, nâng cấp kiến trúc RAG "Monolith" từ Day 08 thành kiến trúc phân tán Supervisor-Worker Pattern. Việc này giúp cải thiện debug, mở rộng và tăng độ tin cậy khi xử lý các ticket IT/CS Helpdesk phức tạp.

## 1. Cấu trúc thư mục cốt lõi
- `graph.py`: Đóng vai trò là Supervisor. Nó nhận task (câu hỏi) và đánh giá `route_reason`, `risk_high`, `needs_tool` để quyết định xem giao việc tiếp cho ai. 
    - Các edge/node có thể route tới: `retrieval_worker`, `policy_tool_worker`, hoặc `human_review`.
- `workers/`: Chứa các Worker chuyên biệt.
    - `retrieval.py`: Xử lý semantic search (ChromaDB) để trả về các chunks tài liệu và score.
    - `policy_tool.py`: Phân tích policy (dành cho exception cases như Flash Sale, Digital Product). Nếu cần thiết (`needs_tool=True`), worker này dùng MCP (Model Context Protocol) để lấy thêm thông tin (vé Jira, quyền truy cập).
    - `synthesis.py`: Node tổng hợp câu trả lời dựa trên context và policy analysis. Yêu cầu trả lời chặt chẽ, không hallucinate và có source (trích dẫn `[tên_file]`). Tính toán `confidence` dựa trên `chunks score` & độ phân tán tự tin.
- `mcp_server.py`: Giả lập MCP Server, giúp `policy_tool` giao tiếp với nguồn dữ liệu ngoài. Cung cấp các công cụ như `search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket`.
- `eval_trace.py`: Chạy pipeline trên `test_questions.json`, chấm điểm `grading_questions.json`, log ra metrics về latencies, confidence, routing dist... và so sánh (compare) giữa giải pháp Single Agent của Day 08 với Multi Agent của Day 09.
- `contracts/worker_contracts.yaml`: Tài liệu định nghĩa tiêu chuẩn rõ ràng cho Input và Output của từng node trong graph. Supervisor và Worker phải tuyệt đối tuân theo.

## 2. Sprint Todo Breakdown
Nếu cần thực hành hoặc review lại quá trình xây dựng, tiến độ phân chia như sau:
- **Sprint 1 (graph.py):** Viết logic phần `supervisor_node()` sử dụng keyword (vd: hoàn tiền, p1, lỗi, sla...) để set route state chính xác (`retrieval`, `policy_tool` hay bắt buộc `human_review`).
- **Sprint 2 (workers):** Implement xử lý độc lập cho từng worker (`retrieval.py` nối ST/OpenAI + ChromaDB, `policy_tool.py` phân tích ngoại lệ quy định, `synthesis.py` nối prompt grounded vào GenAI/LLM).
- **Sprint 3 (mcp_server.py):** Hoàn thiện client-server Model Context Protocol thay cho việc hardcode direct calls. Có thể nâng cao bằng chạy HTTP server thực.
- **Sprint 4 (eval_trace.py):** Chạy lệnh evaluation, lưu logs traces (`artifacts/traces`), điền các báo cáo (`docs/routing_decisions.md`, `docs/single_vs_multi_comparison.md`) và kiểm chứng bằng metrics.

## 3. Bài học về hệ thống
- **Observability:** Bằng cách gắn logging rõ ràng ở state (như `history`, `worker_io_logs`, `route_reason`), ta dễ dàng trace lỗi do ai gây ra (lỗi route từ Supervisor hay Retrieval kéo nội dung không đúng?).
- **Extensibility:** Pattern này cho phép dễ dàng tích hợp thêm Node (ví dụ `human_review` cho HITL) hoặc External Tools qua MCP mà không cần phá vỡ cấu trúc tổng thể.
- **Contract-first:** Ranh giới trách nhiệm, ví dụ Supervisor thì tạo luồng (không được dùng LLM tự trả lời domain) còn Worker giữ domain skill, giúp test unit dễ dàng.
