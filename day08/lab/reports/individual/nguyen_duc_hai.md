# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Đức Hải  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 13-04-2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, với vai trò là Eval Owner, nhiệm vụ chính của tôi tập trung vào **Sprint 4**: xây dựng hệ thống Evaluation & Scorecard cho pipeline RAG. Cụ thể, tôi đã thiết kế và implement toàn bộ cơ chế **LLM-as-Judge** trong file `eval.py` để tự động chấm điểm cho 4 metrics: Faithfulness, Answer Relevance, Context Recall và Completeness thay vì phải thực hiện đánh giá thủ công. 

Tôi cũng mở rộng luồng xử lý test data, cấu hình để load tự động nhiều file test khác nhau (như `test_questions.json`, `test_questions2.json` và `grading_questions.json`) thành một mảng dữ liệu xuyên suốt. Thêm vào đó, để tối ưu hoá chi phí và thời gian gọi LLM qua API, tôi đã implement một cơ chế **Caching** kết quả, cho phép bypass (bỏ qua chạy lại) các câu hỏi đã được đánh giá đối với từng `retrieval_mode`. Phần việc này kết nối chặt chẽ với Retrieval Owner: tôi cung cấp "thước đo" khách quan dạng bảng `ab_comparison.csv` giúp team thấy rõ Variant (Hybrid + Rerank) hoạt động tốt hay kém Baseline (Dense) ở những câu hỏi cụ thể nào.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Hai concept cốt lõi mà tôi thực sự nắm vững là **LLM-as-Judge** và sự khác biệt giữa các **RAG Metrics**. 

Trước đây tôi không hiểu rõ làm sao để đo lường tự động một câu trả lời kiểu ngôn ngữ tự nhiên. Việc tự tay viết prompt cho một LLM đóng vai trò "Judge", buộc model trả về dưới định dạng `{"score": <int>, "reason": "<string>"}` giúp tôi hiểu việc định lượng hoá output là hoàn toàn khả thi. Dựa trên Regex (`re.search`) để parse kết quả từ chuỗi String của LLM cho thấy việc tích hợp AI vào Software Engineering thiên về kiểm soát tính trơn tru của format output.

Thứ hai, chia rạch ròi 2 nhóm: Retrieval metrics (như Context Recall: tài liệu get về có trúng không?) và Generation metrics (như Faithfulness: sinh ra có chém gió ngoài tài liệu không) làm quá trình debug dễ dàng hơn gấp bội.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất và tiêu tốn nhiều thời gian nhất của tôi là **khống chế output format của LLM-Judge**. Giả thuyết ban đầu của tôi là chỉ cần dặn "hãy trả về JSON" thì LLM sẽ luôn tuân thủ 100%. Thực tế, thi thoảng LLM (đặc biệt là Gemini/OpenAI mini) lại kẹp thêm markdown blocks ` ```json ` hay thậm chí thòng thêm câu mào đầu như "Here is the result...". Điều này làm crash ứng dụng khi cố load JSON. Tôi buộc phải xây dựng cơ chế Regex (`re.search(r'\{.*\}', response_text, re.DOTALL)`) để "trích xuất" phần lõi object để giảm thiểu error-rate.

Một rào cản phụ nữa là sự cố Encoding `cp932/unicode` làm crash lệnh `print()` xuất test logs lên màn hình Console của Windows. Xử lý qua tham số `$env:PYTHONIOENCODING="utf-8"` đã giải quyết được trở ngại này.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** *[q06] Cấp quyền phê duyệt cho dự án nội bộ Level 3 cần phải qua những ai?* (Mô phỏng câu hỏi Access Control SOP)

**Phân tích:**
Trong lần thi hành với `scorecard_baseline.md` (Dense retrieval mode), câu này tuy retrieve ra 3 chunks liên quan nhưng lại bị sót mắt đoạn chunk chứa thông tin các Level. Do các khái niệm "cấp quyền", "Level 3" đều là các từ nối bị Vector Embedding làm trôi ý nghĩa so sánh cục bộ, nên Retriever không bắt được chính xác. Kết quả là generation báo lỗi thiếu dữ kiện (Abstain) hoặc sinh ra thiếu Completeness, nhận Completeness = 3. 

Sau khi áp dụng Variant cấu hình Hybrid (Sparse + Dense) cùng cross-encoder `use_rerank=True`, cơ chế **Sparse (BM25)** đã làm xuất sắc vai trò match đúng exact-keywords "Level 3". Tiếp theo đó, module **Rerank** thực hiện thao tác proxy sắp xếp và đưa chính xác section SOP nói về Approval Matrix lên rank đầu. Pipeline khi đó vừa đủ Context Recall (5/5), vừa giúp Model sinh chữ bắt trọn vẹn điểm "Completeness" (5/5). Lỗi ở baseline nằm thuần túy tại khâu **Retrieval** (chứ không phải **Generation** - LLM không hề bịa đặt, nó chỉ thiếu knowledge document), và Variant là giải pháp bù đắp hoàn hảo.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Tôi sẽ thay thế LLM của hệ thống Judge bằng một Model mạnh hơn (vd: GPT-4o hoặc Gemini 1.5 Pro) độc lập với LLM tạo ra Generation (GPT-4o mini).** Việc "vừa làm cầu thủ, vừa làm trọng tài" từ cùng một weight space có thể gây ra thiên kiến ưu ái (Self-enhancement bias) ở những câu prompt ngặt nghèo.
2. **Xây dựng module đánh giá trực tiếp Chunking Parameter:** Vì kết quả eval chỉ ra ở một số câu trả lời Variant vẫn bị thọt so với Baseline, khả năng cao do Chunk Size quá nhỏ phá vỡ flow context, tôi muốn A/B testing chính config `chunk_size` trực tiếp thông qua điểm Context Recall.
