# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Duy Hiếu
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài:** ~700 từ

---

## 1. em đã làm gì trong lab này? (145 từ)

Đảm nhận vai trò Documentation Owner, nhưng để viết tài liệu kỹ thuật một cách sát thực tế nhất, em đã trực tiếp chạy toàn bộ pipeline từ Sprint 1 đến Sprint 4. Cụ thể, em chịu trách nhiệm chính trong Sprint 4: thu thập log, đối chiếu kết quả từ hệ thống LLM-as-Judge và xuất bảng so sánh A/B. Em đã phân tích các file `logs/grading_run.json` và `results/scorecard_*.md` để tìm ra Root Cause (nguyên nhân gốc rễ) cho các câu hỏi bị điểm thấp ở cấu hình Baseline. Dựa trên dữ liệu thực tế thu thập được, em đã hoàn thiện file `docs/architecture.md` mô tả cấu trúc hệ thống và `docs/tuning-log.md` để đưa ra lập luận bảo vệ quyết định sử dụng mô hình Cross-encoder Rerank ở Sprint 3 của toàn đội. Công việc của em giúp kết nối các con số khô khan thành một báo cáo có tính thuyết phục cao.

---

## 2. Điều em hiểu rõ hơn sau lab này (146 từ)

Khái niệm em hiểu sâu sắc nhất chính là "Rerank" và tư duy phễu lọc (Funnel logic) trong Retrieval. Ban đầu, em lầm tưởng rằng Vector Database (như ChromaDB) là chiếc đũa thần có thể hiểu mọi ngữ nghĩa. Nhưng qua bài lab, em nhận ra Dense Retrieval chỉ tìm kiếm dựa trên sự tương đồng về mặt từ vựng (Cosine Similarity) nên tốc độ quét nhanh nhưng lại nông, rất dễ bị lừa bởi các cụm từ lặp lại. Việc áp dụng Rerank bằng mô hình Cross-encoder đóng vai trò như một "chuyên gia thẩm định vòng cuối". Thay vì duyệt toàn bộ kho, nó chỉ lấy Top 10 văn bản do Dense Search tìm ra, sau đó đọc lại cẩn thận từng cặp **[Câu hỏi - Đoạn văn]** để chấm lại điểm độ liên quan (Re-score). Kỹ thuật này giúp bộ context đưa vào prompt cho LLM cực kỳ "sạch" và chính xác.

---

## 3. Điều em ngạc nhiên hoặc gặp khó khăn (152 từ)

Điều khiến em ngạc nhiên nhất là sức mạnh và sự khắt khe của hệ thống LLM-as-Judge. Lúc đầu, em e ngại việc dùng LLM để tự chấm điểm sẽ mang tính cảm tính. Thực tế, khi prompt được thiết kế chặt chẽ và yêu cầu trả về lý do, mô hình đánh giá rất gắt gao và khách quan hơn nhiều so với việc chấm bằng mắt. Khó khăn lớn nhất em quan sát thấy trong quá trình làm lab là ở bước parse output JSON từ LLM-Judge. Do tính chất tự do của LLM, đôi khi nó sinh ra chuỗi JSON bị kẹp giữa các ký tự markdown thừa (như ```json). Điều này làm pipeline bị crash khi chạy scorecard đánh giá. Việc chứng kiến cách hệ thống dùng chuỗi lệnh cắt `.find("{")` và `.rfind("}")` để khắc phục lỗi giúp em nhận ra tầm quan trọng của việc xây dựng cơ chế validation khi làm việc với LLM.

---

## 4. Phân tích một câu hỏi trong scorecard (187 từ)

**Câu hỏi:** q02 - "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?"

**Phân tích:** Ở cấu hình Baseline (Dense Search cơ bản), hệ thống LLM trả lời "Em không thể tìm thấy thông tin..." và nhận điểm Completeness chỉ là 1/5. Bằng cách trace log, em phát hiện lỗi hoàn toàn nằm ở bước Retrieval chứ không phải ở Generation. Hàm `retrieve_dense` đã lôi chunk "Điều 4: Quy trình xử lý" đưa vào Top 3 vì đoạn này chứa cụm từ "yêu cầu hoàn tiền" lặp lại nhiều lần, vô tình đẩy chunk "Điều 2: Điều kiện" (chứa đáp án 7 ngày) văng ra khỏi danh sách.

Khi hệ thống chạy Variant (kích hoạt `use_rerank = True`), kết quả Completeness cải thiện ngoạn mục lên mức 5/5. Mô hình Cross-encoder `ms-marco-MiniLM-L-6-v2` đã phân tích kỹ lại Top 10 chunk ứng viên. Nhờ khả năng hiểu ngữ cảnh sâu, nó nhận diện đúng chunk Điều 2 mới là câu trả lời trực tiếp cho keyword "bao nhiêu ngày", và xếp hạng chunk này lên vị trí Top 1. Nhờ context chuẩn xác, LLM cuối cùng đã sinh ra được câu trả lời hoàn hảo.

---

## 5. Nếu có thêm thời gian, em sẽ làm gì? (81 từ)

Nếu có thêm thời gian, ngoài việc điều chỉnh thuật toán truy xuất (như nhóm đã làm), em muốn đề xuất quay lại Sprint 1 để fine-tune kích thước `chunk_size`. Hiện tại nhóm dùng mức 400 tokens, đôi khi gom quá nhiều điều khoản khác nhau vào cùng một chunk làm loãng ngữ nghĩa khi tính cosine similarity. Em muốn giảm `chunk_size` xuống khoảng 200 tokens và tăng overlap để xem Context Recall có ổn định hơn đối với các câu hỏi chi tiết hẹp hay không.