# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline
**Họ và tên:** Hoàng Bá Minh Quang
**Vai trò trong nhóm:** Tech Lead
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ
---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)
- Trong lab này, tôi phụ trách vai trò Tech lead, tập trung vào điều phối, lên kế hoạch, xử lý một vài task và hỗ trợ team hoàn thành lab
- Về kỹ thuật, tôi đã làm phần index.py tức là đảm nhiệm phần index data trên cloud để cả team dùng chung. Trong đó, tôi đã khảo sát các model free nhưng có khả năng embedding tốt, thiết kế các parameter dựa trên rule of thumbs, xây dựng thêm hàm _split (trong chunking) để đạt được kết quả tốt
-> kết quả gần như 5/5 cho phần retrieval trong các tập test
- Bên cạnh đó, tôi còn đảm nhiệm vai trò tune tham số, kỹ thuật trong phase 3
_________________
---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)
Sau lab này, tôi hiểu rõ hơn về toàn bộ vòng đời của RAG, từ tiền xử lý dữ liệu, quy trình index, và các giải pháp retrieval để tổng hợp sinh câu trở lời. Đồng thời, tôi còn nắm được cách khởi tạo tham số ban đầu, cách để tune từng phần/tham số một để nhận biết tune nào tốt/không tố. Hơn nữa, tôi cũng nhận ra chunking là yếu tố cũng khá quan trọng, vì nếu chunk cắt sai ranh giới ý thì retrieval đúng nguồn nhưng answer vẫn thiếu hoặc sai. Ngoài ra, tôi hiểu rõ hơn sự khác biệt giữa các chiến lược dense/sparse/hybrid, và khi nào nên dùng từng cách. Quan trọng nhất là tư duy đo lường: không chỉ nhìn một vài câu trả lời “có vẻ đúng”, mà phải nhìn theo metric và failure mode để cải tiến bền vững.
_________________
---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)
- Điều khiến tôi ngạc nhiên là kỹ thuật “mạnh hơn” chưa chắc cho kết quả tốt hơn trong bối cảnh cụ thể. Khi thử sparse và hybrid, tôi kỳ vọng điểm sẽ tăng, nhưng thực tế một số metric lại giảm so với baseline dense dù context recall vẫn cao. Điều này cho thấy hệ thống RAG không chỉ phụ thuộc retriever, mà còn phụ thuộc cách ghép context, prompt và hành vi sinh của model.
 
- Khó khăn lớn nhất của tôi là quản lý thời gian: ở giai đoạn đầu tôi dành nhiều công sức cho thử nghiệm kỹ thuật, dẫn tới cuối sprint bị dồn việc, đặc biệt ở bước tổng hợp báo cáo và chuẩn hóa kết quả.
_________________
---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)
**Câu hỏi:** gq05 - Contractor từ bên ngoài công ty có thể được cấp quyền Admin Access không? Nếu có, cần bao nhiêu ngày và có yêu cầu đặc biệt gì?

**Phân tích:**
- Câu gq05 là một câu kiểm tra RAG khó chịu vì buộc hệ thống kết hợp nhiều mảnh thông tin trong cùng tài liệu thay vì trích từ 1 mảnh đơn lẻ. Trọng tâm không chỉ là trả lời có hay không mà còn xác định đúng phạm vi áp dụng (contractor được xét cấp quyền), sau đó nối sang rule chi tiết của Admin Access (Level 4) gồm ba thành phần bắt buộc: approver, thời gian xử lý, và yêu cầu training. Ở đây, nếu retriever chỉ lấy chunk nói về Level 4 mà thiếu Section 1, model dễ suy diễn là contractor không được cấp; ngược lại nếu chỉ có scope mà thiếu section policy chi tiết, câu trả lời sẽ thiếu approver hoặc SLA thời gian.

- Failure mode quan trọng nhất là nhầm lẫn giữa Level 3 và Level 4, vì cả hai đều liên quan quyền cao nhưng khác phê duyệt. Vì vậy, đáp án tốt cần nêu đủ: contractor được áp dụng quy trình, Level 4 cần IT Manager + CISO, thời gian 5 ngày làm việc, và training security policy bắt buộc. Câu này đo cả độ chính xác lẫn completeness, nên rất phù hợp để bắt lỗi retriever và prompt grounding.
_________________
---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)
Nếu có thêm thời gian, tôi sẽ viết lại file run_tuning_experiments.py rõ ràng hơn và tôi cũng có thể đủ thời gian để chạy full experiments để vừa tuning hyperparameter vừa tuning các strategy index dữ liệu và vừa có thể thử nghiệm các giải pháp giúp tăng performance như rerank, query transformation





