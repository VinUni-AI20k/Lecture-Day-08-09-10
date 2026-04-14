# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** 67  
**Ngày:** 14/04/2026

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.82 (Mock) | 0.587 | -0.233 | Confidence của hệ Day 09 chân thực hơn nhờ áp dụng logic trừ độ tự tin khi trả lời Abstain (0.3). |
| Avg latency (ms) | 3450 (Mock) | 3891 | +441ms | Có sự tăng nhẹ về latency do chạy qua Supervisor để điều hướng trước khi vào Worker. |
| Abstain rate (%) | 1/15 (6.7%) | 2/15 (13%) | Tăng | Day 09 dứt khoát hơn trong việc Abstain do tự định hướng rõ tài liệu. Vd: `gq07` "Không đủ thông tin". |
| Multi-hop accuracy | Kém (Thiếu Context) | Khá Tốt | Đáng kể | Đặc biệt xử lý cực tốt các câu cần Policy Tools (Q09) truy vấn liên luồng SLA & Access. |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Dễ dàng debug vì log in thẳng route_reason. |
| Debug time (estimate) | >30 phút | ~5-10 phút | Trực tiếp | Có Trace Log và Input/Output cho từng node. |

> **Lưu ý:** Day 08 lab gốc không cung cấp `eval.py` lưu log xuất ra `avg_latency` hay `avg_confidence` JSON, con số sử dụng cho Day 08 ở đây là Mock Baseline (theo như gợi ý template) để đo tính biến động của file report JSON.

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Khá tốt | Rất Tốt |
| Latency | ~2000-3000ms | ~2500ms (Trung bình câu `retrieval_worker`) |
| Observation | Truy xuất nhanh trực tiếp tài liệu liên quan thông qua Vector Search duy nhất. | Vẫn query tương tự qua ChromaDB thông qua `retrieval_worker` nhưng bị tốn khoảng 500ms overhead lúc đầu ở Node Supervisor. |

**Kết luận:** Multi-agent không có lợi ích về độ trễ với cấu trúc truy vấn đơn giản.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Thấp | Độ phủ cao |
| Routing visible? | ✗ | ✓ |
| Observation | Nếu LLM tìm thiếu Chunk => Hallucination hoặc trả lời thiếu ý. Dễ bị nhầm lẫn tài liệu. | Logic `policy_tool_worker` kết hợp đa công cụ `search_kb` + `get_ticket_info` giúp ráp trúng điều kiện (Vd câu cấp quyền khẩn cấp Level 3). |

**Kết luận:** Multi-agent hoàn toàn tỏ rõ uy thế sức mạnh tổng quát tại các truy vấn Multi-hop.

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | Thấp | Cao và chặt chẽ |
| Hallucination cases | Dễ bị "Bịa" câu từ | Chủ động chặn bằng luồng HITL cho câu risk_high |
| Observation | LLM có xu hướng "chiều ý" người dùng nếu lỡ tìm lộn Chunk (False Positive). | Nhờ giới hạn của `synthesis_prompt`, nó tự ép về trả lời "Không đủ thông tin" và phạt điểm Confidence. |

**Kết luận:**
Thiết kế Node Supervisor giới hạn Rủi ro tốt, chặn Hallucination ở mức tối đa.

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai → đọc lại Prompt RAG → sửa top_K ChromaDB → Generate lại
Không có trace rõ ràng từng đoạn, tốn > 30 phút.
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc file /artifacts/traces/run_XYZ.json
Xem `route_reason` (Vd: `default_route`) -> Phát hiện truy vấn bị trôi logic -> Fix if/else array trong graph.
Thời gian ước tính: 5 phút.
```

**Câu cụ thể nhóm đã debug:** 
Câu q09 ("ERR-403-AUTH"). Supervisor đã chặn cứng (HITL triggered) và chuyển route = human_review. Mở file truy vết JSONL phát hiện mảng `worker_io_logs` vẫn đang lưu log từng Tool đã chạy, giúp việc Audit an toàn 100%.

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Cài cắm Agent trung tâm cực phức tạp | Import tool vào `mcp_server.py` là có thể xài |
| Thêm 1 domain mới | Retrain/Tăng Prompt token | Thêm nhánh `Worker` riêng lẻ |
| Thay đổi retrieval strategy | Khó khăn | Đổi class trong `retrieve.py` mà không ảnh hưởng node `policy` |
| A/B test một phần | Phải fork toàn code | Chì cần chêm thêm 1 nhánh trong graph |

**Nhận xét:**
Kiến trúc Micro-agent (Supervisor) đạt điểm tuyệt đối về bảo trì hệ thống và cắm rút (Scalability/Extensibility).

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 1 LLM call (Synthesis - Supervisor Day 09 ở lab này đang dùng Code if/else chưa tốn api) |
| Complex query | 1 LLM call | Kéo tool nội bộ Policy Check, có LLM synthesis ráp lại nối tiếp |
| MCP tool call | N/A | Call thẳng DB (`mcp_server` local db) |

**Nhận xét về cost-benefit:**
Sự hi sinh ~500ms là vô cùng xứng đáng vì chi phí bảo mật mà nó bù đắp vượt chuẩn chất lượng. Đặc tả Code Day 09 dùng Supervisor Node bằng IF_ELSE tĩnh giúp giảm tải Token phải gánh ở Routing.

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**
1. Bảo mật: Traceability (File Logs rất sâu) và Trigger dừng theo Rule cho các câu "ERR" hoặc "Emergency" (HITL).
2. Kết nối: MCP Tool Server giúp truy cập logic vượt ngoài tầm với của VectorDB.

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**
1. Latency trung bình kéo dài thêm tầm 10-15%. Coder phải duy trì Code Base phức tạp hơn (rất nhiều file tách rời).

> **Khi nào KHÔNG nên dùng multi-agent?**
Dùng chatbot support tra cứu đơn giản (Ví dụ như FAQ của trang thương mại điện tử). Không có nhiều API cần móc.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**
Cấp quyền Tool Calling (Function Calling) thẳng cho LLM ở nhánh Supervisor để làm Classifier thay vì Code Python `if_else` String Tĩnh. Mở rộng Policy Analyzer nội hàm bên trong Worker Policy bằng gpt-4o-mini thay vì rule-based.
