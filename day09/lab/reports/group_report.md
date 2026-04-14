# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** A4-C401
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Quân | Supervisor Owner | 26ai.hiepnd@vinuni.edu |
| Dương | Retrieval Worker Owner,Synthesis Worker | 26ai.quannm@vinuni.edu |
| Hiệp | Policy Worker Owner | 26ai.hiepnd@vinuni.edu |
| Đạt |  Trace Owner | 26ai.datbv@vinuni.edu |
| Chung | MCP / Tool Owner |  26ai.chunghq@vinuni.edu |
| Đức Anh | Trace & Docs Owner | 26ai.anhtd@vinuni.edu |

**Ngày nộp:** 14/04/2026  
**Repo:** `https://github.com/chrugez/C401-A4-Day-08-09-10`  
**Độ dài khuyến nghị:** 600–1000 từ

---

## 1. Kiến trúc nhóm đã xây dựng

**Hệ thống tổng quan:**  
Nhóm đã xây dựng một pipeline Supervisor-Worker, tách riêng phần điều phối từ phần xử lý nghiệp vụ. `graph.py` chịu trách nhiệm đọc `task`, xác định `supervisor_route`, `route_reason`, `needs_tool` và `risk_high`. Dựa trên quyết định này, request sẽ đi vào một trong hai worker chính: `retrieval_worker` hoặc `policy_tool_worker`, rồi kết thúc bằng `synthesis_worker`.

**Routing logic cốt lõi:**  
Supervisor dùng rule-based routing dựa trên từ khóa và tín hiệu rủi ro. Các câu hỏi chứa `refund`, `policy`, `cấp quyền`, `access` sẽ vào `policy_tool_worker`; câu chứa `P1`, `escalation`, `ticket`, `SLA` sẽ ưu tiên vào `retrieval_worker`; mã lỗi nghiêm trọng như `ERR-` kết hợp `risk_high` sẽ kích hoạt nhánh `human_review` placeholder.

**MCP tools đã tích hợp:**  
- `search_kb`: được gọi từ `policy_tool_worker` khi cần tìm thêm evidence.  
- `get_ticket_info`: được gọi trên yêu cầu ticket/incident trong trace gq09.  
- `check_access_permission`: được gọi khi task chứa yêu cầu cấp quyền khẩn cấp.

**Ví dụ trace MCP:**  
Trace `gq09` cho thấy `policy_tool_worker` gọi lần lượt `search_kb`, `check_access_permission`, và `get_ticket_info`, rồi synthesize trả final answer với sources `access_control_sop.txt`, `sla_p1_2026.txt`, `policy_refund_v4.txt`.

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:**  
Chọn kiến trúc Supervisor-Worker với routing rõ ràng và MCP integration, thay vì giữ pipeline monolithic như Day 08.

**Bối cảnh vấn đề:**  
Day 08 xử lý bằng một pipeline RAG đơn lẻ, nên khó xác định lỗi khi kết quả sai; phần retrieval, policy và synthesis bị trộn chung. Day 09 cần trace visibility và khả năng mở rộng worker riêng biệt.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|------------|
| Single-agent RAG (Day 08) | Triển khai nhanh, ít thành phần | Khó debug, khó mở rộng tool, route reason không rõ |
| Supervisor-Worker với rule-based router | Có route_reason, dễ đo lường, dễ mở rộng worker/MCP | Cần thiết kế interface giữa worker, có overhead routing |
| LLM-based router | linh hoạt với ngôn ngữ, học được nhiều biểu đạt | khó kiểm soát, cần thêm chi phí API và còn thiếu trace rõ ràng |

**Phương án đã chọn và lý do:**  
Nhóm chọn Supervisor-Worker vì mục tiêu chính của Day 09 là “trace & observability”. Kiến trúc này cho phép kiểm tra độc lập từng worker, giúp chúng tôi dễ phát hiện khi `policy_tool_worker` gặp lỗi MCP hoặc khi retrieval trả nguồn `unknown` do fallback embedding. Thêm nữa, triết lý này phù hợp với yêu cầu mở rộng capability qua MCP.

**Bằng chứng từ trace/code:**  
```
[supervisor] route=policy_tool_worker needs_tool=True risk_high=True reason=access-control signal detected | incident/SLA context also detected | MCP lookup enabled for policy worker | risk_high flagged
[policy_tool_worker] called MCP search_kb
[policy_tool_worker] called MCP check_access_permission
[policy_tool_worker] called MCP get_ticket_info
```
Trace `gq09` đã cho thấy logic router và worker flow rõ ràng.

---

## 3. Kết quả grading questions

**Tổng điểm raw ước tính:** 78 / 96  
(Ước tính từ độ chính xác trace, confidence, và số câu success; chưa có scorecard chính thức.)

**Câu pipeline xử lý tốt nhất:**
- ID: `gq09` — Lý do tốt: route đúng vào `policy_tool_worker`, trace ghi rõ các bước MCP, và synthesis kết hợp được cả ticket info lẫn access policy với confidence `0.76`.

**Câu pipeline fail hoặc partial:**
- ID: `gq07` — Fail về nguồn evidence: routing đúng vào `retrieval_worker`, nhưng `retrieved_sources` trả về `unknown` do môi trường thiếu ChromaDB/`sentence-transformers`.  
  Root cause: thiếu dependency retrieval nên pipeline phải dùng fallback embeddings, làm source citation kém tin cậy.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?  
Mặc dù gq07 không thực sự abstain, chúng tôi phát hiện câu này bị ảnh hưởng bởi fallback retrieval. Do đó, đội Trace & Docs đã gán `unknown` source và ghi nhận đây là điểm yếu của deployment hiện tại, không phải lỗi routing.

**Câu gq09 (multi-hop khó nhất):**  
Trace ghi đúng 2 workers: `policy_tool_worker` và `synthesis_worker`. `policy_tool_worker` gọi thêm ba MCP tools, rồi `synthesis_worker` trả answer với sources `access_control_sop.txt`, `sla_p1_2026.txt`, `policy_refund_v4.txt`.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được

**Metric thay đổi rõ nhất:**  
Routing visibility và trace coverage. Day 09 có thể thống kê rõ `supervisor_route` và `route_reason` trong mỗi trace, còn Day 08 chỉ có output answer. Điều này giúp phân biệt nhanh failure mode là `retrieval`, `policy`, hay `synthesis`.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**  
Chúng tôi bất ngờ rằng việc tách worker không chỉ giúp debug, mà còn làm lộ nhanh hơn các dependency thiếu: nhiều câu policy route đúng nhưng lại fail khi `mcp_server` hoặc embedding không đủ. Việc này cho thấy multi-agent không chỉ là “modular hơn”, mà còn giúp chúng tôi xác định đúng chỗ cần fix.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**  
Multi-agent làm tăng latency vì thêm bước supervisor và MCP calls. Kết quả grading hiện tại cho thấy latency trung bình khoảng `4479ms` trên 76 trace, cao hơn so với một pipeline đơn giản. Nhánh policy đặc biệt chậm hơn do `search_kb` và `get_ticket_info` được gọi liên tiếp.

---

## 5. Phân công và đánh giá nhóm

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
 Quân| Xây dựng `graph.py` và supervisor routing | 1 |
| Dương| Triển khai `retrieval_worker`, `policy_tool_worker` và ChromaDB integration | 2 |
| Hiệp | Triển khai `synthesis_worker`, business rule logic và prompt grounding | 2 |
| Chung | Implement MCP server, `search_kb`, `get_ticket_info`, `check_access_permission` | 3 |
| Đạt | Viết `eval_report` và `group_report` | 4 |
| Đức Anh | Trace & Docs Owner| 4

**Điều nhóm làm tốt:**  
Nhóm phối hợp rõ ràng theo vai trò. Supervisor và Worker Owner đã hoàn thiện flow `task -> route -> worker -> synthesis`, MCP Owner đã tích hợp success `search_kb`/`get_ticket_info`, và Trace Owner đã xác định các chỉ số cần đo trong `eval_trace.py`.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**  
Quá trình setup dependency chưa đồng bộ, dẫn đến môi trường một số thành viên thiếu `chromadb`/`sentence-transformers` và `google.generativeai` deprecation. Điều này khiến một số câu chạy fallback thay vì truy cập evidence thật.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**  
Sẽ phân công rõ ràng hơn phần môi trường dev/test ngay từ Sprint 2, đồng thời chuẩn hóa `requirements.txt` và cách build ChromaDB trước khi chạy grading.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

1. Hoàn thiện tích hợp ChromaDB/`sentence-transformers` để loại bỏ fallback `unknown` source và cải thiện retrieval quality.  
2. Triển khai bộ phân loại router LLM hoặc keyword+score hybird cho supervisor để giảm false positive route policy/retrieval.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
