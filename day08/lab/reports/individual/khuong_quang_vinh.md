# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Khương Quang Vinh 
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, với vai trò là Retrieval Owner, tôi đóng góp chủ yếu vào Sprint 2 và Sprint 3 của dự án. Đặc biệt, tôi tập trung chịu trách nhiệm xây dựng tính năng truy hồi thông tin (Retrieval) cốt lõi của RAG Pipeline. 

Cụ thể, tôi đã thực hiện lập trình trực tiếp để hoàn thiện 3 hàm quan trọng trong `rag_answer.py` bao gồm:
- `retrieve_dense`: Tìm kiếm theo semantic embeddings trong vector store (ChromaDB) để bắt nghĩa ngữ cảnh của Query. Embed query bằng các dùng model đã dùng khi index, query ChromaDB với embedding đó, rả về kết quả kèm score
- `retrieve_sparse`: Tìm kiếm theo keyword dựa trên thuật toán BM25 (`rank_bm25`) để giữ lại sự chính xác xác của các mã lỗi hay tên riêng. Cài rank_bm25, load tất cả chunks từ ChromaDB, tokenize và tạo BM25Index, query và trả về top_k kết quả
- `retrieve_hybrid`: Kết hợp kết quả của cả hai phương pháp trên thông qua Reciprocal Rank Fusion (RRF), Sort theo RRF score giảm dần, trả về top_k và ghi đè score cũ bằng score RRF giúp tăng hiệu suất truy hồi tổng thể trên đa đạng loại câu hỏi. 

Công việc của tôi là bản lề kết nối trực tiếp với phần Generation: đầu ra danh sách các chunks văn bản chính xác nhất từ các hàm retrieve này được đóng gói vào làm "Context block" đẩy sang cho thành viên làm Prompt engineering và LLM generate, giúp giảm thiểu hallucination và mang về kết quả mong đợi trong pipeline.

## 2. Điều tôi hiểu rõ hơn sau lab này

---

- Sau khi tự tay code và kết hợp các phương pháp tìm kiếm trong pipeline, concept tôi thực sự hiểu sâu sắc nhất chính là Hybrid Retrieval và cách dung hòa điểm số qua RRF. 

- Tôi nhận thấy điểm mạnh - yếu rất rõ ràng của từng phương pháp: Dense Vector cực kì xuất sắc trong việc nắm bắt các từ đồng nghĩa, nhưng lại hay dễ miss các từ khóa cụ thể như tên riêng. Ngược lại, BM25 bắt keyword rất nhạy bén nhưng lại vô dụng trước những câu hỏi dùng nhiều từ đồng nghĩa.

- Hybrid sinh ra để kết hợp 2 phương pháp. Ứng dụng thuật toán RRF. RRF giải quyết tốt điều đó bằng cách không quan tâm điểm gốc, mà quy tất cả về Rank. 

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

- **Điều bất ngờ nhất:** Tôi khá ngạc nhiên khi `retrieve_dense` (Dùng OpenAI embedding) đôi khi lại bỏ sót các mã lỗi cực kỳ cụ thể như "ERR-403-AUTH". Dù về mặt ngữ nghĩa nó liên quan đến "Authorization", nhưng vector search đôi khi ưu tiên các đoạn mô tả chung chung về quyền truy cập hơn là đoạn chứa chính xác mã lỗi đó. 

- **Khó khăn nhất:** Việc cài đặt `retrieve_sparse` gặp trở ngại ở khâu hiệu năng. Vì ChromaDB không hỗ trợ BM25 mặc định, tôi phải load toàn bộ corpus về RAM để build `BM25Okapi` index mỗi lần query. Điều này gây trễ (latency) rõ rệt khi số lượng chunk tăng lên. 

- **Lỗi debug lâu nhất:** Đó là việc xử lý score trong ChromaDB. Ban đầu tôi quên rằng ChromaDB trả về `distance` (càng nhỏ càng gần), trong khi pipeline yêu cầu `score` (càng lớn càng tốt). Việc chuyển đổi `1 - distance` và sau đó kết hợp với RRF trong `retrieve_hybrid` đòi hỏi tôi phải verify lại thứ tự xếp hạng rất nhiều lần để đảm bảo tính hội tụ. 


---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

Với câu hỏi 9 ("ERR-403-AUTH là lỗi gì và cách xử lý?"), phản hồi của bot là "Khong du du lieu trong tai lieu hien co" — điều này khớp với `expected_answer` và vì vậy được coi là đúng về mặt nội dung. Đánh giá: đạt điểm cho tính chính xác. Vì hệ thống không tạo thông tin sai; điểm cho tính hữu ích có thể bị giảm nhẹ vì thiếu hướng dẫn tạm thời cụ thể.

Nguyên nhân chính: retrieval/indexing. Khả năng cao là tập tài liệu đã index không chứa thông tin về mã lỗi này, hoặc nếu có thì phương pháp truy vấn hiện tại (chỉ dense) đã bỏ sót token chính xác "ERR-403-AUTH". Generation không phải lỗi chủ yếu vì LLM chỉ sinh dựa trên context được cung cấp.

Đề xuất cải thiện: 
- Mở rộng corpus (logs, FAQ, IT Helpdesk) để tăng khả năng có document chứa lỗi
- Tinh chỉnh prompt để yêu cầu model nêu rõ khi thiếu dữ liệu và cung cấp bước xử lý tạm thời (ví dụ: kiểm tra logs, liên hệ IT).

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

- Tôi sẽ thực hiện **Xây dựng bộ Index BM25 tĩnh (Persistent Sparse Index)** thay vì build on-the-fly để giảm latency từ ~200ms xuống dưới 20ms cho mỗi query tìm kiếm từ khóa.

- Tôi sẽ tích hợp bước **Rerank dùng Cross-Encoder** (`ms-marco-MiniLM`) vào sau Hybrid Retrieval. Vì kết quả Eval cho thấy mặc dù Hybrid đã lấy đúng chunk chứa mã lỗi lên top 10, nhưng đôi khi LLM vẫn bị xao nhãng bởi các chunk có RRF score cao khác. Reranker sẽ giúp lọc ra đúng 3 chunk liên quan nhất để đưa vào context, từ đó giảm thiểu tối đa hallucination và tăng độ chính xác tuyệt đối cho các câu hỏi kỹ thuật.


---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
