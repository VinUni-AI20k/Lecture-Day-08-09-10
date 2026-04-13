# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyen Thi Ngoc  
**Vai trò trong nhóm:** Documentation Owner (hỗ trợ Eval)  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab Day 08, mình tập trung vào phần **tài liệu hoá + tổng hợp bằng chứng đánh giá** để nhóm có thể giải thích rõ pipeline thay vì chỉ “chạy được”. Cụ thể, mình hoàn thiện `docs/architecture.md` bằng cách mô tả kiến trúc end-to-end (index → ChromaDB → retrieve/rerank → grounded prompt → LLM), quyết định chunking (chunk size/overlap/strategy) và cấu hình baseline/variant mà nhóm đang chạy. Đồng thời mình tổng hợp và chuẩn hoá cách ghi chép thí nghiệm trong `docs/tuning-log.md`: nêu rõ giả thuyết dựa trên các câu yếu (ví dụ q09/q06), tuân thủ A/B rule ở mức có thể trong thời gian lab, và ghi lại quan sát “cải thiện/regression” theo từng câu để cả nhóm thống nhất hướng tune tiếp. Mình cũng hỗ trợ báo cáo nhóm (`reports/group_report.md`) bằng cách tóm tắt “key decisions” và cách đọc scorecard để người chấm thấy reasoning và evidence.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, mình hiểu rõ hơn sự khác nhau giữa **retrieval quality** và **generation quality** khi debug RAG. Trước đây mình hay nhìn câu trả lời “đúng/sai” theo cảm giác, nhưng scorecard buộc mình tách ra: (1) **Context Recall** nói về “có retrieve đúng evidence không”, (2) **Faithfulness** nói về “có bịa ngoài evidence không”, còn (3) **Answer Relevance** và (4) **Completeness** nói về “trả lời đúng trọng tâm và đủ điều kiện/ngoại lệ chưa”. Nhờ vậy, mình thấy một hệ có thể rất grounded (faithfulness cao) nhưng vẫn “lệch câu hỏi” hoặc thiếu điều kiện vì evidence top-k chưa bao phủ hết. Mình cũng hiểu rõ hơn “funnel” search rộng → chọn top nhỏ: top_k_search, rerank, và top_k_select không phải tham số phụ, mà ảnh hưởng trực tiếp đến việc câu trả lời có đủ và đúng hay không.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm mình ngạc nhiên là một thay đổi “nghe có vẻ đúng” vẫn có thể tạo **regression** nếu không đúng với dữ liệu/miền bài toán. Nhóm thử bật retrieval stack (hybrid + rerank + query expansion) với kỳ vọng cải thiện các câu có keyword/mã lỗi và câu cần nhiều evidence. Tuy nhiên trong tuning-log của nhóm, variant lại làm giảm **context recall** và **completeness** tổng thể, và quan trọng nhất là **không fix được q09 (ERR-403-AUTH)** — câu có mã lỗi cụ thể. Khó khăn lớn nhất là trace ngược từ symptom (“recall=0” hoặc “answer sai lệch”) về nguyên nhân: có thể do BM25 không bắt được term, do reranker cho điểm gần như đồng đều (khó phân biệt), hoặc do query expansion tạo nhiễu khiến top-k bị lệch. Việc ghi lại quan sát theo từng câu trong tuning-log giúp mình tránh kết luận cảm tính và chỉ ra rõ “biến nào giúp/biến nào hại”.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q09 (ERR-403-AUTH / Insufficient Context)

**Phân tích:**

Trong `docs/tuning-log.md` của nhóm, q09 là câu yếu nhất của baseline vì **Context Recall = 0/5**: truy vấn chứa mã lỗi “ERR-403-AUTH” nhưng dense retrieval không mang về đúng evidence (thường chỉ lấy các đoạn “access control” chung chung). Vì vậy baseline phải đối mặt với hai lựa chọn: hoặc bịa (rất nguy hiểm), hoặc **abstain**. Nhóm kỳ vọng hybrid (dense + BM25) sẽ giúp bắt exact keyword/mã lỗi tốt hơn, sau đó rerank sẽ đẩy đúng chunk lên top-3.

Tuy nhiên tuning-log ghi nhận variant vẫn **không fix được q09** (recall vẫn 0) và reranker cho điểm gần như đồng đều giữa các candidate (khó phân biệt relevance). Mình rút ra đây là “retrieval-data mismatch”: nếu corpus không có đoạn nào thực sự chứa/giải thích mã lỗi, thì BM25 và rerank cũng không thể “tạo ra evidence”. Trong trường hợp này, abstain đúng là hành vi an toàn, nhưng nó cũng cho thấy cần bổ sung dữ liệu (ví dụ tài liệu “error code reference”) hoặc thay đổi chiến lược (rule-based: nếu query là mã lỗi mà không có evidence thì trả lời “không có trong tài liệu” kèm hướng dẫn liên hệ IT).

Nếu có thêm thời gian, mình sẽ giữ A/B rule và thử một bước nhỏ: tăng `top_k_search` trước rerank để tăng cơ hội bắt đúng term; nếu vẫn không cải thiện, kết luận chính xác là “thiếu dữ liệu” thay vì tiếp tục tuning tham số.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Mình sẽ làm 2 việc nhỏ nhưng “trúng đích”. (1) Theo A/B rule, chỉ đổi **một biến** trong funnel: tăng `top_k_search` (10 → 15) trước rerank để xem recall/completeness có cải thiện ổn định không, tránh “đổ lỗi cho model” khi thực ra thiếu evidence. (2) Với failure mode kiểu q09 (mã lỗi), mình sẽ đề xuất **bổ sung dữ liệu**: thêm một tài liệu “error code reference” hoặc FAQ chứa các mã lỗi phổ biến và hướng xử lý. Nếu không thể bổ sung dữ liệu, mình sẽ chốt policy “abstain rõ ràng + hướng dẫn bước tiếp theo” để tránh hallucination và tối ưu điểm phần anti-hallucination trong grading.

