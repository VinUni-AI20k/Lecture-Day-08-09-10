# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** C401 - C5  
**Ngày:** 14/04/2026

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | ___ | ___ | ___ | |
| Avg latency (ms) | ___ | ___ | ___ | |
| Abstain rate (%) | ___ | ___ | ___ | % câu trả lời "không đủ thông tin" |
| Multi-hop accuracy | ___ | ___ | ___ | % câu hỏi phức tạp trả lời đúng |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | |
| Debug time (estimate) | 20-30 phút | 5-10 phút | -65% | Thời gian tìm ra một bug |

---

## 2. Phân tích định tính

### 2.1 Câu hỏi đơn giản
Multi-agent không mang lại lợi thế về độ chính xác (accuracy) cho câu hỏi đơn giản nhưng giúp hệ thống minh bạch hơn qua log `route_reason`.

### 2.2 Câu hỏi multi-hop
Đây là điểm mạnh nhất của Multi-agent. Hệ thống có thể bóc tách task phức tạp thành các task đơn giản cho từng worker chuyên biệt (Retrieval vs Policy).

### 2.3 Khả năng từ chối (Abstain)
Hệ thống Multi-agent an toàn hơn cho môi trường doanh nghiệp nhờ cơ chế Policy Worker kiểm soát các điều kiện ngoại lệ trước khi Synthesis trả lời.

---

## 3. Phân tích khả năng Debug (Debuggability)

**Day 08:** Khi AI trả lời sai, phải đọc lại toàn bộ prompt dài và context để đoán model sai ở đâu. Không có vết (trace) chi tiết.
**Day 09:** Chỉ cần đọc file trace, kiểm tra node nào trả về kết quả sai để sửa node đó một cách độc lập.

---

## 4. Khả năng mở rộng (Extensibility)

Kiến trúc Multi-agent có tính modular cực kỳ cao:
- Muốn thêm tính năng mới: Thêm 1 Worker mới.
- Muốn cập nhật luật: Sửa `policy_tool_worker`.
- Muốn đổi model: Chỉ cần sửa trong cấu hình của từng Worker.

---

## 5. Kết luận

- **Ưu điểm:** Tăng tính minh bạch (Observability), dễ bảo trì (Modularity), và kiểm soát rủi ro tốt hơn (Policy Enforcement).
- **Nhược điểm:** Tăng độ trễ (Latency) và chi phí vận hành (API tokens).
- **Khuyến nghị:** Nên dùng Multi-agent cho hệ thống Enterprise yêu cầu sự chính xác và kiểm soát cao. Dùng Single Agent cho các ứng dụng nhỏ, yêu cầu tốc độ phản hồi tức thì.
