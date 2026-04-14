# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** C401-E3  
**Ngày nộp:** 14/04/2026  
**Repo:** https://github.com/jot2003/Lab8-Lab9-Lab10_C401_E3

## Thành viên và vai trò

| Tên | Vai trò |
|-----|---------|
| Đặng Đình Tú Anh | Supervisor Owner |
| Phạm Quốc Dũng | Retrieval + MCP Owner |
| Quách Gia Được | Policy Worker Owner |
| Hoàng Kim Trí Thành | Synthesis + Eval Owner |
| Nguyễn Thành Nam | Trace + Docs Owner |

---

## 1. Kiến trúc nhóm đã xây dựng

Nhóm triển khai kiến trúc Supervisor-Worker cho bài toán trợ lý nội bộ CS + IT. Hệ thống được chia thành các thành phần rõ vai trò: `graph.py` (supervisor), `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py`, và `mcp_server.py`.

Supervisor chịu trách nhiệm route câu hỏi dựa trên tín hiệu task, ghi `supervisor_route` và `route_reason` vào state để dễ kiểm tra. Retrieval worker lấy evidence từ ChromaDB collection `day09_docs`. Policy worker xử lý các case policy/access và gọi MCP tools (`search_kb`, `get_ticket_info`, `check_access_permission`). Synthesis worker tổng hợp câu trả lời grounded từ context đã có, trả về `answer`, `sources`, `confidence`.

Theo `artifacts/eval_report.json`, hệ thống đã đi đủ 3 nhánh route: retrieval 53%, policy 28%, multi-hop 18%, và có MCP usage khoảng 46%. Điều này cho thấy pipeline thực sự vận hành theo đúng mô hình Day 09, không chỉ mô phỏng.

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:** dùng rule-based routing có thứ tự ưu tiên (multi-hop -> SLA/retrieval -> policy -> fallback) thay vì router LLM cho Sprint chính.

**Bối cảnh vấn đề:** với câu hỏi phức hợp (vừa incident/SLA vừa access), router đơn giản dễ chọn sai một nhánh, làm mất một phần thông tin. Nếu dùng LLM router, chi phí và độ trễ tăng, đồng thời khó tái lập kết quả giữa các lần grading.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Rule-based routing | Nhanh, deterministic, trace rõ | Phải bảo trì keyword/rule |
| LLM router | Linh hoạt theo ngữ nghĩa | Chậm hơn, khó debug và khó tái lập |

**Phương án đã chọn và lý do:** nhóm chọn rule-based để đáp ứng tiêu chí Day 09 về quan sát route và khả năng debug từng bước. Quy tắc ưu tiên multi-hop giúp giảm lỗi thiếu ý ở câu cross-doc.

**Bằng chứng từ trace/code:**  
- `artifacts/eval_report.json` cho thấy cả 3 route xuất hiện thực tế.  
- `artifacts/grading_run.jsonl` có `supervisor_route` và `route_reason` cho từng câu.  
- Các câu dạng emergency access + P1 đi qua chain nhiều worker.

---

## 3. Kết quả grading questions

**Tổng điểm raw ước tính:** 92-94 / 96 (ước tính nội bộ theo output hiện tại).

**Câu pipeline xử lý tốt nhất:**  
- `gq07`: abstain chuẩn, không bịa penalty SLA khi tài liệu không có dữ liệu.  
- `gq05`, `gq06`: trả lời đầy đủ quy trình access/emergency, có evidence từ worker chain.

**Câu còn rủi ro partial:**  
- `gq08`: đôi lúc chưa phân biệt đủ 2 ngữ cảnh cùng chứa mốc "3 ngày" (nghỉ phép năm vs nghỉ ốm).

**Đánh giá gq09 (multi-hop):**  
Trace thể hiện worker chain phù hợp, câu trả lời đã có các chi tiết chính (chu kỳ đổi mật khẩu, nhắc trước hạn, kênh xử lý).

---

## 4. So sánh Day 08 vs Day 09

Theo `artifacts/eval_report.json`, Day 09 có lợi thế rõ ở khả năng quan sát pipeline: từng run ghi `route_reason`, `workers_called`, `mcp_tools_used`. Day 08 chủ yếu là luồng single-agent nên khi sai khó xác định lỗi thuộc retrieval hay synthesis.

Day 08 baseline có projected khoảng 25.41/30 (từ `day08/lab/results/grading_auto.json`). Day 09 hiện cho thấy chất lượng tổng thể tốt hơn ở các câu policy/multi-hop và khả năng debug cao hơn. Đổi lại, độ trễ trung bình tăng do thêm bước điều phối và MCP.

Trường hợp multi-agent chưa tối ưu là các câu disambiguation cùng số liệu (như gq08), nơi retrieval/synthesis cần tinh chỉnh thêm để ổn định Full ở mọi run.

---

## 5. Phân công và đánh giá nhóm

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Tú Anh | `graph.py`, routing, state contract | 1 |
| Quốc Dũng | `retrieval.py`, `mcp_server.py` | 2-3 |
| Gia Được | `policy_tool.py`, policy exception flow | 2-3 |
| Trí Thành | `synthesis.py`, `eval_trace.py`, final eval loop | 2-4 |
| Thành Nam | docs, tổng hợp trace/report | 4 |

**Điểm nhóm làm tốt:** tách owner theo file rõ ràng, merge theo đợt, có retest sau tích hợp.  
**Điểm chưa tốt:** có lúc sync nhiều remote cùng lúc khiến theo dõi commit khó hơn.  
**Nếu làm lại:** chốt sớm một integration branch duy nhất cho Day 09 để giảm nhiễu merge.

---

## 6. Nếu có thêm 1 ngày

Nhóm sẽ làm hai việc:  
1) thêm auto-grader theo `grading_criteria` để tính raw score nhất quán giữa các lần chạy;  
2) tăng disambiguation cho câu HR có cùng mốc thời gian (đặc biệt gq08) bằng rerank theo section metadata.
