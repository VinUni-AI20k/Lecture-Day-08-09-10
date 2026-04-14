# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** __C401 - C5_____  
**Thành viên:**
| Tên | Vai trò | Mã học viên |
|-----|---------|-------|
| Nguyễn Khánh Nam | Supervisor Owner | ___ |
| Đỗ Minh Phúc | Worker Owner | ___ |
| Lê Tú Nam | Worker Owner | ___ |
| Lê Hữu Hưng | Worker Owner | ___ |
| Chu Minh Quân | MCP Owner | ___ |
| Nguyễn Minh Hiếu | Trace & Docs Owner | ___ |

**Ngày nộp:** 14/04/2026 

**Repo:** https://github.com nam-k-nguyen/Day_08_09_10_C401_C5 

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
Nhóm đã xây dựng hệ thống theo mô hình **Supervisor-Worker**, chia nhỏ quy trình RAG thành các thành phần chuyên biệt. Hệ thống gồm 1 Supervisor điều phối và 3 Workers chính: `retrieval_worker` (truy xuất DB), `policy_tool_worker` (kiểm tra luật & ngoại lệ qua MCP), và `synthesis_worker` (tổng hợp câu trả lời). Kiến trúc này giúp tách biệt logic xử lý tài liệu khỏi logic kiểm tra chính sách nghiệp vụ.

**Routing logic cốt lõi:**
Supervisor sử dụng **Keyword & Regex matching** để đưa ra quyết định routing. Các từ khóa về SLA/Ticket được route sang `retrieval_worker`. Các từ khóa về hoàn tiền/cấp quyền được route sang `policy_tool_worker`. Đặc biệt, hệ thống có khả năng nhận diện các mã lỗi chưa xác định (`err-xxx`) để kích hoạt cơ chế `human_review` (HITL), đảm bảo tính an toàn cho hệ thống.

**MCP tools đã tích hợp:**
- `search_kb`: Công cụ tìm kiếm Knowledge Base nội bộ, cho phép `policy_tool_worker` tự động truy xuất thêm thông tin mà không phụ thuộc vào `retrieval_worker`.
- `get_ticket_info`: Tra cứu thông tin Jira ticket thật (mocked) để kiểm tra trạng thái SLA và người phụ trách.
- `check_access_permission`: Kiểm tra ma trận phê duyệt (Approval Matrix) cho các yêu cầu cấp quyền Level 1/2/3.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Chấp nhận đánh đổi **Độ trễ (Latency)** để đổi lấy **Tính minh bạch (Observability)** qua mô hình Multi-Agent.

**Bối cảnh vấn đề:**
Trong Day 08, nhóm sử dụng một Single Agent RAG duy nhất. Khi hệ thống trả lời sai (ví dụ: trả lời nhầm chính sách v3 thay vì v4), rất khó để xác định lỗi nằm ở bước nào (truy xuất sai hay suy luận sai). Team cần một cách để "mổ xẻ" pipeline và kiểm soát chặt chẽ từng chặng.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Single Agent (Day 08) | Nhanh, rẻ (1 LLM call), đơn giản. | "Hộp đen", khó debug, dễ bị hallucinate khi câu hỏi phức tạp. |
| **Supervisor-Worker (Day 09)** | Minh bạch, dễ debug, kiểm soát được output từng worker. | Tốn kém (nhiều LLM call), độ trễ cao, logic điều phối phức tạp. |

**Phương án đã chọn và lý do:**
Nhóm chọn **Supervisor-Worker**. Lý do chính là để giải quyết bài toán **Governance & Debuggability**. Trong môi trường doanh nghiệp (IT Helpdesk), việc biết *tại sao* AI đưa ra quyết định quan trọng hơn là tốc độ nhanh hơn vài trăm miligiây. Việc tách biệt `policy_tool_worker` cho phép nhóm cập nhật các quy định hoàn tiền mới mà không ảnh hưởng đến phần truy xuất dữ liệu kỹ thuật.

**Bằng chứng từ code:**
Trong `graph.py`, mỗi bước đi qua Supervisor đều ghi lại `route_reason` cực kỳ chi tiết:
```python
if is_multi_hop:
    route = "policy_tool_worker"
    route_reason = "multi-hop: access control + SLA context"
    needs_tool = True
    risk_high = True
```

---

## 3. Kết quả grading questions (150–200 từ)

> [BỎ QUA THEO YÊU CẦU — Đợi kết quả sau 17:00]

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

**Metric thay đổi rõ nhất (có số liệu):**
> [BỎ QUA KẾT QUẢ SỐ LIỆU — Chỉ ghi nhận xét định tính]

Thông qua quan sát `eval_trace.py`, nhóm nhận thấy **Routing Visibility** là cải thiện rõ rệt nhất. Trong khi Day 08 chúng tôi chỉ nhận được 1 câu trả lời cuối cùng, Day 09 cung cấp một lộ trình chi tiết các Nodes và Workers đã tham gia, giúp việc tìm lỗi sai (root cause analysis) diễn ra nhanh gấp đôi.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**
Khả năng "từ chối" (Abstain) của hệ thống Multi-Agent tốt hơn hẳn. Nhờ có `policy_tool_worker` kiểm tra điều kiện trước khi `synthesis_worker` viết câu trả lời, các câu hỏi mẹo hoặc thiếu thông tin được xử lý một cách chuyên nghiệp, ít bị tình trạng LLM tự "bịa" ra thông tin (hallucination) hơn so với prompt gộp của Day 08.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Đối với các câu hỏi rất đơn giản (ví dụ: "SLA P1 là bao lâu?"), việc phải đi qua Supervisor rồi mới đến Retrieval Worker là không cần thiết và làm tăng latency lên khoảng 800ms–1200ms mà chất lượng câu trả lời không đổi so với Single Agent.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nguyễn Khánh Nam | Supervisor Owner, Graph Orchestrator, Routing logic | 1, 2 |
| Đỗ Minh Phúc | Worker Owner (Retrieval Worker & ChromaDB) | 2 |
| Lê Tú Nam | Worker Owner (Policy Tool Worker) | 2, 3 |
| Lê Hữu Hưng | Worker Owner (Synthesis Worker & Prompting) | 2 |
| Chu Minh Quân | MCP Owner (MCP Server & Tool Implementation) | 3 |
| Nguyễn Minh Hiếu | Trace & Docs Owner, Eval Trace, Documentation | 4 |

**Điều nhóm làm tốt:**
Nhóm phối hợp rất tốt về mặt **Interface Contract**. Nhờ thống nhất `AgentState` từ sớm, các Worker của các thành viên khác nhau khi lắp ghép vào `graph.py` hoạt động ngay lập tức mà không gặp lỗi tương thích dữ liệu. Việc phân chia 3 Worker Owner giúp chuyên môn hóa sâu vào từng khía cạnh: Retrieval, Policy và Suy luận, từ đó tối ưu hóa được chất lượng của từng module độc lập.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
Việc debug MCP tool call tốn nhiều thời gian hơn dự kiến do các thành viên ban đầu chưa nắm vững giao thức MCP, dẫn đến việc tích hợp ở Sprint 3 bị chậm so với timeline. Ngoài ra, việc đồng đồng bộ giữa 3 Worker Owner đôi khi cần nhiều thời gian thảo luận để đảm bảo các cạnh nối trong graph hoạt động trơn tru.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ thực hiện 2 cải tiến:
1.  **Async Orchestration:** Chuyển đổi graph sang xử lý bất đồng bộ (Asyncio) để các workers có thể chạy song song, giảm latency tổng thể xuống mức < 2 giây.
2.  **Semantic Supervisor:** Thay thế keyword matching bằng một model nhỏ (ví dụ: `bert-base-uncased` hoặc LLM few-shot) để phân loại Task chính xác hơn, tránh lỗi khi người dùng sử dụng từ lóng hoặc câu hỏi chồng lấn domain.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
