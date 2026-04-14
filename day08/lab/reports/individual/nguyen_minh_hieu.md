# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Minh Hiếu  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi đảm nhận toàn bộ phần code trong [rag_answer.py](day08/lab/rag_answer.py) — tức là sprint 2 và sprint 3 của pipeline. Ở sprint 2, tôi implement `retrieve_dense()` để query ChromaDB bằng cùng embedding model với bước index, rồi viết `call_llm()` và `build_grounded_prompt()` ép model chỉ trả lời dựa trên context, có citation theo dạng `(tên tài liệu, section)` thay vì `[1][2]`, và abstain khi thiếu dữ liệu. Ở sprint 3, tôi thêm `retrieve_sparse()` dùng BM25, gộp với dense bằng Reciprocal Rank Fusion trong `retrieve_hybrid()`, viết `rerank()` bằng LLM và `transform_query()` cho ba strategy expansion/decomposition/HyDE. Phần của tôi nối trực tiếp với indexing của bạn khác (đọc collection `rag_lab`) và được phần evaluation chạy qua `rag_answer()` để chấm điểm.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Tôi hiểu rõ hơn về **hybrid retrieval** và **evaluation loop**. Trước đây tôi nghĩ dense embedding là đủ, nhưng khi thử các query có mã lỗi như "ERR-403-AUTH" hay cấp ticket "P1", dense thường trả về chunk na ná nghĩa nhưng lệch keyword. Hybrid với RRF giải quyết điều này bằng cách cho mỗi doc một điểm dựa trên *thứ hạng* ở cả hai danh sách, không phải điểm tuyệt đối — nên không cần normalize giữa cosine similarity và BM25 score vốn khác scale hoàn toàn. Về evaluation loop, tôi hiểu vì sao phải cố định biến: nếu vừa đổi retrieval vừa đổi prompt thì không biết cải thiện đến từ đâu. Scorecard baseline vs variant chính là cách duy nhất để biết thay đổi có đáng giữ không, thay vì cảm tính "có vẻ hay hơn".

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên nhất là **relevance không tăng như kỳ vọng**: baseline được 2.70/5, variant hybrid + rerank + decomposition chỉ 2.60/5 — thậm chí giảm nhẹ. Faithfulness có nhích từ 4.10 lên 4.50 nhờ rerank lọc noise, nhưng relevance không cải thiện vì câu trả lời dài hơn, lan man sang section kế bên. Về debug, **lỗi mất nhiều thời gian nhất là gọi sai hàm**: tôi vô tình gọi `retrieve_dense()` bên trong `retrieve_hybrid()` với sai tên parameter, khiến kết quả hybrid y hệt dense mà không báo lỗi. Giả thuyết ban đầu của tôi là "hybrid chắc chắn hơn dense", nhưng thực tế cho thấy chỉ có vài câu BM25 thực sự giúp ích (những câu chứa mã lỗi, tên policy), còn lại dense đã đủ tốt — khuếch đại variant lên toàn bộ query là sai hướng.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq01 — "SLA xử lý ticket P1 là bao lâu?" (category: SLA)

**Phân tích:**

Đây là câu mà cả baseline lẫn variant đều chấm Faithful=4, Recall=5, Complete=4, nhưng **Relevance chỉ 2/5** — tức là đã lấy đúng tài liệu nhưng câu trả lời chưa trả lời trúng ý hỏi. Lỗi không nằm ở indexing (recall 5/5 chứng tỏ chunk chứa SLA P1 đã được index và lấy ra), cũng không phải generation bịa (faithful 4/5). Lỗi nằm ở **tầng giữa: retrieval + selection**: top-3 chunk lấy về lẫn cả định nghĩa P1/P2/P3 và quy trình escalation, khiến LLM trả lời dài dòng về cả ba cấp thay vì cô đọng đúng thời gian P1. Variant hybrid + decomposition không cải thiện vì BM25 trên từ "P1" kéo thêm cả chunk nói về "P1 escalation contact" — lẽ ra nên thu hẹp chứ không mở rộng. Nếu phải fix riêng câu này, tôi sẽ giảm `top_k_select` từ 3 xuống 2 kèm rerank với prompt nhấn mạnh "chỉ chọn chunk định nghĩa thời gian phản hồi P1".

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thử các cách **expand query khác**. Cụ thể: (1) thay expansion chung bằng expansion có điều kiện — chỉ expand khi query ngắn dưới 6 từ hoặc chứa alias, vì kết quả eval cho thấy expand tràn lan làm relevance giảm nhẹ (2.70 → 2.60); (2) thử HyDE riêng cho category Cross-Document (gq02, gq06) vốn đang stuck ở Relevant=2-3; (3) decomposition chỉ bật cho query có liên từ "và"/"hoặc" để tránh tách những câu vốn đã đơn giản.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
