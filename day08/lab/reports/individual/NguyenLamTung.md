# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Lâm Tùng  
**Mã học viên:** 2A202600173  
**Vai trò trong nhóm:** Retrieval Owner kiêm hỗ trợ Tech Lead  
**Ngày nộp:** 2026-04-13

---

## 1. Tôi đã làm gì trong lab này?

Trong lab này, phần tôi tập trung nhiều nhất là Sprint 1, gồm preprocessing, chunking, metadata và khả năng quan sát dữ liệu sau khi index. Cụ thể, tôi chỉnh luồng index để cho phép truyền tham số từ command line thay vì cố định đường dẫn. Nhờ đó nhóm có thể đổi thư mục tài liệu đầu vào và thư mục lưu vector database linh hoạt theo từng máy. Tôi cũng thêm cơ chế xuất toàn bộ chunk ra file JSONL để kiểm tra chất lượng chunk sau mỗi lần chạy. Mỗi dòng JSONL là một chunk gồm source_file, chunk_id, section, metadata và text nên tiện cho việc trace lỗi retrieval về sau.

Bên cạnh đó, tôi giữ lại phần preview preprocess và chunking ngay trong lúc chạy để nhóm nhìn nhanh metadata và nội dung chunk trước khi embed. Công việc này kết nối trực tiếp với phần của bạn phụ trách retrieval và evaluation vì chất lượng index là nền tảng cho hai sprint sau.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Điều tôi hiểu rõ hơn là chunking không chỉ là cắt theo độ dài, mà là một quyết định ảnh hưởng toàn bộ pipeline RAG. Nếu chunk quá ngắn thì mất ngữ cảnh; nếu chunk quá dài thì retrieval lấy nhầm đoạn và làm câu trả lời thiếu chính xác. Vì vậy cách tách theo section heading rồi mới tách theo paragraph giúp giữ cấu trúc tài liệu tự nhiên tốt hơn cách cắt cứng theo số ký tự.

Tôi cũng hiểu rõ vai trò của metadata trong retrieval. Các trường như source, section, effective_date không chỉ để hiển thị mà còn dùng để lọc, rerank và giải thích answer. Khi đánh giá pipeline, lỗi sai thường không nằm ở model ngay từ đầu mà nằm ở bước index: chunk bị cắt không đúng hoặc metadata thiếu khiến truy hồi sai nguồn.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Khó khăn lớn nhất của tôi không phải ở logic xử lý text mà là lỗi môi trường hệ thống: thiếu thư viện runtime libstdc++.so.6 làm import NumPy thất bại khi khởi tạo ChromaDB. Điều này làm pipeline dừng ở bước build index dù preprocess và chunking đã chạy ổn. Ban đầu tôi nghĩ do lỗi code hoặc do phiên bản package xung đột, nhưng sau khi đọc stack trace thì root cause là dependency cấp hệ điều hành, không phải bug trong hàm chunk.

Điểm tôi rút ra là cần tách hai lớp kiểm tra: kiểm tra logic nội bộ trước (preprocess, chunk preview, metadata), rồi mới kiểm tra phụ thuộc ngoài (vector store, embedding API). Việc xuất chunk ra JSONL giúp giảm rủi ro bị chặn hoàn toàn khi backend chưa sẵn sàng, vì vẫn có artifact để nhóm review chất lượng dữ liệu trung gian.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** SLA xử lý ticket P1 là bao lâu?

Ở baseline kỳ vọng, đây là câu tương đối dễ nếu index đã chứa đúng tài liệu SLA và section liên quan. Nếu retrieval lấy trúng chunk chứa quy định thời gian xử lý P1, generation chỉ cần tổng hợp ngắn gọn và trích nguồn là đạt. Tuy nhiên với trạng thái chạy hiện tại của nhóm, pipeline chưa đi hết do lỗi môi trường ở bước import ChromaDB, nên câu này chưa thể chấm điểm end-to-end một cách công bằng.

Dù vậy, có thể phân tích failure mode như sau: điểm nghẽn nằm ở tầng indexing infrastructure, không phải lỗi truy vấn hay prompt. Nghĩa là pipeline fail trước khi retrieval diễn ra. Nếu xét theo chuỗi Indexing → Retrieval → Generation thì root cause là Indexing chưa hoàn tất, nên Retrieval không có dữ liệu để trả về context, kéo theo Generation không thể grounded. Trong trường hợp này, fix ưu tiên không phải chỉnh prompt mà là khôi phục môi trường để build index thành công, sau đó kiểm lại câu hỏi P1.

Về cải thiện variant, tôi kỳ vọng sau khi hạ tầng ổn định, có thể thử hybrid retrieval cho dạng câu vừa có ngôn ngữ tự nhiên vừa có từ khóa SLA/P1. Variant này có khả năng tăng context recall so với dense thuần, đặc biệt khi tài liệu chứa cấu trúc policy nhiều heading.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Thứ nhất, tôi sẽ bổ sung chế độ dry-run cho index để xuất chunk JSONL mà không gọi embedding, nhằm cho phép kiểm thử data pipeline độc lập với API và Chroma. Thứ hai, tôi sẽ thêm script thống kê từ file JSONL: số chunk theo tài liệu, độ dài chunk trung bình, tỷ lệ thiếu metadata. Hai cải tiến này giúp phát hiện lỗi sớm trước khi chạy scorecard và giảm thời gian debug ở Sprint 3-4.
