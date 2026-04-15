# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đỗ Minh Hiếu
**Vai trò trong nhóm:** Indexing Owner (Sprint 1)  
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này tôi phụ trách Sprint 1, tức là xây lớp Indexing cho toàn bộ pipeline RAG. Tôi implement luồng đọc tài liệu từ thư mục data/docs, tách metadata từ header (source, department, effective_date, access), chunk theo heading, sau đó embed và lưu vào ChromaDB. Tôi cũng chuẩn hóa source mapping theo đúng expected_sources trong bộ test để tránh lệch tên file giữa indexing và evaluation. Một quyết định quan trọng là cố định chunk size 400 tokens và overlap 80 tokens để cả nhóm có baseline ổn định trong suốt buổi lab. Ngoài phần build_index, tôi hoàn thiện list_chunks và kiểm tra coverage metadata để debug nhanh chất lượng index. Kết quả đầu ra của tôi là một vector store chạy được, có 29 chunks, và đây là dependency trực tiếp để bạn phụ trách retrieval/generation có thể chạy Sprint 2 trở đi. Ngoài ra, tôi cũng xây dựng chat box để có thể hỏi tự do các câu hoỉ thuộc chủ đề.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Điều tôi hiểu rõ nhất sau Sprint 1 là chunking không chỉ là “cắt văn bản”, mà là quyết định chất lượng retrieval từ đầu pipeline. Nếu chunk quá nhỏ thì mất ngữ cảnh, còn quá lớn thì embedding bị pha loãng vì chứa nhiều ý khác nhau. Với các tài liệu policy/SOP có cấu trúc mục rõ, cắt theo heading trước giúp mỗi chunk bám một ý nghiệp vụ cụ thể hơn. Điều thứ hai tôi hiểu sâu hơn là metadata đóng vai trò như “hợp đồng dữ liệu” giữa các sprint. Chỉ cần source không khớp expected_sources là evaluator có thể chấm recall thấp dù thông tin retrieval đúng về mặt nội dung. Vì vậy tôi ưu tiên tính nhất quán metadata ngay từ indexing thay vì đợi đến Sprint 4 mới xử lý. Sau bài này tôi nhìn rõ rằng chất lượng RAG không bắt đầu ở prompt, mà bắt đầu từ dữ liệu và index.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất của tôi là lỗi môi trường và lỗi không nhất quán embedding dimension. Ban đầu tôi nghĩ chỉ cần cài requirements và chạy index là xong, nhưng thực tế phát sinh nhiều vấn đề nhỏ: file .env bị đặt sai tên (có khoảng trắng cuối), lệnh python không có trong PATH ở terminal, và API key OpenAI trả về 401. Khi chuyển qua local embedding để đảm bảo tiến độ, index tạo ra vector 384 chiều; sau đó nếu query bằng OpenAI embedding 1536 chiều thì Chroma báo lệch dimension và truy vấn hỏng. Việc này giúp tôi rút ra một bài học thực tế: trong pipeline RAG, tính đồng bộ giữa indexing-time embedding và query-time embedding là bắt buộc. Nếu không đồng bộ, hệ thống vẫn có thể “chạy” nhưng chất lượng và tính đúng đắn của retrieval sẽ giảm mạnh hoặc phải fallback.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** q09 — "ERR-403-AUTH là lỗi gì và cách xử lý?"

**Phân tích:**

Với câu q09, expected answer lại cố ý không có source nào trong tài liệu, nên đây là bài kiểm tra abstain chứ không phải kiểm tra truy xuất chính xác một fact cụ thể. Baseline của nhóm trả lời theo hướng thận trọng: nêu rằng không tìm thấy thông tin về ERR-403-AUTH trong tài liệu và khuyên liên hệ IT Helpdesk. Điều này phù hợp với yêu cầu của một hệ RAG an toàn vì không bịa con số hay quy trình không có trong corpus. Ngược lại, variant hybrid lại yếu hơn vì dù vẫn giữ được phần “không có trong tài liệu”, nó không cải thiện được chất lượng diễn đạt và còn làm điểm relevance/completeness giảm. Với câu này, tôi xem failure mode không nằm ở indexing, mà nằm ở cách hệ thống xử lý câu hỏi ngoài phạm vi tài liệu: nếu prompt không ép abstain đủ rõ thì model dễ trả lời lan man hoặc suy đoán từ kiến thức nền. Câu q09 cho thấy một pipeline tốt không chỉ cần trả lời đúng khi có evidence, mà còn phải biết dừng lại khi không có evidence.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử hai cải tiến cụ thể. Thứ nhất, nâng cấp hàm _split_by_size theo paragraph-aware chunking thay vì cắt theo ký tự thuần, vì điều này có thể giảm hiện tượng cắt giữa câu và tăng faithfulness ở các câu cần điều kiện/ngoại lệ. Thứ hai, thêm script export sample chunks theo từng source để đội retrieval kiểm tra nhanh index quality trước khi chạy scorecard, vì việc kiểm tra sớm sẽ giảm thời gian debug ở Sprint 2 và Sprint 4. Hai cải tiến này đều tác động trực tiếp lên chất lượng context đầu vào của toàn pipeline.

---

