# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Ngô Hồng Hà 
**Vai trò trong nhóm:** Retrieval OwnerOwner  
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?
- Trong lab này, tôi chủ yếu tham gia vào Sprint 2 và Sprint 3 của pipeline. Công việc chính của tôi là thiết kế và triển khai các phương pháp retrieval, bao gồm dense retrieval, sparse retrieval và hybrid retrieval nhằm cải thiện chất lượng tìm kiếm tài liệu trong hệ thống RAG. Phần công việc của tôi phụ thuộc vào bước indexing trước đó do thành viên Khánh thực hiện, cụ thể là quá trình chunking dữ liệu, tạo embedding và lưu trữ vector vào database. Sau khi hoàn thiện các hàm retrieval, tôi tích hợp chúng vào pipeline chung để đảm bảo hệ thống có thể truy xuất dữ liệu hiệu quả. Kết quả từ phần retrieval của tôi là đầu vào quan trọng để nhóm Eval tiếp tục đánh giá hiệu năng của toàn bộ hệ thống.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.
- Hybrid Retrieval: cơ bản thì hybrid retrieval là sự kết hợp của 2 phương pháp tìm kiếm và trích xuất dữ liệu là Dense retrieval và Sparse retrieval. Hybrid sẽ khắc phục điểm yếu sợ các từ khóa chính xác của Dense, nhưng cũng xử lý được các câu hỏi mơ hồ hoặc sử dụng các từ đồng nghĩa. Hybird hoạt động bằng cách merge kết quả của Dense và Sparse, sau đó ranking bằng RRF score để lấy về top-k chunk. Tuy có độ chính xác cao, nhưng trade off lại là latency lớn hơn khi phải tính toán 2 lần, đồng thời rủi ro nếu 1 trong 2 phương pháp Dense hoặc Sparse fail, Hybrid cũng sẽ fail theo.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Trong quá trình implement hybrid retrieval, do cách đánh id cho các doc sai, các keys trong dict không khớp với trong doc_score nên trả về emty list. Dẫn đến khi test với retrieval mode là hybrid, câu trả lời luôn rỗng. Ban đầu tôi nghĩ vấn đề nằm ở hàm rag_answer hoặc logic RRF, nhưng thực tế nó lại là lỗi đọc dict đơn giản

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** "Khi làm việc remote, tôi phải dùng VPN và được kết nối trên tối đa bao nhiêu thiết bị?"

**Phân tích:**

Baseline trả lời đúng nhưng chưa đủ ý. Câu hỏi này yêu cầu retriver phải lấy được chunk từ 2 tài liệu khác nhau, tuy nhiên khi chạy thử với cả 3 mode, kết quả đều chỉ citation được trong cùng 1 tài liệu. Lý do có thể là do top-k quá nhỏ, khiến cho các tài liệu quan trọng bị bỏ sót. Variant Hybrid cũng không cải thiện được, vì trong data, các từ khóa là các từ đồng nghĩa, nên sparse không thể làm tốt, cũng như do top-k nhỏ nên bị bỏ sót. 

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."
Tôi sẽ thử tăng top-k lên và phát triển thêm phương pháp reranking. Với kết quả của câu hỏi grading question ở trên, tham số top-k đang cho thấy sự kém hiệu quả, tuy nhiên nếu tăng top-k với bộ dữ liệu tương đối nhỏ có thể dễ gây nên tình trạng nhiễu. Vì vậy, có thể áp dụng thêm phương pháp reranking để giải quyết vấn đề, 
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
