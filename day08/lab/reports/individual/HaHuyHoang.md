# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Hà Huy Hoàng  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 13-04-2026  
**Độ dài:** 500–800 từ
---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)


Trong lab này, tôi đóng góp chính vào **Sprint 3 — Tuning và A/B Experimentation** của pipeline RAG. Cụ thể, tôi đã:

- **Implement Variant 1 với Rerank**: Thay đổi cấu hình baseline bằng cách kích hoạt `use_rerank=True`, vẫn giữ nguyên retrieval mode là `dense`. Mục tiêu là cải thiện chất lượng câu trả lời bằng cách sắp xếp lại các chunks theo độ liên quan cao nhất trước khi đưa vào LLM generation.

- **Chạy Evaluation và ký so sánh**: Thực thi eval.py để chấm điểm tất cả 10 câu hỏi test trên cả baseline và variant, thu thập 4 metrics: Faithfulness, Relevance, Context Recall, Completeness.

- **Phân tích Error Tree**: Với guidance từ tuning-log.md, tôi diagnose được rằng lỗi chính nằm ở bước retrieval (dense miss keyword) và generation (context quá nhiễu với thông tin ngoài trọng tâm).

- **Ghi lại kết quả**: Cập nhật tuning-log.md với kết quả experiment, nhận xét rằng variant 1 không tốt hơn baseline về tổng thể (relevance -0.30, completeness -0.30, chỉ faithfulness +0.10).

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)



**A/B Testing mindset trong RAG**: Trước đây, tôi chỉ biết "cải thiện pipeline" là tăng tất cả metrics cùng lúc. Nhưng lab này dạy tôi rằng **chỉ nên thay đổi MỘT biến mỗi lần**, để có thể attribution rõ ràng: "rerank làm gì?", "dense hay hybrid?". Chỉ khi biết tác động cụ thể của từng biến, mới có thể đưa ra quyết định thiết kế tốt.

**Trade-off trong Rerank**: Rerank có thể cải thiện "tính xác thực" (faithfulness +0.10) nhưng giảm "độ liên quan" (relevance -0.30). Điều này khiến tôi nhận ra rằng hầu hết các bài toán đều có trade-off — không có solution perfect cho tất cả metrics. Phải chọn metric nào là quan trọng nhất cho use case.

**Grounding vs Completeness**: Câu hỏi q06 giúp tôi hiểu sâu hơn: gen model có xu hướng add thêm context liên quan nhưng ngoài scope (escalation support vs escalation access control), làm câu trả lời bị "mất tập trung". Điều này là **hallucination theo kiểu khác** — không phải bịa từ không, mà là bịa context không phải lúc.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)


**Ngạc nhiên 1**: Rerank **không cải thiện Context Recall** (vẫn 5.00/5). Tôi ban đầu kỳ vọng rerank sẽ "lọc bớt" chunks noise, nên recall sẽ giảm. Nhưng kết quả cho thấy: recall không đổi, tức là rerank có thể reorder ranking nhưng không bỏ/add chunks. Điều này giúp tôi "debug hypothesis": lỗi không phải ở việc miss source, mà ở việc mix quá nhiều context vào generation.

**Khó khăn**: Khi chạy eval.py lần đầu, tôi chưa hiểu rõ cách scoring manual vs LLM-as-Judge. File eval.py có code template nhưng chưa complete, nên phải đọc kỹ SCORING.md để hiểu luật chấm điểm. Chỉ từ đó mới có thể verify why q04 và q10 bị completeness thấp.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi: q06 — "Escalation trong sự cố P1 diễn ra như thế nào?"**

**Tình hình:**
- Baseline: Faithful=5, Relevant=5, Recall=5, Complete=5 → Điểm tốt
- Variant: Faithful=5, Relevant=4, Recall=5, Complete=4 → Giảm relevance và completeness

**Phân tích lỗi:**
Câu trả lời baseline full 10/10 vì:
1. **Retrieval tốt**: Dense embedding capture được keyword "escalation" + "P1" → lấy đúng source sla_p1_2026.txt
2. **Generation concise**: Prompt có ràng buộc cite source, nên gen model tập trung vào định nghĩa escalation P1 cụ thể.

Nhưng khi bật rerank (Variant), điểm giảm vì:
- Rerank có thể xếp **access-control-sop.md chunks lên cao** (vì chứa từ "escalation" về approval process), khiến generation model bị "split attention" giữa SLA escalation và access escalation.
- Generator vừa trả lời SLA vừa thêm context về access approval → câu trả lời bị lan sang 2 topic, relevance -1, completeness -1.

**Kết luận:**
Lỗi gốc nằm ở bước retrieval + rerank, không phải generation. Rerank ranking heuristic không đủ smart để partition "escalation" context theo semantic intent.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Thử giảm `top_k_select` từ 3 xuống 2**: Giả thuyết: using top-2 chunks thay vì 3 sẽ cắt được noise từ chunk thứ 3 (access-control), làm tăng lại relevance/completeness. Dựa trên tuning-log, đây là next experiment được recommend.

2. **Thay đổi prompt generation**: Thêm instruction "trả lời CHỈ về điều hỏi, không thêm quy trình liên quan" để ép LLM tập trung. Điều này vẫn giữ retrieval là dense, tuỳ theo recommedation "prompt engineering before retrieval tuning".

3. **Implement Hybrid Retrieval**: Nếu thời gian còn, thử `dense + BM25 hybrid` để xem keyword matching (BM25) có bổ sung được gap của dense embedding hay không.
