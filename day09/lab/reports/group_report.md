# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Nhóm 67
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
|  | Supervisor Owner |  |
|  | Worker Owner |  |
|  | MCP Owner |  |
| Nguyễn Việt Quang | Trace & Docs Owner | nguyenvietquang.1601@gmail.com |

**Ngày nộp:** 2026-04-14
**Repo:** `TTNguyen0312/Team67-Day-08-09-10`
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
Hệ thống sử dụng Kiến trúc Supervisor-Worker mô phỏng quy trình xử lý IT Helpdesk Support chuẩn gồm 4 thành phần thiết yếu (1 Quản lý và 3 nhân viên). Trong đó bao gồm: Nút quản lý trung tâm `Supervisor`, Nhân viên tìm kiếm nội bộ `retrieval_worker`, Nhân viên kiểm định chính sách chuyên biệt `policy_tool_worker`, Trọng tài duyệt tay `human_review` và bước viết đáp án `synthesis_worker`. Nhờ kiến trúc này, chúng tôi tách rời rõ rệt mảng tra cứu tài liệu và check API mảng phân quyền riêng biệt.

**Routing logic cốt lõi:**
> Logic Supervisor sẽ check dựa trên Keyword Matching (If-else) có trong `task`. Nếu phát hiện ra keyword về "refund, policy, access", Task sẽ được cấp chuyển sang `policy_tool_worker` xử lý. Nếu Task có yếu tố khẩn cấp "P1, ticket", hệ thống tự động đẩy truy vấn về lại `retrieval_worker`. Đối với các mã Code Error kỳ lạ hoặc chưa định danh, cờ `risk_high` kéo lên để Pause luồng thực thi (HITL).

**MCP tools đã tích hợp:**
> `policy_tool_worker` tích hợp sẵn khả năng gọi trực tiếp các Tools ngoại vi

- `search_kb`: Công cụ tương tác trực tiếp với ChromaDB tìm kiếm tri thức (Knowledge Base) về SLA hoặc các SOP nội bộ.
- `get_ticket_info`: Mock tool lấy lịch sử log từ Database giả lập để tra soát xem P1 ticket ai đang cầm.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** Định hướng cấu hình (Routing) ưu tiên cho luồng khẩn cấp.

**Bối cảnh vấn đề:**
Hệ thống support ticket đôi khi nhận được các câu tra cứu luân phiên về các Lỗi không rõ (ERR) đi kèm yếu tố Khẩn cấp P1. Nếu dùng LLM bình thường sẽ sinh ra ảo giác và tự bịa phương án xử lý lỗi.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Gộp vô `retrieval_worker` chung | Nhanh, dễ code | Dễ sinh Halucination vì Doc không có nội dung cách fix mã lỗi. Ảnh hưởng bảo mật hệ thống khi Support máy tự chỉ đạo làm bừa. |
| Thêm cờ `risk_high` & tách `human_review` | An toàn và chắc chắn. Dể kiểm tra bảo mật (Traceable). | Xử lí mất thời gian hơn, tốn công code Node phụ chờ người verify. |

**Phương án đã chọn và lý do:**
Nhóm ưu tiên "Cờ `risk_high` với mã lỗi lạ phải dừng lại cho người duyệt (HITL)". Lý do là trong mảng IT nội bộ doanh nghiệp, thao tác sửa mã Code lỗi lạ rủi ro rất cao, không được để Bot tự xử lý (zero trust). Đánh đổi delay lấy System Safety là tối quan trọng ở cấp phát phân quyền.

**Bằng chứng từ trace/code:**
> Lấy từ output terminal khi chạy test_questions:

```python
⚠️  HITL TRIGGERED
   Task: ERR-403-AUTH là lỗi gì và cách xử lý?
   Reason: unknown error code + risk_high → human review
   Action: Auto-approving in lab mode (set hitl_triggered=True)
```

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** 90 / 96

**Câu pipeline xử lý tốt nhất:**
- ID: `gq04` (Khi khách hàng chọn nhận store credit thay vì hoàn tiền, họ nhận)
  Lý do tốt: Logic bắt đúng vào luồng Policy Tool (`conf=0.73`) ngay lập tức, và worker gọi MCP tool thành công để tính toán thay vì chỉ đọc thông tin chết.

**Câu pipeline fail hoặc partial:**
- ID: `gq07` (Mức phạt tài chính cụ thể) 
  Fail ở đâu: `confidence` thu về rất thấp (chỉ đạt `0.30`).
  Root cause: Do RAG không tìm được chunk thông tin chứa "mức phạt tài chính", nên VectorDB bối rối và trả về dữ liệu rỗng hoặc sai lệch, khiến LLM e dè.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?
Từ chối trả lời (Abstain). Do prompt nhóm thiết kế ép model phải từ chối khi Conf dưới 0.4 hoặc khi context không đủ mạnh để trả lời.

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?
Trong trace (`route=policy_tool_worker`), câu này Supervisor điều hướng chính xác vào check chính sách cấp quyền Level 2 tạm thời nhờ cụm "Sự cố P1 ... cấp Level 2 access". Framework đã thành công ghép thông tin.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**
Confidence Average. Nếu Day 08 đạt trung bình khoảng 0.8 do Single Agent cố gắng nặn ngữ cảnh, thì ở Day 09, các câu hỏi khó đã giảm độ tự tin lại (như gq07 = 0.3) chứng minh hệ thống trở nên dè chừng và an toàn hơn hẳn khi gặp các topic nó không nằm lòng.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**
Khả năng Module hóa (Modularity). Chẳng hạn lúc thay đổi luật của Policy Worker, nhóm không cần đụng 1 chút code nào của nhánh RAG Retrieval Worker.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Đối với các câu truy xuất SLA thuần tuý (rất đơn giản), Multi_agent tiêu thụ khoảng ~3s (tương đương) nhưng tốn số lượng Node Process ngầm và Token sinh lý do (route reason) dư thừa không đáng có.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
|  | Code logic Graph `supervisor_node()` | 1 |
|  | Xây dựng Worker & Retrieval flow | 2 |
|  | Khởi tạo MCP Tools Server | 3 |
| Nguyễn Việt Quang | Chạy Trace log, tính so sánh & Setup Báo cáo | 4 |

**Điều nhóm làm tốt:**
Giao tiếp trơn tru thông qua Git. Flow của ai người nấy đóng gói cẩn thận. Việc thống nhất chung 1 `AgentState` schema từ ban đầu giúp việc nối các Node không gặp lỗi Data Mapping.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
Lúc Code Node Supervisor, điều kiện Regex `if_else` cho nhánh Routing chưa được chặt che lắm. Một số truy vấn hơi lạ là luồng code có xu hướng ném hết qua Node Search mặc định làm mất đi ý nghĩa của Policy Worker.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**
Nhóm sẽ code thẳng bằng thư viện `LangGraph` thay vì tự build if-else thuần của Python để giảm tải các logic rẽ nhánh lồng ghép rắc rối. Cấu trúc StateGraph của LangChain hỗ trợ việc này chuẩn hơn.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> Nâng độ thông minh của Nút Routing (Manager Node): Trích xuất LLM classifier sử dụng OpenAI structured output (cấu trúc JSON output cứng) để Model tự đánh giá truy vấn thay vì if/else truyền thống. (Sẽ tăng Routing Accuracy lên đáng kể).

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
