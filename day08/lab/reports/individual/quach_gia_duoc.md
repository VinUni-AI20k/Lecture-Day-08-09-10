# Báo Cáo Cá Nhân — Quach Gia Duoc

**Họ và tên:** Quach Gia Duoc  
**MSSV:** 2A202600423  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  

## 1. Tôi đã làm gì trong lab này?
Trong Day 08, tôi tập trung vào retrieval và evidence cho tuning. Ở code, tôi hoàn thành ba thay đổi chính trong `rag_answer.py`: (1) refactor luồng chọn strategy dense/sparse/hybrid để dễ đọc; (2) chuẩn hóa nhánh abstain bằng thông điệp thống nhất và thêm guard cho các tình huống context yếu/rỗng; (3) bổ sung trace retrieval chi tiết hơn (score range, nguồn giữ lại, số chunk bị loại) để debug nhanh khi điểm A/B bất thường. Ở docs, tôi cập nhật `docs/tuning-log.md` theo rule "single-variable A/B": baseline và variant chỉ đổi đúng một biến, có bảng trước/sau, và chốt quyết định bằng evidence thay vì cảm tính. Phần của tôi kết nối trực tiếp với phần của bạn Dung (Eval Owner) vì kết luận retrieval dựa vào scorecard và `ab_comparison.csv`.

## 2. Điều tôi hiểu rõ hơn sau lab này
Điều tôi hiểu rõ nhất sau lab là retrieval không chỉ là "chọn dense hay hybrid" mà còn là bài toán hiệu chuẩn score theo từng strategy. Trước đây tôi nghĩ hybrid gần như luôn tốt hơn dense vì tận dụng thêm keyword matching; sau khi làm thật, tôi thấy nếu không calibrate ngưỡng và cách chọn candidate theo đúng phân phối score thì hybrid có thể làm hệ thống abstain hàng loạt. Tôi cũng hiểu sâu hơn rule A/B "chỉ đổi một biến": khi giữ nguyên `top_k_search`, `top_k_select`, `use_rerank` và chỉ đổi `retrieval_mode`, mình mới xác định được vấn đề đến từ retrieval strategy thay vì do các tham số khác. Trace có cấu trúc cũng giúp tách lỗi retrieval và generation nhanh hơn.

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn
Điều làm tôi bất ngờ nhất là một variant tưởng như "xịn hơn" lại cho kết quả tổng thể kém hơn rõ rệt. Giả thuyết ban đầu của tôi là hybrid sẽ cải thiện câu có alias như "Approval Matrix" vì BM25 bắt keyword tốt. Nhưng khi chạy scorecard, variant hybrid-only rơi vào tình trạng relevance thấp và context recall gần như bằng 0 do pipeline trả abstain cho nhiều câu có dữ liệu. Khó khăn lớn nhất là ban đầu nhìn kết quả chỉ thấy "Không đủ dữ liệu..." nên tưởng lỗi nằm ở prompt; sau khi soi trace và đối chiếu bảng điểm theo từng câu, tôi mới khoanh vùng được nguyên nhân nằm ở retrieval path và ngưỡng điều kiện trước bước generate. Bài học tôi rút ra là phải nhìn cả pipeline context, không chỉ nhìn câu trả lời cuối cùng.

## 4. Phân tích một câu hỏi trong scorecard
**Câu hỏi đã chọn:** q07 — "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"  

Đây là câu tôi chọn vì nó đúng trọng tâm retrieval alias mapping. Ở baseline dense, pipeline trả lời đúng tài liệu `it/access-control-sop.md`, điểm từng thành phần cao (faithfulness/relevance/recall đều đạt mức tốt), dù completeness chưa tối đa vì chưa diễn đạt đầy đủ phần "tên mới". Điều này cho thấy dense vẫn truy được nguồn đúng. Ở variant hybrid-only của đợt A/B single-variable, kết quả chuyển sang abstain và điểm relevance + context recall giảm mạnh. Tôi truy dấu qua scorecard và trace thì thấy lỗi không nằm ở generation (output vẫn tuân thủ abstain), mà nằm ở retrieval path: candidate dùng cho answer không đạt điều kiện để đưa vào context hữu ích, dẫn đến mô hình không có bằng chứng để trả lời. Nghĩa là variant fail chủ yếu ở retrieval/selection stage, không phải vì prompt bịa. Từ câu q07, tôi kết luận hướng cải tiến tiếp theo là calibrate threshold theo từng mode hoặc bổ sung normalize score trước guard.

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?
Tôi sẽ làm hai việc cụ thể. Thứ nhất, tách ngưỡng guard theo strategy (dense/hybrid) và benchmark lại để tránh tình trạng hybrid bị "under-score" rồi abstain quá tay. Thứ hai, tạo thêm tập truy vấn alias/paraphrase có expected source rõ ràng để đo riêng retrieval recall trước khi chạy full scorecard. Hai việc này trực tiếp dựa trên evidence rằng variant hybrid-only hiện tại giảm mạnh relevance và context recall, nên cần sửa ở retrieval calibration trước khi thử thêm kỹ thuật khác.

