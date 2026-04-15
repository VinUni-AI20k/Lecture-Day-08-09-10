# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Ngô Hải Văn  
**Vai trò trong nhóm:** Retrieval Owner — Sprint 3 (Hybrid & Rerank) + Variant C Improvement  
**Ngày nộp:** 2026-04-14  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi phụ trách Sprint 3 và phần cải thiện pipeline sau khi có kết quả scorecard.

**Sprint 3:** Implement `retrieve_sparse()` (BM25Okapi), `retrieve_hybrid()` (RRF với dense_weight=0.6, sparse_weight=0.4), và `rerank()` (cross-encoder + fallback lexical). Viết `_normalize_tokens()` và `_doc_key()` để dedup khi merge RRF.

**Variant C (cải thiện sau scorecard):** Sau khi phân tích kết quả eval, tôi xác định Context Recall = 5.0 ở cả hai cấu hình cũ — retriever đã lấy đúng tài liệu, bottleneck là generation. Tôi implement `build_grounded_prompt_v2` với 3 quy tắc cứng (COMPLETENESS, ABSTAIN, EMERGENCY), thêm param `prompt_version` vào `rag_answer()`, thêm low-score abstain guard, và sửa bug trong `score_faithfulness` đang chấm sai câu abstain đúng. Kết quả: Faithfulness +0.50, Completeness +0.30 so với baseline.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Bài học quan trọng nhất: **đọc metric trước khi chọn giải pháp**. Khi thấy Completeness thấp, phản xạ đầu tiên của tôi là "retrieval yếu — thêm hybrid và rerank". Kết quả Hybrid+Rerank ra đúng bằng baseline, thậm chí tệ hơn một chút. Lúc đó mới nhìn lại và thấy Context Recall = 5.0 — retriever đã lấy đúng hết rồi, vấn đề nằm ở LLM không tổng hợp đủ từ những gì đã có.

Từ đó tôi hiểu rõ hơn về evaluation loop như vòng lặp chẩn đoán: Context Recall đo retrieval quality, Completeness đo generation quality — hai metric này chỉ đúng bệnh khi đọc cùng nhau. Nếu CR cao mà Completeness thấp → sửa prompt, không sửa retriever. Đây là bài học A/B cụ thể hơn slide: không phải "đổi một biến" mà là "đổi đúng biến sau khi đọc metric".

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên nhất là Hybrid+Rerank không cải thiện gì mà còn làm Completeness giảm nhẹ (-0.10). Giả thuyết ban đầu của tôi là hybrid sẽ bắt được cross-document signals tốt hơn. Thực tế, vì corpus chỉ có 5 tài liệu nhỏ (29 chunks) và dense retrieval đã recall đủ 100%, thêm BM25 chỉ gây noise trong RRF merge thay vì bổ sung chunk mới.

Khó khăn kỹ thuật: bug trong `score_faithfulness` — câu trả lời abstain đúng ("Thông tin này không có trong tài liệu hiện có") bị LLM-judge chấm F=1 vì judge thấy context có nội dung SLA nhưng answer không dùng. Pipeline abstain đúng nhưng điểm thấp giả. Phải thêm danh sách `abstain_phrases` để detect và bypass judge, trả F=5 trực tiếp.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi gq05:** "Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?"

**Baseline (F=2, R=5, CR=5, C=4):**  
Context Recall = 5 — retriever lấy đúng `access_control_sop.md`. Nhưng Faithfulness = 2 và Completeness = 4 — câu trả lời thiếu yêu cầu training bắt buộc về security policy (nằm trong Level 4 detail). Lỗi không phải ở retrieval mà ở generation: với top_k_select=3, LLM nhận được chunk chứa Level 4 approver (IT Manager + CISO) và thời gian xử lý (5 ngày), nhưng thiếu chunk chứa "mandatory security policy training" vì nó nằm ở section riêng và bị cắt ra ngoài top-3.

**Variant C (F=5, R=5, CR=5, C=5):**  
Tăng top_k_select từ 3 → 5 đưa vào đủ cả Section 1 (scope: contractor included) và Level 4 detail section. Prompt v2 với quy tắc "liệt kê TẤT CẢ yêu cầu" khiến LLM nêu đủ 4 tiêu chí: contractor được phép, approver, thời gian, training bắt buộc. Đây là ví dụ điển hình: multi-section question cần nhiều chunk hơn single-fact question.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thử **Variant D: bật cross-encoder rerank** (`RERANK_WITH_CROSS_ENCODER=1` với `ms-marco-MiniLM-L-6-v2`) kết hợp với prompt_v2 và top_k_select=5. Lý do: gq09 (mật khẩu) vẫn giữ Faithfulness=2 dù content đúng — nhiều khả năng top-5 chunk có chunk nhiễu từ file khác. Cross-encoder chấm lại từng cặp (query, chunk) sẽ loại chunk nhiễu chính xác hơn, giữ Faithfulness cao mà không cần giảm top_k_select. Bằng chứng từ trace: gq09 retrieve được helpdesk-faq nhưng context block còn chứa cả chunk từ access_control_sop làm LLM cite thêm thông tin ngoài câu hỏi.

---

*File: `reports/individual/Ngo_Hai_Van_report.md`*  
*Sprint 3 + Variant C — 2026-04-14*
