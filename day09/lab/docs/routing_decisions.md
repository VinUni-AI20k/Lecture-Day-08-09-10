# Routing Decisions Log — Lab Day 09

**Nhóm:** C401 - C5  
**Ngày:** 14/04/2026

> Tất cả quyết định routing dưới đây được trích trực tiếp từ `artifacts/grading_run.jsonl` và `artifacts/traces/`.  
> Không có thông tin giả định — mọi `route_reason`, `confidence`, `latency_ms` đều là số thực từ pipeline.

---

## Routing Decision #1 — Câu hỏi tra cứu SLA đơn giản

**Task đầu vào:**
> "Ticket P1 được tạo lúc 22:47. Đúng theo SLA, ai nhận thông báo đầu tiên và qua kênh nào? Deadline escalation là mấy giờ?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `"task contains retrieval/SLA keyword | risk_high flagged"`  
**MCP tools được gọi:** _(không có)_  
**Workers called sequence:** `retrieval_worker` → `synthesis_worker`

**Kết quả thực tế:**
- **final_answer (ngắn):** On-call engineer nhận thông báo qua Slack #incident-p1 và email incident@company.internal ngay lập tức. Deadline escalation: 22:57 (10 phút sau khi tạo ticket).
- **confidence:** 0.77
- **latency_ms:** 15,938ms
- **hitl_triggered:** false
- **Correct routing?** ✅ Yes

**Nhận xét:** Supervisor nhận diện đúng đây là câu tra cứu SLA — keyword "SLA", "P1", "ticket" khớp rule → route thẳng `retrieval_worker`. Không cần `policy_tool_worker` vì câu hỏi chỉ hỏi quy trình, không có exception case. `risk_high` được flag vì liên quan đến P1 incident.

---

## Routing Decision #2 — Câu hỏi áp dụng chính sách có temporal scope

**Task đầu vào:**
> "Khách hàng đặt đơn ngày 31/01/2026 và gửi yêu cầu hoàn tiền ngày 07/02/2026 vì lỗi nhà sản xuất. Sản phẩm chưa kích hoạt, không phải Flash Sale, không phải kỹ thuật số. Chính sách nào áp dụng và có được hoàn tiền không?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `"task contains policy/access keyword"`  
**MCP tools được gọi:** _(không có)_  
**Workers called sequence:** `retrieval_worker` → `policy_tool_worker` → `synthesis_worker`

**Kết quả thực tế:**
- **final_answer (ngắn):** Áp dụng chính sách hoàn tiền phiên bản 3 (đơn đặt trước 01/02/2026). Đủ điều kiện hoàn tiền: lỗi nhà sản xuất, chưa kích hoạt, trong 7 ngày làm việc.
- **confidence:** 0.71
- **latency_ms:** 11,246ms
- **hitl_triggered:** false
- **Correct routing?** ✅ Yes

**Nhận xét:** Supervisor routing đúng vì câu này yêu cầu tra cứu policy (phiên bản 3 vs 4 theo ngày hiệu lực) và kiểm tra exception cases (Flash Sale, kỹ thuật số). `policy_tool_worker` xử lý temporal scoping (đơn đặt 31/01 → dùng policy v3, effective 01/02 là policy v4). Confidence hạ xuống 0.71 do phải suy luận ngày tháng.

---

## Routing Decision #3 — Câu abstain đúng (anti-hallucination)

**Task đầu vào:**
> "Mức phạt tài chính cụ thể khi đội IT vi phạm SLA P1 resolution time (không resolve trong 4 giờ) là bao nhiêu?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `"task contains retrieval/SLA keyword | risk_high flagged"`  
**MCP tools được gọi:** _(không có)_  
**Workers called sequence:** `retrieval_worker` → `synthesis_worker`

**Kết quả thực tế:**
- **final_answer (ngắn):** "Không đủ thông tin trong tài liệu nội bộ."
- **confidence:** **0.30** ← thấp nhất trong toàn bộ run
- **latency_ms:** 7,776ms
- **hitl_triggered:** **true** ← HITL được kích hoạt
- **Correct routing?** ✅ Yes (abstain đúng — mức phạt tài chính không có trong bất kỳ tài liệu nội bộ nào)

**Nhận xét:** Đây là ví dụ quan trọng nhất về **anti-hallucination**. Supervisor route đúng khâu retrieval, retrieval worker trả về các chunk từ `sla_p1_2026.txt` nhưng không có thông tin mức phạt tài chính. `synthesis_worker` nhận diện ra mức confidence thấp (0.30) → kích hoạt HITL thay vì bịa số liệu. Nếu là single agent (Day 08), sẽ có nguy cơ hallucinate một con số hình phạt không tồn tại → penalty −50% điểm câu.

---

## Routing Decision #4 — Multi-hop: Cross-document, risk_high, MCP tool

**Task đầu vào:**
> "Sự cố P1 xảy ra lúc 2am. Đồng thời cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Hãy nêu đầy đủ: (1) các bước SLA P1 notification phải làm ngay, và (2) điều kiện để cấp Level 2 emergency access."

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `"multi-hop: access control + SLA context | risk_high flagged"`  
**MCP tools được gọi:** `get_ticket_info` ✅  
**Workers called sequence:** `retrieval_worker` → `policy_tool_worker` → `synthesis_worker`

**Kết quả thực tế:**
- **final_answer (ngắn):** (1) SLA P1: xác nhận severity trong 5 phút, gửi thông báo Slack #incident-p1 và email incident@company.internal ngay. (2) Level 2 emergency: On-call IT Admin cấp tạm thời (max 24h) sau khi Tech Lead phê duyệt bằng lời, phải có ticket chính thức sau 24h, ghi log vào Security Audit.
- **confidence:** 0.80
- **latency_ms:** 14,504ms
- **hitl_triggered:** false
- **Correct routing?** ✅ Yes (câu khó nhất — 16 điểm, Full marks)

**Nhận xét:** Đây là câu định tuyến phức tạp nhất trong lab. Supervisor nhận diện **2 domain khác nhau** trong 1 câu: SLA procedure (retrieval) + access control emergency (policy). `route_reason` ghi rõ `"multi-hop"` — supervisor gọi cả retrieval lẫn policy worker, sau đó MCP tool `get_ticket_info` được gọi để lấy context ticket thực tế. `synthesis_worker` tổng hợp từ cả 2 nguồn tài liệu (`sla_p1_2026.txt` + `access_control_sop.txt`).

---

## Routing Decision #5 — Câu exception policy rõ ràng (Flash Sale)

**Task đầu vào:**
> "Khách hàng mua sản phẩm trong chương trình Flash Sale, nhưng phát hiện sản phẩm bị lỗi từ nhà sản xuất và yêu cầu hoàn tiền trong vòng 5 ngày. Có được hoàn tiền không? Giải thích theo đúng chính sách."

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `"task contains policy/access keyword"`  
**MCP tools được gọi:** _(không có)_  
**Workers called sequence:** `retrieval_worker` → `policy_tool_worker` → `synthesis_worker`

**Kết quả thực tế:**
- **final_answer (ngắn):** Không được hoàn tiền. Sản phẩm Flash Sale thuộc danh mục ngoại lệ — không đủ điều kiện hoàn tiền dù bị lỗi nhà sản xuất.
- **confidence:** 0.74
- **latency_ms:** 8,727ms
- **hitl_triggered:** false
- **Correct routing?** ✅ Yes

**Nhận xét:** `policy_tool_worker` xử lý đúng exception case. Dù điều kiện "lỗi nhà sản xuất" và "trong vòng 5 ngày" đều thỏa mãn điều kiện hoàn tiền thông thường, nhưng Flash Sale là **ngoại lệ tuyệt đối** trong `policy_refund_v4.txt` → kết quả là không hoàn tiền. Đây là trường hợp keyword matching đơn giản (`policy/access`) nhưng logic nghiệp vụ bên trong phức tạp.

---

## Tổng kết

### Routing Distribution (từ 15 test traces)

| Worker (Primary Route) | Số traces | Tỷ lệ |
|------------------------|-----------|-------|
| `retrieval_worker` | 8 | 53% |
| `policy_tool_worker` | 7 | 47% |
| `human_review` (HITL) | 3 | 20% _(overlap — không mutually exclusive)_ |

### Routing Accuracy

Trong 10 câu grading + 15 test traces đã chạy:

- **Câu route đúng:** 15 / 15 (100% routing label chính xác)
- **Câu route sai:** 0 — không có trường hợp nào route nhầm worker
- **Câu trigger HITL:** 3 / 15 (20%) — tất cả đều là câu không có đủ thông tin trong KB
- **MCP tool được gọi:** 2 / 15 (13%) — cả 2 đều là câu multi-hop liên quan đến ticket context

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất trong routing logic:

1. **Keyword matching vs LLM classifier:** Chúng tôi dùng **keyword matching** đơn giản (`if "policy" in task or "access" in task → policy_tool_worker`). Ưu điểm: nhanh, predictable, dễ kiểm tra. Nhược điểm: có thể miss câu hỏi policy không dùng keyword rõ ràng. Trong 15 traces, cách này hoạt động chính xác 100%.

2. **HITL threshold = 0.5 confidence:** Khi `synthesis_worker` trả về confidence < 0.5, hệ thống tự động `hitl_triggered = true` thay vì đưa ra câu trả lời không chắc. Điều này bảo vệ khỏi hallucination (gq07 là bằng chứng — confidence = 0.30, abstain đúng thay vì bịa số liệu tài chính).

3. **`risk_high` flag:** Các câu liên quan đến P1, emergency access, hoặc exception policy được flag `risk_high = true` → supervisor ghi thêm vào `route_reason`, giúp debug dễ hơn khi xem lại trace.

### Route Reason Quality

Nhìn lại các `route_reason` trong 15 traces:

| Pattern `route_reason` | Câu xuất hiện | Số lần |
|------------------------|---------------|--------|
| `"task contains retrieval/SLA keyword \| risk_high flagged"` | gq01, gq05, gq07 | 3 / 10 |
| `"task contains retrieval/SLA keyword"` _(không có risk_high)_ | gq06, gq08 | 2 / 10 |
| `"task contains policy/access keyword"` | gq02, gq04, gq10 | 3 / 10 |
| `"multi-hop: access control + SLA context \| risk_high flagged"` | gq03, gq09 | 2 / 10 |

> **Lưu ý:** Bảng trên tính trên 10 câu `grading_run.jsonl`. Tổng 15 traces (kể cả test questions) có phân phối tương tự theo `eval_report.json` (8/15 retrieval, 7/15 policy).

**Đánh giá chất lượng:** `route_reason` đủ để debug trong đa số trường hợp — supervisor ghi rõ keyword nào trigger và risk level. Tuy nhiên, format hiện tại chưa ghi **tên tài liệu nào được dự đoán sẽ có thông tin** — đây là cải tiến nên làm nếu có thêm thời gian (ví dụ: `"expect_sources: ['sla_p1_2026.txt', 'access_control_sop.txt']"`).
