# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Hoàng Văn Kiên 
**Vai trò trong nhóm:** Worker Owner (Synthesis Worker)
**Ngày nộp:** 14-04-2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong lab này, tôi phụ trách xây dựng Synthesis Worker — thành phần chịu trách nhiệm tổng hợp câu trả lời cuối cùng từ các kết quả trung gian của hệ thống multi-agent.

Cụ thể, tôi làm việc trong file workers/synthesis.py, nơi tôi implement các chức năng chính như:

synthesize() — tổng hợp câu trả lời từ retrieval và policy
_build_context() — chuẩn hóa context đầu vào cho LLM
_call_llm() — gọi model (OpenAI/Gemini)
_estimate_confidence() — tính toán độ tin cậy của câu trả lời
run() — entry point để tích hợp vào pipeline

Công việc của tôi nhận input từ Retrieval Worker (retrieved_chunks) và Policy Worker (policy_result), sau đó kết hợp hai nguồn này để tạo ra final_answer, sources, và confidence. Phần của tôi là bước cuối cùng trong pipeline nên quyết định trực tiếp chất lượng output mà người dùng nhận được.

**Bằng chứng:**
- Cấu trúc Graph trong `graph.py` kết nối Supervisor -> Worker -> Synthesis.
- Trace log tại `artifacts/traces/run_20260414_165345.json` thể hiện các trường `supervisor_route` và `route_reason` do tôi thiết kế.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định**: Tôi quyết định sử dụng LLM-based synthesis kết hợp với prompt strict grounding thay vì chỉ nối chuỗi dữ liệu (rule-based formatting).

**Lý do**:
Ban đầu, tôi cân nhắc 2 cách:

Rule-based: ghép các chunk lại thành câu trả lời
LLM-based: dùng model để hiểu và tổng hợp thông tin

Tôi chọn LLM-based vì:

Có khả năng hiểu context tốt hơn
Tổng hợp được nhiều nguồn thông tin (multi-chunk)
Tạo câu trả lời tự nhiên và dễ đọc

Tuy nhiên, để tránh hallucination, tôi thiết kế SYSTEM_PROMPT với các ràng buộc chặt chẽ:


## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

Lỗi: Synthesis Worker trả về câu trả lời không rõ ràng khi không có context.

Symptom (pipeline làm gì sai?):
Khi retrieved_chunks rỗng, hệ thống vẫn cố generate câu trả lời, dẫn đến nội dung mơ hồ hoặc không chính xác.

Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):
Trong _build_context(), nếu không có dữ liệu thì chỉ trả về string trống hoặc (Không có context) nhưng không có cơ chế buộc LLM phải xử lý trường hợp này:

if not parts:
    return "(Không có context)"

Cách sửa:

Tôi xử lý theo 2 bước:

Giữ (Không có context) làm tín hiệu rõ ràng cho LLM
Bổ sung rule trong prompt để bắt buộc abstain:
2. Nếu context không đủ → "Không đủ thông tin trong tài liệu nội bộ"

Đồng thời cập nhật _estimate_confidence():

if not chunks:
    return 0.1

Bằng chứng trước/sau:

Trước: câu trả lời mơ hồ, không rõ nguồn
Sau: hệ thống trả lời rõ ràng “Không đủ thông tin” và confidence thấp (~0.1–0.3)

Sau khi sửa, hệ thống an toàn hơn và tránh hallucination.

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

Tôi làm tốt nhất ở việc xây dựng được Synthesis Worker hoàn chỉnh, có thể tổng hợp dữ liệu từ nhiều nguồn và tạo ra câu trả lời có cấu trúc rõ ràng, kèm theo citation.

Tôi cũng thiết kế được cơ chế kiểm soát chất lượng output thông qua prompt và confidence scoring, giúp hệ thống tránh trả lời sai khi thiếu dữ liệu.

Tuy nhiên, tôi chưa tối ưu tốt latency do phụ thuộc vào LLM và chưa xử lý tốt các trường hợp phức tạp như multi-intent hoặc conflict giữa các nguồn.

Nhóm phụ thuộc vào tôi ở phần output cuối — nếu synthesis sai, toàn bộ hệ thống sẽ trả lời sai. Ngược lại, tôi phụ thuộc vào Retrieval và Policy Worker để cung cấp context chính xác.

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ cải thiện _estimate_confidence() bằng cách sử dụng LLM-as-Judge thay vì heuristic.

Lý do:
Trace cho thấy có trường hợp chunk có score cao nhưng câu trả lời chưa thực sự chính xác.

Giải pháp:
Dùng LLM đánh giá lại answer dựa trên context để tính confidence chính xác hơn.