# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Hữu Hưng  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này tôi chủ yếu phụ trách Sprint 2 — xây dựng pipeline trả lời có grounding từ ChromaDB. Cụ thể, tôi implement hàm `retrieve_dense()` để query ChromaDB bằng embedding, hàm `call_llm()` gọi OpenAI gpt-4o-mini, và hàm `rag_answer()` kết nối toàn bộ pipeline từ query đến answer có citation. Bên cạnh đó, tôi điều chỉnh `build_grounded_prompt()` để cải thiện điểm Completeness trong eval: bỏ instruction `"Keep your answer short"` vì nó khiến LLM bỏ sót số liệu quan trọng, thay bằng rule yêu cầu LLM include tất cả key facts, numbers và conditions từ context. Phần của tôi kết nối trực tiếp với Sprint 1 (ChromaDB do nhóm đã build) và Sprint 4 (eval.py chấm điểm output của pipeline tôi tạo ra).

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này tôi hiểu rõ hơn về tầm quan trọng của **grounded prompt design** và cách nó ảnh hưởng trực tiếp đến từng metric trong eval. Trước đây tôi nghĩ "prompt ngắn gọn là tốt" — nhưng thực tế khi chạy qua LLM-as-Judge, câu trả lời ngắn thường bị trừ điểm Completeness vì thiếu điều kiện hoặc ngoại lệ. Ví dụ câu hỏi về SLA P1: LLM chỉ trả lời "4 giờ" nhưng expected answer yêu cầu cả "15 phút phản hồi ban đầu" lẫn "4 giờ xử lý" — đây là hai thông tin khác nhau. Tôi cũng hiểu hơn về **abstain behavior**: nếu không có instruction rõ ràng, LLM sẽ cố trả lời dù context không đủ, dẫn đến hallucination. Việc đặt một chuỗi abstain cố định (`"Không đủ dữ liệu để trả lời câu hỏi này."`) giúp judge nhận diện đúng hơn.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến tôi mất thời gian nhất là hiểu tại sao log RAG hiển thị `it/access-control-sop.md` thay vì `access_control_sop.txt`. Ban đầu tôi nghĩ hệ thống đang đọc sai file, hoặc có file `.md` nằm đâu đó trong thư mục mà tôi chưa thấy. Sau khi đọc kỹ `preprocess_document()` trong `index.py`, tôi mới nhận ra: mỗi file `.txt` chứa dòng header `Source: it/access-control-sop.md` bên trong nội dung, và code đọc dòng đó rồi **ghi đè** `metadata["source"]` — nên tên file `.txt` vật lý hoàn toàn biến mất khỏi ChromaDB. Đây là thiết kế có chủ đích để citation trông giống hệ thống thực tế, nhưng nếu không đọc kỹ code sẽ rất dễ nhầm lẫn khi debug.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** `q09 — "ERR-403-AUTH là lỗi gì và cách xử lý?"`

**Phân tích:**

Đây là câu hỏi thuộc category *Insufficient Context* — không có tài liệu nào trong corpus đề cập đến mã lỗi này. Đây là test case kiểm tra khả năng **abstain** của pipeline.

Với baseline (dense, không tune prompt), LLM có xu hướng trả lời theo prior knowledge về lỗi authentication nói chung, thay vì thừa nhận không có dữ liệu. Điều này khiến điểm **Faithfulness thấp** (answer không grounded trong context) và **Answer Relevance thấp** (không abstain đúng cách theo rubric).

Sau khi tune prompt với rule 2 — `"If the context is insufficient, respond exactly: 'Không đủ dữ liệu để trả lời câu hỏi này.'"` — LLM trả về đúng chuỗi abstain. Judge nhận diện được và cho điểm Answer Relevance cao hơn vì model không bịa thông tin ngoài context.

Lỗi không nằm ở retrieval (context_recall = N/A vì expected_sources rỗng) mà nằm ở **generation**: prompt ban đầu không đủ constraint để ngăn LLM dùng prior knowledge.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thử thêm **score threshold** vào pipeline: nếu chunk có score thấp hơn 0.3 thì không đưa vào context, vì eval cho thấy một số câu hỏi abstain (như `q09`) vẫn retrieve được chunk liên quan xa với score thấp, khiến LLM cố trả lời thay vì abstain. Ngoài ra tôi muốn thử **query expansion** cho `q07` (Approval Matrix → Access Control SOP) vì đây là alias query mà dense retrieval yếu, và hybrid chưa chắc đã đủ nếu BM25 không tìm được từ khóa chính xác.

---


