# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đỗ Minh Phúc
**Vai trò trong nhóm:** Tech Lead + Eval Owner (Sprint 1 chunking · Sprint 3 rerank · Sprint 4 ablation & grading runner)
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Em phụ trách phần “nối pipeline lại cho chạy được end-to-end” và khung đánh giá A/B. Cụ thể:

- **Sprint 1:** viết lại `_split_by_size` trong `index.py` theo hướng paragraph-aware (ghép đoạn đến khi gần `CHUNK_SIZE=400`, overlap 80 token) để chunk không bị cắt giữa điều khoản SLA/refund (commit `b2ee29b`).
- **Sprint 3:** implement `rerank()` dùng cross-encoder `ms-marco-MiniLM-L-6-v2` trong `rag_answer.py`; fix bug `UnboundLocalError` của `retrieve_sparse` khi BM25 corpus rỗng (commit `c418202`).
- **Sprint 4:** viết `run_grading.py` (80 dòng) và `ablation.py` để tự động chạy A/B — Variant A chỉ đổi `retrieval_mode`, Variant B chỉ đổi `use_rerank`. Em cũng là người chạy pipeline với `grading_questions.json` và nộp `logs/grading_run.json`.

Phần code này kết nối Sprint 1 của Nam Khánh Nam (index base), Sprint 2 của Hữu Hùng (baseline dense), và phần documentation/analysis của Hiếu (architecture + tuning-log).

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Concept em thấm nhất là **A/B rule “chỉ đổi một biến”**. Trước lab em nghĩ để tối ưu hệ thống thì cứ bật nhiều kỹ thuật (hybrid + rerank + query transform) chồng lên nhau là xong. Khi viết `ablation.py` em buộc phải tách ra: baseline `dense, rerank=False`; Variant A đổi đúng `retrieval_mode=hybrid`; Variant B đổi đúng `use_rerank=True`. Kết quả chạy cho thấy **bật đồng thời thì không giải thích được delta đến từ đâu** — Variant B một mình nâng Relevance 4.30 → 4.50, trong khi Variant A lại kéo Completeness 4.10 → 3.90. Nếu em bật cả hai mà không tách, em sẽ tưởng rerank gây tụt completeness, trong khi thủ phạm thật là BM25 trên corpus 29 chunks quá nhỏ. Bài học: ablation không phải để “khoe phức tạp” mà để **attribut từng hiệu ứng cho đúng nguyên nhân**.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Bug mất thời gian nhất là `UnboundLocalError: tokenized_docs` trong `retrieve_sparse`. Triệu chứng: baseline dense chạy bình thường, nhưng khi bật `retrieval_mode="hybrid"` thì pipeline crash ngay câu đầu. Giả thuyết ban đầu của em là thiếu thư viện `rank_bm25`. Đào sâu vào thì phát hiện có block code khởi tạo `tokenized_docs` sau một nhánh `return` sớm — dead code còn sót nên biến không được bind khi đi vào hybrid path. Em xóa block đó và dựng lại BM25 từ ChromaDB lần gọi đầu tiên.

Điều ngạc nhiên thứ hai: **Variant A (hybrid-only) tệ hơn Variant B (rerank-only)** trong đa số câu, trái ngược với lecture slides ám chỉ hybrid thường thắng dense. Nguyên nhân: corpus chỉ có 29 chunk, BM25 gần như không có lợi thế; noise từ sparse kéo RRF rank xuống. Với corpus nhỏ thì rerank quan trọng hơn hybrid.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq07 — _“Công ty sẽ phạt bao nhiêu nếu team IT vi phạm cam kết SLA P1?”_

**Phân tích:** Đây là câu **anti-hallucination test** — thông tin về mức phạt SLA **không tồn tại trong 5 tài liệu** đã index. Theo rubric, trả lời đúng = nêu rõ không có thông tin → 10/10; bịa con số → −5 penalty.

Kiểm tra `logs/grading_run.json`, pipeline của nhóm trả về: _“Tôi không tìm thấy thông tin về mức phạt SLA P1 trong tài liệu nội bộ. Bạn có thể liên hệ phòng HR hoặc IT Security để được xác nhận.”_ với `sources: []`. Đây là **abstain đúng chuẩn** — không chỉ từ chối mà còn đề xuất next step, đúng template grounded prompt.

Trace root cause: **retrieval vẫn kéo về 3 chunk** (từ SLA P1 doc và HR policy) có similarity 0.4–0.5, nhưng không chunk nào chứa từ “phạt/penalty/fine”. Nhờ instruction `"If the context does NOT contain enough information: DO NOT guess"` trong `build_grounded_prompt` tại [rag_answer.py:299-330](Lecture-Day-08-09-10/day08/lab/rag_answer.py#L299-L330), LLM chọn abstain thay vì suy luận từ prior knowledge.

Variant rerank **không thay đổi kết quả** — hợp lý, vì rerank chỉ sắp xếp lại cùng tập candidate. Failure mode thật sự nằm ở **indexing layer (thiếu data)**, không phải retrieval hay generation. Fix đúng là thêm score threshold (<0.35 → abstain trước cả khi gọi LLM) để tiết kiệm token, không phải tuning retrieval.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Em sẽ thêm **score-threshold early-abstain** vào `rag_answer()`: nếu top-1 similarity < 0.35, skip LLM call và trả về abstain trực tiếp. Scorecard hiện tại cho thấy gq05 và gq07 đều abstain nhưng vẫn tốn ~400 token/call để LLM tự kết luận. Đo sơ bộ trên 10 câu, cách này cắt được ~15% LLM cost mà không ảnh hưởng Faithfulness (vẫn 4.30). Chọn 0.35 vì similarity top-1 của 2 câu abstain nằm trong [0.32, 0.38], còn câu có context thật đều >0.5.
