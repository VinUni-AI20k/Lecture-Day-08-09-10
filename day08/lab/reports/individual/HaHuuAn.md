# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Hà Hữu An
**Vai trò trong nhóm:** Retrieval  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi tập trung vào việc xây dựng và tối ưu module retrieval trong pipeline RAG, cụ thể là triển khai các hàm retrieve_dense, retrieve_sparse, retrieve_hybrid và rerank trong file rag_answer.py.

Với retrieve_dense, tôi sử dụng embedding (text-embedding-3-small) kết hợp ChromaDB để thực hiện semantic search. Ở retrieve_sparse, tôi implement BM25 nhằm xử lý các truy vấn chứa keyword cụ thể hoặc tên riêng. Sau đó, tôi phát triển retrieve_hybrid bằng cách kết hợp kết quả từ dense và sparse thông qua Reciprocal Rank Fusion (RRF) để cải thiện recall. Cuối cùng, tôi tích hợp bước rerank sử dụng LLM để sắp xếp lại các candidate passages theo mức độ liên quan thực sự với câu hỏi.

Phần công việc của tôi đóng vai trò cốt lõi trong việc nâng cao chất lượng retrieval trước khi đưa vào bước generation.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn rằng retrieval là thành phần quan trọng nhất trong pipeline RAG, thậm chí còn ảnh hưởng lớn hơn cả bước generation. Trước đây tôi nghĩ embedding có thể giải quyết hầu hết các bài toán tìm kiếm, nhưng thực tế cho thấy dense retrieval có hạn chế rõ ràng khi gặp các truy vấn chứa keyword chính xác hoặc alias.

Việc implement retrieve_sparse giúp tôi thấy rõ sức mạnh của BM25 trong việc match exact terms. Khi kết hợp hai phương pháp trong retrieve_hybrid, tôi nhận ra rằng mỗi phương pháp bù đắp điểm yếu của nhau.

Ngoài ra, bước rerank giúp cải thiện precision đáng kể, vì dù hybrid retrieval tăng recall, nhưng vẫn có nhiều noise. LLM-based reranking đóng vai trò như một lớp lọc cuối cùng để đảm bảo context đưa vào generation là chất lượng nhất.
---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến tôi ngạc nhiên nhất là việc dense retrieval hoàn toàn thất bại trong một số trường hợp tưởng chừng đơn giản, đặc biệt là khi truy vấn sử dụng tên cũ hoặc alias không xuất hiện trực tiếp trong nội dung chính.

Khó khăn lớn nhất của tôi nằm ở việc thiết kế và debug retrieve_hybrid. Việc kết hợp hai danh sách kết quả từ dense và sparse không đơn giản chỉ là nối lại, mà cần một cơ chế fusion hợp lý. Tôi đã mất thời gian để hiểu và triển khai đúng công thức Reciprocal Rank Fusion sao cho cân bằng giữa hai nguồn kết quả.

Ngoài ra, việc tuning số lượng candidates trước và sau rerank cũng khá thử thách — nếu lấy quá ít thì mất recall, nhưng quá nhiều thì tăng noise và chi phí LLM.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

Đây là câu hỏi khó nhất trong bộ test vì nó dùng tên cũ "Approval Matrix" trong khi tài liệu thực tế đã đổi tên thành "Access Control SOP" (access_control_sop.txt).

**Baseline (Dense):** Context recall thấp (2/5). Dense search tìm được một số chunk từ access_control_sop nhờ semantic similarity với "cấp quyền", nhưng chunk chứa dòng ghi chú "Tài liệu này trước đây có tên Approval Matrix for System Access" không nằm trong top-3. Kết quả: LLM trả lời chung chung về quy trình cấp quyền mà không mention tên tài liệu cũ.

**Variant (Hybrid + Rerank):** Context recall cải thiện lên 4/5. BM25 match trực tiếp keyword "Approval Matrix" trong ghi chú, đẩy chunk chứa thông tin alias lên top results. Rerank xác nhận chunk này relevant nhất. LLM trả lời chính xác: tài liệu Approval Matrix hiện có tên mới là Access Control SOP.

Lỗi nằm ở **retrieval** — generation hoạt động tốt khi có đúng evidence. Hybrid retrieval giải quyết triệt để vấn đề alias/tên cũ.

---

## 5. Kết luận

Qua lab này, tôi nhận ra rằng chất lượng của RAG pipeline phụ thuộc chủ yếu vào retrieval. Việc triển khai retrieve_dense, retrieve_sparse, retrieve_hybrid và rerank giúp cải thiện đáng kể cả recall lẫn precision.

Hybrid retrieval kết hợp với reranking là hướng tiếp cận hiệu quả để xử lý các tình huống thực tế như alias, keyword mismatch và noise trong dữ liệu. Bài học quan trọng nhất là: nếu retrieval không đúng, thì generation dù tốt đến đâu cũng không thể tạo ra câu trả lời chính xác.