# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Đức Anh  
**Vai trò trong nhóm:** Retrieval Owner
**Ngày nộp:** 13/04/2026 
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

- Trong phần lab này, tôi phụ trách phần Sprint 3 - Sử dụng hybrid retrieval strategy dense + sparse để lấy thông tin trong tài liệu.
- Ngoài role chính là Retrieval Owner ra, một role nhỏ khác của tôi là kiểm soát và tổ chức các source code cho đồng đội để merge hiệu quả.
- Ở Sprint 3, tôi phát triển một strategy mới trong việc retrieve dữ liệu, cụ thể là retrieve_hybrid() để truy vấn dữ liệu bằng cách kết hợp 2 phương pháp dense và sparse, và bổ sung thêm vào các function của sprint 2 như call_llm() để sinh câu trả lời, rag_answer() để kết hợp context với prompt.
---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, công nghệ mới nhất tôi học được là việc hybrid 2 phương pháp retrieval là dense và sparse, nhận ra điểm mạnh và yếu của dense rằng việc chỉ retrieve bằng ngữ cảnh đôi lúc lại là con dao 2 lưỡi khi gặp những case thuần statistic và việc tích hợp sparse để tăng hiệu quả của việc retrieve dữ liệu. Không chỉ dừng lại ở việc kết hợp, việc tối ưu hóa mô hình còn nằm ở việc sử dụng bộ parameters ứng với từng loại usecases khác nhau, cụ thể với bài lab hôm nay là về FAQ nên việc ưu tiên hiểu context của người dùng qua dense có vẻ quan trọng hơn. Ngoài ra việc xử lý đúng dữ liệu (chunking) cũng góp phần ảnh hưởng tới khả năng của dense, như học liệu cũng nhấn mạnh việc xử lý dữ liệu đúng và chính xác ảnh hưởng lớn tới kết quả của model.
---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Hiện tại, tôi gặp khó khăn khi phân tích case gq05: dù đã thử cả dense retrieval và hybrid retrieval, câu trả lời vẫn bị trả về là "Không đủ dữ liệu". Sau khi xem lại dữ liệu gốc, tôi nhận ra đây không phải case chỉ cần tìm đúng một chunk, mà là bài toán tổng hợp nhiều mảnh thông tin trong cùng một tài liệu: Section 1 nói SOP áp dụng cho contractor, còn Section 2 mới chứa thông tin về Admin Access, thời gian xử lý và yêu cầu training. Điều tôi gặp khó là hybrid giúp tăng recall nhưng chưa đủ để model tự ghép các bằng chứng thành một kết luận chắc chắn. Trường hợp này làm tôi hiểu rõ hơn rằng semantic retrieval chỉ giải quyết một phần của vấn đề; muốn trả lời đúng còn cần chunking tốt hơn, evidence coverage rõ hơn và prompt khuyến khích model tổng hợp thông tin từ nhiều chunk thay vì abstain quá sớm.
_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** gq05 – “Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?”

**Trả lời**: Không đủ dữ liệu

**Phân tích:**
- Ở lớp data process, ground truth của gq05 là một câu trả lời tổng hợp: Section 1 nói SOP áp dụng cho contractor, còn Section 2 nói Level 4 Admin Access có approver, thời gian xử lý, và training. Nhưng doc không có câu explicit kiểu “contractor được phép Admin Access”, nên đây là bài toán suy luận từ scope + policy, không phải lookup một dòng duy nhất.

- Ở lớp chunking, `index.py` đang chunk theo section tự nhiên. Điều này tốt cho recall, nhưng Section 2 gom cả Level 1 đến Level 4 vào một chunk lớn, làm tín hiệu cho Level 4 bị “loãng” giữa nhiều level khác. Model phải tự tách đúng phần cần dùng, dễ dẫn tới thận trọng quá mức.

- Ở lớp hybrid RAG, `retrieve_hybrid()` chỉ fuse rank bằng RRF; nó tăng recall nhưng không thực hiện evidence composition. Nói cách khác, hybrid giúp “lấy đúng chunk”, nhưng không giúp “ghép đúng lập luận”. Khi `call_llm()` thấy câu hỏi cần kết luận chắc chắn mà không có câu explicit authorize contractor → Admin Access, nó có thể abstain theo prompt grounding.
_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

- Biến đổi thêm các parameters trong hybrid methods thành nhiều trường hợp để đánh giá sâu sắc hơn việc thay đổi các biến dense > sparse, sparse > dense, banlance ảnh hưởng như nào tới cách retrieving dữ liệu cũng như output của mô hình.
- Không chỉ thử trên retrieve, RAG còn được xây dựng trên index, việc kết hợp nhiều phương pháp khác nhau tạo ra một không gian đa dạng nhằm thí nghiệm trên nhiều use case khác nhau để học hỏi cũng như hiểu được rõ ràng hơn tính áp dụng của các phương pháp trên nhiều trường hợp khác nhau trong ứng dụng thực tế.
_________________

---
