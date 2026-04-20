# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Vũ Văn Huân  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ  

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi đảm nhận vai trò Retrieval Owner và tập trung chính vào Sprint 2 và Sprint 3 của pipeline RAG.

Ở Sprint 2, tôi xây dựng baseline Dense Retrieval bằng ChromaDB. Tôi implement hàm retrieve_dense() để embed query và truy xuất các chunk dựa trên cosine similarity. Đồng thời, tôi phối hợp với phần generation để đảm bảo câu trả lời có citation và cơ chế “Không đủ dữ liệu” khi không tìm thấy thông tin.

Ở Sprint 3, tôi phát triển variant Hybrid Retrieval kết hợp Dense và BM25. Tôi implement BM25 bằng rank_bm25, cache toàn bộ corpus để tăng tốc, và sử dụng Reciprocal Rank Fusion (RRF) để merge kết quả. Ngoài ra, tôi thử thêm rerank logic để cải thiện chất lượng top-k context.

Công việc của tôi kết nối trực tiếp với Eval Owner, vì toàn bộ output retrieval là đầu vào cho scorecard đánh giá hệ thống.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu sâu hơn về vai trò của Retrieval và ý nghĩa của từng metric trong Evaluation Loop.

Điểm quan trọng nhất tôi nhận ra là Context Recall = 5 không có nghĩa là hệ thống tốt. Trong kết quả của nhóm, cả baseline và variant đều đạt Context Recall 5.00, nhưng Completeness chỉ khoảng 2.10. Điều này cho thấy Retriever đã lấy đúng tài liệu, nhưng phần Generation hoặc logic pipeline đã không tận dụng được thông tin đó.

Ngoài ra, tôi hiểu rõ hơn về sự khác biệt giữa Dense và Sparse Retrieval. Dense mạnh về ngữ nghĩa, nhưng dễ miss keyword; còn BM25 bắt keyword tốt nhưng không hiểu ngữ cảnh. Hybrid giúp kết hợp hai yếu tố này, nhưng nếu không chuẩn hóa score thì lại gây tác dụng ngược.

Lab này giúp tôi nhìn rõ rằng Retrieval không chỉ là “lấy đúng tài liệu”, mà phải “lấy đúng + usable cho LLM”.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến tôi bất ngờ nhất là Hybrid + Rerank không cải thiện kết quả so với baseline, dù về lý thuyết nó phải tốt hơn.

Kết quả scorecard cho thấy:
- Baseline Dense: Completeness = 2.10
- Variant Hybrid Rerank: Completeness = 2.10 (không cải thiện)

Ban đầu, tôi giả thuyết rằng Hybrid sẽ giúp xử lý tốt các query dạng keyword như “ERR-403-AUTH” hoặc “Approval Matrix”. Tuy nhiên, thực tế cho thấy hệ thống vẫn trả lời “Không đủ dữ liệu” cho nhiều câu.

Sau khi phân tích, tôi nhận ra vấn đề không nằm ở retrieval mà ở pipeline logic:
- Score giữa Dense và RRF không cùng scale
- Threshold chặn output hoạt động sai
- Không có rerank thực sự (chỉ cắt top-k)

Ngoài ra, một vấn đề lớn là missing source (Context Recall log báo thiếu file), cho thấy pipeline retrieval chưa match đúng expected document.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** Q05 - "Quy trình xử lý sự cố mạng là gì?"

**Phân tích:**

Baseline (Dense):  
F=2, R=1, Rc=5, C=1 → Trả lời sai (không đúng nội dung)

Variant (Hybrid Rerank):  
F=1, R=1, Rc=5, C=1 → Trả lời sai hoàn toàn

Điểm đáng chú ý là Context Recall = 5 trong cả hai trường hợp. Điều này cho thấy hệ thống đã retrieve được đúng tài liệu liên quan đến network troubleshooting. Tuy nhiên, model vẫn trả lời “Không tìm thấy thông tin” → đây là dấu hiệu lỗi ở bước Generation hoặc filtering logic.

Nguyên nhân chính nằm ở:
1. Threshold: Score của Hybrid (RRF) rất thấp nên bị chặn
2. Context không được format đủ rõ để LLM hiểu
3. Không có rerank thực sự nên top-k có thể chứa noise

Ngoài ra, expected answer yêu cầu các bước cụ thể (restart router, check VLAN…), nhưng context có thể bị chia nhỏ (chunking issue), khiến LLM không tổng hợp được đầy đủ.

Kết luận: Đây là lỗi pipeline (retrieval → generation), không phải lỗi dữ liệu.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Chuẩn hóa score giữa Dense và Hybrid: Tôi sẽ áp dụng normalization để đưa tất cả score về cùng thang [0,1], vì kết quả hiện tại cho thấy Hybrid bị đánh giá sai do khác hệ quy chiếu.

Implement rerank thật (cross-encoder): Tôi sẽ dùng cross-encoder để chọn top-k chunk tốt nhất thay vì cắt thẳng, vì kết quả eval cho thấy nhiều câu bị nhiễu context.

Cải thiện chunking: Tôi sẽ thử chunk theo semantic hoặc theo section để tránh việc thông tin bị chia nhỏ, vì Completeness thấp cho thấy LLM không tổng hợp đủ dữ kiện.

---
