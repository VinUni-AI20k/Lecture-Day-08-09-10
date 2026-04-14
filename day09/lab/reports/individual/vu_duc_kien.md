# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** member_2  
**Vai trò trong nhóm:** Policy/MCP Owner  
**Ngày nộp:** 2026-04-14

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong lab này, tôi phụ trách lớp policy và tích hợp MCP. Cụ thể là `workers/policy_tool.py`, `mcp_server.py`, `mcp_mock_server.py`, và file cấu hình `mcp_config.json`. Tôi làm phần policy analysis dựa trên rule nội bộ, đồng thời bảo đảm worker có thể gọi tool đúng cách qua HTTP hoặc fallback in-process. Tôi cũng xử lý các rule an toàn để không vô tình tạo ticket hay thực hiện side effect khi không được phép. Phần tôi làm nối trực tiếp với retrieval ở đầu vào và synthesis ở đầu ra: retrieval cung cấp evidence, policy tool quyết định policy có áp dụng không và có cần tool gọi thêm không, còn synthesis dùng kết quả đó để viết câu trả lời cuối. Nói đơn giản, tôi giữ cho hệ thống vừa “biết hỏi tool”, vừa “biết không hỏi tool khi chưa cần”.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** tôi tách rõ real HTTP MCP server với mock/in-process fallback, và chỉ gọi `get_ticket_info` khi task có ticket id rõ ràng.

Tôi cân nhắc giữa việc gọi MCP cho hầu hết query policy, hoặc chỉ gọi khi thực sự cần. Tôi chọn phương án thứ hai vì latency của Day09 không nên bị đội lên bởi các round-trip không cần thiết. Với query access-intent, local retrieval đã đủ để đọc SOP; chỉ khi câu hỏi có ticket id thật như `IT-9847` hay `P1-LATEST` thì mới cần `get_ticket_info`. Ngoài ra, tôi tách `mock-only`, `hybrid` và `http` để team có thể demo dễ dàng mà không phụ thuộc mạng. Trade-off là phải viết thêm logic phân nhánh, nhưng đổi lại hệ thống rõ ràng hơn, dễ debug hơn, và đặc biệt là an toàn hơn vì `create_ticket` bị chặn mặc định. Đây cũng là lý do `q13` và `q15` cuối cùng vẫn đúng route nhưng chạy nhanh hơn sau pass latency.

**Bằng chứng từ code:**

- `_call_mcp_tool()` có fast path cho `mock-only`
- `TICKET_ID_PATTERN` chỉ nhận ticket id rõ ràng
- `mcp_config.json` khai báo guardrail `allowSideEffects=false`

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** ở giai đoạn đầu, worker policy gọi tool hơi “tham”, dẫn tới một số query bị hỏi MCP dù chưa cần thiết, đặc biệt khi task chỉ cần đọc policy sẵn có.

**Symptom (pipeline làm gì sai?):** latency của policy path cao hơn mức cần thiết. Các query access hoặc multi-hop có thể đi qua HTTP rồi mới fallback, làm thời gian phản hồi bị phình ra. Một số tình huống còn gây rối vì task chứa chữ “ticket” nhưng không có ticket id rõ ràng, khiến logic lookup bị kích hoạt sai thời điểm.

**Root cause:** rule chọn tool còn thô, chưa phân biệt giữa intent thật sự cần ticket lookup với intent chỉ nói chung chung về incident. Ngoài ra, mode parsing của `MCP_SERVER_MODE` cũng cần robust hơn vì `.env` có thể có inline comment.

**Cách sửa:** tôi làm ba việc: (1) thêm fast path bỏ HTTP trong mock-only, (2) chỉ gọi `get_ticket_info` khi regex bắt được id rõ ràng, (3) chuẩn hóa parse mode để comment không phá config.

**Bằng chứng trước/sau:** latency của các query policy đa nhánh giảm rõ ở run `sprint4_test_latencyopt_20260414` mà không mất route correctness.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

Điểm tôi làm tốt là tôi ưu tiên safety và tính nhất quán của tool calling. MCP là nơi dễ gây lỗi nhất nếu không kiểm soát rõ input, mode và side effect. Tôi cũng làm tốt phần làm cho repo dễ demo vì có cả HTTP server lẫn mock fallback. Điểm tôi chưa tốt là phần mô tả schema và tài liệu tool vẫn còn hơi “kỹ thuật” hơn mức một người mới clone repo mong đợi. Nhóm phụ thuộc vào tôi ở chỗ policy path là cửa ngõ của các case refund/access; nếu MCP sai, toàn bộ trace sẽ bị ảnh hưởng. Tôi phụ thuộc vào member_1 để retrieval trả evidence sạch và member_3 để synthesis viết câu trả lời cuối không bị lệch giọng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ viết thêm các test âm cho side-effect tools, đặc biệt là trường hợp cố tình gọi `create_ticket` khi `allow_side_effects=false`. Ngoài ra, tôi muốn chuẩn hóa luôn output schema của tool call để trace dễ đọc hơn, vì hiện tại trace đã đủ dùng nhưng vẫn có thể làm gọn hơn cho phần demo và grading.
