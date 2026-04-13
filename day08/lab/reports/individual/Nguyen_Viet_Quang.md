# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Việt Quang 
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi đảm nhận vai trò **Retrieval Owner**, chịu trách nhiệm chính trong **Sprint 3** — phần tuning retrieval strategy của pipeline RAG.

Cụ thể, tôi implement hai variant retrieval nâng cao trong file `rag_answer.py`:

- **Sparse retrieval (`retrieve_sparse()`)**: Sử dụng thư viện `rank-bm25` (BM25Okapi) để tìm kiếm theo keyword. Tôi thiết kế hàm tokenize riêng với regex strip punctuation để tránh lỗi token không khớp khi dấu câu dính vào từ.

- **Hybrid retrieval (`retrieve_hybrid()`)**: Kết hợp dense (vector similarity) và sparse (BM25) bằng thuật toán **Reciprocal Rank Fusion (RRF)** với trọng số `dense_weight=0.6`, `sparse_weight=0.4` và hằng số RRF K=60.

- **Rerank (`rerank()`)**: Implement cross-encoder reranking dùng model `cross-encoder/ms-marco-MiniLM-L-6-v2` từ Sentence Transformers, với caching model (biến global `_cross_encoder_model`) để tránh reload mỗi lần gọi.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Trước lab, tôi chỉ biết dense retrieval (vector search) là cách duy nhất tìm kiếm trong RAG. Sau khi implement hybrid retrieval, tôi nhận ra rằng **dense và sparse bổ sung cho nhau rất rõ ràng**: dense mạnh về semantic similarity (hiểu nghĩa câu hỏi paraphrase), nhưng yếu với exact keyword như mã lỗi, tên riêng, số điều khoản. Ngược lại, BM25 bắt chính xác các keyword đó nhưng không hiểu ngữ nghĩa.

Thuật toán RRF giúp merge kết quả từ hai nguồn khác nhau mà **không cần normalize score** — chỉ dùng ranking position. Đây là điểm rất hay vì cosine similarity score của dense và BM25 score có scale hoàn toàn khác nhau, không thể cộng trực tiếp.

Tôi cũng hiểu rõ hơn về **rerank pipeline** theo funnel logic: search rộng (top-10) → rerank (cross-encoder chấm lại relevance thực sự) → select (top-3 vào prompt). Cross-encoder chậm hơn bi-encoder nhưng chính xác hơn vì nó xem xét cặp (query, document) cùng lúc.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên lớn nhất là **BM25 có thể kéo chunk không liên quan lên top** nếu tokenization không chuẩn. Ban đầu tôi dùng `query.lower().split()` đơn giản, nhưng dấu câu dính vào token khiến BM25 không match được keyword chính xác. Ví dụ, token `"approval"` (có ngoặc kép) khác với `approval`. Sau khi thêm regex strip punctuation, kết quả cải thiện rõ rệt.

Một khó khăn khác là **câu gq05** — hỏi về contractor và Admin Access. Pipeline trả lời đúng rằng contractor thuộc phạm vi áp dụng, nhưng thiếu chi tiết về thời gian xử lý 5 ngày và yêu cầu training bắt buộc. Root cause: thông tin nằm ở **hai section khác nhau** trong cùng document (`access-control-sop.md`), và hybrid retrieval chỉ lấy được chunk chứa scope mà bỏ qua chunk chứa Level 4 detail. Đây là failure mode điển hình của multi-section retrieval.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q10 — "Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?"

**Phân tích:**

Câu q10 thuộc loại **grounding khi thiếu context** — tài liệu không đề cập quy trình riêng cho VIP. Expected answer là "mọi yêu cầu hoàn tiền đều theo quy trình tiêu chuẩn 3-5 ngày".

Theo scorecard:

| Metric | Baseline (dense) | Variant (hybrid+rerank) | Delta |
|--------|:-:|:-:|:-:|
| Faithfulness | 4 | 5 | +1 |
| Relevance | 1 | 5 | +4 |
| Recall | 5 | 5 | 0 |
| Completeness | 4 | 1 | −3 |

**Quan sát**: Cả baseline lẫn variant đều retrieve đúng chunk (Recall=5/5). Tuy nhiên baseline có Relevance chỉ 1/5 — tức câu trả lời **lệch hướng** dù context đúng. Lỗi nằm ở tầng **generation**, không phải retrieval. Variant cải thiện Relevance lên 5/5 và Faithfulness lên 5/5, nhưng Completeness giảm từ 4 xuống 1 — note scorecard ghi "Câu trả lời abstain đúng khi không có thông tin", nghĩa là variant chọn abstain thay vì cố trả lời.

**Nhận xét**: Đây là trade-off rõ ràng giữa **Relevance vs Completeness**. Baseline cố trả lời nhưng lệch hướng (R=1); variant abstain đúng (R=5) nhưng thiếu chi tiết về quy trình tiêu chuẩn (C=1). Hybrid + rerank giúp model tự tin hơn khi quyết định abstain, nhờ các chunk được sắp xếp lại chính xác hơn.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Cải thiện Context Recall cho q06**: Scorecard cho thấy cả baseline lẫn variant đều chỉ đạt Recall=**2/5** ở câu hỏi về SLA escalation — thấp nhất trong toàn bộ scorecard (trừ q09 abstain). Tôi sẽ thử tăng `top_k_search` từ 10 lên 15 kết hợp rerank để tăng khả năng retrieve đúng chunk liên quan.

2. **Cải thiện Completeness cho q10**: Variant đạt Relevance=5 nhưng Complete=1 (theo scorecard). Tôi sẽ thử điều chỉnh prompt để khi model nhận ra không có quy trình đặc biệt, vẫn nêu rõ quy trình tiêu chuẩn thay vì chỉ abstain — giúp cân bằng giữa Relevance và Completeness.
