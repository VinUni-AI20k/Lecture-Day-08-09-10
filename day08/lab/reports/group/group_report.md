# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** 401-B3

**Thành viên:**

| Tên | Vai trò | Email |
|---|---|---|
| Nguyễn Bình Minh | Data Engineer | minhnguyen041104@gmail.com |
| Nguyễn Việt Hoàng | RAG Developer | hoangnvhe170385@fpt.edu.vn |
| Trần Quốc Việt | Optimization Specialist | vquoc2532@gmail.com |
| Ngô Quang Phúc | Eval Specialist | phuc652003@gmail.com |
| Bùi Quang Vinh | Technical Writer & Quality | Noterday1@gmail.com |
| Lê Quang Minh | Quality & Reports | Mninh25@gmail.com |

**Ngày nộp:** 13-04-2026  
**Repo:** https://github.com/minh041104/C401-B3  
**Độ dài khuyến nghị:** 600–900 từ  

---

> **Hướng dẫn nộp group report:**
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào quyết định kỹ thuật cấp nhóm — không trùng lặp với individual reports
> - Phải có bằng chứng từ code, scorecard, hoặc tuning log — không mô tả chung chung

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

**Chunking strategy:**
Nhóm đã xử lý 5 tài liệu nội bộ, sinh ra tổng cộng 30 chunks. Các chunks được phân bổ rõ ràng theo phòng ban (IT Security: 8, HR: 5, IT: 11, CS: 6). Mỗi chunk đều được cấu trúc hóa với metadata chuẩn xác gồm `source`, `section`, và `effective_date`. Việc phân chia theo section header (ví dụ: `===` hoặc `Section X`) đảm bảo tính nguyên vẹn về ngữ nghĩa cho từng chính sách, tránh tình trạng cắt nửa chừng các điều khoản quan trọng.

**Embedding model:**
Hệ thống sử dụng mô hình embedding mã nguồn mở `paraphrase-multilingual-MiniLM-L12-v2` để mã hóa tài liệu. Đây là cấu hình tối ưu để thực hiện thử nghiệm tại môi trường local, sinh ra các vector 384 chiều. Dữ liệu vector được lưu trữ và quản lý hiệu quả thông qua thư viện ChromaDB.

**Retrieval variant (Sprint 3):**
Nhóm quyết định triển khai chiến lược **Hybrid Retrieval**, kết hợp giữa tìm kiếm ngữ nghĩa (Dense) và tìm kiếm từ khóa (Sparse/BM25). Mục tiêu là tận dụng khả năng bắt đúng các từ khóa chuyên biệt (như mã lỗi `ERR-403-AUTH`, cấp độ sự cố `P1`, thuật ngữ `VPN`) mà mô hình Dense đôi khi xử lý không chính xác do giới hạn về mặt ngữ nghĩa thuần túy.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:**
Áp dụng **Hybrid Retrieval** nhằm thay thế Baseline Dense-only để khắc phục tình trạng LLM sinh ra câu trả lời thiếu trung thực (Hallucination) đối với các câu hỏi có thuật ngữ kỹ thuật phức tạp.

**Bối cảnh vấn đề:**
Trong Baseline (Dense-only), dù Context Recall đạt mức tối đa (5.0/5.0) nhưng điểm Faithfulness (độ trung thực của LLM so với context) trung bình chỉ đạt 3.80/5. Điều này cho thấy LLM bị "nhiễu" bởi các chunks tương đồng về ngữ nghĩa nhưng sai biệt về chi tiết nghiệp vụ cụ thể, dẫn đến việc tự ý "sáng tác" câu trả lời (điển hình là câu gq05 có điểm Faithful chỉ đạt 1/5).

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| **Dense-only** | Đơn giản, tốc độ nhanh, Recall tốt | Dễ gây Hallucination, điểm Faithful thấp (3.80) |
| **Hybrid (Dense + Sparse)** | Bắt chính xác từ khóa, giảm vùng nhiễu | Phải đánh đổi nhẹ điểm Completeness |
| **Rerank với Cross-encoder**| Độ chính xác cực cao | Phức tạp, tăng đáng kể độ trễ (latency) |

**Phương án đã chọn và lý do:**
Chọn **Hybrid Retrieval** để tiến hành A/B test vì phương pháp này cho phép hệ thống bám sát hơn vào các từ khóa gốc trong văn bản nguồn. Việc này ép LLM phải trả lời dựa trên dữ liệu thực thay vì dựa vào kiến thức nền của mô hình, giúp tăng tính an toàn và tin cậy cho hệ thống hỗ trợ nội bộ.

**Bằng chứng từ scorecard/tuning-log:**
- Dựa trên `ab_comparison_grading.csv`, Variant Hybrid đã nâng điểm Faithfulness trung bình từ **3.80 lên 4.10 (+0.30)**.
- Cải thiện rõ rệt tại câu `gq06` (quy trình xử lý sự cố P1 lúc 2 giờ sáng), đạt điểm tuyệt đối 5/5 ở tất cả các tiêu chí so với sự thiếu hụt thông tin ở bản Baseline.

---

## 3. Kết quả grading questions (100–150 từ)

**Ước tính điểm raw:** 86/100 (Dựa trên trung bình cộng các tiêu chí đánh giá từ 3.80 đến 5.0).

**Câu tốt nhất:** ID: `gq06` (Cấp quyền khẩn cấp lúc 2h sáng).
* **Lý do:** Variant Hybrid xử lý hoàn hảo đạt điểm 5/5/5/5. Hệ thống đã truy xuất đúng quy trình từ `access-control-sop.md`, nêu rõ vai trò của "On-call IT Admin" và tính chất tạm thời của quyền truy cập, vượt xa khả năng của bản Baseline.

**Câu fail:** ID: `gq07` (Hình phạt vi phạm SLA P1).
* **Root cause:** Dữ liệu này không tồn tại trong corpus hiện có. Dù hệ thống đã nhận diện đúng và trả lời "Tôi không biết" (abstain), nhưng do không khớp với định dạng phản hồi mà bộ chấm điểm (LLM Judge) mong muốn, nên bị đánh giá thấp điểm (1/1/None/1).

**Câu gq07 (abstain):**
Pipeline đã thực hiện đúng về mặt logic bảo mật là không tự ý bịa đặt thông tin. Tuy nhiên, nhóm cần tinh chỉnh lại System Prompt để trả về câu trả lời chuyên nghiệp hơn như: *"Dựa trên tài liệu hiện có, không tìm thấy thông tin về các hình thức xử phạt vi phạm SLA."*

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

**Biến đã thay đổi (chỉ 1 biến):** Thay đổi phương thức truy xuất từ Dense sang Hybrid.

| Metric | Baseline | Variant | Delta |
|--------|----------|---------|-------|
| **Context Recall** | 5.00/5 | 5.00/5 | 0 |
| **Faithfulness** | 3.80/5 | 4.10/5 | +0.30 |
| **Relevance** | 4.60/5 | 4.60/5 | 0 |
| **Completeness** | 4.00/5 | 3.80/5 | -0.20 |

**Kết luận:**
Bản Variant Hybrid cho thấy sự cải thiện quan trọng ở chỉ số **Faithfulness (+0.30)**. Điều này chứng minh rằng việc kết hợp tìm kiếm từ khóa giúp giới hạn không gian thông tin, giúp LLM tập trung vào các dữ kiện thực tế hơn là suy diễn. Mặc dù có sự sụt giảm nhẹ ở điểm **Completeness (-0.20)** do sự thay đổi trọng số làm một số thông tin bổ trợ bị đẩy xuống dưới top-k, nhưng sự đánh đổi này là xứng đáng để có được một hệ thống trả lời trung thực và an toàn hơn.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nguyễn Bình Minh | Thiết lập Index pipeline, khắc phục lỗi ChromaDB | 1 |
| Nguyễn Việt Hoàng| Triển khai Baseline RAG, tích hợp API LLM | 2 |
| Trần Quốc Việt | Cấu hình tham số và thực hiện A/B test Hybrid | 2 |
| Ngô Quang Phúc | Xây dựng bộ tiêu chí đánh giá Scoring | 3 |
| Bùi Quang Vinh | Tổng hợp file kiến trúc, ghi chép nhật ký tuning và so sánh Baseline vs Variant. | 4 |
| Lê Quang Minh | Test các câu hỏi và hoàn thiện Group Report | 4 |

**Điều nhóm làm tốt:**
- Quản lý mã nguồn sạch sẽ, xử lý dứt điểm các lỗi xung đột database và file rác (`.sqlite3`, `__pycache__`) trên Git.
- Duy trì được điểm Context Recall tuyệt đối (5.0/5.0) nhờ chiến lược gán metadata và chunking hợp lý.

**Điều nhóm làm chưa tốt:**
- Chưa tối ưu hóa tốt System Prompt cho các tình huống cần từ chối trả lời (Abstain).
- Quá trình tuning trọng số cho Hybrid chiếm nhiều thời gian hơn dự kiến.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

1. **Cải thiện Prompt Engineering cho Abstain:** Thiết lập quy tắc phản hồi cứng rắn hơn để xử lý các câu hỏi bẫy (như `gq07`), đảm bảo điểm Relevance không bị kéo thấp khi hệ thống không tìm thấy dữ liệu.
2. **Tích hợp Reranker:** Sử dụng một mô hình Cross-encoder để sắp xếp lại 10 kết quả đầu tiên trước khi đưa vào LLM. Điều này sẽ giúp khắc phục nhược điểm về Completeness của Hybrid, đảm bảo những thông tin chi tiết nhất luôn được ưu tiên hiển thị.