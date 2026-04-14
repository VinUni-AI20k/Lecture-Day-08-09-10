# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Khánh Nam

**Vai trò trong nhóm:** Tech Lead  

**Ngày nộp:** 13/4/2026

**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Mô tả cụ thể phần bạn đóng góp vào pipeline:
> Sprint nào bạn chủ yếu làm?

Làm sprint 1 nhiều nhất, và một ít sprint 2 + 3

> Cụ thể bạn implement hoặc quyết định điều gì?

Implement toàn phần indexing, thiết kế và chỉnh sửa system prompt, chỉnh sửa import+code của file rag_answer.py, test baseline and variants strategies

> Công việc của bạn kết nối với phần của người khác như thế nào?

> Việc làm indexing xong sớm và tốt đã giúp xây dựng và test retrieval strategy nhanh chóng hơn, giúp cả team đẩy nhanh tiến độ. Sau khi làm xong phần của mình, tôi giúp các thành viên khác hoàn thiện phần của họ và giải thích pipeline để team không chỉ code được mà còn hiểu thêm code làm gì và như thế nào.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Concept thứ nhất mà tôi đã hiểu rõ hơn là query transformation. Chúng ta thực hiện điều này để làm cho query đầy đủ ngữ nghĩa hơn, toàn diện hơn, và dễ search hơn. Nếu làm tốt có thể tăng recall.

Concept thứ hai mà tôi đã hiểu rõ hơn là hybrid retrieval pipeline. Để trả lời query của user, chúng có thể tùy chọn transform query, sau đó dùng query đó để thực hiện dense retrieval bằng vector embedding, và thực hiện sparse retrieval qua BM25. Sau đó ta sẽ hợp nhất hai tập đó lại (loại dedup dùng id của document) và thực hiện rerank (ở đây dùng cross-encoder), do rerank, dù chính xác hơn, nhưng lại tốn nhiều thời gian và tài nguyên hơn. Do đó ta cần một tập document nhỏ và tồn đọng hơn, chính là kết quả của dense và sparse retrieval. Sau đó ta apply grounded prompt và để LLM trả lời. 

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Thực ra phần lab này diễn ra khá suôn sẻ và nhóm không gặp nhiều bước cản lớn, do guide lab khá dễ hiểu và follow. Tuy nhiên, tôi có phần ngạc nhiên ở phần nhóm dùng LLM để đánh giá completeness, faithfullness, recall, và relevance. Ở phần này, nhóm dùng baseline chỉ có dense retrieval, nhưng retrieval metric của strategy này lại có trung bình cao hơn strategy variant dùng hybrid retrieval. Giả thuyết ban đầu của tôi là do system prompt chưa đúng, vì dù sao tôi cũng chưa tinh chỉnh nó. Nhưng mà nếu system propmt tốt hơn thì baseline cũng sẽ tốt hơn, và sự khác biệt giữa hai strategy này vần sẽ tồn tại. Thực tế, lý do khả thi hơn là do các test case đều không có quá nhiều ví dụ cần match cụ thể nhiều từ khóa giống chính xác như trong các chunk. Ví dụ như các điều khoản chẳng hạn. Với dataset to hơn, và khi cần tìm nhiều cụm từ chính xác cụ thể hơn, thì phần sparse retrieval trong hybrid sẽ có tác dụng tốt hơn.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** Câu 09: "ERR-403-AUTH là lỗi gì và cách xử lý?", expected answer: "Không tìm thấy thông tin về ERR-403-AUTH trong tài liệu hiện có. Đây có thể là lỗi liên quan đến xác thực (authentication), hãy liên hệ IT Helpdesk.",
**Phân tích:** Tôi thấy câu hỏi này hay bởi vì nó vừa test xem model có tự halulu và bịa câu trả lời không (faithfulness), và vừa xem system prompt của hệ thống có đủ tốt để graceful degradation không.

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Nếu có thêm thời gian, tôi sẽ thử tạo thêm test question mà để trả lời, cần thu thập document bao gồm các cụm chính xác hơn là các cụm chứa ngữ nghĩa thích hợp. Với có thể tôi sẽ thử thêm một số chiến thuật sparse retrieval và rerank khác.

_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
