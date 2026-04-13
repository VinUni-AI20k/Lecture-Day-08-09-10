# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Vũ Quang Phúc 
**Vai trò trong nhóm:** Document Owner
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong role Document Owner và kỹ năng lập trình cá nhân, tôi đã tham gia tìm hiểu sâu kiến trúc và cài đặt mã nguồn cho toàn bộ RAG Pipeline từ Sprint 1 đến Sprint 3. Đặc biệt, tôi đã khởi tạo ChromaDB kết hợp mô hình `sentence-transformers` nội bộ để xây dựng Vector Database, sau đó triển khai được **Dense Retrieval**. Gần đây nhất, tại Sprint 3, tôi tự tay implement thuật toán **Sparse Retrieval (Keyword BM25)** kết hợp với **Hybrid Retrieval** sử dụng cấu trúc chấm điểm Reciprocal Rank Fusion (RRF). Việc viết code trực tiếp, tinh chỉnh các trọng số dense và sparse giúp tôi có cái nhìn rất thực tế về một hệ thống AI kết hợp kỹ thuật tìm kiếm truyền thống. Nhờ đó, pipeline hiện tại có thể phản hồi xuất sắc với các truy vấn mã đặc thù như `ERR-403-AUTH` ngay cả khi Dense Retrieval bỏ sót.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Trước đây, tôi có cái nhìn khá đơn giản về tìm kiếm Semantic Search, cứ nghĩ Vector Encoding sẽ lo hết mọi vấn đề đồng nghĩa hay từ vựng. Qua Sprint 3, tôi hiểu rõ hơn rào cản của Dense Retrieval: nó thực sự "hụt hơi" đối với các query yêu cầu độ chính xác keyword tuyệt đối (như mã lỗi ERP, danh pháp tên riêng dài). Điều đó khiến **Sparse Retrieval (BM25)** — thứ tôi tưởng là công nghệ lỗi thời trước thời đại AI — lại trở thành vị cứu tinh không thể thiếu. Tôi cũng thực chứng được sự tinh tế của **RRF (Reciprocal Rank Fusion)** trong Hybrid Search: thuật toán này kết nối hai thế giới từ khóa chính xác và ý nghĩa ngữ nghĩa lại với nhau cực kỳ tài tình. Hơn nữa, những bài học về chunking theo tự nhiên (`heading` hay `\n`) thay vì cắt cứng tokens cũng giúp cho các chunk giữ được ngữ cảnh tốt, cho phép kết quả LLM trở nên mượt mà. Đôi khi chỉ một cải tiến rất nhỏ ở Input đã tiết kiệm cho mô hình LLM vô vàn Context Token.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất tôi gặp phải là việc phải phối hợp nhiều thành phần lại với nhau trong lúc tích hợp Hybrid Retrieval. Cụ thể là làm thế nào để mapping logic trả về của ChromaDB với cấu trúc danh sách tokenized của thư viện `rank_bm25`, và tạo ID cho từng đoạn text để việc hợp nhất điểm (Fusion) không bị dính duplicate. 

Điều làm tôi kinh ngạc nhất là LLM không phải lúc nào cũng "ảo tưởng" (hallucinate) nếu ta làm RAG tốt. Đặc biệt là khi truyền truy vấn `"ERR-403-AUTH là mã lỗi gì?"`, lúc thiếu văn bản liên quan có chứa keyword do retriever chỉ bốc đại, mô hình Gemini/OpenRouter đã thành thật trả lời là "Tôi không biết" vì bị Prompt ép strict citation. Điều này tạo cho tôi niềm tin cực kỳ lớn vào tính ứng dụng của LLM trong doanh nghiệp hiện đại.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q04 — "ERR-403-AUTH là lỗi gì?"

**Phân tích:**

Đây là dạng câu hỏi Exact Matching / Keyword Specification.
Trong quá trình code Sprint 3, tôi nhận thấy rõ sự chênh lệch qua hàm so sánh A/B test.

**Baseline (dense):** Dense Search bắt ngữ nghĩa chung chung của "lỗi, từ chối" rồi trả về những document không liên quan đến hệ thống quản lý uỷ quyền. Không hề có đoạn `ERR-403-AUTH` nào lọt vào Top 3. Kết quả là LLM buộc phải trả lời: "Tôi không biết." Tính trung thực (Faithfulness) vẫn là xuất sắc nhưng độ hoàn thiện trả lời (Relevance/Completeness) bị nhận điểm 0.

**Variant (Hybrid RRF):** Nhờ cơ chế BM25, chuỗi token "ERR-403-AUTH" được đẩy điểm sparse score lên rất cao (vì hiếm gặp trong toàn cục corpus nhưng xuất hiện chính xác trong file `access-control-sop.md`). Khi hòa trộn với RRF, đoạn nội dung này chắc chắn nằm ở [1] hay [2] để nhét vào Generation Prompt. Kết cục là LLM đã phản hồi chính xác hệ thống nào và tool nào bắn ra lỗi này. Điều này chứng minh hoàn toàn bài học: muốn RAG tốt đối bài toán kỹ thuật tra cứu, BM25 luôn phải là xương sống cơ bản.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Bổ sung Cross-Encoder Rerank:** Sau khi có Hybrid Retrieval đẩy lượng lớn data, tôi sẽ muốn thực hiện thêm Reranker trước khi đưa vào Top 3 LLM. Điều này tuy chậm tốc độ xử lý hơn một tí nhưng khiến độ chính xác được ép lên mức cận hoàn hảo.
2. **Cải tiến logic Metadata Extractor:** Mình muốn trích xuất chi tiết hơn các thẻ Metadata như `doc_title` hay `effective_date` và thêm chúng làm bộ lọc (Pre-Filtering) ngay trong lúc gọi hàm lấy Vector, giúp giảm không gian tìm kiếm (Vector Space) để query chạy nhanh hơn trên các CSDL đồ sộ.
