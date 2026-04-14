# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** member_4  
**Vai trò trong nhóm:** UI/UX + Demo + Setup Owner  
**Ngày nộp:** 2026-04-14

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong buổi lab này, tôi phụ trách phần demo và hoàn thiện trải nghiệm clone-and-run cho repo. Các file tôi quan tâm nhất là `README.md`, `.env.example`, `requirements.txt`, `docs/pitch_guide.md`, cùng các phần giao diện `static/` và `templates/` để khi pitch thì có một đường demo rõ ràng, không phải mở mã nguồn rồi đoán. Tôi tập trung làm cho người mới clone repo có thể hiểu ngay cần cài gì, điền biến môi trường nào, chạy file nào trước, và demo theo thứ tự nào. Phần này nghe có vẻ “bề mặt”, nhưng thực ra rất quan trọng vì nếu setup rối thì dù backend tốt đến đâu team cũng dễ bị mất nhịp khi pitch hoặc khi người khác muốn tái tạo kết quả. Tôi xem đây là lớp đóng gói cuối cùng để backend có thể trình diễn mượt mà.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** tôi giữ UI/UX theo hướng tối giản, ưu tiên demo flow và setup clarity hơn là xây thêm tính năng phức tạp.

Tôi cân nhắc giữa việc làm một dashboard nhiều widget, hay chỉ hoàn thiện một giao diện đủ rõ để show trace, route, và kết quả cuối. Tôi chọn phương án tối giản vì Day09 không cần thắng bằng độ “lòe loẹt”; nó cần thắng bằng khả năng giải thích pipeline. Với nhóm multi-agent, thứ người xem muốn hiểu nhất là: câu hỏi đi qua đâu, vì sao route như vậy, tool nào được gọi, và câu trả lời cuối đến từ evidence nào. Một UI rối sẽ làm mất trọng tâm này. Vì vậy tôi tập trung vào README, pitch guide, `.env.example`, và `requirements.txt` để clone là chạy được, cộng với demo path ngắn gọn. Trade-off là giao diện không có nhiều hiệu ứng, nhưng đổi lại rất chắc cho pitch và cho người khác tái lập môi trường.

**Bằng chứng từ setup docs:**
- `README.md` được cập nhật để khớp với `GROQ_API_KEY`
- `.env.example` được bổ sung đầy đủ biến cần thiết
- `requirements.txt` liệt kê đúng package cần cài

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** tài liệu setup cũ không khớp với runtime thực tế, dễ làm người mới clone hiểu nhầm cách chạy.

**Symptom (pipeline làm gì sai?):** trước khi cập nhật, README vẫn gợi ý người dùng điền `OPENAI_API_KEY` hoặc `GOOGLE_API_KEY`, trong khi synthesis hiện chạy bằng Groq API qua `GROQ_API_KEY`. Điều này khiến setup flow bị lệch giữa tài liệu và code, và rất dễ làm team demo mất thời gian debug một lỗi không thuộc backend.

**Root cause:** file docs đã cũ hơn code. Ngoài ra, `requirements.txt` cũng đang ở dạng comment optional khá lâu, nên người mới không chắc package nào thực sự cần cài để repo chạy được.

**Cách sửa:** tôi đồng bộ lại `.env.example` và `README.md` để phản ánh đúng env hiện tại, đồng thời làm `requirements.txt` gọn hơn, chỉ giữ các dependency thật sự cần cho runtime và test. Tôi cũng chèn hướng dẫn ngắn về MCP mode để người mới biết lúc nào dùng HTTP, lúc nào dùng mock.

**Bằng chứng trước/sau:** sau cập nhật, repo trở nên clone-friendly hơn và hợp với demo flow hơn, đặc biệt với thành viên mới chưa đọc toàn bộ code.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

Điểm mạnh nhất của tôi là biến một repo có thể chạy được thành một repo có thể trình diễn được. Với các lab kiểu này, nếu setup không rõ thì người xem sẽ mất hứng ngay cả khi model chạy đúng. Điểm tôi chưa tốt là tôi không đi sâu vào thuật toán backend, nên đôi khi chỉ nhìn được lớp bề mặt của trải nghiệm demo. Nhóm phụ thuộc vào tôi ở chỗ cuối cùng vẫn cần có một đường chạy rõ ràng để clone repo, điền env, cài dependencies và demo trong vài phút. Tôi phụ thuộc vào member_1, member_2, member_3 và Huy vì mọi thứ UI/UX chỉ có ý nghĩa khi backend đã ổn và trace/report có số liệu thật.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ làm một màn demo ngắn dạng “one-click walkthrough” với các ví dụ câu hỏi được chọn sẵn, kèm nút chạy từng sprint. Tôi cũng muốn thêm phần nhắc lỗi setup phổ biến ngay trong README, ví dụ quên `GROQ_API_KEY` hoặc chạy sai `MCP_SERVER_MODE`, để người mới không phải mò quá lâu.
