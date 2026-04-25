# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Việt Phương
**Vai trò trong nhóm:** Retrieval Owner 
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)


Chủ yếu làm Sprint 2, file index.py và rag_answer.py phần rerank
Là công việc quan trọng vì việc phân chia data thành các chunk không bị mất thông tin và ngữ nghĩa là điều kiện tiên quyết để các bước sau có thể thực hiện đúng 
_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)



Qua lab này tôi hiểu rõ hơn về indexing pipeline. 
Về cơ bản, đó là quá trình biến data (text, pdf, word,...) thành tập các chunk nhỏ hơn, mỗi chunk chứa 1 mảnh thông tin, sau đó mã hóa chúng thành các vector và lưu lại database.
Thực tế, mặc dù các llm hiện nay có khả năng nhận input rất lớn, context window có thể đạt 2M token hoặc hơn, tuy nhiên nếu làm thế sẽ rất tốn tài nguyên, thời gian và chi phí. AI còn có thể phải gọi lại những input đó cho những câu trả lời sau nên rất dễ bị quá tải, dẫn đến ảo giác, không biết nên cái gì quan trọng để nhớ vì có quá nhiều dữ liệu thừa.

Những chiến lược bao gồm Fixed-size chunking, Recursive chunking, Sementic chunking, ngoài ra còn có Parent-child chunking. 

Fixed-size chunking sẽ cắt cố định 1 số lượng token. Dễ hiểu và làm, nhưng cũng dễ sai; cắt "không | đúng" thì nghĩa của câu mất hết

Recursive chunking cố gắng cắt sao cho câu từ hoàn thiện nhất có thể. Ưu tiên cắt đoạn, nếu không được sẽ cắt dấu xuống dòng cho đến cắt câu. Cắt thế này khá hợp lý dưới góc nhìn con người

Sementic chunking cũng gần giống recursive ở điểm sẽ ưu tiên cắt đoạn; nhưng ở đây đúng hơn là cắt cấu trúc của tài liệu: nếu sub-heading là phân mục nhỏ nhất của tài liệu, nội dung từng sub-heading sẽ nằm hết trong 1 chunk, không quan trọng kích cỡ

Parent-child chunking cắt văn bản thành các chunk bé (vd từng câu một), nhưng sẽ thêm các chunk to hơn đóng vai trò Parent. Khi tìm trúng 1 chunk child, sẽ gửi về nguyên chunk parent để llm xem xét


_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)


Kỳ vọng sẽ ít gặp lỗi vặt hơn, thực tế team và cá nhân gặp khá nhiều lỗi vặt dẫn đến chậm triển khai. Kết hợp với thiếu API dẫn đến việc testing thiếu hiệu quả. Một vài lỗi khiến cá nhân thấy phiền phức nhất: quản lý git chưa đủ tốt, tạo môi trường python còn lắm lỗi, dùng model local yêu cầu download lại model dù đã có từ lab trước.
_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)



Câu hỏi thấy thú vị: Công ty sẽ phạt bao nhiêu nếu team IT vi phạm cam kết SLA P1?

Baseline chỉ trả lời ngắn gọn: Tôi không có thông tin này
Không hẳn là lỗi, tuy nhiên hoàn toàn có thể trả lời dài hơn 1 chút: thừa nhận không biết, có thể đưa tài liệu liên quan nhưng khẳng định đó không phải là cái bạn hỏi, hay gợi ý mở để người dùng đưa thêm thông tin. Phần này là do generation, system prompt đã được viết rất chặt chẽ, cũng vì thế mà câu trả lời đã ngắn như vậy.


---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Nếu có thêm thời gian, tôi sẽ thử cách indexing khác, ví dụ parent-child chunking. Format của dữ liệu đầu vào khá phù hợp với kiểu indexing này, tuy nhiên bản thân cách chunking theo từng phần này cũng đã đủ tốt trong giới hạn lab. Metadata sẽ cần thêm 1 chút, ngoài sự trùng lặp về thời gian, department cũng đã bị lặp ở 2 chỗ, có thể ảnh hưởng đến việc tìm kiếm chunk phù hợp ở bước sau, phần này hoặc data đầu vào hoặc metadata có thêm phân biệt giữa IT helpdesk và IT support sẽ tốt hơn. 
_________________

---

`*
