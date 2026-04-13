# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Nhật Vĩ  
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 2026-04-13 
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Trong lab Day 08, em đảm nhận vai trò **Documentation Owner**, chịu trách nhiệm hoàn thiện tài liệu kiến trúc và nhật ký tuning của nhóm ở Sprint 4. Cụ thể, em viết và chuẩn hóa hai file `docs/architecture.md` và `docs/tuning-log.md`, trong đó mô tả đầy đủ luồng Indexing -> Retrieval -> Generation -> Evaluation, các quyết định chunking/metadata, cấu hình baseline vs variant, bảng scorecard và kết luận A/B.

Ngoài phần tài liệu, em cũng tham gia trực tiếp vào `rag_answer.py` ở các khối quan trọng: `call_llm()` (cấu hình Gemini qua Vertex AI), `transform_query()` (expansion/HyDE), `rerank()` (LLM-based rerank), và `retrieve_hybrid()` (RRF dense+sparse). Vai trò của em kết nối phần code của Tech Lead/Retrieval Owner với phần phân tích của Eval Owner: em chuyển kết quả chạy thực nghiệm thành quyết định kỹ thuật có thể giải thích được và tái sử dụng cho lần sau.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Sau lab này, em hiểu rõ hơn hai điểm. Thứ nhất là hybrid retrieval không mặc định tốt hơn dense. Trước đây em nghĩ cứ thêm BM25 vào là tăng chất lượng. Nhưng qua A/B trong `tuning-log.md`, em thấy hybrid chỉ có ích khi tokenizer và dữ liệu phù hợp; với corpus tiếng Việt nhỏ, BM25 `.split()` có thể kéo nhiễu vào top-k và làm giảm Relevance/Completeness.

Thứ hai là evaluation loop mới là trung tâm của tuning. Nếu chỉ đọc vài câu trả lời thì rất dễ chủ quan. Khi nhìn theo từng metric (Faithfulness, Relevance, Context Recall, Completeness) và từng câu hỏi, em xác định được lỗi nằm ở retrieval hay generation thay vì đoán. Điều này giúp nhóm ra quyết định dựa trên bằng chứng: giữ baseline dense cho grading thay vì cố giữ variant chỉ vì “nghe có vẻ nâng cấp”.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Khó khăn lớn nhất với em là chuyển từ “ghi chép kết quả” sang “giải thích nguyên nhân kỹ thuật”. Ví dụ cùng một câu trả lời sai có thể đến từ chunking, retrieve sai hoặc prompt thiếu ràng buộc; nếu không bám Error Tree thì tài liệu tuning sẽ rất cảm tính. Em mất nhiều thời gian để đối chiếu kết quả scorecard với behavior thực tế của pipeline trong `rag_answer.py`.

Điều làm em ngạc nhiên là có những trường hợp **Context Recall vẫn cao nhưng answer vẫn kém**. Điều này xuất hiện khi chunk đúng có mặt trong danh sách retrieve, nhưng do xếp hạng top-3 hoặc do generation không tổng hợp đủ nên output vẫn sai/thiếu. Bài học rút ra là “retrieve được” chưa đủ, còn phải “đưa đúng ngữ cảnh vào prompt” và “ép model trả lời bám chứng cứ”.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** q07 - "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Đây là câu hỏi em thấy rõ nhất giá trị của việc phân tách lỗi theo tầng. Với **baseline dense**, hệ thống thường nhận ra mối liên hệ ngữ nghĩa giữa “Approval Matrix” và nội dung về quy trình cấp quyền trong `access_control_sop`, nên trả lời đúng hướng. Tuy nhiên có lần baseline bị trừ Faithfulness vì model thêm chi tiết không thật sự được nêu rõ trong context. Nghĩa là retrieval ổn nhưng generation còn “thêm mắm muối”.

Khi chuyển sang **variant hybrid (Dense + BM25 via RRF)**, kết quả không cải thiện như kỳ vọng. Trong log, q07 có hiện tượng giảm mạnh về Relevance/Completeness. Nguyên nhân chính là nhánh BM25 dựa trên tách từ đơn giản không xử lý tốt alias tiếng Anh trong ngữ cảnh tài liệu tiếng Việt, làm điểm fusion kéo một số chunk nhiễu lên trên. Mặc dù Context Recall tổng thể vẫn cao, top chunk đưa vào prompt lại không đủ “sạch” để model kết luận đúng.

Vì vậy, lỗi của q07 là lỗi “liên tầng”: retrieval hybrid bị nhiễu nhẹ và generation không đủ kỷ luật để tự hiệu chỉnh. Kết luận của em trong tài liệu là chọn dense baseline cho grading, đồng thời đề xuất cải thiện tokenizer/rerank trước khi quay lại hybrid.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Nếu có thêm thời gian, em sẽ chạy một vòng tuning có kiểm soát cho hybrid: giảm `sparse_weight` (ví dụ 0.4 -> 0.2), giữ nguyên biến còn lại, rồi đo lại riêng các câu alias/keyword để xem fusion có bớt nhiễu không. Em cũng muốn siết prompt generation theo checklist “trả lời theo từng ý + chỉ dùng evidence đã trích” để cải thiện Completeness. Hai thay đổi này bám sát đúng điểm yếu đã lộ ra trong scorecard hiện tại.

---