# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** C401-A2
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
|Đỗ Lê Thành Nhân | Supervisor Owner | Thiết kế Graph & Routing |
| Nguyễn Công Quốc Huy, Trần Quang Long, Nguyễn Anh Tài Worker Owner | Triển khai 3 Workers |
| Hoàng Bá Minh Quang MCP Owner | Triển khai Mock MCP Server |
| Vũ Minh QUân-Trace & Docs Owner | Đánh giá & Báo cáo |

**Ngày nộp:** 2026-04-14
**Repo:** VinUni-AI20k/Lecture-Day-08-09-10

---

## 1. Kiến trúc nhóm đã xây dựng

Hệ thống của chúng tôi sử dụng mô hình logic **Supervisor-Worker** để phân tách các nhiệm vụ tra cứu và xử lý chính sách.

**Hệ thống tổng quan:**
Bao gồm 1 Supervisor chính sử dụng bộ lọc từ khóa chuyên sâu để điều phối yêu cầu giữa 3 Worker chuyên trách: Retrieval (tra cứu), Policy Tool (kiểm tra quy định + gọi MCP), và Synthesis (tổng hợp).

**Routing logic cốt lõi:**
Supervisor sử dụng **Keyword-based routing**. Chúng tôi đã xác định 5 danh mục chính: SLA, Refund, Access, IT FAQ, và rủi ro cao. Mỗi danh mục có bộ từ khóa trọng yếu (như "p1", "it-9847", "flash sale") để quyết định Worker xử lý.

**MCP tools đã tích hợp:**
Chúng tôi đã triển khai Standard MCP với các công cụ:
- `search_kb`: Tra cứu tài liệu nội bộ (ChromaDB).
- `get_ticket_info`: Tra cứu thông tin Jira ticket thời gian thực.
- `check_access_permission`: Kiểm tra quyền truy cập hệ thống.

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:** Sử dụng **Shared State** kết hợp với **Worker Chaining** trong Graph.

**Bối cảnh vấn đề:**
Một câu hỏi về chính sách thường cần cả dữ liệu thô từ Retrieval Worker và logic xử lý từ Policy Worker. Ban đầu chúng tôi định chạy song song (Parallel Agents), nhưng điều này gây lãng phí tài nguyên.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Parallel Agents | Nhanh | Tốn token, lãng phí LLM call |
| Sequential Chaining | Tiết kiệm, logic rõ ràng | Độ trễ cao hơn một chút |

**Phương án đã chọn và lý do:**
Chúng tôi chọn **Sequential Chaining** (Supervisor -> Policy -> Retrieval if needed). Lý do là vì Policy Worker có thể tự quyết định mình cần thêm context gì từ MCP tool trước khi yêu cầu Retrieval. Điều này giúp tối ưu hóa luồng dữ liệu.

**Bằng chứng từ trace/code:**
Trong trace `run_20260414_163351.json`, khi hỏi về ticket, Supervisor chọn `policy_tool_worker`, sau đó worker này gọi `get_ticket_info` thành công.

---

| Metric | Day 08 | Day 09 | Delta |
|--------|--------|--------|-------|
| Multi-hop Accuracy | 40% | 80% | +40% |
| Avg Latency | ~2.5s | ~21.1s | +18.6s |
| Routing Visibility | None | High | N/A |

**Điều nhóm bất ngờ nhất:**
Sự minh bạch trong quá trình debug. Thay vì phải "mò kim đáy bể" trong prompt của Day 08, chúng tôi chỉ cần nhìn vào `route_reason` để biết tại sao hệ thống đi sai hướng. Đặc biệt, việc tích hợp MCP giúp Agent trở nên rất linh hoạt.

---

## 3. Kết quả grading questions

**Tổng điểm raw ước tính:** 96 / 96 (Dựa trên kết quả chạy 12/12 câu grading và 15/15 câu test thành công).

**Câu pipeline xử lý tốt nhất:**
- ID: gq15 — Lý do tốt: Kết hợp được thông tin từ cả `search_kb` (SLA) và Policy check một cách liền mạch.

---

## 5. Phân công và đánh giá nhóm

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| A | Xây dựng Supervisor & Graph | Sprint 1 |
| B | Triển khai Workers & Integration | Sprint 2 |
| C | Setup MCP Server & Tools | Sprint 3 |
| D | Evaluation & Documentation | Sprint 4 |

**Điều nhóm làm tốt:**
- Tích hợp thành công dữ liệu từ Lab 08 vào hệ thống mới mà không làm mất thông tin.
- Xử lý triệt để lỗi Unicode trên môi trường Windows.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

Chúng tôi sẽ triển khai **LLM-based Supervisor** thay cho Keyword-based để xử lý được các câu hỏi có ngữ cảnh phức tạp và ngôn ngữ tự nhiên đa dạng hơn, từ đó giảm sai sót định tuyến xuống 0%.
