# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Đặng Quang Huy
**Vai trò trong nhóm:** RAG OWNER
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Trong lab này, tôi tham gia trực tiếp vào **Sprint 1** và **Sprint 4**. Ở Sprint 1, tôi làm phần xây dựng index trong `index.py`: preprocess tài liệu, chunk theo heading/paragraph, gắn metadata quan trọng như `source`, `section`, `effective_date`, `department`, `access`, rồi embed và lưu vào ChromaDB. Tôi cũng kiểm tra chất lượng index bằng `list_chunks()` và `inspect_metadata_coverage()` để chắc rằng dữ liệu vào vector store không bị cắt giữa điều khoản. Sang Sprint 4, tôi hỗ trợ chạy evaluation, so sánh baseline với các biến thể retrieval, và ghi kết quả scorecard/log để nhóm có số liệu thật khi viết báo cáo.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Sau lab này, tôi hiểu rõ hơn hai concept: **chunking** và **retrieval**. Trước đây tôi nghĩ chunking chỉ là chia file thành đoạn nhỏ, nhưng khi làm thật mới thấy chunking là quyết định giữ hay mất ngữ cảnh. Nếu chunk quá ngắn thì thiếu chi tiết; nếu quá dài thì context bị loãng và LLM dễ bỏ sót điểm quan trọng. Retrieval cũng vậy: dense search không phải lúc nào cũng thắng, vì nó có thể “đúng nghĩa” nhưng bỏ qua alias, tên cũ hoặc keyword đặc thù. Hybrid, rerank và query transform là các cách khác nhau để cải thiện bước lấy evidence trước khi sinh câu trả lời. Tôi đặc biệt thấy rõ rằng chất lượng answer phụ thuộc rất nhiều vào chất lượng context được retrieve, chứ không chỉ phụ thuộc vào model sinh câu trả lời.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Khó khăn lớn nhất của tôi là phần **finetuning theo nghĩa tinh chỉnh pipeline** chứ không phải train model. Ban đầu tôi nghĩ chỉ cần thêm hybrid hoặc rerank là kết quả sẽ cải thiện rõ rệt, nhưng thực tế không đơn giản như vậy. Với bộ test nhỏ của nhóm, dense baseline đã đạt recall rất cao, nên hybrid không cải thiện nhiều. Khi thử rerank và query transform, tôi thấy điểm số có thể tốt hơn ở một số câu, nhưng latency tăng lên khá rõ. Điều này làm tôi nhận ra rằng “tối ưu” không đồng nghĩa với “thêm nhiều biến hơn”, mà phải đổi đúng một biến và đo lại cẩn thận. Tôi cũng mất thời gian để debug chuyện model load và cache, vì reranker có thể làm thời gian chạy tăng mạnh nếu không kiểm soát tốt.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** "Escalation trong sự cố P1 diễn ra như thế nào?"

**Phân tích:**

Ở câu này, baseline dense trả lời chưa đúng hoàn toàn. Điểm của baseline cho câu q06 là faithfulness 5, relevance 3, completeness 1: câu trả lời có bám tài liệu nhưng lại đi sang quy trình escalation khác, nên thiếu chi tiết cốt lõi mà expected answer yêu cầu. Tôi xem đây là lỗi nằm giữa **retrieval và generation**: retrieval vẫn kéo được tài liệu liên quan, nhưng phần context được chọn và cách model diễn giải chưa đủ đúng trọng tâm. Khi chuyển sang biến thể rerank, câu trả lời cải thiện rõ hơn: model nêu đúng mốc 10 phút và tự động escalate theo mô tả expected answer, nên completeness tăng mạnh. Điều này cho tôi thấy rerank không chỉ giúp “đổi thứ tự chunk”, mà còn giúp prompt nhận đúng evidence quan trọng hơn để answer đi đúng hướng. Với câu này, rerank có tác dụng rõ hơn hybrid.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Nếu có thêm thời gian, tôi sẽ thử **tinh chỉnh query transform rules theo alias thực tế** và thêm cache/warmup cho reranker để giảm latency. Ngoài ra, tôi muốn viết thêm một bộ test nhỏ cho các câu kiểu “tên cũ/tên mới” như Approval Matrix → Access Control SOP, vì đây là nhóm query dễ làm lộ điểm yếu của dense baseline. Nếu làm tiếp Sprint 4, tôi cũng sẽ thử chấm thủ công một vài câu bằng rubric cố định để so sánh với scorecard hiện tại.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
