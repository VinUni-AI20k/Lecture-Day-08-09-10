# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Dương Văn Hiệp  
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này tôi làm Tech Lead nên tập trung nhiều nhất ở Sprint 1 và Sprint 2, đồng thời giữ nhịp để pipeline chạy end-to-end. Ở Sprint 1, tôi nối phần preprocess, chunking, metadata và build index trong `index.py`: chuẩn hóa text, tách chunk theo section/paragraph, giữ các metadata như `source`, `section`, `effective_date`, rồi đưa embedding vào ChromaDB. Tôi cũng chốt hướng dùng embedding local/fallback để cả nhóm có thể test nhanh trước khi phụ thuộc API. Sang Sprint 2, tôi hoàn thiện baseline RAG trong `rag_answer.py`: dense retrieval từ ChromaDB, grounded prompt, citation, và logic abstain khi không đủ bằng chứng. Vai trò của tôi là tạo bộ khung ổn định để Retrieval Owner có thể thử hybrid, Eval Owner chấm scorecard, và Documentation Owner ghi lại kiến trúc cùng tuning log mà không bị đứt pipeline.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này tôi hiểu rõ hơn hai khái niệm là chunking và grounded prompt. Trước đây tôi nghĩ chunking chủ yếu là chia văn bản cho vừa context, nhưng khi làm thật tôi thấy chunking quyết định luôn chất lượng retrieve. Nếu cắt giữa một điều khoản hoặc trộn nhiều ý trong cùng một chunk, retriever vẫn có thể lấy đúng file nhưng model lại khó tổng hợp đúng ý cần trả lời. Chunk tốt là chunk còn giữ được ranh giới tự nhiên như section, paragraph và có metadata đủ rõ để trace ngược.

Với grounded prompt, điều quan trọng không chỉ là câu nhắc “chỉ trả lời theo context”, mà là thiết kế cả hành vi abstain và citation. Một pipeline RAG tốt không phải lúc nào cũng trả lời nhiều, mà phải biết từ chối đúng khi tài liệu không có dữ liệu và giữ `sources` rỗng để tránh tạo cảm giác trả lời có căn cứ.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi ngạc nhiên nhất là hybrid retrieval không tốt hơn baseline như giả thuyết ban đầu của nhóm. Lúc bắt đầu Sprint 3, tôi nghĩ thêm BM25 sẽ giúp bắt alias và keyword tốt hơn, nhất là các câu như `Approval Matrix` hay mã lỗi. Nhưng scorecard cho thấy baseline dense vẫn tốt hơn tổng thể: Faithfulness từ 4.50 xuống 4.30, Relevance từ 4.80 xuống 4.40, còn Completeness cũng giảm nhẹ.

Ca debug mất thời gian nhất là `q06` về escalation P1. Ban đầu tôi nghi retrieval chưa đủ recall, nhưng nhìn score thì `Context Recall` vẫn 5/5 ở cả baseline và variant. Nghĩa là vấn đề không nằm ở việc không lấy được tài liệu, mà ở chỗ hybrid kéo thêm chunk có keyword liên quan nhưng lệch trọng tâm, làm model tổng hợp sai. Điều này giúp tôi hiểu rõ error tree hơn: có lúc recall đã ổn, nhưng selection/generation mới là nút thắt thật sự.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** `q07` — "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Đây là câu tôi thấy thú vị nhất vì nó kiểm tra đúng bài toán alias/tên cũ. Với baseline dense, hệ thống lấy đúng nguồn `it/access-control-sop.md` nên `Context Recall` đạt 5/5, nhưng câu trả lời vẫn chưa trọn ý: Faithfulness chỉ 2/5, Relevance 4/5 và Completeness 2/5. Tức là retriever đã mang đúng tài liệu về, nhưng model chưa diễn đạt rõ quan hệ “Approval Matrix for System Access” là tên cũ và tên hiện tại là `Access Control SOP`. Nói cách khác, lỗi chính nằm ở khâu generation hoặc chọn evidence đưa vào prompt, không phải indexing.

Khi chạy variant hybrid, tôi kỳ vọng BM25 sẽ bám tốt hơn cụm từ “Approval Matrix”, nhưng kết quả không cải thiện: Faithfulness vẫn 2/5, Relevance còn giảm xuống 3/5, Completeness giữ ở 2/5. Lý do là recall vốn đã đủ; hybrid chỉ tăng thêm keyword match chứ không giúp model hiểu tốt hơn ý “đổi tên tài liệu”. Trường hợp này cho thấy không phải câu hỏi có alias nào cũng cần hybrid. Nếu có thêm thời gian, tôi sẽ ưu tiên dense + rerank hoặc chỉnh prompt để buộc model trả lời theo mẫu “tên cũ / tên mới / file nguồn”, vì failure mode ở đây nằm sau retrieval chứ không nằm ở recall.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử `dense + rerank` thay vì tiếp tục đẩy hybrid, vì scorecard cho thấy `Context Recall` đã 5/5 nhưng `Completeness` vẫn thấp ở các câu như `q07`, `q09`, `q10`. Tôi cũng muốn chỉnh grounded prompt theo template chặt hơn, buộc model nêu rõ alias/tên mới hoặc phần “không được đề cập trong tài liệu” khi abstain. Hai thay đổi này sát hơn với lỗi thực tế mà eval đã chỉ ra.
