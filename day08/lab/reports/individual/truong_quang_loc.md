# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trương Quang Lộc  
**Vai trò trong nhóm:** Retrieval Owner
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm: 2, 3
> - Cụ thể bạn implement hoặc quyết định điều gì: 
> + Sprint 2: retrieve_dense(), call_llm(), rag_answer()
> + Sprint 3: transform_query()
> - Công việc của bạn kết nối với phần của người khác như thế nào: Pair-coding cùng Tiến (Tech Lead), mở rộng transform_query sang để LLM quyết định luôn trọng số khi dùng Hybrid (dense:sparse)

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)
> Tôi hiểu rõ hơn phần: rerank, transform query, hybrid search
> Việc lựa chọn search strategy thực sự quan trọng để có thể lấy được đúng dữ liệu. Dữ liệu lấy sai sẽ dẫn đến LLM đưa câu trả lời sai cho người dùng. Đôi khi tỷ lệ sparse:dense thay đổi một chút cũng ảnh hưởng đến việc có lấy đúng kết quả hay không.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Thử nhiều cách RAG vẫn không thể trả lời được 1 câu hỏi, debug thì mới biết là do ở bước chunking để bỏ sót không chunking phần thông tin đó
> Lỗi chunking bỏ sót thông tin, dẫn đến việc RAG không thể tìm được thông tin đó dù thử cách gì
> Giả thuyết là vì tỷ lệ dense search đang lớn, trong khi câu trả lời lại chứa keyword. Nhóm đã thử cho trọng số sparse search nhiều hơn nhưng vẫn không có kết quả.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> **Câu hỏi:**: q07: Approval Matrix để cấp quyền hệ thống là tài liệu nào?
> **Phân tích:**
> - Baseline lúc đầu trả lời sai
> - Lỗi nằm ở: bước indexing đã bỏ sót thông tin ở mục "chú ý", mục này không nằm trong section nào nên thuật toán chunking đã bỏ qua 
> - Variant có cải thiện, nhưng chủ yếu vì ở bước retrieve đã lấy đúng chunk

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

> Tôi sẽ ưu tiên sửa chunking/indexing trước khi thử thêm kỹ thuật mới, vì kết quả test cho thấy có câu vẫn “không đủ dữ liệu” dù tài liệu liên quan đã được retrieve 
> Tìm cách đảm bảo toàn bộ nội dung tài liệu đều được chunking, và chunking một cách tối ưu (đủ ngữ nghĩa, cấu trúc). Vd bài này tôi sẽ bổ sung rule chunk cho các mục không có section title và kiểm tra lại coverage theo từng tài liệu.
> Bổ sung thêm metric đo bằng tỉ lệ câu trả lời đúng nguồn thay vì chỉ nhìn answer text.
_________________


