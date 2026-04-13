# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Thành Nam  
**Vai trò trong nhóm:** Documentation Support (docs-only)  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500-800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab Day 08, tôi tập trung vào phần tài liệu để hỗ trợ nhóm chạy pipeline ổn định và nộp bài rõ ràng. Cụ thể, tôi cập nhật mục Quick Start theo dạng copy/paste cho cả Windows PowerShell và macOS/Linux, giúp thành viên mới có thể chạy từ bước tạo môi trường đến truy vấn RAG mà không phải đoán thứ tự lệnh. Tiếp theo, tôi bổ sung phần lỗi thường gặp, tập trung vào ba tình huống thực tế: API chưa chạy, trùng port và thiếu biến môi trường trong `.env`. Tôi cũng chuẩn hóa heading/bullet để README dễ quét nhanh khi debug theo nhóm. Ngoài README, tôi thêm đoạn giải thích ngắn trong `docs/architecture.md` để trả lời câu hỏi “vì sao tuning tốt hơn baseline” bằng ngôn ngữ dễ hiểu, dùng được trực tiếp trong phần report.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn rằng chất lượng câu trả lời RAG phụ thuộc rất mạnh vào retrieval, không chỉ vào model sinh văn bản. Trước đây tôi thường nghĩ mô hình càng mạnh thì kết quả càng đúng, nhưng khi làm tài liệu và đọc flow thực tế, tôi thấy nếu context đưa vào sai hoặc nhiễu thì model vẫn có thể trả lời thiếu chính xác. Tôi cũng hiểu thêm sự khác nhau giữa baseline dense retrieval và biến thể hybrid + rerank: hybrid giúp mở rộng khả năng tìm bằng cả ngữ nghĩa lẫn từ khóa, còn rerank giúp chọn lại các chunk thực sự liên quan trước khi gửi vào prompt. Nói ngắn gọn, tuning tốt hơn không phải vì “LLM thông minh hơn”, mà vì pipeline đưa đúng ngữ cảnh hơn.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến tôi ngạc nhiên là nhiều lỗi “nhỏ” trong phần vận hành lại ảnh hưởng rất lớn tới trải nghiệm demo. Ví dụ, chỉ cần API chưa chạy hoặc sai cổng, giao diện sẽ báo lỗi khiến người dùng tưởng rằng mô hình sai, trong khi vấn đề thật sự nằm ở kết nối service. Khó khăn lớn nhất của tôi là viết tài liệu sao cho vừa ngắn gọn vừa đủ chi tiết để người khác xử lý lỗi nhanh mà không bị quá tải thông tin. Ban đầu tôi viết theo kiểu mô tả dài, nhưng sau khi test lại tôi nhận ra checklist dạng dấu hiệu -> cách xử lý -> lệnh cụ thể sẽ hiệu quả hơn. Từ đó, tôi chỉnh lại cấu trúc thành các mục ngắn để phù hợp bối cảnh làm lab theo thời gian giới hạn.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** “SLA xử lý ticket P1 là bao lâu?”

**Phân tích:**

Với câu hỏi này, baseline thường trả lời được ý chính nhưng đôi lúc thiếu bối cảnh hoặc trích dẫn chưa sát đoạn có thông tin SLA quan trọng nhất. Khi retrieval chỉ dựa trên dense similarity, hệ thống có thể lấy các chunk gần nghĩa nhưng không phải chunk có thông tin định lượng rõ ràng. Điều này làm điểm faithfulness và relevance có thể dao động giữa các lần chạy, đặc biệt nếu ngữ cảnh đầu vào chứa thêm nhiễu từ FAQ liên quan.

Ở biến thể tuning (hybrid + rerank), khả năng lấy đúng chunk chứa điều khoản SLA ổn định hơn vì hybrid tận dụng thêm tín hiệu từ khóa (“P1”, “SLA”) và rerank loại bớt chunk lan man trước khi đưa vào prompt. Nhờ vậy, phần trả lời ngắn gọn hơn, bám đúng nguồn hơn và citation nhất quán hơn. Theo góc nhìn quy trình, lỗi cốt lõi của baseline nằm nhiều ở retrieval selection hơn là generation. Model không hẳn “trả lời kém”, mà nó chỉ phản hồi theo ngữ cảnh được cung cấp; khi context tốt lên, chất lượng câu trả lời cũng tăng tương ứng.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ bổ sung một “runbook 1 trang” cho cả nhóm theo dạng quyết định nhanh: lỗi nào kiểm tra ở API, lỗi nào kiểm tra ở retrieval, lỗi nào kiểm tra ở generation. Tôi cũng muốn thêm bảng mapping giữa triệu chứng thường gặp và lệnh kiểm tra tương ứng để giảm thời gian debug trong lúc demo. Mục tiêu là giúp mọi thành viên, kể cả không phụ trách code chính, vẫn có thể hỗ trợ vận hành và khoanh vùng lỗi nhanh.

