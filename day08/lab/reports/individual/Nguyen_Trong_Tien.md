# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Trọng Tiến
**Mã số SV:** 2A202600228
**Vai trò trong nhóm:** Tech Lead
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, em chịu trách nhiệm quản lý và hỗ trợ nhóm triển khai toàn bộ pipeline từ đầu đến cuối. Ở Sprint 1, em implement `index.py`, chunking heading thành metadata, thông tin ghi chú và paragraph từng section thành content, embed bằng `text-embedding-3-small`, và lưu vào ChromaDB. Ở Sprint 2–3, em hỗ trợ Lộc và Quang review code `rag_answer.py`, thêm phần điều chỉnh hàm có dùng rerank hay transform query hay không và hàm điều chỉnh tỉ lệ sparse và dense trong hybrid retrieval. Em cũng thiết kế cơ chế abstain hai tầng: kiểm tra score threshold trước khi gọi LLM, và normalize sau khi nhận kết quả. Ở Sprint 4, em implement toàn bộ `eval.py` với 4 LLM-as-Judge metrics, tách prompt ra module `prompt/`, và build Streamlit UI để so sánh baseline vs variant trực tiếp. Điểm kết nối chính là `rag_answer()`, tất cả module khác (eval, app, grading run) đều gọi vào hàm này.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Điều em hiểu rõ nhất sau lab là **tại sao hybrid retrieval không phải lúc nào cũng tốt hơn dense**. Trước lab, em nghĩ thêm BM25 vào dense là cải tiến an toàn — BM25 bắt keyword, dense bắt semantic, kết hợp là tốt hơn cả hai. Nhưng thực tế variant hybrid + rerank + query expansion cho kết quả trung bình tệ hơn baseline ở Recall (giảm 0.3), Completeness (giảm 0.2).

Lý do thực sự là **reranker không được fine-tune cho domain này**, nên score tất cả các chunk xấp xỉ 0.016, gần như uniform. Khi scores không phân biệt được, reranker xáo trộn ngẫu nhiên thứ tự các chunk thay vì cải thiện. Bài học: mỗi component trong pipeline cần được đánh giá độc lập trước khi kết hợp. Thêm component nghĩa là thêm failure mode, không phải thêm chất lượng tự động.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Bug khó nhất là câu hỏi q07 ("Approval Matrix để cấp quyền hệ thống là tài liệu nào?"), một alias query mà cả dense và sparse đều không tìm ra đúng chunk. Sau khi debug kỹ, phát hiện đây là **lỗi hai tầng**:

1. **Tầng Preprocessor:** Hàm `preprocess_document()` trong `index.py` có logic xử lý header section. Dòng `Ghi chú: Tài liệu này trước đây có tên "Approval Matrix for System Access"` nằm trong vùng header nhưng không khớp bất kỳ `elif` nào, nên bị **drop hoàn toàn**, dẫn đến alias không bao giờ được index vào ChromaDB.

2. **Tầng BM25 tokenizer:** Tokenizer gốc split theo khoản trắng, giữ nguyên dấu câu. Kết quả là `"Approval` (có dấu ngoặc kép dẫn đầu) không match với token `approval`. BM25 không tìm ra chunk dù content đúng.

Giả thuyết ban đầu của em là lỗi retrieval (sai weights), nhưng thực ra lỗi nằm ở indexing, dữ liệu chưa bao giờ được đưa vào.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q10: *"Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?"*

**Phân tích:**

Baseline trả lời đúng hướng: nêu rõ tài liệu không đề cập quy trình VIP đặc biệt, rồi mô tả quy trình hoàn tiền tiêu chuẩn (3–5 ngày). Điểm Completeness = 4/5 — hợp lý, chỉ thiếu câu kết luận tường minh "không có ngoại lệ".

Variant lại cho kết quả **Completeness = 1/5**. Lỗi nằm ở phần grounding prompt xử lý câu trả lời, vì em đã ép constraint cho prompt trả lời: "Không thể trả lời câu hỏi do thiếu thông tin" cho tất cả các trường hợp thiếu context trả lời. Vì vậy prompt không thể trả lời thêm ý gốc cho câu hỏi này. Giải pháp là nới lỏng constraint có kiểm soát, cho prompt trả ra 1 số gợi ý về thông tin liên quan gần nhất với câu hỏi từ context, trong khi vẫn nhận không đủ thông tin để trả lời.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thử hai hướng cụ thể dựa trên kết quả eval:

1. **Thêm "Error Code Reference" document** (fix q09): Eval cho thấy q09 Recall = 0 ở cả baseline lẫn variant. Lý do là corpus không có document về error codes. Thêm một file structured như `it/error-codes.md` với format `ERR-403-AUTH = ...` sẽ cho BM25 một đối chiếu chính xác hơn.

2. **Tắt query transform cho câu hỏi đơn giản** (fix q10 regression): Thay vì bật transform mặc định, dùng LLM intent classifier kết hợp với indexing context để chỉ bật expansion khi detect alias query, tránh noise cho những câu đã rõ nghĩa.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
