# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Hoàng Văn Kiên 
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 2026-04-13
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi đảm nhận vai trò Eval Owner — chịu trách nhiệm chính cho Sprint 4: thiết kế và chạy bộ đánh giá pipeline RAG. Cụ thể, tôi implement file `eval.py` bao gồm 4 hàm chấm điểm (`score_faithfulness`, `score_answer_relevance`, `score_context_recall`, `score_completeness`), hàm `run_scorecard()` để chạy toàn bộ test questions qua pipeline, và `compare_ab()` để so sánh baseline vs variant.

Mỗi hàm scoring sử dụng heuristic dựa trên keyword coverage — so sánh mức độ xuất hiện của các từ quan trọng giữa answer, context và expected answer. Công việc của tôi phụ thuộc trực tiếp vào output của `rag_answer()` từ Sprint 2 và Sprint 3 do các thành viên khác implement, đồng thời kết quả scorecard tôi tạo ra là đầu vào để nhóm justify lựa chọn variant trong báo cáo chung.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn về **evaluation loop trong RAG** và tại sao nó khó hơn tưởng.

Trước khi làm, tôi nghĩ chấm điểm RAG đơn giản: answer đúng thì cho điểm cao. Nhưng thực tế có 4 chiều hoàn toàn độc lập: faithfulness (có bịa không?), relevance (có trả lời đúng câu không?), context recall (retriever có lấy đúng source không?), completeness (có thiếu ý quan trọng không?). Một câu trả lời có thể relevance cao nhưng faithfulness thấp nếu model dùng kiến thức ngoài context.

Tôi cũng hiểu rõ hơn tại sao A/B rule quan trọng: nếu đổi cùng lúc nhiều thứ (chunking + hybrid + rerank), dù điểm tăng cũng không biết yếu tố nào thực sự có tác dụng. Chỉ đổi một biến mỗi lần mới rút ra được kết luận có giá trị.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều tôi ngạc nhiên nhất là **kết quả A/B so sánh**: tôi kỳ vọng hybrid retrieval sẽ tốt hơn hoàn toàn so với baseline dense, vì lý thuyết hybrid giữ được cả ngữ nghĩa lẫn keyword chính xác. Nhưng thực tế baseline dense lại tốt hơn ở một số câu nhất định.

Sau khi phân tích, tôi nhận ra nguyên nhân có thể do scoring heuristic của mình còn thô — keyword matching không phân biệt được từ quan trọng và từ thường, nên điểm đôi khi phản ánh sai chất lượng thật của answer. Ngoài ra, hybrid với BM25 tokenize đơn giản (`lower().split()`) chưa xử lý tốt tiếng Việt có dấu, khiến sparse retrieval đôi khi kéo về những chunk không liên quan và "pha loãng" kết quả so với dense thuần.

Đây là bài học thực tế: metric đo không chuẩn thì kết quả A/B cũng không đáng tin.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** *"ERR-403-AUTH là lỗi gì?"*

**Phân tích:**

Đây là câu hỏi được thiết kế để kiểm tra khả năng **abstain** — tức là pipeline phải nhận ra rằng không có đủ thông tin trong docs và trả lời "không đủ dữ liệu" thay vì bịa.

Ở baseline (dense), pipeline retrieve được một số chunk liên quan đến access control và permission, nhưng không có chunk nào định nghĩa cụ thể mã lỗi `ERR-403-AUTH`. Nếu prompt grounded hoạt động đúng, LLM sẽ abstain và cho điểm faithfulness = 5, relevance = 5. Nếu LLM không abstain mà cố trả lời, faithfulness sẽ rất thấp vì thông tin bịa ra.

Với variant hybrid, BM25 có lợi thế hơn ở đây vì `ERR-403` là exact keyword — sparse retrieval sẽ tìm đúng hơn nếu term này xuất hiện trong docs. Nhưng vì docs không có mã lỗi này, cả hai đều nên abstain như nhau.

Điều thú vị là câu này test cả retrieval lẫn generation cùng lúc: retrieval phải không tìm thấy evidence, generation phải đủ "dũng cảm" để nói không biết thay vì hallucinate.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi sẽ thay thế heuristic keyword matching trong 4 hàm scoring bằng **LLM-as-Judge**. Kết quả eval hiện tại cho thấy baseline đôi khi "thắng" hybrid chỉ vì cách đếm từ thiếu chính xác — không phản ánh đúng chất lượng thật. Cụ thể, tôi sẽ implement LLM-as-Judge cho `score_faithfulness` và `score_completeness` trước, vì đây là hai metric khó đo bằng keyword matching nhất, và chạy lại A/B comparison để xem delta có thay đổi không.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*