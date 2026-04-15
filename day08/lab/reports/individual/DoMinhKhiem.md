# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đỗ Minh Khiêm  
**Vai trò trong nhóm:** Indexing Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi phụ trách Sprint 1 — toàn bộ indexing pipeline trong file `index.py`. Cụ thể, tôi implement bốn phần chính: `preprocess_document()` để extract metadata (source, department, effective_date, access) từ header của mỗi tài liệu và normalize nội dung; `chunk_document()` để chia tài liệu theo ranh giới section heading (`=== ... ===`) trước, rồi split tiếp theo paragraph nếu section quá dài; `get_embedding()` hỗ trợ cả OpenAI (`text-embedding-3-small`) lẫn Sentence Transformers (`paraphrase-multilingual-MiniLM-L12-v2`) chạy local; và `build_index()` để upsert toàn bộ chunks vào ChromaDB với cosine similarity. Ngoài ra, tôi viết thêm `list_chunks()` và `inspect_metadata_coverage()` để kiểm tra chất lượng index sau khi build. Công việc của tôi là nền tảng cho Dũng và Văn — nếu chunk sai hoặc metadata thiếu thì retrieval sẽ kém dù thuật toán tìm kiếm có tốt đến đâu.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Trước lab, tôi nghĩ chunking chỉ là cắt text theo số ký tự cố định. Sau khi làm, tôi hiểu rằng chiến lược chunking ảnh hưởng trực tiếp đến chất lượng retrieval. Section-first chunking — cắt theo heading tự nhiên của tài liệu trước, rồi mới split tiếp nếu quá dài — giữ được ngữ cảnh hoàn chỉnh của mỗi điều khoản, tránh bị cắt giữa câu hay giữa một quy trình. Overlap (80 tokens) giữa các chunk liền kề giúp retriever không bỏ sót thông tin nằm ở ranh giới chunk. Tôi cũng hiểu tầm quan trọng của metadata: field `section` cho phép retriever biết chunk thuộc phần nào của tài liệu, còn `effective_date` giúp phân biệt phiên bản cũ và mới của cùng một chính sách. Metadata không chỉ để hiển thị mà còn là tín hiệu filtering cho retrieval.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)
Khó khăn lớn nhất là xử lý dedup khi build index. Ban đầu mỗi lần chạy `build_index()` lại thêm chunk mới vào ChromaDB mà không xóa chunk cũ, dẫn đến index bị duplicate — cùng một đoạn text xuất hiện nhiều lần với các ID khác nhau. Điều này làm retrieval trả về các chunk trùng lặp, lãng phí slot trong top-k. Giải pháp là xóa toàn bộ ID cũ trong collection trước khi upsert lại, đảm bảo mỗi lần build là một bản index sạch. Điều ngạc nhiên là khi kiểm tra bằng `inspect_metadata_coverage()`, tôi phát hiện một số tài liệu có format header không nhất quán — có file dùng "Effective Date:" nhưng có file lại để trống, khiến metadata bị rơi về giá trị "unknown". Tôi phải quay lại kiểm tra từng file trong `data/docs/` để đảm bảo parser xử lý đúng các trường hợp edge case.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q01 — "SLA xử lý ticket P1 là bao lâu?"

**Phân tích:**

Đây là câu hỏi difficulty=easy nhưng kết quả scorecard baseline cho thấy Faithfulness=5, Relevance=2, Context Recall=5, Completeness=4. Context Recall đạt tối đa nghĩa là chunk chứa thông tin về SLA P1 đã được retrieve thành công — indexing hoạt động đúng. Tuy nhiên, Relevance chỉ đạt 2/5, cho thấy câu trả lời tuy dựa trên đúng context nhưng chưa trả lời trúng ý câu hỏi.

Nhìn từ góc độ indexing, chunk chứa thông tin SLA P1 (phản hồi 15 phút, xử lý 4 giờ) nằm trong section riêng biệt với metadata `source: support/sla-p1-2026.pdf` và `section` rõ ràng, nên dense retrieval bắt được dễ dàng. Vấn đề ở đây không phải indexing hay retrieval mà nằm ở tầng generation — prompt có thể cần điều chỉnh để LLM trích xuất con số cụ thể thay vì mô tả chung chung. Completeness=4 cho thấy answer gần đầy đủ nhưng có thể thiếu một trong hai con số (15 phút hoặc 4 giờ).

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thêm metadata filtering vào retrieval pipeline. Hiện tại retriever tìm trên toàn bộ index, nhưng nếu câu hỏi rõ ràng thuộc domain "SLA" hoặc "HR", có thể filter theo field `department` trước khi search để giảm noise. Scorecard cho thấy q09 (ERR-403-AUTH) bị abstain sai — nếu có metadata `category` chi tiết hơn, retriever có thể nhận biết sớm rằng không có tài liệu nào thuộc category "error codes" và abstain chính xác hơn.

---
