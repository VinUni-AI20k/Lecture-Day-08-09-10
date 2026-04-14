# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Thanh Phong
**Vai trò trong nhóm:** MCP Owner
**Ngày nộp:** 2026-04-14
**Độ dài:** ~700 từ

---

## 1. Tôi phụ trách phần nào?

Trong dự án Day 09, tôi đảm nhận vai trò **MCP Owner**. Trách nhiệm chính của tôi xoay quanh việc thiết lập "xương sống" kết nối các thành phần trong hệ thống (Orchestration Wiring) và triển khai tầng giao tiếp công cụ (MCP Tools).

**Module/file tôi trực tiếp chịu trách nhiệm:**
- **`mcp_server.py`**: Tôi thiết kế và triển khai Mock MCP Server với 4 công cụ cốt lõi: `search_kb`, `get_ticket_info`, `check_access_permission`, và `create_ticket`. Tôi xây dựng `TOOL_SCHEMAS` chuẩn để Supervisor và Workers có thể "khám phá" và gọi công cụ một cách nhất quán.
- **`graph.py`**: Tôi trực tiếp thực hiện việc "wiring" (nối dây) các node trong LangGraph (phiên bản rút gọn). Tôi implement hàm `build_graph` và logic điều phối luồng chạy giữa `retrieval_worker`, `policy_tool_worker` và `synthesis_worker`. Đặc biệt, tôi đã xử lý luồng multi-hop: nếu câu hỏi chứa cả tín hiệu SLA/P1 và Policy, hệ thống sẽ tự động chạy Retrieval trước để lấy evidence rồi mới chuyển sang Policy Worker.
- **`workers/policy_tool.py`**: Tôi tích hợp hàm `_call_mcp_tool` để thực hiện MCP dispatching thật sự thay vì dùng placeholder.

**Cách công việc của tôi kết nối với nhóm:**
Công việc của tôi đóng vai trò là "chất keo" liên kết. Nếu không có phần wiring trong `graph.py`, các worker đơn lẻ của bạn Vĩ (Worker Owner) sẽ không thể phối hợp nhịp nhàng. Phần MCP tools của tôi cung cấp dữ liệu "động" (thông tin ticket, quyền truy cập) mà retrieval thuần túy từ văn bản không có được, giúp nhóm đạt điểm tối đa ở các câu hỏi yêu cầu tra cứu hệ thống nội bộ.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Triển khai **Sequential Worker Chain có điều kiện (Conditional Multi-hop)** trong `graph.py`.

Trong quá trình xây dựng Orchestrator, tôi nhận thấy có nhiều câu hỏi phức tạp (như gq09: vừa hỏi về P1 SLA vừa hỏi về Access Level 2). Nếu chỉ route vào một worker duy nhất, câu trả lời sẽ bị thiếu hụt thông tin trầm trọng.

**Các lựa chọn thay thế:**
1. **Parallel Execution**: Chạy tất cả worker cùng lúc. Tuy nhiên, cách này gây lãng phí tài nguyên và khó tổng hợp context đồng nhất cho Synthesis.
2. **Fixed Sequence**: Luôn chạy Retrieval -> Policy -> Synthesis cho mọi câu hỏi. Cách này làm tăng latency cho các câu hỏi FAQ đơn giản.

**Lý do chọn Sequential Chain có điều kiện:**
Tôi chọn kiểm tra keyword trong `build_graph`. Nếu `needs_retrieval_first` là True, tôi cho chạy Retrieval Worker trước để nạp `retrieved_chunks` vào state, sau đó mới gọi Policy Worker. Điều này đảm bảo Policy Worker có đủ context để phân tích nội dung chuyên sâu. 

**Bằng chứng từ code (`graph.py`):**
```python
# Multi-hop case: lấy evidence retrieval trước để policy + synthesis có đủ 2 domain.
if needs_retrieval_first:
    state = retrieval_worker_node(state)
    state["history"].append("[graph] multi-hop: retrieval before policy")

state = policy_tool_worker_node(state)
```
Quyết định này giúp nhóm đạt điểm tuyệt đối `16/16` cho câu **gq09**, vì trace ghi nhận sự hiện diện của cả hai luồng xử lý domain.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** Mất đồng bộ Embedding Model giữa Indexing và Retrieval.

**Symptom:** Khi chạy pipeline, hệ thống báo trả về 0 chunks hoặc chunks không hề liên quan đến câu hỏi (relevance score rất thấp < 0.3), mặc dù tài liệu đã được nạp đầy đủ vào ChromaDB.

**Root cause:**
Trong Sprint 2, do phối hợp chưa chặt chẽ, file build index dùng model `text-multilingual-embedding-002` (Vertex AI), trong khi Retrieval Worker của tôi lại dùng fallback `all-MiniLM-L6-v2` (Sentence Transformers) do chưa cấu hình xong credential. Việc vector hóa query và văn bản bằng hai model khác nhau khiến phép đo Cosine Similarity hoàn toàn mất tác dụng.

**Cách sửa:**
Tôi đã cấu hình lại `_get_embedding_fn` trong `workers/retrieval.py` để ưu tiên load credential từ file `.env` và khởi tạo Vertex AI đúng chuẩn. Tôi cũng thêm log `[retrieval] embedding provider=vertex` để đảm bảo khi chạy cả nhóm đều biết model nào đang hoạt động.

**Bằng chứng:**
- **Trước khi sửa:** `retrieved_chunks: []`, `avg_confidence: 0.1`.
- **Sau khi sửa:** `retrieved_chunks` trả về đúng header file `policy_refund_v4.txt`, `avg_confidence` tăng lên `0.85`.
- **File đã sửa:** `workers/retrieval.py`.

---

## 4. Tôi tự đánh giá đóng góp của mình

**Điểm tôi làm tốt nhất:** 
Tôi đã thiết kế tầng MCP rất linh hoạt. Việc mô phỏng `dispatch_tool` giúp nhóm dễ dàng chuyển đổi từ Mock Data sang Real API sau này mà không cần sửa logic ở Worker. Tôi cũng hỗ trợ nhóm rất nhiều trong việc debug luồng State qua `history` logs.

**Điểm tôi làm chưa tốt:**
Do quá tập trung vào wiring, tôi chưa dành đủ thời gian để tối ưu hóa `synthesis.py` bằng LLM-as-Judge, mà vẫn phải dùng một số rule-based synthesis để đảm bảo format của rubric chấm điểm.

**Sự phụ thuộc:**
Nhóm phụ thuộc vào tôi ở cấu trúc `AgentState` và routing logic; nếu graph lỗi thì toàn bộ pipeline đóng băng. Ngược lại, tôi phụ thuộc hoàn toàn vào Trace Owner để biết được routing của mình có thực sự mang lại kết quả đúng cho 15 câu grading hay không.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ nâng cấp MCP Server từ dạng import trực tiếp sang **FastAPI HTTP Server**. Trace của câu `gq04` cho thấy việc gọi MCP trong-process đôi khi làm chậm chu kỳ event loop của Graph. Nếu tách thành service riêng, chúng ta có thể tận dụng async calls để giảm latency xuống dưới 2000ms cho các câu phức động.

---
