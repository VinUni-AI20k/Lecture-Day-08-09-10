# Báo cáo cá nhân — Quách Ngọc Quang

## Vai trò
Supervisor Owner — Sprint 1: graph.py, routing logic, state management, 
kết nối workers.

## Nhiệm vụ chính
- [x] Thiết kế AgentState schema (15+ fields cho trace đầy đủ)
- [x] Implement supervisor_node() với routing logic 3-tier
- [x] Viết _needs_policy_check() phân biệt tra cứu vs exception check
- [x] Kết nối 3 real workers với try/except fallback
- [x] Thiết kế graph flow: retrieval-first cho policy path

## 1 quyết định kỹ thuật — Keyword-based vs LLM classifier

**Quyết định**: Dùng keyword-based routing (3-tier: human_review → 
policy_check → retrieval) thay vì LLM classifier.

**Lý do**:
- Latency: Routing keyword ~ 0ms, LLM call ~ 500-2000ms. Với 15 câu hỏi,
  tiết kiệm 7-30 giây tổng.
- Deterministic: Cùng input luôn cho cùng route → dễ debug, dễ test.
- Đủ tốt: 15/15 test questions route đúng với logic 3-tier.

**Trade-off nhận thấy**: Keyword matching không xử lý được câu hỏi 
ambiguous (VD: "hoàn tiền" vừa có thể là tra cứu, vừa có thể là check 
exception). Giải quyết bằng hàm _needs_policy_check() kiểm tra có 
exception signal đi kèm không.

**Evidence từ trace**: 
`"route_reason": "policy check required: refund_exception_check"` cho các exception queries và `"route_reason": "refund policy information lookup (no exception check needed)"` cho general retrieval lookup.

## 1 lỗi đã sửa — Route sai cho "hoàn tiền đơn giản"

**Lỗi**: Lỗi ban đầu route sai với "hoàn tiền" đơn lẻ. Bất cứ câu hỏi nào chứa Keyword "hoàn tiền" ("Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?") đều bị route sai sang policy_tool.

**Nguyên nhân gốc**: Routing logic ban đầu dùng flat keyword list — bất kỳ 
câu nào chứa "hoàn tiền" đều đi policy. Nhưng một số câu chỉ hỏi thông tin, 
không cần check exception.

**Cách sửa**: Tách logic thành 2 mức:
- "hoàn tiền" đơn lẻ → retrieval_worker (tra cứu)
- "hoàn tiền" + exception signal (flash sale, license, store credit, 
  được không?, temporal date) → policy_tool_worker

**Trước sửa**: route=policy_tool_worker, reason="task contains 
policy/access keyword"
**Sau sửa**: route=retrieval_worker, reason="refund policy information 
lookup (no exception check needed)"

## Tự đánh giá

**Làm tốt**: Routing logic cover được 15/15 test questions. Route reason 
chi tiết, traceability cao. Flow retrieval-first giúp policy worker có 
context tốt hơn.

**Yếu**: Chưa implement hybrid routing (keyword + LLM fallback) cho 
trường hợp ambiguous. Risk detection chỉ dựa keyword, chưa dùng 
confidence threshold.

**Nhóm phụ thuộc vào mình ở**: Routing accuracy ảnh hưởng trực tiếp đến 
kết quả grading (20% điểm/câu bị trừ nếu thiếu route_reason). Flow 
orchestration quyết định thứ tự gọi workers.

## Nếu có 2h thêm

Implement **hybrid routing**: Dùng LLM classifier (GPT-4o-mini) cho câu 
hỏi mà keyword matching confidence thấp (<2 signal matches). Cụ thể:
- Thêm `_routing_confidence()` đếm số signal matches
- Nếu ≤ 1 match → gọi LLM phân loại (retrieval/policy/abstain)
- Nếu ≥ 2 match → dùng keyword (nhanh, deterministic)

Evidence cần thêm: So sánh latency và accuracy giữa pure keyword vs 
hybrid trên 15 câu test.
