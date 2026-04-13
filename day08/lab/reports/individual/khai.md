# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Tuấn Khải  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi phụ trách toàn bộ tầng Indexing và Retrieval của pipeline — từ Sprint 1 đến Sprint 3.

Sprint 1: Implement `build_vector_index()` để build Chroma từ danh sách Document, và `build_bm25_index()` để persist BM25S sparse index ra file pkl. Hàm `build_all()` orchestrate toàn bộ quá trình ingestion từ 5 file `.txt`.

Sprint 2–3: Implement `retrieve_dense()`, `retrieve_sparse()` (BM25S), `retrieve_hybrid()` (RRF fusion), `transform_query()` (HyDE), và `rerank()` (LLM-as-reranker). Các hàm này được thiết kế độc lập và kết nối trực tiếp vào `rag_answer()` — entry point do Tech Lead (Nhật) xây skeleton.

Ngoài code, tôi resolve conflict khi merge code từ Khánh và Nhật về nhánh chính, giữ lại implementation đúng trong khi integrate phần của đồng đội.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

**Hybrid Retrieval và RRF.** Trước lab này, tôi biết khái niệm dense và sparse retrieval nhưng chưa hiểu cách kết hợp đúng. Sau khi tự implement RRF, tôi mới thấy điểm thú vị: RRF không cần normalize score của hai hệ thống về cùng thang — nó chỉ dùng thứ hạng (rank), nên tránh được vấn đề scale mismatch giữa cosine similarity (~0.0–1.0) và BM25 score (không giới hạn trên).

Điều này cũng giúp tôi hiểu tại sao không thể áp threshold chung cho hybrid và dense mode — score RRF (~0.001–0.01) hoàn toàn khác scale với dense score (~0.0–0.24 với Chroma L2). Trước đây tôi nghĩ "score là score", nhưng thực ra mỗi retrieval system có score distribution riêng, phải hiểu source của nó mới đặt threshold đúng.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất là bug `RELEVANCE_THRESHOLD=0.35` khiến toàn bộ query bị abstain. Khi chạy eval lần đầu, Abstain Accuracy = 0.00 — nghĩa là pipeline abstain hết, kể cả câu có đáp án rõ ràng trong tài liệu. Giả thuyết đầu tiên của tôi là lỗi ở generation hoặc prompt — tôi mất thời gian kiểm tra system prompt trước.

Thực ra vấn đề nằm ở retrieval: Chroma dùng L2 distance, và `score = 1 - distance`. Với embedding chất lượng cao và corpus nhỏ, score thực tế chỉ đạt tối đa ~0.24 — thấp hơn threshold 0.35. Pipeline lọc sạch toàn bộ candidate → `has_context=False` → abstain.

Lesson học được: khi pipeline trả lời sai, debug theo thứ tự từ retrieval → generation, không giả định ngay vấn đề ở generation.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi gq05:** *"Quy trình cấp quyền truy cập cho contractor (nhà thầu) có khác với nhân viên nội bộ không?"*

Baseline Dense trả lời sai (abstain). Hybrid cũng abstain — điểm Abstain Accuracy = 0.00 cho câu này.

Lỗi nằm ở **Indexing**: keyword "contractor" chỉ xuất hiện ở dòng 11 của `access_control_sop.txt` — trong phần header metadata, không nằm trong bất kỳ chunk nào. BM25S chỉ index `page_content` của Document, không index header. Dense cũng không retrieve được vì embedding query "contractor" không đủ gần với text "Áp dụng cho tất cả nhân viên" trong chunk.

Fix: thêm "contractor", "third-party vendor", "nhà thầu" vào `ALIAS_MAP` của `index.py` — tương tự cách đang inject alias "approval matrix" cho câu gq07. Alias được append vào `page_content` của chunk đầu tiên trước khi index, để BM25S tokenize và index được.

Sau fix, BM25S sẽ bắt được query có keyword "contractor" và trả về chunk Section 1 (Phạm vi) của access_control_sop — nơi quy trình áp dụng cho tất cả nhân viên và contractor được mô tả.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thử **metadata-aware filtering** cho temporal queries. Kết quả scorecard cho thấy gq10 ("Chính sách hoàn tiền version 4 có còn hiệu lực không?") và gq01 (SLA version history) cần biết `effective_date` của từng tài liệu. Hiện tại pipeline retrieve theo semantic similarity, không ưu tiên chunk từ phiên bản mới nhất. Thêm filter `effective_date >= "2026-01-01"` vào Chroma query sẽ giúp pipeline tự động loại bỏ chunk từ policy cũ mà không cần LLM phân biệt.
