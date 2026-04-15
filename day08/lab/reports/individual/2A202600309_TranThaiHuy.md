# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Thái Huy  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab Day 08, tôi làm vai trò Eval Owner nên phần việc chính của tôi tập trung vào kiểm thử và đánh giá chất lượng pipeline thay vì retrieval hay indexing. Tôi đọc kỹ `roles.md`, `README.md`, `SCORING.md` và các tài liệu trong `data/docs/` để xác định bộ câu hỏi nào đủ sức test end-to-end toàn pipeline. Sau đó tôi rà lại `test_questions.json` hiện có, đồng thời tạo thêm một bộ câu hỏi mở rộng theo cùng format để phủ các tình huống như câu hỏi fact, câu hỏi theo mốc thời gian, alias/tên cũ, multi-document và abstain. Tôi cũng làm rõ flow đánh giá baseline → variant → compare A/B, rồi hoàn thiện hướng chấm trong `eval.py` theo hai mode là LLM-based và rule-based để đội có thể vừa debug nhanh vừa có thể dùng judge mềm hơn khi cần.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, điều tôi hiểu rõ hơn là evaluation trong RAG không phải là bước “đọc đáp án thấy có vẻ ổn” mà phải là một vòng lặp có cấu trúc. Tôi hiểu rõ hơn sự khác nhau giữa `baseline`, `variant` và `scorecard`. Baseline là bản pipeline cơ bản dùng để lấy mốc, còn variant là bản chỉ đổi đúng một biến để xem thay đổi đó có thực sự tạo ra cải thiện hay không. Tôi cũng hiểu rõ hơn 4 metric trong scorecard: `faithfulness` đo câu trả lời có bám vào evidence retrieve được hay không, `context recall` đo retriever có kéo đúng nguồn hay không, `relevance` xem model có trả lời đúng câu hỏi không, và `completeness` xem câu trả lời có bỏ sót điều kiện hay ngoại lệ quan trọng không. Đây là lần đầu tôi thấy rõ evaluation loop gắn chặt với debugging như thế nào.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi ngạc nhiên nhất là phần evaluation tưởng như “cuối pipeline” nhưng thực ra phải chuẩn bị rất sớm. Nếu không chuẩn bị `test_questions`, expected sources, và logic chấm từ đầu thì đến lúc retrieval và generation chạy được cũng rất khó biết hệ thống thực sự tốt hay chỉ đang trả lời nghe trôi chảy hơn. Khó khăn lớn nhất là câu hỏi về `faithfulness` và `relevance` không đơn giản để chấm bằng rule-based, vì hai tiêu chí này mang tính ngôn ngữ và ngữ nghĩa nhiều hơn việc so khớp từ khóa. Ban đầu tôi nghĩ chỉ cần so token overlap là đủ, nhưng sau khi phân tích kỹ thì thấy rule-based chỉ phù hợp làm heuristic nhanh; còn nếu muốn chấm mềm hơn cho các câu diễn đạt khác wording thì cần LLM-as-Judge. Vì vậy tôi chọn hướng để `eval.py` hỗ trợ cả hai mode thay vì ép cả nhóm chỉ dùng một cách chấm.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** “Tài liệu Approval Matrix for System Access hiện nay là tài liệu nào và hệ thống IAM được dùng là gì?”

**Phân tích:**

Tôi chọn câu này vì nó kiểm tra cùng lúc hai năng lực của RAG: nhận diện alias/tên cũ của tài liệu và rút đúng fact cụ thể trong tài liệu hiện hành. Với baseline dense-only, tôi dự đoán hệ thống có thể fail ở bước retrieval nếu embedding không kéo được `access-control-sop.md` khi người dùng dùng tên cũ là “Approval Matrix for System Access”. Đây là failure mode thiên về retrieval chứ không phải generation, vì nếu retriever không mang đúng chunk về thì model rất dễ trả lời mơ hồ hoặc bịa. Trong scorecard, câu này nên có `context recall` thấp nếu source không được retrieve, kéo theo `faithfulness` và `completeness` cùng giảm. Variant hợp lý cho câu này là hybrid retrieval hoặc query expansion, vì tài liệu SOP đã ghi chú rất rõ tên cũ của tài liệu. Nếu variant retrieve được đúng source, model có thể trả lời đủ hai ý: tài liệu hiện tại là `Access Control SOP` và hệ thống IAM là `Okta`. Như vậy, sự cải thiện nếu có sẽ là bằng chứng khá sạch cho việc tune retrieval theo alias thay vì chỉ sửa prompt.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ làm hai việc. Thứ nhất, tôi sẽ nối hẳn flow trong `eval.py` để chạy một mạch baseline, variant và `compare_ab()` thay vì dừng ở từng bước riêng lẻ. Thứ hai, tôi sẽ cải thiện phần rule-based scoring bằng cách kiểm tra entity và number chặt hơn, vì các câu như SLA, refund và access control phụ thuộc rất nhiều vào con số và vai trò phê duyệt. Kết quả scorecard sẽ đáng tin hơn nếu phần này được làm kỹ.
