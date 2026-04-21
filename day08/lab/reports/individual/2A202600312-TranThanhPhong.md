# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Thanh Phong  
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi đảm nhận vai trò **Tech Lead**, chịu trách nhiệm điều phối công việc giữa các thành viên và đảm bảo pipeline hoạt động trơn tru từ đầu đến cuối. 

Ở **Sprint 1**, tôi hỗ trợ Retrieval Owner trong việc thiết kế cấu trúc metadata và kiểm tra tính nhất quán khi lưu vào ChromaDB. Ở **Sprint 2**, tôi trực tiếp implement hàm `call_llm()` sử dụng Vertex AI (`gemini-2.5-flash`) và xây dựng hàm `rag_answer()` để kết nối các module lại với nhau. Tôi đã đưa ra quyết định quan trọng về việc sử dụng `temperature=0` để đảm bảo kết quả ổn định phục vụ cho việc chấm điểm (evaluation). 

Trong **Sprint 3**, tôi hỗ trợ các thành viên chọn và tích hợp variant Hybrid Search, đồng thời trực tiếp xử lý các lỗi phát sinh khi chuyển đổi giữa các embedding model của OpenAI và Google.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn về tầm quan trọng của **Grounding** và **Prompt Engineering** trong hệ thống RAG. Ban đầu, tôi nghĩ chỉ cần đưa context vào là LLM sẽ trả lời đúng. Tuy nhiên, qua thực tế, tôi thấy rằng nếu không có các chỉ dẫn nghiêm ngặt (như "Chỉ trả lời dựa trên context cung cấp", "Nói không biết nếu thiếu dữ liệu"), model rất dễ bị "ảo giác" (hallucination) dựa trên kiến thức có sẵn của nó.

Tôi cũng hiểu sâu hơn về quy trình **Evaluation Loop**. Việc có một scorecard tự động dùng LLM-as-judge không chỉ giúp chấm điểm nhanh mà còn giúp tôi nhận ra các điểm yếu của pipeline ngay lập tức theo từng metric như Faithfulness hay Completeness, thay vì chỉ nhìn vào câu trả lời cuối cùng một cách cảm tính.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi ngạc nhiên nhất là việc chuyển đổi giữa các embedding model lại gây ra lỗi hệ thống nghiêm trọng trong ChromaDB. Khi đổi từ OpenAI sang Vertex AI, dimension của vector thay đổi từ 1536 xuống 768, và ChromaDB không cho phép cập nhật collection hiện có. Điều này buộc nhóm phải xóa sạch database và build index lại từ đầu, một bài học quý giá về việc quản lý cấu trúc dữ liệu trong vector store.

Khó khăn lớn nhất là việc duy trì tính **Completeness**. Model thường trả lời rất ngắn gọn và bỏ qua các chi tiết phụ quan trọng (ví dụ: điều kiện về probation period). Tôi đã phải tốn khá nhiều thời gian để tinh chỉnh prompt, yêu cầu model "trả lời đầy đủ và bao quát các điều kiện" để cải thiện metric này trong Sprint 4.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 - *"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"*

**Phân tích:**

Đây là một câu hỏi thuộc loại "Alias Query" — người dùng hỏi bằng một thuật ngữ không xuất hiện trực tiếp trong văn bản gốc. Trong tài liệu, hệ thống phê duyệt được gọi là "Access Control SOP" (ma trận phê duyệt), nhưng người dùng lại hỏi về "Approval Matrix".

Ở cấu hình **Baseline (Dense)**, hệ thống đã trả lời đúng đạt điểm 5/5 cho cả Relevance và Context Recall. Điều này chứng minh sức mạnh của semantic search: embedding model hiểu được sự tương đồng về nghĩa giữa "Approval Matrix" và "Access Control SOP". Tuy nhiên, tôi nhận thấy có một lỗi nhỏ về Faithfulness (điểm 1) khi model tự bịa thêm đường dẫn file chi tiết mà trong context không thể hiện rõ ràng.

Khi chuyển sang **Variant (Hybrid)**, kết quả lại tệ đi (Relevance=1). Lý do là BM25 filter không tìm thấy từ khóa "Approval Matrix" trong văn bản tiếng Việt, dẫn đến việc các chunk nhiễu được đưa vào top-3, đẩy các chunk đúng ra ngoài. Điều này dạy cho tôi bài học rằng Hybrid search không phải lúc nào cũng tốt hơn nếu tokenizer không được tối ưu cho ngôn ngữ đích.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ tập trung vào việc **Optimize Prompt** để cải thiện metric Completeness. Kết quả hiện tại cho thấy model vẫn còn khá lười biếng trong việc liệt kê các ngoại lệ. Ngoài ra, tôi muốn thử nghiệm thêm bộ reranker mạnh hơn (Cross-encoder) để lọc nhiễu tốt hơn sau bước Hybrid search, giúp giải quyết triệt để các trường hợp như câu q07 ở trên khi BM25 gặp khó khăn.

---

