# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đỗ Văn Quyết
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi đảm nhận vai trò Tech Lead, chịu trách nhiệm xây dựng toàn bộ RAG pipeline từ đầu đến cuối. Ở Sprint 1, tôi implement phần indexing: đọc 5 tài liệu nội bộ, preprocess để extract metadata (source, department, effective_date), chunk theo heading tự nhiên, và embed bằng OpenAI text-embedding-3-small rồi lưu vào ChromaDB. Sprint 2, tôi hoàn thành baseline retrieval với dense search và grounded answer function sử dụng gpt-4o-mini với prompt ép citation. Sprint 3, tôi implement hybrid retrieval kết hợp dense + BM25 qua Reciprocal Rank Fusion, thêm LLM-based rerank để lọc noise. Công việc của tôi tạo nền tảng cho Eval Owner chạy scorecard và Documentation Owner viết báo cáo.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab, tôi hiểu rõ hơn về tầm quan trọng của chunking strategy trong pipeline RAG. Ban đầu tôi nghĩ chunk size là yếu tố quan trọng nhất, nhưng thực tế ranh giới chunk mới ảnh hưởng lớn nhất — cắt giữa điều khoản khiến LLM mất ngữ cảnh hoàn toàn. Splitting theo heading "=== Section ===" trước rồi mới fallback sang paragraph giúp giữ nguyên vẹn từng điều khoản.

Concept thứ hai là hybrid retrieval. Dense embedding tốt với câu hỏi tự nhiên nhưng bỏ lỡ keyword chính xác. BM25 bù đắp bằng cách match exact term. Kết hợp qua RRF cho recall tốt hơn đáng kể, đặc biệt với query dùng alias hoặc tên cũ.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên nhất là câu hỏi q07 ("Approval Matrix để cấp quyền là tài liệu nào?") — baseline dense hoàn toàn miss vì tên cũ "Approval Matrix" không xuất hiện trong section heading hay nội dung chính, chỉ nằm trong một dòng ghi chú. Dense embedding không capture được mối liên hệ ngữ nghĩa giữa tên cũ và tên mới "Access Control SOP".

Khó khăn kỹ thuật lớn nhất là debug ChromaDB distances. Ban đầu tôi quên rằng ChromaDB cosine trả về distance (1 - similarity) chứ không phải similarity trực tiếp, dẫn đến score hiển thị ngược. Mất thời gian debug do kết quả retrieval trông đúng nhưng score lại thấp bất thường.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

Đây là câu hỏi khó nhất trong bộ test vì nó dùng tên cũ "Approval Matrix" trong khi tài liệu thực tế đã đổi tên thành "Access Control SOP" (access_control_sop.txt).

**Baseline (Dense):** Context recall thấp (2/5). Dense search tìm được một số chunk từ access_control_sop nhờ semantic similarity với "cấp quyền", nhưng chunk chứa dòng ghi chú "Tài liệu này trước đây có tên Approval Matrix for System Access" không nằm trong top-3. Kết quả: LLM trả lời chung chung về quy trình cấp quyền mà không mention tên tài liệu cũ.

**Variant (Hybrid + Rerank):** Context recall cải thiện lên 4/5. BM25 match trực tiếp keyword "Approval Matrix" trong ghi chú, đẩy chunk chứa thông tin alias lên top results. Rerank xác nhận chunk này relevant nhất. LLM trả lời chính xác: tài liệu Approval Matrix hiện có tên mới là Access Control SOP.

Lỗi nằm ở **retrieval** — generation hoạt động tốt khi có đúng evidence. Hybrid retrieval giải quyết triệt để vấn đề alias/tên cũ.

---

## 5. Kết luận

Pipeline RAG hoạt động end-to-end. Hybrid retrieval + rerank cải thiện chất lượng đáng kể so với baseline dense, đặc biệt ở context recall. Bài học quan trọng: retrieval quality quyết định phần lớn chất lượng output — nếu evidence sai, generation dù tốt cũng không cứu được.
