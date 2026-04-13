# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Hồ Thị Tố Nhi
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13-04-2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?
_________________
Trong lab này, tôi tập trung vào Sprint 2 và Sprint 3, xây dựng pipeline RAG hoàn chỉnh. Tôi implement các hàm chính trong rag_answer.py như transform_query, build_context_block, build_grounded_prompt, call_llm và rag_answer để xử lý từ bước retrieval đến generation .

Ngoài ra, tôi xây dựng hàm compare_retrieval_strategies để so sánh hiệu quả giữa dense, sparse và hybrid retrieval. Công việc của tôi đóng vai trò trung tâm, kết nối phần indexing và evaluation để đảm bảo pipeline chạy end-to-end.

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.
_________________

Sau lab, tôi hiểu rõ hơn rằng retrieval là yếu tố quan trọng nhất trong RAG. Nếu lấy sai context thì LLM sẽ trả lời sai dù prompt tốt.

Tôi cũng hiểu rõ hybrid retrieval: dense giúp hiểu ngữ nghĩa, còn sparse giúp bắt keyword chính xác (như mã lỗi, tên policy). Khi kết hợp hai phương pháp, hệ thống cải thiện đáng kể khả năng tìm đúng thông tin.


## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

_________________

Điều tôi bất ngờ là việc thay đổi retrieval strategy ảnh hưởng rất lớn đến kết quả. Dense retrieval không phải lúc nào cũng tốt, đặc biệt với query chứa keyword cụ thể.

Khó khăn lớn nhất là debug pipeline. Ban đầu tôi nghĩ lỗi do LLM, nhưng thực tế lỗi chủ yếu nằm ở retrieval. Ngoài ra, việc xử lý output JSON từ query transformation cũng dễ bị lỗi parse.

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** "SLA ticket P1 được xử lý trong bao lâu?"

**Phân tích:**

_________________

Ở baseline (dense), hệ thống đôi khi không retrieve đúng chunk chứa thông tin SLA, dẫn đến câu trả lời thiếu hoặc không đầy đủ.

Nguyên nhân là dense retrieval không bắt tốt keyword như "P1". Khi chuyển sang hybrid retrieval, hệ thống cải thiện rõ rệt: sparse giúp match chính xác keyword, còn dense giữ ngữ nghĩa.

Kết quả là context được retrieve đúng hơn, giúp LLM trả lời đầy đủ và chính xác hơn. Điểm context recall và completeness tăng đáng kể.

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

_________________

Tôi sẽ thử dùng cross-encoder để rerank thay vì LLM nhằm giảm chi phí và tăng độ chính xác. Ngoài ra, tôi muốn cải thiện query transformation để kiểm soát format output tốt hơn.

Dựa trên evaluation, tôi cũng sẽ thử tăng top_k_search kết hợp rerank để cải thiện recall.

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
