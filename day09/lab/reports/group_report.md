# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** C401-E6  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Quang | Supervisor Owner | quang.dev@company.internal |
| Tuấn | Retrieval Worker | tuan.retrieval@company.internal |
| Hải | Policy Tool Worker | hai.policy@company.internal |
| Huy | MCP Owner | huy.mcp@company.internal |
| Dũng | Synthesis Worker | dung.synthesis@company.internal |
| Long | Trace & Eval Owner | long.trace@company.internal |
| Thuận | Docs & Reports Owner | thuan.docs@company.internal |

**Ngày nộp:** 14/04/2026  
**Repo:** https://github.com/dungnguyen1806/C401-E6-08-09-10.git

**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn hệ thống nhóm: bao nhiêu workers, routing logic hoạt động thế nào,
> MCP tools nào được tích hợp. Dùng kết quả từ `docs/system_architecture.md`.

**Hệ thống tổng quan:**
Nhóm xây dựng hệ thống theo mô hình **Supervisor-Worker** chuyên biệt cho CS & IT Helpdesk. Hệ thống gồm 1 Supervisor trung tâm điều phối và 3 Workers chính: Retrieval (truy xuất tri thức), Policy Tool (kiểm tra ngoại lệ & quy trình) và Synthesis (tổng hợp câu trả lời). Ngoài ra còn có một Node Human Review làm placeholder để xử lý các tác vụ rủi ro cao.

**Routing logic cốt lõi:**
Supervisor sử dụng kết hợp lọc từ khóa (keyword matching) và logic dựa trên luật (rule-based) để phân loại ý định người dùng. Logic được thiết kế đa tầng: phát hiện mã lỗi (HITL), kiểm tra chính sách đặc biệt (Policy) và cuối cùng là tra cứu tài liệu chung (Retrieval). Nếu phát hiện yêu cầu nhạy cảm, Supervisor sẽ gán cờ `risk_high` để Workers tiếp theo xử lý cẩn trọng hơn.

**MCP tools đã tích hợp:**
- `search_kb`: Truy xuất cơ sở tri thức (Knowledge Base) thông qua ChromaDB.
- `get_ticket_info`: Lấy metadata thực tế của ticket (status, deadline) để đối soát SLA.
- `check_access_permission`: Kiểm tra quyền hạn của requester dựa trên role và tài liệu SOP.
- `create_ticket`: Tự động khởi tạo ticket hỗ trợ khi hệ thống không thể giải quyết hoặc cần escalation.


---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** Tách rời `policy_tool_worker` khỏi `retrieval_worker` thay vì gộp chung vào 1 RAG pipeline.

**Bối cảnh vấn đề:**
Trong Day 08, chúng tôi nhận thấy LLM gặp khó khăn khi phải vừa đọc tài liệu, vừa nhớ các quy tắc "ngoại lệ" (ví dụ: hàng Flash Sale không được hoàn tiền dù lỗi NSX). Các quy tắc này thường mâu thuẫn với thông tin hoàn tiền chung trong tài liệu chính.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Gộp vào Prompt Single Agent | Nhanh, tốn ít LLM call | Dễ bị "quên" logic ngoại lệ khi context quá dài |
| Tách Node Policy chuyên biệt | Chính xác tuyệt đối, dễ debug, kiểm soát được MCP calls | Tăng độ trễ (latency) do tốn thêm bước định tuyến |

**Phương án đã chọn và lý do:**
Nhóm chọn **Tách Node Policy**. Lý do là trong doanh nghiệp, tính **Safety** và **Compliance** quan trọng hơn tốc độ. Việc có một node riêng giúp chúng tôi thực hiện các "SOP check" nghiêm ngặt và gọi các MCP tools để lấy dữ liệu thực tế (như trạng thái ticket) trước khi đưa ra kết luận cuối cùng.


**Bằng chứng từ trace/code:**
Dưới đây là ví dụ về quyết định định tuyến chính xác khi hệ thống phát hiện ngoại lệ Flash Sale, điều mà mô hình Single-Agent thường bỏ qua:

```json
{
  "question": "Khách hàng mua sản phẩm trong chương trình Flash Sale... Có được hoàn tiền không?",
  "supervisor_route": "policy_tool_worker",
  "route_reason": "policy check required: refund_exception_check",
  "workers_called": ["retrieval_worker", "policy_tool_worker", "synthesis_worker"]
}
```

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** 96 / 96

**Câu pipeline xử lý tốt nhất:**
- ID: gq10 (Flash Sale Refund) — Lý do tốt: Routing nhận diện đúng keyword "Flash Sale", chuyển sang Policy Worker và trả lời chính xác việc không được hoàn tiền theo đúng Điều 3 của chính sách.

**Câu pipeline fail hoặc partial:**
- ID: q10 (vòng test) — Fail ở đâu: Ban đầu bị route nhầm sang Retrieval do thiếu keyword "store credit".
  Root cause: Do Supervisor logic lúc đầu chỉ bắt keywords "refund", "hoàn tiền" mà quên mất "store credit" cũng là một dạng chính sách hoàn trả đặc biệt.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?
Hệ thống thực hiện rất tốt. Synthesis Worker tính toán Confidence score dựa trên số lượng chunk tìm được. Vì câu này không có thông tin phạt trong docs, confidence chỉ đạt 0.2, dẫn đến việc synthesis trả về: "Không đủ thông tin trong tài liệu nội bộ" – tránh được lỗi hallucination.

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?
Có. Trace ghi nhận luồng chạy qua `retrieval_worker` (để lấy thông tin SLA P1) và sau đó Supervisor chuyển tiếp liên mạch qua `policy_tool_worker` để check điều kiện cấp quyền Level 2 (Emergency). Kết quả trả về đầy đủ cả 2 ý của câu hỏi.


---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**
Độ tin cậy trung bình (**Avg Confidence**) tăng từ **0.72** (Day 08) lên **0.92** (Day 09). Điều này chứng minh kiến trúc đa tác nhân giúp câu trả lời được "Grounding" tốt hơn. Tuy nhiên, Latency tăng khoảng **5.3 giây** (từ 2.8s lên 8.1s).

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**
Khả năng "tự soi lỗi" của hệ thống. Nhờ có `route_reason` và `final_answer` tách biệt, việc debug trở nên dễ dàng hơn bao giờ hết. Chúng tôi không còn phải đoán xem AI sai ở bước nào.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Đối với các câu hỏi FAQ cực kỳ đơn giản (ví dụ: "SLA P1 là gì?"), việc đi qua Supervisor và Retrieval Worker tạo ra độ trễ không đáng có (overhead ~1-2s) so với việc chỉ dùng một câu prompt trực tiếp.


---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Quang | Coding Graph.py & Routing logic | 1 |
| Tuấn & Hải | Retrieval & Policy Worker development | 2 |
| Dũng | Synthesis Worker & Citations | 2 |
| Huy | MCP Server & Tools integration | 3 |
| Long | Tracing & Evaluation system | 4 |
| Thuận | Documentation & Performance Analysis | 4 |

**Điều nhóm làm tốt:**
Phối hợp đồng bộ và tuân thủ chặt chẽ Interface `AgentState`. Mọi thành viên đều hiểu rõ dữ liệu mình nhận vào và truyền đi ở đâu.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
Việc quản lý các phiên bản code qua Git đôi khi còn bị xung đột (divergence) ở giai đoạn cuối Sprint 4 khi mọi người cùng nộp báo cáo.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**
Chúng tôi sẽ xây dựng một bộ "Cơ sở dữ liệu Mock Trace" ngay từ Sprint 1 để Docs Owner có thể xây dựng tài liệu song song thay vì phải đợi đến phút cuối cùng.


---

**Nếu có thêm 1 ngày, nhóm sẽ làm gì?**
1. Nâng cấp Supervisor lên sử dụng **LLM Classifier** thay vì keyword matching để xử lý được những câu hỏi mang tính ẩn dụ hoặc ngôn ngữ tự nhiên phức tạp hơn.
2. Triển khai tính năng **Self-Correction** (nếu confidence < 0.5, hệ thống tự động refactor query để retrieve lại lần 2).


---
