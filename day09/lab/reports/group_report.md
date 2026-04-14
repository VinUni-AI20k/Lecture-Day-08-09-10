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

**Repo:** https://github.com/nam-k-nguyen/Lecture-Day-08-09-10

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
Supervisor sử dụng **Keyword & Regex matching** để đưa ra quyết định routing. Các từ khóa về SLA/Ticket được route sang `retrieval_worker`. Các từ khóa về hoàn tiền/cấp quyền được route sang `policy_tool_worker`. Trường hợp câu hỏi multi-hop (vừa có access control + SLA) được nhận diện riêng và gọi cả 2 workers. Hệ thống nhận diện mã lỗi không xác định (`err-xxx`) để route sang `human_review` node — node này auto-approve trong lab mode rồi tiếp tục về `retrieval_worker`, đồng thời đặt `hitl_triggered = True` trong trace.

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

Nhóm đã chạy pipeline với **10 câu grading questions** (gq01–gq10) trong khung 17:00–18:00. Kết quả được lưu tại `artifacts/grading_run.jsonl`.

**Tổng quan kết quả:**

| Câu | Supervisor Route | Confidence | HITL | MCP Tool | Latency (ms) |
|-----|-----------------|-----------|------|----------|--------------|
| gq01 | retrieval_worker | 0.77 | ✗ | — | 15,938 |
| gq02 | policy_tool_worker | 0.71 | ✗ | — | 11,246 |
| gq03 | policy_tool_worker | 0.77 | ✗ | get_ticket_info | 10,639 |
| gq04 | policy_tool_worker | 0.72 | ✗ | — | 7,853 |
| gq05 | retrieval_worker | 0.80 | ✗ | — | 8,360 |
| gq06 | retrieval_worker | 0.79 | ✗ | — | 10,074 |
| gq07 | retrieval_worker | **0.30** | ✅ | — | 7,776 |
| gq08 | retrieval_worker | 0.77 | ✗ | — | 9,508 |
| gq09 | policy_tool_worker | 0.80 | ✗ | get_ticket_info | 14,504 |
| gq10 | policy_tool_worker | 0.74 | ✗ | — | 8,727 |

**Điểm nổi bật:**
- **gq07 (anti-hallucination):** Pipeline trả lời đúng "Không đủ thông tin trong tài liệu nội bộ." với confidence = 0.30, kích hoạt HITL. Không bịa mức phạt tài chính — tránh được penalty −50%.
- **gq09 (multi-hop, 16 điểm):** Supervisor nhận diện đúng `"multi-hop: access control + SLA context | risk_high flagged"`, gọi cả 3 workers + MCP tool `get_ticket_info`. Câu trả lời nêu đủ cả 2 phần (SLA notification + Level 2 emergency access).
- **gq02 (temporal policy scoping):** Policy worker xác định đúng phiên bản chính sách v3 (đơn đặt trước 01/02/2026), không áp nhầm policy v4.
- **Avg confidence:** 0.717 (trên 10 câu grading).
- **Avg latency:** 10,467ms — cao hơn Day 08 nhưng đổi lại độ chính xác và traceability.

---


## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

**Metric thay đổi rõ nhất (số liệu từ `artifacts/eval_report.json`):**

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Thay đổi |
|--------|----------------------|---------------------|----------|
| Avg confidence | 0.82 | 0.643 | −22% (thận trọng hơn) |
| Avg latency | 1,850ms | 11,542ms | +524% |
| HITL / Abstain rate | 13% | 20% (3/15 traces) | +7% |
| Multi-hop accuracy | ~20% | ~80%+ (gq09 Full) | +60% |
| Routing visibility | ✗ Không có | ✓ `route_reason` mọi câu | N/A |

**Metric thay đổi rõ nhất:** Routing Visibility là cải thiện rõ rệt nhất về mặt vận hành. Trong khi Day 08 chỉ trả về 1 câu trả lời cuối cùng, Day 09 cung cấp `worker_io_logs` chi tiết từng node — cho phép nhóm xác định ngay lỗi ở `retrieval_worker` hay `synthesis_worker` mà không cần đọc lại toàn bộ prompt.

**Điều nhóm bất ngờ nhất khi chuyển sang multi-agent:**
Khả năng abstain (từ chối trả lời) của Multi-Agent tốt hơn hẳn. Cụ thể: câu **gq07** hỏi về mức phạt tài chính — thông tin **không có trong bất kỳ tài liệu nào**. Day 09 pipeline trả confidence = 0.30 và kích hoạt HITL, trả lời "Không đủ thông tin trong tài liệu nội bộ." thay vì bịa số liệu. Đây là hành vi mà Single Agent (Day 08) rất dễ mắc phải do không có cơ chế kiểm tra confidence theo ngưỡng.

**Trường hợp multi-agent KHÔNG giúp ích:**
Với các câu hỏi đơn giản như **gq08** ("Mật khẩu đổi sau bao nhiêu ngày?"), pipeline phải đi qua supervisor → retrieval_worker → synthesis_worker với latency = 9,508ms — trong khi Day 08 trả lời tương đương chỉ ~1,850ms. Với loại câu này, overhead của multi-agent không mang lại giá trị thêm.

---


## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nguyễn Khánh Nam | Supervisor Owner, Graph Orchestrator, Routing logic | 1  |
| Đỗ Minh Phúc | Worker Owner (Synthesis Worker & Prompting) | 2 |
| Lê Tú Nam | Worker Owner (Policy Tool Worker) | 2 |
| Lê Hữu Hưng | Worker Owner (Retrieval Worker & ChromaDB)  | 2 |
| Chu Minh Quân | MCP Owner (MCP Server & Tool Implementation) | 3 |
| Nguyễn Minh Hiếu | Trace & Docs Owner, Eval Trace, Documentation | 4 |

**Điều nhóm làm tốt:**
Nhóm phối hợp rất tốt về những mặt sau: 
**Interface Contract**. Nhờ thống nhất `AgentState` từ sớm, các Worker của các thành viên khác nhau khi lắp ghép vào `graph.py` hoạt động ngay lập tức mà không gặp lỗi tương thích dữ liệu. Việc phân chia 3 Worker Owner giúp chuyên môn hóa sâu vào từng khía cạnh: Retrieval, Policy và Suy luận, từ đó tối ưu hóa được chất lượng của từng module độc lập.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
Việc debug MCP tool call tốn nhiều thời gian hơn dự kiến do các thành viên ban đầu chưa nắm vững giao thức MCP, dẫn đến việc tích hợp ở Sprint 3 bị chậm so với timeline. Ngoài ra, việc đồng bộ giữa 3 Worker Owner đôi khi cần nhiều thời gian thảo luận để đảm bảo các cạnh nối trong graph hoạt động trơn tru.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ thực hiện 2 cải tiến:
1.  **Async Orchestration:** Chuyển đổi graph sang xử lý bất đồng bộ (Asyncio) để các workers có thể chạy song song, giảm latency tổng thể xuống mức < 2 giây.
2.  **Semantic Supervisor:** Thay thế keyword matching bằng một model nhỏ (ví dụ: `bert-base-uncased` hoặc LLM few-shot) để phân loại Task chính xác hơn, tránh lỗi khi người dùng sử dụng từ lóng hoặc câu hỏi chồng lấn domain.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
