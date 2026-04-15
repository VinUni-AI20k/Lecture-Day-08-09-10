# Routing Decisions Log — Lab Day 09

**Nhóm:** C401 - C5  
**Ngày:** 14/04/2026

> Ghi lại 4 routing decisions thực tế từ trace `artifacts/traces/`.  
> Mỗi entry lấy trực tiếp từ field `supervisor_route`, `route_reason`, `workers_called`, `confidence` trong JSON.

---

## Routing Decision #1

**Task đầu vào:**
> `"SLA xử lý ticket P1 là bao lâu?"`

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `task contains retrieval/SLA keyword | risk_high flagged`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer: *"SLA xử lý ticket P1 là 4 giờ cho việc khắc phục sự cố sau phản hồi ban đầu trong 15 phút kể từ khi ticket được tạo [2]."*
- confidence: 0.75
- latency: 19,232ms
- Correct routing? **Yes**

**Nhận xét:**  
Routing đúng — keyword `"p1"` và `"sla"` đều nằm trong `retrieval_keywords` của `supervisor_node()`. Retrieval lấy đúng doc `sla_p1_2026.txt`. Tuy nhiên `risk_high=True` bị flag do keyword `"p1"` dù đây là câu hỏi tra cứu thông thường — không ảnh hưởng route nhưng là false positive nhỏ cho risk flag.

---

## Routing Decision #2

**Task đầu vào:**
> `"Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?"`

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword`  
**MCP tools được gọi:** `search_kb` (query: câu hỏi đầu vào, top_k=3 → trả về 3 chunks từ `policy_refund_v4.txt` và `it_helpdesk_faq.txt`)  
**Workers called sequence:** `policy_tool_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer: *"Khách hàng yêu cầu hoàn tiền cho sản phẩm lỗi trong chương trình Flash Sale sẽ không được chấp nhận, vì sản phẩm thuộc danh mục hàng hóa không được hoàn tiền theo chính sách [1]."*
- confidence: 0.73
- latency: 16,293ms
- Correct routing? **Yes**

**Nhận xét:**  
Routing đúng — `"flash sale"` thuộc `policy_keywords`. MCP tool `search_kb` được gọi tự động (`needs_tool=True`) và trả về chunks từ `policy_refund_v4.txt`, đặc biệt Điều 3 nêu rõ Flash Sale là ngoại lệ không được hoàn tiền. Câu trả lời có citation và phản ánh đúng policy.

---

## Routing Decision #3

**Task đầu vào:**
> `"ERR-403-AUTH là lỗi gì và cách xử lý?"`

**Worker được chọn:** `human_review` → `retrieval_worker` (sau khi human approve)  
**Route reason (từ trace):** `unknown error code + risk_high → human review | human approved → retrieval`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `human_review → retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer: *"Không đủ thông tin trong tài liệu nội bộ."*
- confidence: 0.3
- hitl_triggered: True
- latency: 9,543ms
- Correct routing? **Yes**

**Nhận xét:**  
Đây là trường hợp HITL hoạt động đúng thiết kế. Regex `\berr-[a-z0-9\-]+\b` trong `supervisor_node()` phát hiện mã lỗi `err-403-auth` → route sang `human_review`. Sau khi auto-approve (lab mode), pipeline tiếp tục sang retrieval nhưng không tìm thấy doc nào mô tả lỗi này → synthesis abstain với `confidence=0.3 < HITL_THRESHOLD=0.4` → `hitl_triggered=True` được set lần thứ hai. Hệ thống **không hallucinate** dù không có context — đây là hành vi đúng.

---

## Routing Decision #4 — Trường hợp routing khó nhất

**Task đầu vào:**
> `"Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?"`

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `multi-hop: access control + SLA context | risk_high flagged`  
**MCP tools được gọi:** `search_kb` (3 chunks: `access_control_sop.txt`, `sla_p1_2026.txt`), `get_ticket_info` (ticket IT-9847 — P1 đang active)

**Kết quả thực tế:**
- final_answer: *"Quy trình cấp quyền Level 3 để khắc phục sự cố P1 khẩn cấp như sau: 1. On-call IT Admin có thể cấp quyền tạm thời (tối đa 24 giờ) sau khi được Tech Lead phê duyệt bằng lời..."*
- confidence: 0.76
- latency: 6,532ms
- Correct routing? **Yes**

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**

Câu hỏi này chứa từ khóa của **cả 2 nhóm** — `"level 3"` (policy_keywords) lẫn `"p1"` + `"khẩn cấp"` (retrieval_keywords + risk_triggers). Nếu routing đơn giản theo thứ tự `if/elif`, kết quả phụ thuộc vào keyword nào được check trước. Nhóm xử lý bằng cách kiểm tra `is_multi_hop` trước tất cả, với điều kiện kết hợp:
```python
is_multi_hop = any(kw in task for kw in ["level 2", "level 3", "level 4", "cấp quyền"]) \
               and any(kw in task for kw in ["p1", "sla", "incident", "emergency"])
```
Nhờ đó route sang `policy_tool_worker` với `needs_tool=True`, gọi MCP để lấy context từ cả 2 doc (`access_control_sop.txt` + `sla_p1_2026.txt`) và thông tin ticket thực từ `get_ticket_info`. Câu trả lời đúng, có citation rõ ràng, confidence=0.76.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 18/36 | 50% |
| policy_tool_worker | 18/36 | 50% |
| human_review | 2/36 (1 loại câu hỏi) | ~5.6% |

*Lưu ý: `human_review` không phải điểm cuối — sau đó vẫn route sang `retrieval_worker`. Các trace của ERR-403-AUTH được tính trong nhóm `retrieval_worker` cho routing cuối cùng.*

### Routing Accuracy

Trong 17 câu hỏi unique nhóm đã chạy:
- Câu route đúng: **17 / 17**
- Câu route sai: 0
- Câu trigger HITL: 2 (`ERR-403-AUTH` và `"Ticket P1 lúc 22:47 — ai nhận thông báo?"`)

### Lesson Learned về Routing

1. **Multi-hop detection phải được check TRƯỚC keyword đơn lẻ** — nếu để sau `elif`, câu "Level 3 + P1" sẽ bị route sai sang một trong hai nhánh thay vì kích hoạt multi-hop logic.
2. **Fail-loud `route_decision()` quan trọng hơn silent fallback** — mọi trace đều có `route_reason` đọc được, không có run nào bị route ẩn/sai mà không phát hiện được ngay.

### Route Reason Quality

Các `route_reason` trong trace đủ thông tin để debug: format `"<trigger keyword group> | risk_high flagged"` cho biết ngay nguyên nhân phân loại. Trường hợp multi-hop có format `"multi-hop: access control + SLA context | risk_high flagged"` — rõ ràng hơn nữa. Nếu cải tiến: thêm keyword cụ thể đã match vào reason (VD: `matched_keywords=['level 3', 'p1']`) để debug nhanh hơn khi có false positive.
