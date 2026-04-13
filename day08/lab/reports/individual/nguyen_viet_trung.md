# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyen Viet Trung
**Vai trò trong nhóm:** Tech Lead
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Với vai trò Tech Lead, tôi chịu trách nhiệm tổ chức git cho nhóm — tạo branch, hướng dẫn quy trình commit và giải quyết conflict để các thành viên không giẫm chân nhau khi làm việc song song.

Về kỹ thuật, tôi cùng nhóm xây dựng workflow cho từng phần dựa trên góp ý của mỗi thành viên: ai phụ trách indexing, ai viết retrieval, ai lo prompt và generation. Tôi trực tiếp implement `query_trans.py` gồm 4 kỹ thuật (expansion, step-back, decomposition, HyDE), và tích hợp `transform_query()` vào pipeline chính. Trong quá trình chạy thử, tôi phát hiện và fix các bug như doc ID key mismatch trong `retrieve_hybrid()` khiến hybrid luôn trả về 0 chunk, và thiếu hàm `retrieve_by_embedding` cho HyDE.

Công việc của tôi là phần backbone — các thành viên khác có thể test và evaluate trên pipeline đã chạy ổn định mà không cần lo phần kỹ thuật bên dưới.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

**Grounded Prompt và cơ chế Abstain:** Trước lab này tôi nghĩ chỉ cần đưa context vào là model sẽ tự biết giới hạn. Thực tế không phải vậy — nếu không có instruction rõ ràng, model vẫn sẽ suy luận ngoài context và tạo ra câu trả lời nghe hợp lý nhưng không có cơ sở. Điều quan trọng là prompt phải ép buộc ba hành vi: chỉ dùng context đã cung cấp, nói "không biết" khi context không đủ, và gắn citation `[1]`/`[2]` để câu trả lời có thể kiểm chứng. Thiếu bất kỳ điều nào trong ba điều này, pipeline sẽ cho điểm thấp ở faithfulness dù retrieval hoàn toàn đúng.

**Query Transformation cần logic kiểm tra rõ ràng trước khi kích hoạt:** Tôi học được rằng không nên áp dụng transform cho mọi query. Mỗi kỹ thuật đều tốn ít nhất một lần gọi LLM — expansion sinh 5 biến thể, decomposition sinh sub-questions, HyDE sinh hypothetical doc — đều có chi phí token và latency thực sự. Nếu query đã đủ rõ và probe retrieval trả về kết quả tốt (score cao, từ một nguồn nhất quán), việc transform chỉ thêm noise. Pipeline trong lab dùng tín hiệu cụ thể để quyết định: độ dài query, pattern regex (mã lỗi, Jira ID, tên tool), số nguồn khác nhau trong probe, và ngưỡng score `[0.45, 0.58]` cho HyDE. Có logic kiểm tra rõ ràng giúp transform chỉ chạy khi thực sự cần, tránh lãng phí token và tăng latency không cần thiết.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Bug tốn thời gian nhất là `retrieve_hybrid()` luôn trả về 0 chunk dù dense và sparse đều hoạt động đúng riêng lẻ. Giả thuyết ban đầu của tôi là lỗi ở RRF scoring — tôi kiểm tra weight, hằng số 60, logic sort, nhưng không tìm ra gì.

Thực tế lỗi nằm ở chỗ hoàn toàn khác: `doc_scores` dùng `get_doc_id(doc)` làm key — một composite string `source|section_title|chunk_index`, nhưng `id_to_doc` lại dùng `metadata.get("id", f"dense_{rank}")` — một key scheme hoàn toàn khác. Kết quả: top_docs có 3 ID từ scheme A, id_to_doc có key từ scheme B, không có ID nào match, output luôn là `[]`.

Điều này dạy tôi một bài rất thực tế: khi debug "tại sao output rỗng", hãy trace từng bước key/value riêng biệt thay vì giả định logic tổng thể sai. Một silent mismatch ở layer lookup có thể vô hiệu hoá toàn bộ pipeline mà không có error nào.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** _"Approval Matrix để cấp quyền hệ thống là tài liệu nào?"_ (q07 — difficulty: hard)

**Phân tích:**

Đây là câu hỏi dùng tên cũ ("Approval Matrix") trong khi tài liệu đã đổi tên thành "Access Control SOP". Đây là bài test điển hình cho vocabulary mismatch.

**Baseline (dense):** Trả lời đúng — cosine similarity tìm được chunk liên quan từ `it/access-control-sop.md` vì embedding nắm được ngữ nghĩa, không cần khớp chính xác từ khóa. Điểm tốt.

**Baseline (hybrid — trước fix):** Trả về 0 chunk, output "Tôi không biết" — hoàn toàn sai. Lỗi nằm ở retrieval layer (bug key mismatch đã mô tả ở mục 3), không phải ở indexing hay generation.

**Baseline (hybrid — sau fix):** Trả về đúng 3 chunk từ `it/access-control-sop.md` với RRF score 0.43–0.54. Generation cho câu trả lời chính xác. Điểm tốt hơn dense vì RRF kết hợp cả semantic match (dense) lẫn keyword "Approval" (sparse).

**Kết luận:** Variant hybrid sau fix cải thiện rõ rệt so với baseline hybrid bị bug. So với dense, hybrid bổ sung thêm signal từ BM25 giúp câu trả lời có context rộng hơn. Lỗi không nằm ở indexing (chunk đã có đủ nội dung) mà hoàn toàn do implementation bug tầng retrieval.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ implement **cross-encoder rerank** thực sự vào hàm `rerank()` — hiện tại hàm này chỉ trả về `candidates[:top_k]` mà không chấm lại gì. Kết quả chạy cho thấy một số câu hỏi như q09 (ERR-403-AUTH) kéo về chunk từ `helpdesk-faq.md` nhưng chunk đó không đủ cụ thể — hybrid đưa vào top-3 vì rank keyword cao, nhưng nếu có cross-encoder chấm lại pair (query, chunk) thì chunk đó sẽ bị loại. Tôi sẽ dùng `cross-encoder/ms-marco-MiniLM-L-6-v2` vì nhẹ, chạy được local và đã được test trên multilingual corpus tương tự.

---

_Lưu file này với tên: `reports/individual/[ten_ban].md`_
_Ví dụ: `reports/individual/nguyen_van_a.md`_
