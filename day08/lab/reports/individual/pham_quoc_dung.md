# Báo Cáo Cá Nhân — Pham Quoc Dung

**Họ và tên:** Pham Quoc Dung  
**MSSV:** 2A202600490  
**Vai trò trong nhóm:** Evaluation Owner  
**Ngày nộp:** 13/04/2026  

## 1. Tôi đã làm gì trong lab này?
Trong vai trò Evaluation Owner, tôi tập trung vào cả phần code chấm điểm lẫn phần artifact đầu ra để nhóm có thể theo dõi chất lượng RAG theo từng vòng tinh chỉnh. Tôi xử lý các edge case trong eval.py như tránh chia cho 0, hiển thị đúng N/A khi metric không có dữ liệu, và bảo đảm phép tính delta không bị sai khi một phía thiếu điểm. Sau đó, tôi chuẩn hóa định dạng scorecard markdown để bảng gọn hơn, ổn định hơn khi có ký tự đặc biệt, đồng thời dễ so sánh giữa baseline và variant. Tôi cũng cải thiện luồng xuất báo cáo trong grade_grading_run.py (thêm tổng hợp verdict, chuẩn hóa ô markdown, hiển thị tỉ lệ criteria đạt). Cuối cùng, tôi kiểm tra lịch sử commit, đối chiếu artifact mới nhất và xác nhận mức độ hoàn thành 5 đầu việc được giao.

## 2. Điều tôi hiểu rõ hơn sau lab này
Sau lab này, tôi hiểu rõ hơn việc “đánh giá tốt” không chỉ là có điểm cao, mà là có quy trình đánh giá đáng tin cậy và tái lập được. Tôi nắm chắc hơn ý nghĩa từng metric: faithfulness giúp kiểm soát hallucination, relevance phản ánh mức bám câu hỏi, context recall cho biết retrieval có lấy đúng nguồn không, còn completeness đo độ đầy đủ thông tin. Một điểm quan trọng tôi rút ra là phải xử lý nghiêm các trường hợp biên như None, N/A, hoặc tập mẫu rỗng; nếu bỏ qua, dashboard và báo cáo có thể nhìn đẹp nhưng sai bản chất. Tôi cũng hiểu rõ lợi ích của việc chuẩn hóa format markdown: khi dữ liệu được trình bày nhất quán, nhóm dễ review nhanh, ít hiểu nhầm, và thuận lợi cho việc so sánh A/B theo từng lần chạy.

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn
Khó khăn lớn nhất là đồng bộ giữa trạng thái code và trạng thái artifact trong bối cảnh nhánh thay đổi liên tục. Có lúc cùng một mục tiêu cập nhật scorecard xuất hiện hai commit khác nhau, nên nếu chỉ nhìn message sẽ dễ kết luận sai tiến độ thực tế. Tôi cũng gặp tình huống merge dở dang với conflict ở hai file scorecard; cần xử lý cẩn thận để giữ đúng phiên bản mong muốn của nhánh hiện tại trước khi pull tiếp từ main. Ngoài ra, khi đọc log lịch sử theo nhiều nhánh, việc xác định “đã hoàn thành theo chức năng” và “đã có đúng message commit yêu cầu” là hai chuyện khác nhau. Điều này buộc tôi phải kiểm tra theo nhiều lớp: commit message, diff file thay đổi, và nội dung code/artifact hiện tại, thay vì chỉ dựa vào một dấu hiệu đơn lẻ.

## 4. Phân tích một câu hỏi trong scorecard
**Câu hỏi đã chọn:** q10 — Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?  
Ở câu q10, baseline_dense đạt Faithfulness = 5, Relevance = 1, Context Recall = 5, Completeness = 1; trong khi variant_hybrid_only đạt Faithfulness = 5, Relevance = 1, Context Recall = 0, Completeness = 1. Điều này cho thấy cả hai cấu hình đều tránh bịa thông tin (faithfulness cao), nhưng khả năng trả lời đúng trọng tâm nghiệp vụ vẫn yếu. Với baseline, hệ thống có truy xuất đúng nguồn (recall cao) nhưng câu trả lời vẫn thiên về “không đủ dữ liệu”, tức là phần tổng hợp câu trả lời chưa tận dụng tốt ngữ cảnh đã lấy được. Với variant, recall về 0 nên kết quả gần như thất bại hoàn toàn ở retrieval, làm relevance và completeness thấp là điều dễ hiểu. Điểm thú vị là metric faithfulness một mình không đủ để kết luận hệ thống tốt; nếu mô hình luôn chọn đáp án an toàn thì vẫn có thể “không sai” nhưng “không hữu ích”. Vì vậy, tôi xem q10 là ví dụ điển hình để nhóm cân bằng giữa an toàn nội dung và khả năng đưa ra câu trả lời có giá trị cho người dùng.

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?
Nếu có thêm thời gian, tôi sẽ bổ sung bộ kiểm thử hồi quy tự động cho pipeline đánh giá: kiểm tra edge case (N/A, None, chia 0), kiểm tra format markdown đầu ra, và cảnh báo khi artifact thay đổi bất thường giữa các lần chạy. Tôi cũng muốn thêm dashboard nhỏ để theo dõi xu hướng từng metric theo commit, giúp nhóm nhìn thấy rõ tác động của mỗi lần tuning thay vì chỉ so sánh thủ công từng file.

## 6. Tổng hợp kiểm tra 5 commit được giao

| Đầu việc | Message yêu cầu | Kết quả kiểm tra | Kết luận |
|---|---|---|---|
| Commit 1 | `fix(day08-lab): guard edge cases for delta and averages` | Tìm thấy commit `83957c2`, cập nhật `lab/eval.py` đúng phần guard N/A/chia 0 | Đã hoàn thành |
| Commit 2 | `feat(day08-lab): improve scorecard markdown formatting` | Tìm thấy commit `94e4912`, chuẩn hóa xuất markdown scorecard trong `lab/eval.py` | Đã hoàn thành |
| Commit 3 | `feat(day08-lab): refine grading report export` | Tìm thấy commit `f4be715`, cải thiện export trong `lab/grade_grading_run.py` | Đã hoàn thành |
| Commit 4 | `chore(day08-lab): refresh scorecard and ab comparison artifacts` | Tìm thấy 2 commit cùng message (`e29ba1e`, `27d2f4b`) cập nhật `scorecard_baseline.md`, `scorecard_variant.md`, `ab_comparison.csv` | Đã hoàn thành |
| Commit 5 | `chore(day08-lab): refresh grading result artifacts` | Chưa thấy đúng message này; tuy nhiên artifact `grading_auto.json` và `grading_auto_report.md` đã được cập nhật trong commit đồng bộ mới hơn (đặc biệt `8b9e96c`) | Đã hoàn thành về mặt chức năng, chưa khớp message |

