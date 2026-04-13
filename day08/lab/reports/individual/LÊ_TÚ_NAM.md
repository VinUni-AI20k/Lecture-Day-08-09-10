# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Tú Nam 
**Vai trò trong nhóm:**  Retrieval Owner(sprint 1+3)
**Ngày nộp:** 13/4/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Em chủ yếu tham gia vào Sprint 3 của bài lab, tập trung vào việc cải thiện pipeline RAG thông qua các kỹ thuật tuning. Cụ thể, em đã implement các phương pháp retrieve_sparse (BM25), retrieve_hybrid (kết hợp dense và sparse bằng RRF), rerank bằng cross-encoder, và transform_query để mở rộng truy vấn. Ngoài ra, em cũng thử nghiệm các variant khác nhau nhằm so sánh hiệu quả so với baseline. Đối với Sprint 2( pipeline baseline) để làm mốc đánh giá,Sprint 3 xây dựng thêm các hàm, từ đó phân tích xem các cải tiến ở Sprint 3 có thực sự giúp nâng cao chất lượng retrieval và câu trả lời hay không.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Sau lab này, em hiểu rõ hơn về cách các phương pháp retrieval hoạt động và ảnh hưởng trực tiếp đến chất lượng câu trả lời trong hệ thống RAG. Đầu tiên là về chunking, đặc biệt là cách tiếp cận “heading-based + paragraph fallback”. Việc ưu tiên tách theo các heading tự nhiên giúp giữ được cấu trúc tài liệu, từ đó mỗi chunk mang ý nghĩa rõ ràng hơn và dễ trích dẫn khi sinh câu trả lời. Nếu section quá dài, mới tiếp tục chia nhỏ theo paragraph hoặc kích thước, giúp cân bằng giữa tính đầy đủ và độ chi tiết. Bên cạnh đó, em hiểu rõ sự khác biệt giữa dense, sparse và hybrid retrieval. Dense retrieval giúp nắm bắt ngữ nghĩa tốt, phù hợp với câu hỏi tự nhiên hoặc paraphrase, trong khi sparse retrieval lại mạnh ở việc match chính xác keyword như mã lỗi hoặc thuật ngữ kỹ thuật. Hybrid retrieval kết hợp cả hai, giúp cải thiện cả độ bao phủ (recall) và độ chính xác (precision), nên thường cho kết quả ổn định hơn trong thực tế.
_________________

---
## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?


Trong quá trình xây dựng hệ thống RAG, điều gây bất ngờ nhất là việc các metric đánh giá không tăng đồng thời như kỳ vọng. Ban đầu, em giả định rằng khi cải thiện retrieval (ví dụ chuyển sang hybrid), cả Answer Relevance và Faithfulness đều sẽ tăng. Tuy nhiên, thực tế cho thấy dù relevance được cải thiện, faithfulness lại có thể giảm do mô hình sinh bị “nhiễu” khi nhận quá nhiều thông tin từ nhiều nguồn, dẫn đến việc tổng hợp sai hoặc hallucination. Khó khăn lớn nhất là debug các lỗi liên quan đến môi trường và pipeline, đặc biệt là lỗi sai môi trường Python (venv) khiến thư viện không được nhận diện, gây mất nhiều thời gian xử lý. Ngoài ra, việc điều chỉnh pipeline như chọn số lượng chunk phù hợp, thiết kế prompt và kiểm soát output của LLM cũng không đơn giản. Qua đó, em nhận ra rằng giả thuyết “retrieval tốt hơn sẽ luôn cho câu trả lời tốt hơn” là chưa đủ, mà cần kết hợp chặt chẽ giữa retrieval, selection và generation để đạt kết quả tối ưu.
_________________


---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** q09 

**Phân tích:**
Ở câu hỏi này, cả baseline và các variant đều trả lời “Tôi không biết”, và đây là câu trả lời đúng theo yêu cầu của hệ thống RAG khi không có thông tin trong database. Điểm số đạt mức tối đa về faithfulness và correctness (1, 1, None, 1), cho thấy mô hình đã tuân thủ tốt nguyên tắc grounded answer, không tự bịa thông tin.

Về nguyên nhân, lỗi không nằm ở indexing, retrieval hay generation, mà nằm ở bản chất dữ liệu: câu hỏi này hoàn toàn không có trong tập tài liệu đã index. Retrieval (dù là dense hay hybrid) không thể tìm ra chunk liên quan, dẫn đến context block không đủ thông tin. Nhờ prompt được thiết kế đúng (có cơ chế abstain), mô hình đã chọn cách từ chối trả lời thay vì hallucinate.

Khi áp dụng các variant như hybrid retrieval hoặc rerank, kết quả không thay đổi. Điều này hợp lý vì các kỹ thuật này chỉ giúp cải thiện khi có dữ liệu liên quan trong corpus. Trường hợp này cho thấy hệ thống hoạt động đúng kỳ vọng: ưu tiên độ tin cậy hơn là cố gắng trả lời mọi câu hỏi.
_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."
Nếu có thêm thời gian, em muốn thử cải tiến bước rerank để tăng điểm Completeness. Hiện tại, việc dùng CrossEncoder có xu hướng chọn các chunk “relevant nhất” nhưng lại bỏ sót các thông tin bổ sung, dẫn đến câu trả lời chưa đầy đủ (Completeness ~3.9). Vì vậy, em muốn thử kết hợp thêm cơ chế diversity như MMR (Maximal Marginal Relevance) hoặc tăng số lượng chunk sau rerank. Lý do là kết quả eval cho thấy vấn đề không nằm ở thiếu relevance mà là thiếu độ bao phủ thông tin trong context.
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
