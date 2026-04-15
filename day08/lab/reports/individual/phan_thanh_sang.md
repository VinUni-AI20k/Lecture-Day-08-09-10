# Báo Cáo Cá Nhân - Lab Day 08: RAG Pipeline

**Họ và tên:** Phan Thanh Sang  
**Vai trò trong nhóm:** Tech Lead / Retrieval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài:** ~650 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong buổi lab này, tôi tập trung vào phần kỹ thuật cốt lõi của pipeline RAG, chủ yếu ở Sprint 1, 2 và một phần Sprint 3. Ở Sprint 1, tôi hoàn thiện file `index.py`: preprocess metadata từ các dòng header (source, department, effective date, access), chunking theo section + paragraph, và bổ sung overlap để giảm mất ngữ cảnh ở ranh giới chunk. Sau đó tôi kết nối embedding backend theo hai hướng: OpenAI nếu có API key, hoặc local sentence-transformers nếu chạy offline. Ở Sprint 2, tôi implement dense retrieval từ ChromaDB, tạo grounded prompt và hàm gọi LLM (OpenAI/Gemini). Ở Sprint 3, tôi thêm sparse retrieval bằng BM25, kết hợp hybrid bằng RRF và rerank fallback. Toàn bộ phần việc này được nối lại để `eval.py` có thể chạy scorecard baseline/variant.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab, tôi hiểu rõ hơn rằng chất lượng RAG không nằm ở một thành phần duy nhất, mà là sự phối hợp của indexing, retrieval và generation. Trước đây tôi thường nghĩ prompt là quan trọng nhất, nhưng qua bài này tôi thấy nếu retrieval sai thì prompt hay đến đâu cũng không cứu được. Tôi cũng hiểu rõ sự khác nhau giữa dense và sparse retrieval: dense mạnh ở matching theo nghĩa, sparse mạnh ở exact term, ví dụ như `P1`, `Level 3`, hay alias `Approval Matrix`. Vì vậy hybrid retrieval có giá trị thực tế trong corpus doanh nghiệp, nơi văn bản vừa có câu tự nhiên vừa có nhiều từ khóa chuyên ngành. Ngoài ra, tôi nhận ra metadata như source, section, effective date không chỉ để hiển thị citation, mà còn quan trọng cho freshness và tracing khi debug.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất không phải là viết hàm, mà là thứ tự vận hành pipeline. Lúc đầu script `rag_answer.py` chạy được nhưng trả về “không đủ dữ liệu” cho gần như mọi câu. Nguyên nhân là collection `rag_lab` chưa được build trước khi retrieval. Điều này giúp tôi thấy rõ một failure mode phổ biến: code đúng nhưng data flow sai thứ tự. Một điểm nữa là việc chunking: nếu cắt theo ký tự thuần túy thì rất dễ cắt giữa câu hoặc điều khoản, làm retrieval và generation mất ngữ nghĩa. Khi chuyển sang section-first + paragraph-first + overlap, chất lượng context ổn hơn rõ rệt. Tôi cũng thấy việc eval tự động cần cân bằng: metric heuristic giúp chạy nhanh, nhưng để kết luận nghiêm túc vẫn cần manual review hoặc LLM-as-judge cho những câu hỏi khó.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 - "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Đây là câu hỏi rất hay vì nó đánh thẳng vào bài toán alias query. Trong tài liệu thực tế, tên cũ “Approval Matrix for System Access” đã được đổi thành “Access Control SOP” và được ghi ở phần ghi chú của `access_control_sop.txt`. Ở baseline dense retrieval, nếu embedding không bắt được alias hoặc context index chưa đầy đủ thì rất dễ trả về kết quả thiếu hoặc không đúng. Với variant hybrid, BM25 có thể bắt từ khóa “Approval Matrix” trực tiếp, trong khi dense giữ vai trò bắt nghĩa gần với “cấp quyền hệ thống”. RRF merge hai danh sách giúp tăng khả năng đưa đúng chunk vào top-k context. Nếu generation được ràng buộc bằng grounded prompt, câu trả lời kỳ vọng là: tài liệu hiện tại là Access Control SOP, tên cũ là Approval Matrix for System Access, và có citation rõ ràng. Theo tôi, lỗi trong câu hỏi này nếu có sẽ nằm ở retrieval trước, không phải generation. Vì vậy q07 là minh họa rõ ràng cho lý do chọn hybrid trong Sprint 3.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm 1 giờ, tôi sẽ làm 2 việc cụ thể. Thứ nhất, tôi sẽ bật cross-encoder rerank để lọc top-k cuối, vì eval cho thấy retrieval có lúc đúng source nhưng chunk chưa sát câu hỏi. Thứ hai, tôi sẽ bổ sung LLM-as-judge cho faithfulness và completeness để scorecard giảm tính chủ quan so với heuristic token overlap. Hai cải tiến này sẽ giúp so sánh baseline và variant có cơ sở thuyết phục hơn.
