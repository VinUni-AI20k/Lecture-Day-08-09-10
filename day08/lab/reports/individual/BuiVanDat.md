# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Bùi Văn Đạt  
**Vai trò trong nhóm:** Tech Lead / Retrieval Owner / Documentation Owner  
**Ngày nộp:** 13/4/2026 
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi phụ trách phần báo cáo kiến trúc và đảm bảo luồng kỹ thuật từ Sprint 1 đến Sprint 3. Ở Sprint 1, tôi thực hiện index pipeline: kiểm tra tài liệu, preprocess metadata, cắt chunk theo section và paragraph, và xác nhận index được lưu đúng vào ChromaDB. Ở Sprint 2, tôi làm việc với retrieval rồi xây hàm `rag_answer()` để lấy dense retrieval và sinh câu trả lời grounded.  Ở Sprint 3, tôi tập trung vào biến thể hybrid retrieval, xem sự khác biệt giữa baseline và hybrid. Song song, tôi hoàn thiện `architecture.md` để mô tả rõ flow của pipeline và các quyết định kỹ thuật.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Qua lab này tôi hiểu rõ hơn về hai khái niệm chính: chunking và hybrid retrieval. Chunking không chỉ đơn thuần là chia đủ kích thước, mà còn cần cắt theo heading và paragraph để giữ ngữ nghĩa và metadata. Hybrid retrieval giúp cân bằng giữa semantic search và exact-match, nhưng phải thiết kế sao cho không phá hoại dense baseline bằng cách ưu tiên dense và chỉ dùng sparse khi sparse thật sự bổ sung thêm evidence. 

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điểm khiến tôi ngạc nhiên nhất là hybrid không tự động tốt hơn dense baseline. Ban đầu tôi nghĩ kết hợp BM25 và embedding sẽ luôn cải thiện, nhưng thực tế phải điều chỉnh trọng số và cơ chế fallback. Khó khăn nhất nằm ở tuning hybrid: nếu sparse đưa vào quá nhiều chunk không phù hợp thì answer sẽ bị sai hoặc thiếu tập trung. Nó khiến kết quả demo của tôi luôn thua baseline

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:**  "ERR-403-AUTH là lỗi gì?"

**Phân tích:**
Baseline dense và variant hybrid đều trả đúng abstain, cho thấy hệ thống hiện tại phân biệt được khi không có thông tin trong corpus. Ở câu này, lỗi không nằm ở generation mà ở retrieval: cả hai phương pháp không tìm thấy chunk chứa mã lỗi cụ thể `ERR-403-AUTH` vì tài liệu không đề cập. Với baseline, câu trả lời đúng ở mức `faithfulness` và `completeness` khi abstain. Với variant hybrid, vì bài toán là không có evidence, hybrid không cải thiện được và giữ kết quả tie. Như vậy câu hỏi này minh chứng rằng biến thể hybrid chỉ có giá trị khi corpus chứa exact-term hoặc alias; nếu document không đề cập tới mã lỗi thì bất kỳ retrieval nào cũng phải abstain. Vì vậy, việc thông báo rõ giới hạn corpus và giữ abstain đúng là quan trọng.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử hai cải tiến cụ thể: 1) thêm rerank bằng cross-encoder với candidate đa dạng từ hybrid để giữ nguồn evidence tốt nhất, 2) bổ sung query expansion/alias map cho những thuật ngữ như "Approval Matrix" hay "P1".  Hai cải tiến này dựa trên kết quả rằng hybrid hiện tại cần thêm filter chất lượng và alias matching để thực sự vượt baseline.

---

## Flow công việc từ Sprint 1 đến Sprint 3

1. Sprint 1: Read docs → Preprocess metadata → Chunk theo heading/paragraph → Upsert chunks vào ChromaDB → Kiểm tra với `list_chunks()`.
2. Sprint 2: Xây `retrieve_dense()` → Build context block → Prompt grounded → Gọi LLM → Kiểm tra citation và abstain.
3. Sprint 3: Kiểm tra `retrieve_sparse()` với BM25 → Implement hybrid fusion → So sánh dense vs hybrid → Ghi lý do chọn variant vào `architecture.md`.

---
