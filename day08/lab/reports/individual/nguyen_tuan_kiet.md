# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Tuấn Kiệt  
**Vai trò trong nhóm:** Eval Owner 
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong Lab Day 08, tôi đảm nhận vai trò **Eval Owner**, tập trung chính vào Sprint 4 (Evaluation & Scorecard). Tôi triển khai pipeline đánh giá tự động theo hướng **LLM-as-Judge** trong `day08/lab/llm_eval.py`: chạy 10 câu hỏi kiểm thử qua RAG pipeline, chấm theo 4 metrics (Faithfulness, Relevance, Context Recall, Completeness), và xuất báo cáo để nhóm dùng cho vòng tuning tiếp theo.

Cụ thể, tôi đã:
- Hiện thực hóa các hàm chấm điểm và prompt rubric cho LLM Judge, đồng thời xử lý trường hợp model trả về “text thừa” bằng cách trích JSON bằng regex để parse ổn định.
- Chạy A/B cho hai cấu hình: **baseline_dense** (dense retrieval) và **variant_hybrid** (hybrid retrieval), rồi tổng hợp kết quả.
- Xuất 3 artifact phục vụ báo cáo nhóm: `day08/lab/results/llm_scorecard_baseline.md`, `day08/lab/results/llm_scorecard_variant.md`, và `day08/lab/results/llm_ab_comparison.csv`.

Cả hai scorecard cho thấy variant cải thiện nhẹ so với baseline: trung bình **Faithfulness** tăng từ **3.70 → 3.90**, **Relevance** tăng từ **4.00 → 4.40**, trong khi **Context Recall** giữ ở **5.00** và **Completeness** giữ ở **3.90** (các điểm rơi vẫn tập trung ở câu policy/insufficient-context).

Công việc của tôi nối trực tiếp với phần của các bạn khác: retrieval/generation do nhóm implement trong `rag_answer.py`, còn tôi biến output thành scorecard và insight để quyết định tuning theo dữ liệu thay vì cảm tính.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu sâu sắc hơn về khái niệm **Evaluation Loop** và **LLM-as-Judge**. 

Trước đây tôi thường đánh giá RAG theo kiểu “đọc rồi thấy ổn/không ổn”. Nhưng khi chấm theo 4 metrics, tôi thấy rõ: một câu có thể **rất liên quan** nhưng lại **không trung thực** (hallucination) hoặc **thiếu ý quan trọng**. LLM-as-Judge giúp tiêu chuẩn hóa việc đánh giá, đặc biệt hữu ích khi nhóm muốn so sánh baseline vs variant và lặp tuning nhanh. 

Ngoài ra, tôi hiểu rõ hơn giá trị thực tế của **Hybrid Retrieval**: nó không tự động “làm mọi thứ tốt hơn”, mà chủ yếu giảm rủi ro *miss* khi câu hỏi chứa thuật ngữ/tên tài liệu. Dù điểm trung bình của variant cải thiện, các lỗi generation (ví dụ thiếu tên tài liệu cụ thể) vẫn làm tụt điểm Completeness — tức retrieval tốt chưa đủ, cần kiểm soát output theo yêu cầu câu hỏi.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều làm tôi ngạc nhiên là **Context Recall trung bình đạt 5.0/5 cho cả baseline và variant**, nhưng điểm Faithfulness/Completeness vẫn có các “điểm rơi” rõ rệt. Điều này cho thấy retrieval đã mang về đúng nguồn, nhưng generation vẫn có thể suy diễn hoặc trả lời thiếu đúng trọng tâm.

Khó khăn lớn nhất là xử lý case **q04 (Refund cho sản phẩm kỹ thuật số)**: câu trả lời thường thêm ngoại lệ “trừ khi lỗi nhà sản xuất”, trong khi expected answer yêu cầu “không hoàn tiền” như một ngoại lệ rõ ràng của policy. Trên scorecard, q04 bị chấm **Faithfulness = 2/5** ở cả baseline và variant, phản ánh lỗi hallucination/overgeneralization khi gặp câu hỏi dạng policy.

Một vướng mắc khác là **định dạng output của LLM Judge** không luôn “JSON sạch”; đôi lúc có phần giải thích thừa. Tôi giải quyết bằng cách trích block JSON bằng regex trước khi `json.loads`, giúp việc chạy scorecard end-to-end ổn định hơn.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** "Sản phẩm kỹ thuật số có được hoàn tiền không?" (ID: q04)

**Phân tích:**
- **Baseline (baseline_dense):** Điểm số thể hiện lỗi ở tầng generation: **Faithfulness = 2/5**, **Relevance = 5/5**, **Context Recall = 5/5**, **Completeness = 3/5**. Câu trả lời có đúng chủ đề (relevant) và retriever đã kéo đúng evidence (recall), nhưng model lại tự thêm ngoại lệ “trừ khi có lỗi do nhà sản xuất”, mâu thuẫn với policy “hàng kỹ thuật số là ngoại lệ không hoàn tiền”.
- **Variant (variant_hybrid):** Gần như không cải thiện ở câu này: **Faithfulness vẫn = 2/5**, **Relevance = 5/5**, **Recall = 5/5**, **Completeness = 3/5**. Điều này cho thấy đổi retrieval sang hybrid không giải quyết được lỗi cốt lõi, vì vấn đề nằm ở cách model “suy diễn” vượt quá context (hallucination).
- **Kết luận debug:** q04 là ví dụ rõ cho việc **retrieval tốt chưa đủ**. Để tăng Faithfulness, cần siết prompt/guardrail cho câu hỏi policy: yêu cầu model chỉ được trả lời theo context, và nếu policy nói “không” thì không được thêm bất kỳ điều kiện/ngoại lệ nào không xuất hiện trong chunks.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử 2 cải tiến cụ thể:

- (1) **Tối ưu prompt generation theo loại câu hỏi**: với câu hỏi “tài liệu nào / policy nào”, bắt buộc output phải chứa *tên tài liệu* (và nếu có thì kèm filename/path). Điều này nhắm trực tiếp vào lỗi q07 (thiếu “Access Control SOP”).
- (2) **Guardrail giảm hallucination cho policy**: thêm ràng buộc “nếu context không nêu ngoại lệ thì không được tự thêm ngoại lệ”, vì q04 đang bị Faithfulness 2/5 ở cả hai cấu hình dù recall tốt.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_tuan_kiet.md`*
