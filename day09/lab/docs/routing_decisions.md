# Routing Decisions Log — Lab Day 09

**Nhóm:** C401-A2
**Ngày:** 2026-04-14

---

## Routing Decision #1

**Task đầu vào:**
> "SLA xử lý ticket P1 là bao lâu?"

**Worker được chọn:** `policy_tool_worker`
**Route reason (từ trace):** `task relates to policy, access or requires external tool (MCP)`
**MCP tools được gọi:** `search_kb`
**Workers called sequence:** `['policy_tool_worker', 'retrieval_worker', 'synthesis_worker']`

**Kết quả thực tế:**
- final_answer (ngắn): Phản hồi ban đầu 15 phút, thời gian xử lý 4 giờ.
- confidence: 0.12
- Correct routing? Yes

**Nhận xét:** Routing chính xác vào Policy Worker vì câu hỏi chứa từ khóa "ticket" (được thiết kế để kích hoạt MCP Jira lookup nếu cần). Hệ thống sau đó nhận ra cần ngữ cảnh nên tự động gọi thêm Retrieval Worker.

---

## Routing Decision #2

**Task đầu vào:**
> "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?"

**Worker được chọn:** `policy_tool_worker`
**Route reason (từ trace):** `task relates to policy, access or requires external tool (MCP)`
**MCP tools được gọi:** `search_kb`
**Workers called sequence:** `['policy_tool_worker', 'retrieval_worker', 'synthesis_worker']`

**Kết quả thực tế:**
- final_answer (ngắn): Không, đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4.
- confidence: 0.24
- Correct routing? Yes

**Nhận xét:** Routing chuẩn xác vào Policy Worker để kiểm tra các ngoại lệ trong chính sách hoàn tiền.

---

## Routing Decision #3

**Task đầu vào:**
> "Tra cứu thông tin ticket P1-LATEST giúp tôi."

**Worker được chọn:** `policy_tool_worker`
**Route reason (từ trace):** `task relates to policy, access or requires external tool (MCP)`
**MCP tools được gọi:** `get_ticket_info`
**Workers called sequence:** `['policy_tool_worker', 'synthesis_worker']`

**Kết quả thực tế:**
- final_answer (ngắn): Ticket IT-9847, Priority: P1, Status: In Progress.
- confidence: 0.11
- Correct routing? Yes

**Nhận xét:** Đây là minh chứng cho việc tích hợp MCP thành công. Supervisor nhận diện từ "ticket" và "p1-latest" để chuyển sang Policy Worker gọi công cụ tra cứu Jira.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 12 | 27% |
| policy_tool_worker | 31 | 72% |
| human_review | 2 | 4% |

### Routing Accuracy

- Câu route đúng: 41 / 43
- Câu route sai: 2 (Mã lỗi ERR- không mong muốn đi vào retrieval - đã điều chỉnh lại regex)
- Câu trigger HITL: 2

### Lesson Learned về Routing

1. **Keyword-based vs LLM**: Keyword-based nhanh (~5ms) nhưng dễ bị đánh lừa bởi từ đồng nghĩa. Nhóm đã tối ưu bộ từ khóa chuyên biệt cho IT Helpdesk.
2. **Needs Tool Flag**: Việc tách biệt điều kiện gọi MCP Tool (needs_tool) giúp tiết kiệm tài nguyên khi chỉ gọi tool khi supervisor thực sự yêu cầu.
