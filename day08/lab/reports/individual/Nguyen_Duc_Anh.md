# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Đức Anh  
**Vai trò trong nhóm:** Tech Lead / Retrieval Owner (tích hợp hybrid, rerank, query transform; hợp nhất nhánh, code từ mọi người)  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi tập trung vào các hàm retrieval và luồng trả lời: cài `retrieve_sparse` (BM25), `retrieve_hybrid` (hợp nhất thứ hạng RRF giữa `retrieve_dense` và sparse), tùy chọn `rerank` cùng `_get_rerank_model`, và `transform_query` (tách chiến lược expansion, có nhánh local khi không gọi API) rồi gom kết quả tìm kiếm trên nhiều biến thể câu hỏi. Trong `rag_answer` tôi nối các nhánh trên với `build_context_block`, `build_grounded_prompt`, `call_llm`, kèm ngưỡng abstain theo điểm dense/hybrid; khi debug tôi dùng `compare_retrieval_strategies`. Phía chấm điểm tôi chỉnh `run_scorecard` và `compare_ab` để luôn gọi đúng tham số vào `rag_answer` (baseline dense đối chứng variant hybrid) mà không đổi contract các hàm `score_faithfulness`, `score_answer_relevance`, `score_context_recall`, `score_completeness`. Sau khi gộp nhánh tôi phải thống nhất thủ công các phiên bản `call_llm` và logic retrieve để không mất rerank hay query transform.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Trước lab tôi chỉ nghĩ hybrid là “cộng điểm hai nguồn”. Sau khi viết `retrieve_hybrid` theo RRF (trộn thứ hạng từ `retrieve_dense` và `retrieve_sparse` thay vì cộng score trực tiếp), tôi hiểu rõ hơn vì sao trọng số và kích thước pool ứng viên ảnh hưởng độ ổn định: hai không gian khác thang đo, RRF giảm bias thang. Khái niệm thứ hai là vòng `run_scorecard` → `rag_answer`: không chỉ nhìn điểm trung bình mà phải đọc từng câu để biết lỗi nằm ở tầng `retrieve_*`, `rerank`, hay `call_llm`, hay ngưỡng abstain trong `rag_answer`.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó nhất là conflict sau pull: hai nhánh cùng sửa `retrieve_hybrid` / `rerank` / `transform_query` với nhánh `call_llm`, phải gộp tay để không mất tính năng. Kỳ vọng của tôi là `retrieve_hybrid` luôn giúp recall trên câu alias; thực tế bảng điểm cho thấy `score_context_recall` vẫn cao nhưng `score_faithfulness` hoặc hành vi abstain trong `rag_answer` có thể tệ hơn. Bất ngờ phụ là Unicode trên Windows khi `run_scorecard` in log tiếng Việt, phải cấu hình UTF-8 ở `__main__` mới chạy ổn.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 — “Approval Matrix để cấp quyền hệ thống là tài liệu nào?” (alias/tên cũ, mục đích thử `retrieve_hybrid` so với `retrieve_dense`).

**Phân tích:** Luồng chỉ `retrieve_dense` (baseline_dense, chạy qua `run_scorecard`): q07 đạt Faithfulness 5, Relevance 5, Context Recall 5, Completeness 2 — bám ngữ cảnh và `score_context_recall` đủ, nhưng `score_completeness` thấp hơn (khả năng `call_llm` chưa nêu rõ mapping “Approval Matrix” → “Access Control SOP”). Cùng câu khi `rag_answer` dùng `retrieve_hybrid`: Faithfulness 3, Recall 5, Relevance 5, Completeness 2. Như vậy `retrieve_hybrid` không làm mất chunk đúng (recall judge vẫn 5) nhưng cách `build_context_block` + `call_llm` diễn đạt khiến `score_faithfulness` giảm. Kết luận: cần chỉnh trọng số trong `retrieve_hybrid`, thử `rerank` sau pool RRF, hoặc prompt trong `build_grounded_prompt` để nói rõ alias, thay vì chỉ đổi hàm retrieve.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ grid-search nhẹ tham số bên trong `retrieve_hybrid` (trọng số dense/sparse, kích thước pool) vì `run_scorecard` cho variant làm faithfulness trung bình giảm (4.40 so với 5.00) dù `score_context_recall` tăng. Đồng thời tôi bật `rerank` sau `retrieve_hybrid` rồi chạy lại `compare_ab` / `run_scorecard` để xem `score_faithfulness` trên q07 và q09 có hồi phục không.

---