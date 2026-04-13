# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Mã Khoa Học  
**Vai trò trong nhóm:**  Eval Owner 
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Trong lab này em làm chính ở Sprint 4, phụ trách phần đánh giá kết quả (evaluation). Em viết và chỉnh `manual_eval.py` để chạy 10 câu hỏi test, sau đó chấm 4 điểm: faithfulness, relevance, context recall và completeness. Em cũng tách rõ 2 cấu hình để so sánh A/B: baseline dùng dense, variant dùng hybrid, cùng top_k và không bật rerank để so sánh công bằng.

Sau khi chạy, em xuất kết quả ra thư mục `results/` dưới dạng markdown và csv để cả nhóm dễ xem. Em đọc từng câu trả lời để xem câu nào tốt hơn, câu nào tệ hơn, rồi ghi lại lý do. Công việc của em giúp nhóm biết thay đổi ở retrieval có thực sự làm pipeline tốt hơn hay không, thay vì chỉ đoán theo cảm giác.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Sau lab này em hiểu rõ hơn một điều: lấy đúng tài liệu chưa chắc trả lời đã tốt. Trong kết quả của nhóm, context recall gần như luôn 5/5, nhưng faithfulness chỉ quanh 2/5. Nghĩa là hệ thống thường lấy đúng nguồn, nhưng câu trả lời vẫn có thể lệch ý hoặc chưa bám sát bằng chứng.

Em cũng hiểu rõ hơn về evaluation loop. Mình không cần công cụ quá phức tạp mới bắt đầu đánh giá. Chỉ cần chấm theo bộ tiêu chí thống nhất và so sánh baseline với variant là đã thấy vấn đề ở đâu. Cách làm này giúp nhóm sửa đúng chỗ: nếu lỗi ở retrieval thì chỉnh retrieval, nếu lỗi ở cách trả lời thì chỉnh prompt hoặc bước generation.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Điều làm em bất ngờ là hybrid không tốt hơn dense ở mọi mặt. Em nghĩ đổi sang hybrid thì điểm sẽ tăng đều, nhưng thực tế không phải vậy. Faithfulness chỉ tăng nhẹ, completeness giữ nguyên, còn relevance lại giảm. Ví dụ câu q10 bị giảm relevance khá mạnh.

Phần khó nhất là debug các câu “đã lấy đúng source nhưng điểm vẫn thấp”. Lúc đầu em nghĩ do thiếu tài liệu hoặc lỗi index. Nhưng khi kiểm tra lại, source kỳ vọng đã có đủ. Vậy nên lỗi chính nằm ở cách model trả lời: có lúc nói chưa đúng trọng tâm, có lúc diễn đạt khác ý expected answer. Từ đó em rút ra là cần cải thiện bước generate, không chỉ retrieval.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** q07 - "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Với baseline dense, câu q07 có điểm 2/3/5/2. Điểm recall là 5, tức là hệ thống đã lấy đúng tài liệu liên quan. Nhưng câu trả lời lại chưa nêu đúng ý chính mà đề bài cần: tài liệu cũ đã đổi tên thành `Access Control SOP`. Vì vậy completeness thấp.

Sang variant hybrid, điểm thành 4/3/5/2. Faithfulness tăng, nghĩa là câu trả lời bám vào dữ liệu lấy về tốt hơn. Tuy nhiên completeness vẫn thấp vì vẫn chưa trả lời đúng trọng tâm “tài liệu nào”. Như vậy, retrieval đã ổn nhưng generation chưa ổn. Từ câu này, em thấy nếu chỉ nhìn một metric thì dễ hiểu sai kết quả. Cần nhìn cùng lúc recall, faithfulness và completeness mới biết hệ thống đang yếu ở đâu.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Nếu có thêm thời gian, em sẽ làm 2 việc rõ ràng. Một là thêm bước rerank để ưu tiên đoạn nào chứa thông tin đổi tên tài liệu hoặc mapping. Hai là sửa prompt để model trả lời thẳng vào ý chính trước, rồi mới giải thích sau. Em chọn 2 hướng này vì kết quả hiện tại cho thấy hệ thống không thiếu source, mà chủ yếu trả lời chưa đúng trọng tâm.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
