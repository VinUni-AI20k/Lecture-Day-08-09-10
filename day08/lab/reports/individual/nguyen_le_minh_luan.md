# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Lê Minh Luân  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Với vai trò Eval Owner, tôi chủ yếu tham gia Sprint 3 và Sprint 4. Trong Sprint 3, tôi thiết kế bộ 10 câu hỏi kiểm thử (`data/test_questions.json`) bao gồm nhiều mức độ khó (easy, medium, hard) và nhiều category (SLA, Refund, Access Control, IT Helpdesk, HR Policy, Insufficient Context) để đảm bảo pipeline được đánh giá toàn diện. Tôi cũng xác định expected answer và expected sources cho từng câu. Trong Sprint 4, tôi implement 4 scoring functions trong `eval.py` theo phương pháp LLM-as-Judge: `score_faithfulness()`, `score_answer_relevance()`, `score_context_recall()`, và `score_completeness()`. Sau đó tôi chạy `run_scorecard()` cho cả baseline (dense) và variant (hybrid + rerank), rồi chạy `compare_ab()` để so sánh delta giữa hai cấu hình. Kết quả eval được tôi xuất ra `results/scorecard_baseline.md` và `scorecard_variant.md`, đồng thời tôi hỗ trợ Documentation Owner điền số liệu vào `docs/tuning-log.md`.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab, tôi hiểu sâu hơn hai khái niệm: **evaluation scorecard** và **faithfulness vs. completeness trade-off**. Trước đây tôi nghĩ đánh giá RAG chỉ cần kiểm tra "câu trả lời đúng hay sai", nhưng thực tế cần chia thành 4 chiều riêng biệt. Faithfulness đo xem model có bám vào context đã retrieve hay không — tức là có bịa thêm không. Completeness đo xem answer có bao phủ đủ thông tin expected hay không. Hai metric này có thể xung đột: một answer rất faithful (chỉ nói những gì trong context) có thể thiếu completeness nếu retriever bỏ lỡ document quan trọng. Tôi cũng nhận ra Context Recall là metric phát hiện lỗi retrieval sớm nhất — nếu recall thấp thì model không có chứng cứ để trả lời, lúc đó debug generation là vô nghĩa. Error Tree (Index → Retrieval → Generation) giúp tôi hệ thống hóa việc debug thay vì đoán ngẫu nhiên.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên nhất là câu q09 (ERR-403-AUTH) — câu mà pipeline lẽ ra phải abstain vì không có thông tin trong docs. Ở baseline (dense), pipeline lại tự tổng hợp thông tin từ document Access Control SOP để "trả lời" câu hỏi, cho ra faithfulness = 5 nhưng completeness chỉ = 3 so với expected answer (nên nói "Không đủ dữ liệu"). Khi chuyển sang variant (hybrid + rerank), pipeline lại trả về "Tôi không biết" — quá ngắn gọn, thiếu gợi ý hữu ích, dẫn đến faithfulness = 1 và relevance = 1. Tôi mất khá nhiều thời gian để hiểu rằng đây là vấn đề của grounded prompt: prompt yêu cầu "nếu không đủ context thì nói không biết" nhưng không hướng dẫn model cách abstain lịch sự (ví dụ: gợi ý liên hệ IT Helpdesk). Bài học là prompt cần có hướng dẫn abstain cụ thể hơn.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Câu q07 thuộc dạng **alias query** — người dùng hỏi bằng tên cũ "Approval Matrix" trong khi tài liệu thực tế có tên "Access Control SOP" (`access-control-sop.md`). Đây là câu khó (difficulty: hard) thiết kế để kiểm tra hybrid retrieval.

**Baseline (dense):** Faithfulness = 5, Relevance = 5, Context Recall = 5, Completeness = **2**. Dense retrieval tìm được đúng document (recall = 5/5) nhờ embedding nắm được ngữ nghĩa "approval matrix" ≈ "access control". Tuy nhiên, answer chỉ mô tả chung về quy trình cấp quyền mà **không nêu tên mới** của tài liệu là "Access Control SOP" — đây là thông tin quan trọng nhất mà expected answer yêu cầu.

**Variant (hybrid + rerank):** Kết quả gần như tương tự — Completeness vẫn = 2. Nghĩa là vấn đề **không nằm ở retrieval** (đã retrieve đúng document) mà nằm ở **generation**: prompt không yêu cầu model liên hệ tên tài liệu với alias mà người dùng sử dụng. Root cause là generation layer — grounded prompt cần thêm hướng dẫn: "Nếu người dùng dùng tên cũ/alias, hãy nêu rõ tên tài liệu hiện tại."

Đây là ví dụ điển hình cho thấy Context Recall cao không đảm bảo Completeness cao — retriever làm đúng nhưng generator chưa khai thác hết thông tin đã retrieve.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Cải thiện prompt cho abstain case:** Kết quả q09 cho thấy variant trả lời "Tôi không biết" quá cùn — tôi sẽ sửa grounded prompt để hướng dẫn model abstain lịch sự hơn, ví dụ: "Nếu không đủ thông tin, nêu rõ lý do và gợi ý kênh hỗ trợ phù hợp." Điều này sẽ cải thiện relevance và completeness cho các câu insufficient context.

2. **Thêm alias mapping trong prompt:** Từ kết quả q07 (completeness = 2 ở cả baseline và variant), tôi sẽ thêm instruction trong prompt yêu cầu model nhận diện alias/tên cũ và nêu tên tài liệu chính thức, để cải thiện completeness cho các dạng câu hỏi dùng thuật ngữ không còn chính xác.

---

*Lưu file này với tên: `reports/individual/nguyen_le_minh_luan.md`*
