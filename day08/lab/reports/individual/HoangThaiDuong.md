# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Hoàng Thái Dương  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 13/04/2026 
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Trong lab này, tôi phụ trách phần Sprint 4, bao gồm: evaluation và scorecard cho toàn bộ pipeline RAG. Công việc của tôi là đọc yêu cầu trong `README.md` và `SCORING.md`, sau đó hoàn thiện phần chấm điểm trong `eval.py` để hệ thống có thể chạy end-to-end trên 2 bộ câu hỏi test là `test_questions.json` và bộ `grading_questions.json`. 
> Tôi triển khai cơ chế chấm 4 tiêu chí gồm faithfulness, answer relevance, context recall và completeness; đồng thời bổ sung phương pháp AI-as-Judge bằng OpenAI để giúp đánh giá output chính xác và công bằng hơn. Ngoài ra, tôi cũng cấu hình baseline và variant, chạy A/B comparison, sinh các file `scorecard_baseline.md`, `scorecard_variant.md`, `ab_comparison.csv` và `logs/grading_run.json`. Kết nối trực tiếp với code retrieval/generation của các bạn khác, vì chính kết quả evaluation là căn cứ để nhóm quyết định giữ baseline hay thử thêm variant.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Tôi nhận ra evaluation trong RAG không chỉ đơn giản là đánh giá xem output của mô hình là đúng hay sai. Một hệ thống có thể retrieve đúng tài liệu nhưng vẫn trả lời kém nếu context đưa vào prompt không đủ tốt hoặc model quá dễ hallucinate. 
> Tôi cũng hiểu rõ hơn sự khác nhau giữa bốn metric. Context recall dùng để kiểm tra retriever có kéo được đúng nguồn không, còn faithfulness kiểm tra model có bịa ra ngoài context hay không. Relevance đo mức độ bám sát câu hỏi, còn completeness đo việc câu trả lời có đủ các ý quan trọng không. Trước đây tôi nghĩ chỉ cần precision và recall cao là hệ thống ổn, nhưng sau khi thử nghiệm nhiều lần tôi thấy recall có thể đạt tối đa mà answer vẫn thiếu ý hoặc sai hướng nếu generation chưa được kiểm soát tốt.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Tôi nhận ra evaluation trong RAG không chỉ đơn giản là đánh giá xem output của mô hình là đúng hay sai. Một hệ thống có thể retrieve đúng tài liệu nhưng vẫn trả lời kém nếu context đưa vào prompt không đủ tốt hoặc model quá dễ hallucinate. 
> Tôi cũng hiểu rõ hơn sự khác nhau giữa bốn metric. Context recall dùng để kiểm tra retriever có kéo được đúng nguồn không, còn faithfulness kiểm tra model có bịa ra ngoài context hay không. Relevance đo mức độ bám sát câu hỏi, còn completeness đo việc câu trả lời có đủ các ý quan trọng không. Trước đây tôi nghĩ chỉ cần precision và recall cao là hệ thống ổn, nhưng sau khi thử nghiệm nhiều lần tôi thấy recall có thể đạt tối đa mà answer vẫn thiếu ý hoặc sai hướng nếu generation chưa được kiểm soát tốt.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** `gq07` — “Công ty sẽ phạt bao nhiêu nếu team IT vi phạm cam kết SLA P1?”

**Phân tích:** 
Đây là câu tôi thấy đáng chú ý nhất vì nó kiểm tra đúng failure mode nguy hiểm nhất của RAG: hallucination. Trong tài liệu `sla_p1_2026.txt`, hệ thống chỉ có thông tin về SLA, escalation, hotline on-call và lịch sử phiên bản; hoàn toàn không có điều khoản nào nói về mức phạt khi vi phạm SLA. Tuy nhiên ở một lần chạy baseline, answer lại trả về một mức phạt cụ thể, làm điểm faithfulness rơi xuống 1/5. Điều này cho thấy retriever không phải là vấn đề chính, vì source đúng vẫn được lấy về; lỗi nằm ở generation và chính sách abstain. Model đã suy diễn từ kiến thức chung thay vì chỉ bám vào context được retrieve.

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> Nếu có thêm thời gian, tôi muốn thử thêm nhiều phương pháp mới để cải thiện pipeline một cách có hệ thống thay vì chỉ tối ưu một điểm đơn lẻ. Cụ thể, tôi muốn thử thêm rerank sau retrieval để giảm noise ở các câu nhiều ngữ cảnh giống nhau, thử query decomposition cho các câu hỏi nhiều vế, và thử cải tiến prompt theo hướng bắt buộc model trả lời đủ từng ý thay vì trả lời ngắn hoặc abstain quá sớm. Ngoài ra, tôi cũng muốn mở rộng bộ evaluation để đo riêng các lỗi như hallucination, thiếu ý và nhầm ngữ cảnh, vì đây là các lỗi xuất hiện khá rõ trong quá trình chạy scorecard của nhóm.

_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
