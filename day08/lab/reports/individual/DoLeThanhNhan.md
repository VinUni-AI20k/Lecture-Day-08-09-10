# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đỗ Lê Thành Nhân  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026 
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

- Sprint tôi đóng góp trực tiếp vào là Sprint 4. 
- Phần tôi làm chủ yếu là rag_answer.py
- Nhận input từ indexing (Sprint 1) để retrieve dữ liệu,dùng pipeline đã build từ Sprint 2 (baseline RAG),output của mình (answer, chunks_used) được Sprint 4 dùng để chấm điểm (eval.py),giúp team so sánh baseline vs variant và xác định cải thiện.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn về hybrid retrieval và evaluation loop trong RAG. Trước đây tôi nghĩ chỉ cần dùng dense retrieval là đủ, nhưng khi làm thực tế, tôi thấy mỗi phương pháp có điểm mạnh riêng: dense hiểu ngữ nghĩa tốt, còn keyword lại chính xác với các từ khóa cụ thể (như tên policy, mã lỗi). Kết hợp cả hai giúp tăng khả năng lấy đúng tài liệu hơn.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

- Điều khiến tôi ngạc nhiên là việc thêm **rerank và hybrid retrieval** không phải lúc nào cũng cải thiện rõ rệt kết quả như kỳ vọng ban đầu. Tôi nghĩ rằng chỉ cần tăng `top_k_search` và thêm rerank thì answer sẽ tốt hơn, nhưng thực tế có những trường hợp điểm lại giảm. Sau khi debug, tôi nhận ra vấn đề nằm ở việc **chunks bị nhiễu** hoặc không chứa đúng thông tin cần thiết, khiến rerank chọn sai context.

- Lỗi tốn nhiều thời gian nhất là khi **Context Recall thấp dù đã retrieve nhiều chunks**. Ban đầu tôi nghĩ do model kém, nhưng thực tế là do **metadata source không đồng nhất**, dẫn đến việc eval không match đúng expected source. Sau khi chuẩn hóa lại source name, kết quả cải thiện rõ rệt.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq02 — Khi làm việc remote, tôi phải dùng VPN và được kết nối trên tối đa bao nhiêu thiết bị?

**Phân tích:**

Ở baseline, câu trả lời thường chưa đầy đủ — chỉ nêu được VPN là bắt buộc hoặc chỉ trả lời số lượng thiết bị, nên điểm Relevance và Completeness khoảng 3/5, Context Recall thấp vì chỉ retrieve được từ một document. Lỗi chính nằm ở retrieval, cụ thể là không lấy được chunk từ cả hai nguồn (HR policy và IT helpdesk), nên không thể tổng hợp thông tin.

Ở variant (hybrid + rerank), kết quả cải thiện rõ rệt. Hybrid giúp lấy được cả keyword “VPN” và “thiết bị”, còn rerank ưu tiên đúng chunk liên quan. Do đó, answer có đủ: VPN bắt buộc + Cisco AnyConnect + giới hạn 2 thiết bị, và có citation từ 2 nguồn. Điểm tăng lên khoảng 4-5/5 cho hầu hết metrics.

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử **improve chunking theo semantic boundaries (section-based chunking)** thay vì fixed-size, vì eval cho thấy một số câu bị thiếu context (Completeness thấp) do chunk bị cắt giữa các điều khoản. Ngoài ra, tôi muốn thử **metadata filtering theo version/effective_date**, vì ở các câu liên quan đến policy update (như gq01, gq10), pipeline đôi khi retrieve nhầm thông tin cũ dẫn đến giảm Faithfulness.


