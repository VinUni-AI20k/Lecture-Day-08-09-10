# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Vũ Đức Minh  
**MSSV:** 2A202600439
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi là **Retrieval Owner**, phụ trách toàn bộ pipeline từ tài liệu thô đến vector database (Sprint 1) và thử nghiệm retrieval variant (Sprint 3).

**Sprint 1** (`index.py`): Implement hàm `get_embedding()` dùng OpenAI `text-embedding-3-small` để chuyển text thành vector. Cải thiện `_split_by_size()` từ cơ chế cắt cứng theo ký tự sang split theo ranh giới paragraph (`\n\n`) kết hợp overlap 80 tokens — đảm bảo chunk không bao giờ bị cắt giữa câu quan trọng. Implement `build_index()` để chạy toàn bộ pipeline: đọc 5 file `.txt` → `preprocess_document()` → `chunk_document()` → embed → upsert vào ChromaDB. Kết quả: 29 chunks, 0 chunk thiếu metadata.

**Sprint 3** (`rag_answer.py`): Implement `retrieve_sparse()` dùng BM25Okapi, và `retrieve_hybrid()` dùng Reciprocal Rank Fusion (RRF) để kết hợp kết quả dense + BM25 theo trọng số 0.6/0.4.

Công việc của tôi là nền tảng để Tech Lead implement `retrieve_dense()` ở Sprint 2 (phải dùng cùng embedding model), và để Eval Owner có thể chạy A/B compare baseline (dense) vs variant (hybrid) ở Sprint 4.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

**Chunking không phải cắt đều — mà phải cắt đúng chỗ.**

Trước lab, tôi nghĩ chunk size chỉ là con số (400 tokens). Sau khi debug, tôi thấy code gốc cắt text theo ký tự cứng (`start = end - overlap_chars`) dẫn đến chunk bị cắt giữa câu — ví dụ `"...trong vòng 7 ngày làm vi"`. LLM nhận được đoạn cụt như vậy sẽ không thể trả lời chính xác.

Cải tiến của tôi — split theo `\n\n` trước, rồi mới ghép → chunk luôn kết thúc tại ranh giới paragraph tự nhiên. Đây là lý do q02 ("hoàn tiền 7 ngày") trả lời đúng hoàn toàn: chunk giữ nguyên câu `"Khách hàng được quyền yêu cầu hoàn tiền trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng"` không bị cắt.

**Hybrid RRF không chọn kết quả tốt nhất — nó chọn kết quả được cả hai đồng thuận nhất.** Chunk nào vừa được dense ranking cao vừa có BM25 keyword match sẽ nổi lên top, dù không phải top-1 riêng lẻ của từng phương pháp.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

**Query "Approval Matrix" — cả Dense và Hybrid đều abstain, dù source đúng.**

Khi chạy `compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")`, cả hai strategy đều retrieve `it/access-control-sop.md` đúng, nhưng LLM vẫn trả lời "Không tìm thấy thông tin này." Tôi ngạc nhiên vì tưởng đã giải quyết bằng hybrid.

Sau khi điều tra, tôi phát hiện dòng `"Ghi chú: Tài liệu này trước đây có tên 'Approval Matrix for System Access'"` nằm ở phần **preamble** của file `access_control_sop.txt`, trước heading `===` đầu tiên. Hàm `chunk_document()` chỉ chunk theo heading section — phần preamble bị bỏ vào chunk "General" với section rỗng, và khi retrieve, chunk này không được đưa vào top-3 vì score thấp.

Đây là **chunking failure**, không phải retrieval failure. Nếu preamble được giữ lại và gắn vào Section 1, LLM sẽ thấy thông tin alias và trả lời đúng. Đây là hạn chế của sparse heading-based chunking khi document có intro text quan trọng.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** `q07` — *"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"*  
**Expected:** *"Tài liệu 'Approval Matrix for System Access' hiện tại có tên mới là 'Access Control SOP' (access-control-sop.md)."*

**Phân tích:**

Khi chạy baseline (dense), pipeline retrieve được `it/access-control-sop.md` với score 0.511 — đúng file. Nhưng LLM trả lời abstain. Điểm Context Recall = 5/5 (source tìm được), nhưng Completeness = 1/5 (không trả lời được câu hỏi thực sự).

**Root cause nằm ở indexing, không phải retrieval hay generation:**

Dòng `"Ghi chú: Tài liệu này trước đây có tên 'Approval Matrix for System Access'"` nằm ở dòng 7 của file, trước `=== Section 1 ===`. Hàm `chunk_document()` dùng regex `r"=== .+? ==="` để chia section — phần preamble trước heading đầu tiên được đặt vào chunk section `""` (rỗng). Chunk rỗng section này có embedding score thấp với query "Approval Matrix", không lọt vào top-3 chunk gửi cho LLM.

**Variant (hybrid) không cải thiện:** BM25 tìm được keyword "Approval" nhưng cũng không đưa preamble chunk lên top-3 vì BM25 score của nó thấp hơn các section chunks khác.

**Fix đề xuất:** Hàm `chunk_document()` nên prepend nội dung preamble vào Section 1 thay vì tạo chunk riêng với section rỗng.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

**Thứ nhất:** Fix preamble chunking — merge nội dung trước `===` đầu tiên vào Section 1. Scorecard cho thấy q07 fail hoàn toàn do lý do này, và fix chỉ cần ~5 dòng code trong `chunk_document()`.

**Thứ hai:** Thử Query Expansion cho alias queries — dùng LLM sinh thêm `["Access Control SOP", "quy trình cấp quyền"]` từ query gốc "Approval Matrix", rồi merge kết quả retrieve. Hybrid RRF đã cải thiện *thứ tự* chunk, nhưng không giải quyết được *missing information* trong preamble. Query Expansion address đúng root cause hơn.

---

*File lưu tại: `reports/individual/VuDucMinh.md`*  
*Code contribution có comment `[RO]` tại: `index.py` (hàm `get_embedding`, `_split_by_size`, `build_index`) và `rag_answer.py` (hàm `retrieve_sparse`, `retrieve_hybrid`, `compare_retrieval_strategies`)*
