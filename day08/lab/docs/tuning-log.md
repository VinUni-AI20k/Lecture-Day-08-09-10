# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "openai-gpt-4o"
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.50 /5 |
| Answer Relevance | 3.30 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 3.80 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
- q06 (Escalation P1): relevance = 1/5, completeness = 2/5. Answer trộn cả escalation của SLA P1 và escalation quyền truy cập tạm thời từ access-control nên bị dư thông tin ngoài trọng tâm câu hỏi.
- q09 (ERR-403-AUTH): completeness = 2/5. Hệ thống abstain đúng nhưng expected answer có thêm gợi ý liên hệ IT Helpdesk nên điểm completeness không cao.
- q10 (VIP refund): completeness = 2/5. Hệ thống abstain ngắn, chưa nêu đầy đủ ý "không có quy trình VIP riêng, vẫn theo quy trình chuẩn 3-5 ngày".

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** `use_rerank: False -> True`  
**Lý do chọn biến này:**
Dựa trên baseline, các câu q06/q10 bị giảm relevance và completeness do context đưa vào prompt còn nhiễu hoặc thiếu tập trung. Rerank được chọn để giữ nguyên dense retrieval nhưng sắp lại top chunks trước khi generate, kỳ vọng tăng độ đúng trọng tâm câu trả lời.

**Config thay đổi:**
```
retrieval_mode = "dense"
top_k_search = 10
top_k_select = 3
use_rerank = True
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.50/5 | 4.60/5 | +0.10 |
| Answer Relevance | 3.30/5 | 3.00/5 | -0.30 |
| Context Recall | 5.00/5 | 5.00/5 | +0.00 |
| Completeness | 3.80/5 | 3.50/5 | -0.30 |

**Nhận xét:**
- Cải thiện nhẹ faithfulness trung bình (+0.10), một số câu có trích dẫn gọn và tập trung hơn (q01, q07).
- Không cải thiện recall (giữ 5.00/5), chứng tỏ rerank không tác động tới khả năng retrieve đúng source.
- Relevance và completeness giảm ở các câu quan trọng (q01, q04, q06), do rerank đôi lúc đẩy chunk nhiều chi tiết phụ lên cao hoặc làm mất một phần detail then chốt.

**Kết luận:**
Variant 1 không tốt hơn baseline về tổng thể cho bộ câu hỏi hiện tại. Bằng chứng: relevance giảm 0.30 và completeness giảm 0.30, trong khi faithfulness chỉ tăng nhẹ 0.10 và context recall không đổi.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** Chưa thực hiện  
**Config:**
```
# Not run
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.50 | 4.60 | N/A | Variant 1 |
| Answer Relevance | 3.30 | 3.00 | N/A | Baseline |
| Context Recall | 5.00 | 5.00 | N/A | Tie |
| Completeness | 3.80 | 3.50 | N/A | Baseline |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Retriever lấy đúng source nhưng generation vẫn trả lời lan sang chi tiết ngoài trọng tâm (đặc biệt câu hỏi escalation), làm giảm relevance/completeness.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Rerank có tác động rõ tới cách model tổng hợp context, nhưng với cấu hình hiện tại tác động nghiêng về giảm relevance/completeness hơn là cải thiện tổng thể.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Giữ baseline dense và thử thay đổi prompt generation (ràng buộc "chỉ trả lời đúng trọng tâm câu hỏi, không thêm quy trình liên quan") hoặc giảm top_k_select xuống 2 để giảm nhiễu context.
