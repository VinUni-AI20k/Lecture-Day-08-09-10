# Báo Cáo Cá Nhân - Lab Day 08: RAG Pipeline

**Họ và tên:** Hoàng Đình Duy Anh
**Vai trò trong nhóm:** Retrieval Owner
**Ngày nộp:** 2026-04-13
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi đảm nhận vai trò Retrieval Owner, chịu trách nhiệm toàn bộ pipeline lấy dữ liệu từ Sprint 1 đến Sprint 3.

Trong **Sprint 1**, tôi implement `get_embedding()` dùng Vertex AI, `build_index()` để preprocess $\rightarrow$
chunk $\rightarrow$ embed $\rightarrow$ upsert vào ChromaDB với cosine similarity (`hnsw:space: cosine`). Kết quả index
được 29 chunks từ 5 tài liệu với đầy đủ
metadata.

Trong **Sprint 2**, tôi implement `retrieve_dense()` - embed query bằng cùng model lúc index, query ChromaDB và trả về
kết quả kèm score = `1 - distance`.

Trong **Sprint 3**, tôi implement `retrieve_sparse()` dùng BM25Okapi và `retrieve_hybrid()` kết hợp cả hai bằng
Reciprocal Rank Fusion (RRF). Công việc của tôi là nền tảng cho Tech Lead (`call_llm()`) và Eval Owner (scorecard) hoạt
động được.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Trước lab, tôi nghĩ hybrid retrieval chỉ đơn giản là "cộng điểm" từ hai nguồn. Sau khi implement RRF, tôi hiểu tại sao
cách đó không tốt: BM25 trả về raw score không có giới hạn trên, còn cosine similarity nằm trong [0, 1] - cộng trực tiếp
sẽ để BM25 lấn át hoàn toàn.

RRF giải quyết vấn đề này bằng cách chỉ dùng **thứ hạng** (rank), không dùng điểm số thô. Công thức
`weight / (60 + rank)` đảm bảo chunk ở rank 1 luôn được ưu tiên hơn rank 2, bất kể điểm gốc là bao nhiêu. Hằng số 60 là
để "làm mềm" sự chênh lệch giữa các rank cao - rank 1 và rank 2 sẽ không quá khác biệt so với rank 60 và 61.

Điểm quan trọng nữa: RRF dùng `start=1` chứ không phải `start=0` - nếu dùng rank 0 thì mẫu số bằng 60, không phải 61, và
chunk đầu tiên bị over-weight so với chuẩn RRF.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất là lỗi **embedding dimension mismatch** khi chuyển từ OpenAI sang Vertex AI. Ban đầu index được tạo
với OpenAI `text-embedding-3-small` cho ra vector 1536 chiều. Sau khi đổi sang Vertex AI (768 chiều), ChromaDB từ chối
upsert với lỗi: `Collection expecting embedding with dimension of 1536, got 768`.

Tôi tưởng chỉ cần đổi model là xong, nhưng ChromaDB lock dimension ngay lúc tạo collection - không thể thay đổi sau đó.
Giải pháp là xóa toàn bộ `chroma_db/` và build lại từ đầu.

Điều ngạc nhiên là dù không tune `dense_weight` và `sparse_weight` (giữ mặc định 0.6/0.4), Context Recall vẫn đạt 5.00/5
tuyệt đối. Điều này cho thấy với corpus nhỏ 29 chunks, retriever không cần tinh chỉnh nhiều - vấn đề thực sự nằm ở
generation và evaluation, không phải retrieval.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 - *"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"*

**Phân tích:**

Câu hỏi này thú vị vì nó dùng thuật ngữ **"Approval Matrix"** - một alias không xuất hiện trong tài liệu gốc. Tài liệu
thực tế có tên là `access-control-sop.md`, và trong nội dung dùng từ "ma trận phê duyệt" hoặc mô tả quy trình phê duyệt,
không dùng cụm "Approval Matrix".

Baseline (dense) vẫn trả lời đúng: *"Approval Matrix là một phần của tài liệu `it/access-control-sop.md`"*, đạt Context
Recall = 5. Điều này cho thấy dense retrieval (semantic search) xử lý tốt trường hợp alias - embedding hiểu "Approval
Matrix" và "ma trận phê duyệt" có nghĩa tương đồng.

Đây chính là lý do chọn hybrid thay vì pure BM25: nếu chỉ dùng BM25, query "Approval Matrix" sẽ không khớp keyword nào
trong tài liệu và có thể trả về sai. Dense component trong hybrid giữ được khả năng semantic matching này, trong khi
BM25 component bổ sung cho các query có exact term như "P1", "ERR-403".

Lỗi nếu có sẽ nằm ở **generation** - model cần diễn giải đúng rằng "Approval Matrix" là tên gọi khác của quy trình trong
tài liệu đó.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thử **tune RRF weights** có hệ thống: thay vì giữ mặc định 0.6/0.4, chạy grid search trên `dense_weight` ∈ {0.5,
0.6, 0.7, 0.8} và đo Context Recall thay đổi như thế nào - đặc biệt với các câu có exact term (q05 "5 lần", q09 "
ERR-403-AUTH").

Ngoài ra, tôi muốn thêm **caching cho BM25 index** - hiện tại `retrieve_sparse()` rebuild toàn bộ index mỗi lần gọi. Với
29 chunks thì ổn, nhưng nếu corpus lớn hơn đây sẽ là bottleneck nghiêm trọng.

---