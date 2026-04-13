# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Quốc Việt
**Vai trò trong nhóm:** Retrieval Owner (Sprint 3 — Variant)  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi phụ trách Sprint 3 — implement variant hybrid retrieval và tối ưu hóa chất lượng câu trả lời trong `rag_answer.py`. Cụ thể, tôi đã hoàn thiện hàm `retrieve_sparse()` dùng BM25Okapi để bổ sung keyword search, sau đó implement `retrieve_hybrid()` kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF) với trọng số `dense_weight=0.6`, `sparse_weight=0.4` và hằng số `RRF_K=60`. Tôi cũng cài đặt hàm `rerank()` sử dụng cross-encoder `ms-marco-MiniLM-L-6-v2` như một pipeline alternative, và viết sẵn `transform_query()` với ba chiến lược expansion, decomposition và HyDE. Sau khi implement, tôi chạy `compare_retrieval_strategies()` để A/B test giữa dense và hybrid trên bộ grading questions, rồi ghi kết quả vào `docs/tuning-log.md`. Phần tôi kết nối trực tiếp với Sprint 2 (baseline dense) của nhóm và phần eval để đo lường delta.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn hai khái niệm. Thứ nhất là hybrid retrieval không phải lúc nào cũng tốt hơn dense — nó mạnh ở exact term và alias nhưng có thể kéo thêm noise nếu BM25 match sai ngữ cảnh. Reciprocal Rank Fusion giúp cân bằng hai nguồn bằng cách merge theo thứ hạng thay vì raw score, nhưng việc chọn trọng số `dense_weight` và `sparse_weight` ảnh hưởng rõ rệt đến kết quả. Thứ hai là grounded prompt thực sự quan trọng: dù retriever lấy đúng source, nếu prompt không ép model bám sát evidence thì câu trả lời vẫn có thể chứa thông tin bịa đặt (hallucination). Câu `gq05` về Admin Access là minh chứng rõ nhất — cả baseline và variant đều retrieve đúng `access-control-sop.md` nhưng model vẫn tổng hợp nhầm chi tiết.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi ngạc nhiên nhất là hybrid retrieval cải thiện faithfulness rõ rệt (từ 3.80 lên 4.10 trên grading questions) nhưng completeness lại giảm nhẹ (từ 4.00 xuống 3.80). Ban đầu tôi kỳ vọng hybrid sẽ cải thiện cả hai chiều, nhưng thực tế cho thấy khi BM25 đẩy thêm chunk keyword-match vào top-3, đôi khi nó thay thế chunk dense chứa ngữ cảnh đầy đủ hơn, khiến câu trả lời tuy đúng nhưng thiếu chi tiết. Khó khăn lớn nhất là debug câu `gq05` (Contractor Admin Access): baseline bị faithfulness=1 vì model bịa thông tin, variant tăng lên faithfulness=4 nhưng completeness giảm từ 4 xuống 2 vì model bỏ sót approver (IT Manager + CISO) và training bắt buộc. Giả thuyết ban đầu là lỗi retrieval, nhưng Context Recall=5/5 ở cả hai bản cho thấy vấn đề chính nằm ở generation — model chọn sai chi tiết từ chunk đúng.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** `gq05` — Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?

**Phân tích:**
Đây là câu có chênh lệch lớn nhất giữa baseline và variant. Ở baseline dense, faithfulness chỉ đạt 1/5 vì model fabricate thông tin sai về approver và thời gian xử lý, dù Context Recall đạt 5/5 — retriever đã lấy đúng `it/access-control-sop.md`. Lỗi nằm hoàn toàn ở bước generation: tài liệu chứa nhiều access level (Level 1–4) trong cùng một section, model trộn nhầm chi tiết giữa các level. Sang variant hybrid, faithfulness tăng lên 4/5 nhờ BM25 match tốt hơn keyword "Admin Access" và "contractor", giúp chunk relevant được xếp hạng cao hơn. Tuy nhiên completeness giảm từ 4 xuống 2 vì câu trả lời bỏ sót hai ý quan trọng: approver cần cả IT Manager lẫn CISO, và thời gian xử lý đúng là 5 ngày (không phải 1 ngày). Kết quả này cho thấy hybrid cải thiện được grounding (bớt hallucinate) nhưng chưa đủ để model extract đúng và đủ chi tiết. Hướng cải thiện tiếp theo nên tập trung vào prompt engineering hoặc rerank để chọn chunk chính xác hơn cho câu hỏi multi-detail như thế này.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử hai cải tiến. Thứ nhất, bật cross-encoder rerank sau hybrid retrieval vì scorecard cho thấy vấn đề chính là model chọn sai chi tiết từ chunk đúng — rerank sẽ giúp lọc chunk relevant nhất trước khi đưa vào prompt. Thứ hai, tôi sẽ thử query decomposition cho các câu hỏi multi-part như `gq05`, vì kết quả eval cho thấy completeness thấp khi câu hỏi yêu cầu nhiều ý trả lời cùng lúc mà chỉ dùng single-query retrieval.

---
