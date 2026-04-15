# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** C401 - C5  
**Ngày:** 14/04/2026

---

## 1. Metrics Comparison

> **Lưu ý thang đo:** Day 08 dùng **LLM-as-Judge** (thang 1–5, Faithfulness + Relevance), Day 09 dùng **heuristic confidence** (thang 0–1). Hai thang không so sánh trực tiếp được — xem phân tích định tính bên dưới.

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Answer quality | Faithfulness 4.30/5, Relevance 4.50/5 (LLM-as-Judge) | Confidence ~0.74 (real LLM, heuristic 0–1) | N/A — thang đo khác nhau | Day 08 dùng grader LLM, Day 09 dùng score-based heuristic |
| Avg latency (ms) | ~1,850ms | ~16,315ms | +783% | Day 09 gọi nhiều LLM call hơn |
| Abstain rate (%) | 2/10 grading = 20% | ~2/17 test = 11.8% | -8.2pp | Day 09 ít abstain hơn nhờ multi-hop xử lý được |
| Multi-hop accuracy | N/A (single agent không có routing) | 4/4 multi-hop queries = 100% | N/A | Day 08 không phân biệt multi-hop |
| Routing visibility | Không có | Có `route_reason` trong mọi trace | N/A | Cải thiện lớn nhất về observability |
| Debug time (estimate) | 20–30 phút/lỗi | 5–10 phút/lỗi | ~-65% | Nhờ `workers_called` + `history` trong trace |

---

## 2. Phân tích định tính

### 2.1 Câu hỏi đơn giản
Multi-agent không mang lại lợi thế về độ chính xác (accuracy) cho câu hỏi đơn giản. Ví dụ: `"SLA ticket P1 là bao lâu?"` — Day 08 trả lời tốt với single prompt ~1.85s, Day 09 cần qua Supervisor → Retrieval → Synthesis tốn ~19s. Overhead 10× là không cần thiết cho single-doc lookup.

Tuy nhiên ngay cả câu đơn giản, Day 09 vẫn hơn ở **minh bạch**: trace ghi rõ `route_reason="task contains retrieval/SLA keyword"`, `workers_called=['retrieval_worker','synthesis_worker']`, `retrieved_sources=['sla_p1_2026.txt']` — nếu câu trả lời sai, biết ngay lỗi ở node nào.

### 2.2 Câu hỏi multi-hop
Đây là điểm mạnh rõ nhất của Multi-agent. Day 08 (single agent) phải tổng hợp cross-doc trong một prompt dài, dễ bỏ sót hoặc hallucinate. Day 09 phát hiện multi-hop qua combined-keyword logic, gọi `policy_tool_worker` trước rồi lấy thêm retrieval context — kết quả trace cho thấy **4/4 multi-hop queries route đúng** với confidence 0.75–0.79.

Ví dụ điển hình: `"Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp"` → 2 MCP tools được gọi (`search_kb` lấy 3 chunks từ `access_control_sop.txt` + `sla_p1_2026.txt`, `get_ticket_info` lấy trạng thái ticket thực), câu trả lời có citation rõ ràng, confidence=0.76.

### 2.3 Khả năng từ chối (Abstain)
Multi-agent abstain **chính xác hơn** nhờ tách riêng bước kiểm tra evidence:
- `policy_tool_worker` kiểm tra trước khi synthesis — nếu không tìm thấy policy phù hợp, đặt flag sớm
- `synthesis_worker` có `HITL_THRESHOLD=0.4`: confidence < 0.4 → tự động set `hitl_triggered=True`
- Early abstain khi `retrieved_chunks=[]` → không gọi LLM, tránh hallucinate hoàn toàn

Day 08 với single prompt thường "suy diễn" trong các trường hợp thiếu context — abstain rate 20% nhưng có thể có false negative (trả lời tự suy thay vì từ chối).

---

## 3. Phân tích khả năng Debug (Debuggability)

**Day 08:** Khi AI trả lời sai (ví dụ áp policy v3 thay vì v4), phải đọc lại toàn bộ prompt dài và context để đoán model sai ở đâu. Không có vết (trace) chi tiết — ước tính 20–30 phút để pin-point lỗi.

**Day 09:** Chỉ cần đọc file trace JSON (~2–3 KB), kiểm tra:
1. `supervisor_route` — routing đúng không?
2. `retrieved_chunks` — lấy đúng doc chưa?
3. `policy_result` — rule detection đúng không?
4. `final_answer` + `sources` — synthesis có cite đúng không?

Mỗi worker độc lập → test được từng worker bằng `python workers/retrieval.py` (standalone CLI có trong mỗi file). Ước tính debug time giảm xuống 5–10 phút.

---

## 4. Khả năng mở rộng (Extensibility)

Kiến trúc Multi-agent có tính modular cao:
- Muốn thêm tính năng mới: Thêm 1 Worker mới + keyword vào `supervisor_node()`.
- Muốn cập nhật luật: Sửa `policy_tool_worker` — không ảnh hưởng retrieval hay synthesis.
- Muốn đổi model: Chỉ cần sửa `_call_llm()` trong `synthesis.py`.
- Muốn thêm tool mới: Đăng ký trong `TOOL_REGISTRY` của `mcp_server.py`.

Day 08 (single agent): mọi thay đổi đều phải chỉnh sửa system prompt lớn, dễ gây side-effect ("quên" luật cũ do context window).

---

## 5. Kết luận

| Tiêu chí | Day 08 (Single Agent) | Day 09 (Multi-Agent) |
|----------|----------------------|----------------------|
| **Phù hợp với** | App nhỏ, cần tốc độ phản hồi nhanh, câu hỏi đơn giản | Enterprise helpdesk, câu hỏi phức tạp, cần governance |
| **Điểm mạnh** | Latency thấp (~1.85s), ít component, dễ deploy | Observability cao, multi-hop chính xác, abstain an toàn |
| **Điểm yếu** | "Hộp đen", khó debug, dễ hallucinate multi-hop | Latency ~16s avg, nhiều LLM call hơn, phức tạp hơn |
| **Trade-off cốt lõi** | Tốc độ vs Kiểm soát | — |

**Khuyến nghị:** Dùng Multi-agent cho hệ thống Enterprise yêu cầu Governance (audit trail, HITL, policy enforcement). Dùng Single Agent cho chatbot đơn giản, FAQ lookup không có cross-domain logic.
