# Báo cáo cá nhân - Nguyễn Quế Sơn
**Vai trò:** Documentation Owner

## 1. Đóng góp cụ thể
Trong suốt quá trình triển khai RAG Pipeline cho khối hỗ trợ (CS & IT Helpdesk), nhận thấy vai trò Documentation vô cùng quan trọng để kết nối toàn bộ luồng kỹ thuật của các thành viên, tôi đã thực hiện những công việc sau:
- **Xây dựng tài liệu Kiến trúc (`architecture.md`)**: Thống nhất với Tech Lead về sơ đồ kiến trúc hệ thống (Pipeline diagram bằng dạng Mermaid). Cập nhật các quyết định của nhóm về việc sử dụng `semantic split` để giữ lại chất lượng nội dung tốt nhất thay vì chia string cắt ngang ngữ nghĩa văn bản.
- **Duy trì nhật ký thử nghiệm (`tuning-log.md`)**: Theo sát các quyết định thay đổi config quan trọng trong Sprint 1 & 2 như thiết lập điểm số Threshold `0.35` (chống hallucination), sử dụng model `gpt-4o-mini`. 
- **Tổng hợp báo cáo (`group_report.md`)**: Chủ động khởi tạo báo cáo tổng cho cả nhóm, tạo sẵn các luận điểm chính nhằm giúp mọi người chỉ cần điền kết quả A/B Test vào mà không bị lúng túng trong phút chót.
- **Dựng Prototype Web UI (Thuyết trình)**: Chủ động khởi tạo một backend FastAPI nhỏ phục vụ tĩnh nội dung Giao diện HTML (The Digital Architect) có sẵn của nhóm. Gắn kết logic DOM với API ảo nhằm mục đích minh họa "Trace Panel", giúp người theo dõi dễ dàng hiểu được luồng đi của Hybrid Search và Reranker điểm số.

## 2. Phân tích một câu hỏi Grading (gq07)
**Câu hỏi:** "Nhân viên vi phạm quy trình cấp quyền sẽ bị xử phạt như thế nào?"
- **Phân tích:** Đây là một "Abstain case" quan trọng. Tài liệu `access-control-sop.txt` chỉ quy định về quy trình cấp và thu hồi quyền, hoàn toàn không có mục xử phạt.
- **Kết quả:** Hệ thống đạt kết quả tốt khi trả về câu trả lời: "Tôi không tìm thấy thông tin này trong tài liệu". Điều này chứng minh sự hiệu quả của việc thiết lập **Relevance Threshold = 0.35**. Nếu để threshold quá thấp, hệ thống có thể đã cố gắng trích xuất các đoạn văn bản gần giống (như mục Audit) để "bịa" ra hình thức kỷ luật, gây rủi ro thông tin sai lệch.

## 3. Đánh giá và bài học rút ra
- **Khó khăn:** Quá trình làm Documentation Owner gặp bất lợi khi phải liên tục đồng bộ với tốc độ làm việc của các Developer / Eval Owner. Đôi khi một config thay đổi rất nhỏ ở code lại làm thay đổi số liệu cần ghi chép.
- **Bài học:** Việc làm tài liệu hệ thống (Documentation) nên được tiến hành song song cùng mã nguồn (Docs as Code). Khi một quyết định kỹ thuật được chốt, nó cần phải xuất hiện hoặc để lại Log ở các tài liệu liên quan thay vì để đến cuối ngày mới ghi nhớ và tổng hợp lại.

## 4. Đề xuất cải tiến
- **Tối ưu hóa Recall:** Mặc dù Context Recall đã đạt 0.96, nhưng vẫn có thể cải thiện bằng cách sử dụng **Re-ranking model** mạnh hơn (như Cohere Rerank) thay vì chỉ dựa vào RRF đơn thuần, giúp sắp xếp các đoạn văn bản chồng chéo tốt hơn.
- **Xử lý bảng biểu:** Một số tài liệu như SLA có định dạng bảng chưa được parser xử lý tối ưu. Chuyển đổi sang format Markdown Table hoặc dùng Vision model cho PDF sẽ giúp chatbot hiểu cấu trúc so sánh tốt hơn.
