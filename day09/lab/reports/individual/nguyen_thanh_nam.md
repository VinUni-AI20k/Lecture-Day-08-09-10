# Khảo sát Phase 4b — Problem Statement 6-field
> Bài toán: Biên bản họp nhóm + tự động phân bổ Action Items

---

## Field 1 — Actor / Operator
**Ai là người đang phải làm việc này hằng ngày?**
Mô tả rõ: vai trò, bối cảnh, tần suất gặp bài toán.

> Trả lời:  
Thư ký cuộc họp và quản lý dự án là hai vai trò chính xử lý việc này hằng ngày. Trong bối cảnh team sản phẩm/tech họp sprint planning, daily sync và retrospective, họ phải ghi biên bản, chốt quyết định, tách action items và gán owner sau mỗi buổi họp. Tần suất trung bình 3-5 buổi/tuần cho mỗi team, cao điểm có thể 1-2 buổi/ngày khi gần deadline.

---

## Field 2 — Current Workflow
**Hiện tại họ xử lý qua những bước nào? Dùng tool gì?**
Tóm tắt ngắn gọn (đã có workflow diagram rồi, chỉ cần viết lại bằng text).

> Trả lời:  
1) Họp trên Google Meet/Zoom và ghi chép rời rạc trên Google Docs/Notion.  
2) Sau họp, thư ký nghe lại recording hoặc đọc note để viết lại biên bản hoàn chỉnh.  
3) Từ biên bản, quản lý dự án lọc các đầu việc, gán owner và deadline thủ công.  
4) Action items được copy sang Jira/Trello/Asana, rồi nhắn lại qua Slack/Zalo để xác nhận.  
5) 24-48 giờ sau, PM phải follow-up vì có task thiếu owner, thiếu deadline hoặc không ai xác nhận.

---

## Field 3 — Bottleneck
**Bước nào chậm, lỗi, không nhất quán, hoặc tốn thời gian nhất?**
Chỉ rõ 1 bước cụ thể — không viết chung chung "cả flow chậm".

> Trả lời:  
Bottleneck lớn nhất là bước chuyển từ biên bản thô sang danh sách action items có cấu trúc (task, owner, deadline, priority). Bước này hiện làm thủ công nên dễ bỏ sót quyết định trong lúc họp nhanh, và tốn nhiều thời gian do phải đọc lại toàn bộ nội dung trước khi phân bổ.

---

## Field 4 — Impact
**Hậu quả của bottleneck đó là gì?**
Cố gắng có con số: mất bao nhiêu phút/lần, bao nhiêu lần/tuần,
tỉ lệ sai sót, hay hậu quả gì xảy ra khi bị miss?

> Trả lời:  
Mỗi buổi họp mất thêm khoảng 30-45 phút để xử lý hậu kỳ biên bản + phân task. Với tần suất 4 buổi/tuần, team mất khoảng 120-180 phút/tuần chỉ cho thao tác tổng hợp. Tỉ lệ action items thiếu thông tin (thiếu owner hoặc deadline) ước tính 20-30%, khiến PM phải nhắc lại nhiều lần. Khi task bị miss, tiến độ sprint trễ 0.5-1 ngày ở các đầu việc phụ thuộc nhau.

---

## Field 5 — Success Metric
**Khi nào được coi là thành công? Ngưỡng cụ thể là gì?**
Phải có ít nhất 2 metric, mỗi cái phải có số/ngưỡng rõ ràng.

> Metric 1:  
Biên bản chuẩn hóa + danh sách action items được tạo và gửi bản nháp trong vòng <= 5 phút sau khi kết thúc họp.

> Metric 2:  
Tỉ lệ action items thiếu owner/deadline giảm từ mức 20-30% xuống < 5% trong 4 tuần liên tiếp.

---

## Field 6 — Operational Boundary
**AI được phép làm gì? Không được phép làm gì?**
**Điểm nào cần người review/duyệt trước khi gửi đi?**

> AI được phép:  
- Tóm tắt nội dung họp theo cấu trúc (objective, decision, blocker).  
- Trích xuất action items, đề xuất owner tiềm năng theo ngữ cảnh trao đổi.  
- Gợi ý deadline dựa trên mức ưu tiên và mốc sprint.

> AI KHÔNG được phép:  
- Tự động gửi email/tin nhắn chính thức cho toàn team khi chưa được duyệt.  
- Tự tạo/chỉnh sửa ticket trên Jira/Trello ở trạng thái final mà không có xác nhận của PM.  
- Tự thay đổi owner/deadline của các task đang in-progress.

> Người phải duyệt ở bước nào:  
PM hoặc meeting leader bắt buộc duyệt ở bước cuối trước khi publish: xác nhận danh sách action items, owner, deadline và mức ưu tiên; chỉ sau khi approve mới được đồng bộ sang công cụ quản lý công việc và kênh thông báo nhóm.
# Khảo sát Phase 4b — Problem Statement 6-field
> Bài toán: Biên bản họp nhóm + tự động phân bổ Action Items

---

## Field 1 — Actor / Operator
**Ai là người đang phải làm việc này hằng ngày?**
Mô tả rõ: vai trò, bối cảnh, tần suất gặp bài toán.

> Trả lời:  
Thư ký cuộc họp và quản lý dự án là hai vai trò chính xử lý việc này hằng ngày. Trong bối cảnh team sản phẩm/tech họp sprint planning, daily sync và retrospective, họ phải ghi biên bản, chốt quyết định, tách action items và gán owner sau mỗi buổi họp. Tần suất trung bình 3-5 buổi/tuần cho mỗi team, cao điểm có thể 1-2 buổi/ngày khi gần deadline.

---

## Field 2 — Current Workflow
**Hiện tại họ xử lý qua những bước nào? Dùng tool gì?**
Tóm tắt ngắn gọn (đã có workflow diagram rồi, chỉ cần viết lại bằng text).

> Trả lời:  
1) Họp trên Google Meet/Zoom và ghi chép rời rạc trên Google Docs/Notion.  
2) Sau họp, thư ký nghe lại recording hoặc đọc note để viết lại biên bản hoàn chỉnh.  
3) Từ biên bản, quản lý dự án lọc các đầu việc, gán owner và deadline thủ công.  
4) Action items được copy sang Jira/Trello/Asana, rồi nhắn lại qua Slack/Zalo để xác nhận.  
5) 24-48 giờ sau, PM phải follow-up vì có task thiếu owner, thiếu deadline hoặc không ai xác nhận.

---

## Field 3 — Bottleneck
**Bước nào chậm, lỗi, không nhất quán, hoặc tốn thời gian nhất?**
Chỉ rõ 1 bước cụ thể — không viết chung chung "cả flow chậm".

> Trả lời:  
Bottleneck lớn nhất là bước chuyển từ biên bản thô sang danh sách action items có cấu trúc (task, owner, deadline, priority). Bước này hiện làm thủ công nên dễ bỏ sót quyết định trong lúc họp nhanh, và tốn nhiều thời gian do phải đọc lại toàn bộ nội dung trước khi phân bổ.

---

## Field 4 — Impact
**Hậu quả của bottleneck đó là gì?**
Cố gắng có con số: mất bao nhiêu phút/lần, bao nhiêu lần/tuần,
tỉ lệ sai sót, hay hậu quả gì xảy ra khi bị miss?

> Trả lời:  
Mỗi buổi họp mất thêm khoảng 30-45 phút để xử lý hậu kỳ biên bản + phân task. Với tần suất 4 buổi/tuần, team mất khoảng 120-180 phút/tuần chỉ cho thao tác tổng hợp. Tỉ lệ action items thiếu thông tin (thiếu owner hoặc deadline) ước tính 20-30%, khiến PM phải nhắc lại nhiều lần. Khi task bị miss, tiến độ sprint trễ 0.5-1 ngày ở các đầu việc phụ thuộc nhau.

---

## Field 5 — Success Metric
**Khi nào được coi là thành công? Ngưỡng cụ thể là gì?**
Phải có ít nhất 2 metric, mỗi cái phải có số/ngưỡng rõ ràng.

> Metric 1:  
Biên bản chuẩn hóa + danh sách action items được tạo và gửi bản nháp trong vòng <= 5 phút sau khi kết thúc họp.

> Metric 2:  
Tỉ lệ action items thiếu owner/deadline giảm từ mức 20-30% xuống < 5% trong 4 tuần liên tiếp.

---

## Field 6 — Operational Boundary
**AI được phép làm gì? Không được phép làm gì?**
**Điểm nào cần người review/duyệt trước khi gửi đi?**

> AI được phép:  
- Tóm tắt nội dung họp theo cấu trúc (objective, decision, blocker).  
- Trích xuất action items, đề xuất owner tiềm năng theo ngữ cảnh trao đổi.  
- Gợi ý deadline dựa trên mức ưu tiên và mốc sprint.

> AI KHÔNG được phép:  
- Tự động gửi email/tin nhắn chính thức cho toàn team khi chưa được duyệt.  
- Tự tạo/chỉnh sửa ticket trên Jira/Trello ở trạng thái final mà không có xác nhận của PM.  
- Tự thay đổi owner/deadline của các task đang in-progress.

> Người phải duyệt ở bước nào:  
PM hoặc meeting leader bắt buộc duyệt ở bước cuối trước khi publish: xác nhận danh sách action items, owner, deadline và mức ưu tiên; chỉ sau khi approve mới được đồng bộ sang công cụ quản lý công việc và kênh thông báo nhóm.
