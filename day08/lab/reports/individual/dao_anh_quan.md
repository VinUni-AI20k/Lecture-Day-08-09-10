# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đào Anh Quân  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi chủ yếu phụ trách Sprint 1 — xây dựng toàn bộ indexing pipeline trong `index.py`. Cụ thể, tôi implement hàm `preprocess_document()` để parse metadata từ header của từng tài liệu (Source, Department, Effective Date, Access) và làm sạch nội dung trước khi chunk. Tiếp theo, tôi implement `chunk_document()` với chiến lược heading-based: split theo `===...===` section heading trước, sau đó nếu section quá dài thì split tiếp theo paragraph với overlap 80 tokens. Tôi cũng quyết định dùng `text-embedding-3-small` của OpenAI làm embedding model và ChromaDB `PersistentClient` làm vector store với cosine similarity. Cuối cùng, tôi implement `build_index()` để orchestrate toàn bộ pipeline, và `list_chunks()` / `inspect_metadata_coverage()` để kiểm tra chất lượng index. Công việc Sprint 1 là nền tảng cho toàn bộ pipeline — nếu chunk sai hoặc metadata thiếu thì Sprint 2, 3, 4 đều bị ảnh hưởng.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab, tôi hiểu rõ hơn tầm quan trọng của **chunking strategy** và vì sao không nên cắt chunk theo token count cứng. Ban đầu tôi nghĩ cứ chia đều theo số token là đủ, nhưng khi thực hành mới thấy rõ: nếu cắt ngang giữa một điều khoản (ví dụ: điều kiện hoàn tiền), chunk đó sẽ thiếu context để LLM trả lời chính xác. Cắt theo heading section giúp mỗi chunk giữ được một "ý hoàn chỉnh". Tôi cũng hiểu hơn về vai trò của **overlap**: nếu không có overlap, thông tin nằm ở ranh giới giữa hai chunk sẽ bị mất — model sẽ không thể liên kết thông tin từ hai phía. Overlap 80 tokens giúp giữ lại phần kết của chunk trước làm ngữ cảnh cho chunk tiếp theo, đặc biệt hữu ích với tài liệu dạng danh sách điều khoản liên tiếp như refund policy hay access control SOP.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều tôi không ngờ nhất là metadata extraction lại quan trọng hơn tôi nghĩ. Ban đầu tôi chỉ coi metadata là "thông tin phụ để filter", nhưng sau khi xem kết quả eval thì thấy rõ: q07 (Approval Matrix) bị Completeness = 2/5 không phải vì retriever lấy sai document, mà vì LLM không tìm được tên chính thức "Access Control SOP" trong answer. Nếu metadata `source` có ghi rõ tên document thì model có thể cite tên tài liệu chính xác hơn. Khó khăn kỹ thuật tôi gặp là parse regex cho phần header của file `.txt` — một số dòng có thêm khoảng trắng hoặc dấu xuống dòng không chuẩn khiến `line.startswith()` bị miss. Tôi phải thêm bước `.strip()` sau khi split và kiểm tra lại với `inspect_metadata_coverage()` để đảm bảo tất cả 5 tài liệu đều có đủ effective_date và department.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q04 — "Sản phẩm kỹ thuật số có được hoàn tiền không?"

**Phân tích:**

Câu q04 thuộc dạng **policy exception query** (difficulty: medium) — người dùng hỏi về một ngoại lệ trong chính sách hoàn tiền.

**Baseline (dense):** Faithfulness = 4, Relevance = 5, Context Recall = 5, Completeness = 3. Retriever hoạt động đúng — `policy_refund_v4.pdf` được retrieve (Context Recall = 5). Tuy nhiên, answer lại thêm chi tiết "trừ khi có lỗi do nhà sản xuất" mà không có trong expected answer. Đây là trường hợp model dùng kiến thức ngoài context để suy luận thêm — Faithfulness bị trừ 1 điểm. Completeness = 3 vì answer đúng hướng nhưng không cite rõ các ví dụ cụ thể như "license key, subscription".

**Variant (hybrid + rerank):** Kết quả gần như tương đương, Faithfulness tăng lên 5 nhưng Completeness vẫn = 3. Điều này cho thấy lỗi **không nằm ở retrieval** (cả hai config đều retrieve đúng document) mà ở **generation**: prompt không yêu cầu model liệt kê đủ ví dụ cụ thể từ context. Đây là bài học thực tế từ Sprint 1: chunk `policy_refund_v4.txt` đã chứa thông tin đó, nhưng nếu chunk quá dài hoặc thông tin nằm ở cuối đoạn thì model có xu hướng tóm tắt chứ không trích dẫn đầy đủ.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Cải thiện metadata với document title field:** Từ kết quả q07 (completeness = 2), tôi sẽ thêm field `doc_title` vào metadata (ví dụ: `"Access Control SOP"`) để khi LLM nhận context có thể cite tên tài liệu chính xác. Hiện tại `source` chỉ lưu đường dẫn file, không phải tên thân thiện với người đọc.

2. **Thử semantic chunking thay vì heading-based:** Kết quả cho thấy một số chunk vẫn bị mất chi tiết (q04, q10). Tôi muốn thử dùng embedding similarity để quyết định ranh giới chunk — cắt ở chỗ nội dung chuyển chủ đề thay vì cắt theo heading, có thể giữ được nhiều thông tin liên quan trong cùng một chunk hơn.

---
