# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| ___ | Supervisor Owner | ___ |
| ___ | Worker Owner | ___ |
| ___ | MCP Owner | ___ |
| ___ | Trace & Docs Owner | ___ |

**Ngày nộp:** ___________  
**Repo:** ___________  
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

**Hệ thống tổng quan:**
Hệ thống được thiết kế theo mô hình **Supervisor-Worker** sử dụng cấu trúc Graph để điều phối luồng xử lý. Supervisor nhận câu hỏi, thực hiện phân tích định tuyến dựa trên từ khóa và mức độ rủi ro, sau đó phân phối công việc cho các Worker chuyên biệt. Hệ thống tích hợp một tầng **MCP (Model Context Protocol)** để cung cấp các khả năng ngoại vi như tra cứu ticket Jira và kiểm tra quyền truy cập hệ thống.

**Routing logic cốt lõi:**
Nhóm sử dụng logic **Keyword Matching + Regex** tích hợp trong Supervisor. Logic này ưu tiên:
- Phân loại nhanh các yêu cầu về chính sách hoàn tiền/truy cập sang `policy_tool_worker`.
- Phân loại các yêu cầu về sự cố/SLA sang `retrieval_worker`.
- Kích hoạt **Human-in-the-Loop (HITL)** khi phát hiện các mã lỗi hệ thống không xác định hoặc tình huống khẩn cấp ngoài giờ làm việc.

**MCP tools đã tích hợp:**
- `search_kb`: Công cụ tìm kiếm ngữ nghĩa trong cơ sở dữ liệu tri thức ChromaDB.
- `get_ticket_info`: Tra cứu trạng thái và chi tiết các ticket P1/SLA từ hệ thống giả lập.
- `check_access_permission`: Kiểm tra điều kiện cấp quyền dựa trên Access Control SOP.
- `create_ticket`: Hỗ trợ tạo ticket Jira tự động cho các yêu cầu không thể tự xử lý.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** ___________________

**Bối cảnh vấn đề:**

_________________

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| ___ | ___ | ___ |
| ___ | ___ | ___ |

**Phương án đã chọn và lý do:**

_________________

**Bằng chứng từ trace/code:**
> Dẫn chứng cụ thể (VD: route_reason trong trace, đoạn code, v.v.)

```
[NHÓM ĐIỀN VÀO ĐÂY — ví dụ trace hoặc code snippet]
```

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** ___ / 96

**Câu pipeline xử lý tốt nhất:**
- ID: ___ — Lý do tốt: ___________________

**Câu pipeline fail hoặc partial:**
- ID: ___ — Fail ở đâu: ___________________  
  Root cause: ___________________

**Câu gq07 (abstain):** Nhóm xử lý thế nào?

_________________

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?

_________________

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**

_________________

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**

_________________

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**

_________________

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| ___ | ___________________ | ___ |
| ___ | ___________________ | ___ |
| ___ | ___________________ | ___ |
| ___ | ___________________ | ___ |

**Điều nhóm làm tốt:**

_________________

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**

_________________

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**

_________________

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ trace/scorecard.

_________________

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
