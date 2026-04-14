# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lâm Hoàng Hải
**Vai trò trong nhóm:**  Retrieval Owner
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Trong lab này, tôi phụ trách vai trò Retrieval Owner nên tập trung vào hai phần chính: chunking và retrieval tuning. Ở Sprint 1, tôi hoàn thiện preprocess để trích xuất metadata thống nhất cho toàn bộ tài liệu (doc_title, source, department, effective_date, access, section, channels, emails, hotlines, availability_hours). Sau đó tôi triển khai chunking theo cấu trúc section và theo cặp Q/A cho FAQ. Tôi cũng điều chỉnh logic để loại các section liên hệ/kênh hỗ trợ khỏi chunk nhằm giảm nhiễu retrieval, vì thông tin đó đã được lưu trong metadata. Ở phần retrieval, tôi triển khai hybrid retrieval theo hướng kết hợp dense + sparse bằng rank fusion và bổ sung phương án rerank bằng cross-encoder.

---

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Sau lab này, tôi hiểu được cách chunking không chỉ là đơn thuần chia thành các đoạn xử lý, mà nó còn tác động trực tiếp đến kết quả cuối cùng. Cụ thể, ở bước chunking, tôi quyết định chua tách FAQ theo cặp QA để câu trả lời có thể trả lời được cụ thể, thay vì bị mix context với những câu khác. Đồng thời, tôi cũng học được cách phân biệt những đoạn cần bỏ, những từ có thể đưa được vào metadata.

---

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều làm tôi gặp khó khăn nhất là cách xử lý metadata cho phần liên hệ. Ban đầu tôi định tách phần này thành một chunk riêng, tuy nhiên nếu để lẻ thì chunk liên hệ rất dễ được retrieve nhầm cho các câu hỏi nghiệp vụ, làm context bị nhiễu. Tuy nhiên, nếu bỏ hẳn đi thì ngộ nhỡ có người hỏi những thông tin liên hệ thì lại không truy vấn được. Cuối cùng, tôi giữ thông tin liên hệ ở metadata (channels, emails, hotlines, availability_hours) và loại section liên hệ khỏi chunk retrieval chính. Tuy vậy, vẫn còn một nhược điểm, đó là một số tài liệu còn tồn tại những thông tin phụ khác nên không thống nhất được metadata.

---

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q06: "Lúc 2 giờ sáng xảy ra sự cố P1, on-call engineer cần cấp quyền tạm thời cho một engineer xử lý incident. Quy trình cụ thể như thế nào và quyền này tồn tại bao lâu?"

**Phân tích:** Đây là câu hỏi mà mentor đánh giá là khó nhất, tuy nhiên cả baseline và variant đều cho kết quả gần như tương đương. Cả hai đều bám sát Access Control SOP: quyền tạm thời do On-call IT Admin cấp sau khi có phê duyệt bằng lời từ Tech Lead, thời hạn tối đa 24 giờ, sau đó phải có ticket chính thức hoặc quyền bị thu hồi tự động, đồng thời mọi quyền tạm thời phải được ghi log vào Security Audit. Vì evidence của câu này tập trung và khá rõ trong một section, baseline đã đủ mạnh nên hybrid/rerank chưa tạo khác biệt đáng kể về điểm số. Điểm chưa đạt tuyệt đối nằm ở Completeness (4/5) do cả hai câu trả lời chưa nhắc đến chi tiết liên hệ on-call qua hotline ext. 9999 từ tài liệu SLA P1. Tuy vậy, đây là thiếu sót nhỏ và hợp lý, vì câu hỏi không yêu cầu trực tiếp kênh liên hệ mà tập trung vào quy trình cấp quyền tạm thời và thời gian hiệu lực của quyền.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> Nếu có thêm thời gian, tôi sẽ triển khai một nhánh trả lời theo metadata cho nhóm câu hỏi liên hệ (ví dụ: liên hệ ai, gọi số nào, email nào, giờ hỗ trợ). Lý do là trong thiết kế hiện tại, một số nội dung liên hệ đã được đưa vào metadata và oại khỏi chunk text để tránh nhiễu retrieval, nên nếu không có phần này thì model có thể thiếu thông tin khi người dùng hỏi đúng intent này.

---

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
