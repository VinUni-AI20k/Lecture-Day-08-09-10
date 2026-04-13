# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Trí Cao
**Vai trò:** Documentation Owner & Code Contributor
**Ngày nộp:** 13/04/2026

---

## 1. Mình đã làm gì trong buổi lab này?

Trong dự án lab lần này, mình đảm nhận song song cả hai vai trò: vừa lo phần Documentation, vừa trực tiếp "nhúng tay" vào viết code xử lý logic cho pipeline. 
- **Về Documentation**: Mình chịu trách nhiệm thiết lập file `architecture.md` và `tuning-log.md`. Thay vì chỉ liệt kê các bước, mình đã đầu tư vẽ lại sơ đồ `Mermaid` để cả nhóm dễ hình dung luồng dữ liệu đi từ Indexing sang Retrieval Fusion (RRF). 
- **Về mảng Code**: Mình đã cùng Tech Lead trực tiếp tham gia cài đặt thuật toán **Reciprocal Rank Fusion (RRF)** cho phần Hybrid Search. Đây là phần tốn khá nhiều công sức để cân bằng trọng số giữa Dense và Sparse sao cho kết quả trả về không bị "đá" nhau. Ngoài ra, mình cũng phụ trách viết logic cho các hàm chấm điểm **LLM-as-Judge** trong file `eval.py`.

---

## 2. Những điều mình nghiệm ra sau lab

Có một thứ mình thực sự ngộ ra là: **RAG không chỉ mạnh ở mô hình, mà mạnh ở cách mình quản lý dữ liệu và tri thức**. 

Ban đầu mình cứ nghĩ ném văn bản vào Vector DB là xong, nhưng khi làm Documentation Owner, mình mới thấy Metadata quan trọng đến mức nào. Nếu không có metadata được định nghĩa tốt, LLM sẽ rất khó để trích dẫn nguồn chính xác. Việc tự tay viết code RRF cũng giúp mình hiểu rằng Hybrid Retrieval. Nó giúp mình bắt được các từ khóa (keyword) cực nhạy nhưng cũng dễ lôi theo đống "nhiễu" không đáng có.

---

## 3. Khó khăn

Lỗi làm mình tốn nhiều thời gian nhất lại là một thứ tưởng chừng đơn giản: **Vấn đề Encoding tiếng Việt**. Khi chạy script trên terminal Windows, các chuỗi tiếng Việt cứ bị lỗi font loằng ngoằng, khiến cho bảng scorecard xuất ra Markdown trông rất tệ. 

Về mặt logic, mình đã khá bất ngờ  khi thấy kết quả của **Hybrid (Variant)** đôi khi lại thấp hơn cả Baseline. Ban đầu mình rất tin là Hybrid sẽ thắng tuyệt đối, nhưng thực tế điểm Faithfulness và Relevance của nó lại bị sụt giảm trong một số trường hợp. Sau khi ngồi soi lại từng dòng log, mình phát hiện ra model bị "ngộp" thông tin do BM25 kéo về quá nhiều context nhiễu.

---

## 4. Phân tích một case trong scorecard

**Câu hỏi:** "Approval Matrix để cấp quyền hệ thống là tài liệu nào?" (q07)

**Phân tích:**
Đây là câu hỏi mà mình đã phải ngồi soi rất kỹ cả code lẫn documentation để tìm câu trả lời. 
- **Với Baseline (Dense)**: Kết quả vốn dĩ đã khá ổn, model trả lời đúng nhưng hơi ngắn gọn.
- **Với Variant (Hybrid)**: Nhờ có BM25 mà từ khóa "Approval Matrix" được tìm thấy ngay lập tức trong metadata của file `access_control_sop.md`. Tuy nhiên, điểm **Completeness** lại bị tụt xuống 2.0. 
- **Lý do tại sao?**: Qua việc phân tích context block mà mình đã build, mình thấy rằng khi Hybrid mang về đúng tài liệu nhưng lại kèm theo quá nhiều chunk khác có chứa từ "Approval", dẫn đến việc LLM chỉ tập trung trả lời đúng tên file mà quên mất tóm tắt các bước phê duyệt đi kèm. Case này giúp mình hiểu rằng việc tìm đúng (Recall) mới chỉ là 50% chặng đường, 50% còn lại nằm ở việc "gạn đục khơi trong" để LLM không bị lạc lối trong context.

---

## 5. Nếu có thêm thời gian, mình sẽ thử gì tiếp theo?

Chắc chắn mình sẽ không dừng lại ở RRF. Nếu còn thêm thời gian, mình muốn code thêm phần **Reranking** sử dụng Cross-Encoder để lọc lại top 10 kết quả trước khi đưa vào prompt. Ngoài ra, với tư cách Documentation Owner, mình muốn xây dựng một bộ **Metadata Schema** chặt chẽ hơn để việc filter dữ liệu theo phòng ban (Department) được thực hiện triệt để, giúp tăng độ chính xác lên mức tối đa.
