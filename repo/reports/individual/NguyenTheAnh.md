# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Thế Anh  
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 520 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi đảm nhận vai trò Documentation Owner, chịu trách nhiệm hoàn thiện các tài liệu đánh giá và ghi chép experiment. Tôi đã điền đầy đủ `docs/tuning-log.md` dựa trên kết quả `eval.py`, cập nhật nhận xét chi tiết về baseline và variant, đồng thời so sánh các metric faithfulness, relevance, context recall và completeness. Tôi cũng hỗ trợ kiểm tra lại các bước yêu cầu trong README để đảm bảo toàn bộ Sprint 4 có đầy đủ bằng chứng bằng file `scorecard_baseline.md`, `scorecard_variant.md` và gợi ý variant tiếp theo. Công việc của tôi kết nối trực tiếp với nhóm Eval Owner và Retrieval Owner vì cần chuyển kết quả chạy pipeline thành bản ghi thực tế và kết luận rõ ràng.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab, tôi hiểu rõ hơn về vai trò của evaluation loop trong một pipeline RAG. Không chỉ cần index và retrieve tốt, chúng ta phải đánh giá từng metric để phát hiện đúng lỗi. Tôi nhận ra `context recall` có thể rất tốt nhưng không đảm bảo `completeness`, và điều đó cho thấy phần generation/prompt mới là điểm yếu chính. Bài học về cách viết tuning log rõ ràng và phân tách experiment cũng giúp tôi hiểu sâu hơn về việc ghi lại biến đổi, lý do chọn variant, và chứng minh A/B comparison một cách minh bạch.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều tôi ngạc nhiên là kết quả variant hybrid + rerank không nhất thiết tốt hơn baseline, mặc dù intuition ban đầu là retrieval tốt hơn sẽ giúp toàn bộ pipeline. Khó khăn lớn nhất là chuyển dữ liệu thô từ scorecard thành nhận xét ý nghĩa: cần so sánh từng metric và chỉ ra rằng recall 5/5 không đồng nghĩa với quality cao. Tôi ban đầu nghĩ việc tăng retrieval mạnh sẽ giải quyết hầu hết lỗi, nhưng thực tế cho thấy nhiều câu sai do generation vẫn giữ nguyên. Việc viết tuning log trở nên khó hơn khi phải giải thích rõ ràng “tại sao variant không hiệu quả” thay vì chỉ ghi số điểm.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — Approval Matrix để cấp quyền hệ thống là tài liệu nào?

**Phân tích:**
Baseline trả lời sai hoàn toàn ở câu q07 với faithfulness 1, relevance 2, completeness 1. Đoạn trả lời cho biết thông tin không tìm thấy trong tài liệu nội bộ, trong khi answer đúng cần chỉ ra rằng tài liệu Approval Matrix đã đổi tên thành Access Control SOP. Đây là lỗi generation/prompt, không phải retrieval, vì context recall vẫn đạt 5/5 và source liên quan đã được retrieve. Variant hybrid + rerank vẫn không cải thiện q07, điều này xác nhận rằng model không được hướng dẫn đúng để trích xuất và diễn đạt thông tin đã retrieve. Nhận xét này quan trọng vì nó phân biệt lỗi “có thông tin nhưng không dùng đúng” với lỗi “không tìm thấy source”. Do vậy, cần tối ưu prompt và cách tổ chức evidence, thay vì chỉ điều chỉnh retrieval strategy.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ đề xuất thêm hai cải tiến: (1) thử variant chỉ đổi `use_rerank=True` với `retrieval_mode="dense"` để tách tác động rerank ra khỏi hybrid; (2) tinh chỉnh prompt generation để bắt model trả lời từ nguồn đã retrieve, đặc biệt với các câu “no info” như q04 và q07. Kết quả eval cho thấy retrieval đã tốt, nên bước tiếp theo phải là tạo grounding prompt mạnh hơn.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
