# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Vũ Quang Dũng
**Vai trò trong nhóm:**  Retrieval Owner 
**Ngày nộp:** 13/04/2026 
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Tôi chịu trách nhiệm phần Retrieval (Retrieval Owner) và thực hiện các cải tiến chính trong `rag_answer.py` cho Sprint 2/3. Cụ thể, tôi implement HyDE (sinh "hypothetical answer" rồi embed để tăng khả năng khớp ngữ nghĩa), Multi-Query Fusion (sinh các paraphrase của truy vấn và fuse kết quả bằng RRF) và Smart Abstain Detection (dùng threshold để ngừng sớm khi similarity quá thấp). Tôi tích hợp các hàm này với pipeline hybrid (dense + BM25 + RRF), viết hàm xây dựng context `build_context_block()` và tham gia tinh chỉnh các tham số `TOP_K`/`RRF_K`/`ABSTAIN_THRESHOLD`. Công việc của tôi kết nối chặt với phần indexing (index.py) — tôi dùng metadata/aliases do nhóm indexing chuẩn hoá để lọc và trích dẫn nguồn.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Qua lab, tôi hiểu sâu hơn về 2 concept then chốt: (1) HyDE — vì sao embedding của một "hypothetical answer" thường tương đồng hơn với chunks thực tế so với embedding của câu hỏi thô; điều này cải thiện recall cho những truy vấn alias hoặc multi-hop. (2) Hybrid + RRF fusion — cách phối hợp dense và sparse retrieval bằng RRF giúp tận dụng lợi thế semantic của embedding và sự chính xác từ BM25; cần chuẩn hoá/scale điểm để tránh score nhỏ nhưng vẫn có ý nghĩa so sánh. Ngoài ra, tôi hiểu rõ vai trò của abstain detection để giảm hallucination và tiết kiệm cost.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Khó khăn lớn nhất là cân bằng signal giữa các nguồn (dense vs BM25). Ban đầu tôi thấy RRF trả về điểm rất nhỏ (ví dụ ~0.01) nên khó dùng threshold tuyệt đối — cần đổi logic abstain cho các mode RRF/hybrid. Việc build BM25 từ collection Chroma cũng gây lỗi tokenization (phải chuẩn hoá lower()/split()). Thử nghiệm HyDE đôi khi dẫn đến câu giả định quá generic nếu prompt LLM không được viết chặt; điều này làm giảm lợi ích HyDE. Ngoài ra, debug timeout/credential khi gọi LLM (OPENAI/Gemini) chiếm nhiều thời gian. Bài học: validate từng bước retrieval (scores, top-k) trước khi gọi generation.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?

**Phân tích:**

Baseline (dense) có khả năng trả về nội dung từ `policy/refund-v4` và do đó thường trả lời rằng tài liệu chính thức không nêu quy trình VIP mà mọi yêu cầu đều theo quy trình tiêu chuẩn (3–5 ngày). Vì vậy baseline có thể cho kết quả đúng nếu chunk refund policy được retrieve tốt; nếu không, lỗi thường đến từ retrieval (không tìm thấy chunk liên quan) hoặc generation (LLM có thể suy diễn/tha hóa ra quy trình VIP nếu không được grounding). HyDE và Multi-Query giúp cải thiện recall: HyDE sinh đoạn trả lời giả định tập trung vào refund nên embedding dễ match các đoạn policy, Multi-Query giúp bắt paraphrase như "hoàn tiền khẩn cấp" → "expedited refund". Hybrid (BM25 + dense) giảm rủi ro thiếu match khi keyword như "hoàn tiền khẩn cấp" tồn tại. Smart Abstain giúp tránh hallucinate: với dense/sparse, nếu max_score < threshold pipeline sẽ abstain, còn với RRF/hybrid ta dựa vào grounded prompt (rule 2) để buộc model chỉ dùng context. Kết luận: biến thể HyDE+hybrid + grounded prompt có khả năng trả lời đúng và kèm citation `policy/refund-v4.pdf`, trong khi chỉ dùng dense có rủi ro hallucination nếu retrieval yếu.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Tôi sẽ: (1) Calibrate `ABSTAIN_THRESHOLD` bằng dev set (sử dụng các câu hỏi với ground-truth) để giảm false-positive/false-negative abstain; (2) Thêm metadata `customer_segment` hoặc `emergency_procedure` vào lúc indexing để hỗ trợ truy vấn như "VIP"; (3) Viết test end-to-end nhỏ (simulate query → retrieval scores → grounded prompt → compare expected answer) để catch regressions khi tinh chỉnh HyDE/RRF.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*