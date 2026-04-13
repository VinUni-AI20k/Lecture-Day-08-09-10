# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyen Thi Ngoc  
**Vai trò trong nhóm:** Documentation Owner (hỗ trợ Eval), sprint 4, fix bugs, enhancement 
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab Day 08, mình tập trung vào phần **tài liệu hoá + tổng hợp bằng chứng đánh giá** để nhóm có thể giải thích rõ pipeline thay vì chỉ “chạy được”. Cụ thể, mình hoàn thiện `docs/architecture.md` bằng cách mô tả đầy đủ kiến trúc end-to-end (index → ChromaDB → retrieve/rerank → grounded prompt → LLM), quyết định chunking (chunk size/overlap/strategy) và cấu hình baseline/variant. Đồng thời mình điền `docs/tuning-log.md` dựa trên kết quả thực tế trong `results/scorecard_baseline.md` và `results/scorecard_variant.md`: ghi lại giả thuyết, A/B rule, bảng delta theo 4 metrics, và nhận xét trade-off để nhóm thống nhất hướng tune tiếp. Mình cũng hỗ trợ phần báo cáo nhóm (`reports/group_report.md`) bằng cách tóm tắt “key decisions” và cách đọc scorecard để người chấm thấy được reasoning và evidence.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, mình hiểu rõ hơn sự khác nhau giữa **retrieval quality** và **generation quality** khi debug RAG. Trước đây mình hay nhìn câu trả lời “đúng/sai” theo cảm giác, nhưng scorecard buộc mình tách ra: (1) **Context Recall** nói về “có retrieve đúng evidence không”, (2) **Faithfulness** nói về “có bịa ngoài evidence không”, còn (3) **Answer Relevance** và (4) **Completeness** nói về “trả lời đúng trọng tâm và đủ điều kiện/ngoại lệ chưa”. Nhờ vậy, mình thấy một hệ có thể rất grounded (faithfulness cao) nhưng vẫn “lệch câu hỏi” hoặc thiếu điều kiện vì evidence top-k chưa bao phủ hết. Mình cũng hiểu rõ hơn “funnel” search rộng → chọn top nhỏ: top_k_search, rerank, và top_k_select không phải tham số phụ, mà ảnh hưởng trực tiếp đến việc câu trả lời có đủ và đúng hay không.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm mình ngạc nhiên là **tuning có thể cải thiện một metric nhưng làm xấu metric khác**, và nếu không ghi log A/B thì rất dễ tự thuyết phục sai. Trong kết quả của nhóm, variant tăng rõ **faithfulness/relevance** nhưng lại giảm **completeness** ở một số câu. Lúc đầu mình tưởng “bật thêm hybrid + rerank + query expansion” sẽ chỉ tốt hơn, nhưng thực tế khi giới hạn top-3 chunks, pipeline có thể chọn đúng đoạn liên quan nhất nhưng bỏ mất các đoạn chứa ngoại lệ hoặc bước quan trọng. Khó khăn lớn nhất là viết tài liệu sao cho “khớp code + khớp kết quả”: phải đọc scorecard để tìm câu yếu nhất, sau đó liên hệ ngược lại với quyết định retrieval/chunking. Mình nhận ra nếu tài liệu không nêu rõ giả thuyết và evidence, thì phần tuning sẽ giống “đổi tham số may rủi” và người chấm khó tin kết luận.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q10 (Refund)

**Phân tích:**

Trong `results/scorecard_baseline.md`, q10 có **Faithfulness 4/5** nhưng **Answer Relevance chỉ 1/5**. Điều này gợi ý baseline (dense) có thể retrieve được một đoạn policy liên quan, nhưng **câu trả lời lại không bám đúng trọng tâm câu hỏi** (ví dụ trả lời chung chung về hoàn tiền thay vì đúng điều kiện/khung thời gian cụ thể mà câu hỏi cần). Vì faithfulness vẫn cao, lỗi nhiều khả năng nằm ở **retrieval/select** (top-3 chưa đúng phần cần) hoặc **prompting** (hướng dẫn trả lời chưa ép “trả lời đúng câu hỏi” đủ mạnh), hơn là lỗi “bịa”. Ở variant (`results/scorecard_variant.md`), q10 có **Faithfulness 5/5** và **Relevance 5/5** nhưng **Completeness 1/5**. Mình hiểu là variant đã chọn được đoạn đúng trọng tâm hơn (relevance tăng mạnh), tuy nhiên lại **thiếu các ý phụ/ngoại lệ** cần để hoàn chỉnh câu trả lời theo expected_answer. Hướng sửa hợp lý (đúng A/B rule) là giữ retrieval_mode tốt (hybrid) nhưng thử **tăng top_k_search trước rerank** hoặc **tăng top_k_select từ 3 lên 4** để bổ sung coverage, rồi đo lại completeness.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Mình sẽ đề xuất 2 thử nghiệm nhỏ theo A/B rule. (1) Giữ retrieval_mode="hybrid" và use_rerank=True, nhưng tăng `top_k_search` (10 → 15) để reranker có nhiều candidates hơn trước khi chọn top-3, kỳ vọng tăng completeness mà vẫn giữ relevance. (2) Nếu vẫn thiếu điều kiện/ngoại lệ, giữ top_k_search=10 nhưng tăng `top_k_select` (3 → 4) để context block bao phủ tốt hơn; sau đó so sánh lại 4 metrics trong scorecard để xác định biến nào thật sự cải thiện. Song song, mình sẽ cập nhật tuning-log với “câu nào được cải thiện và vì sao” để kết luận có bằng chứng, tránh chỉnh tham số theo cảm tính.

