# Routing Decisions Log — Lab Day 09

> Ba ví dụ định hướng dựa trên `test_questions.json` và logic trong `supervisor_node()` — sau khi chạy `python eval_trace.py`, thay phần trace bằng `run_id` thật từ `artifacts/traces/`.

---

## Routing Decision #1

**Task đầu vào:**
> SLA xử lý ticket P1 là bao lâu?

**Worker được chọn:** `retrieval_worker`  
**Route reason (mẫu):** `SLA / P1 / IT ops keywords — retrieval + synthesis`  
**MCP tools được gọi:** (không — nhánh retrieval không bắt buộc MCP)  
**Workers called sequence:** `retrieval_worker` → `synthesis_worker`

**Kết quả thực tế:**
- Kỳ vọng: trả lời SLA P1 (15 phút first response, 4 giờ resolution) từ `sla_p1_2026.txt`
- Confidence: phụ thuộc độ chắc của retrieval + LLM

**Nhận xét:** Câu có `p1`/`sla` được ưu tiên **trước** nhánh “bao lâu / bao nhiêu ngày” để tránh nhầm sang informational-only.

---

## Routing Decision #2

**Task đầu vào:**
> Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (mẫu):** `policy/access/refund exception keywords — policy_tool uses MCP search_kb (not direct Chroma)`  
**MCP tools được gọi:** `search_kb` (và có thể `get_ticket_info` nếu có từ khóa ticket)  
**Workers called sequence:** `policy_tool_worker` → `synthesis_worker`

**Kết quả thực tế:**
- Policy worker phát hiện Flash Sale exception → `policy_applies` false nếu đúng rule trong docs

**Nhận xét:** Nhánh policy luôn `needs_tool=True` để `search_kb` đi qua MCP (đúng yêu cầu lab).

---

## Routing Decision #3

**Task đầu vào:**
> Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời cho contractor để emergency fix. Nêu đủ cả hai quy trình (SLA + access).

**Worker được chọn:** `multi_hop` (trong trace: `supervisor_route` = `multi_hop`)  
**Route reason (mẫu):** `multi-hop: task mentions incident/SLA/P1/ticket AND access/level/contractor — run retrieval then policy (+ MCP tools)`  
**MCP tools được gọi:** `get_ticket_info` (khi có P1/ticket), có thể thêm MCP khác tùy policy  
**Workers called sequence:** `retrieval_worker` → `policy_tool_worker` → `synthesis_worker`

**Kết quả thực tế:**
- Retrieval lấy evidence cross-doc; policy thêm ticket mock + phân tích Level 2 emergency; synthesis gom context.

**Nhận xét:** Đây là case **khó nhất** — cần cả SLA và access; trace phải ghi rõ ≥2 workers (điểm bonus trong rubric nếu đạt).

---

## Tổng kết

### Routing Distribution

Chạy `python eval_trace.py --analyze` sau khi có đủ file trong `artifacts/traces/` để điền bảng phân phối thực tế.

### Lesson Learned

1. Thứ tự rule: `multi_hop` → `sla_ops` → `policy_strong` / `policy_access` → `info_q` → `err-` → default.
2. `route_reason` phải cụ thể — không dùng `unknown` (trừ điểm chấm).
