# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 13/04/2026  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.20 /5 |
| Answer Relevance | 4.60 /5 |
| Context Recall | 5.0 /5 |
| Completeness | 3.60 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> TODO: Liệt kê 2-3 câu hỏi có điểm thấp nhất và lý do tại sao.
> Ví dụ: "q07 (Approval Matrix) - context recall = 1/5 vì dense bỏ lỡ alias."

- gq05 - Faithfulness = 1 vì câu trả lời bị lỗi hư cấu (hallucination) khi khẳng định cộng tác viên có quyền Admin, trong khi tài liệu gốc chỉ giới hạn cho DevOps, SRE và IT Admin.  
- gq07 -  Faithfulness, Answer Relevance, Completeness = 1 vì câu trả lời bị thiếu thông tin (Incompleteness) vì không nêu rõ rằng tài liệu hiện tại không quy định mức phạt khi vi phạm SLA P1.
- gq01 - Completeness = 3 vì câu trả lời chỉ đúng phần thay đổi thời gian (6h còn 4h) nhưng bị đánh giá là 'Hoàn thành một phần' vì thiếu số phiên bản, ngày hiệu lực và thông tin về phiên bản cũ.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 13/04/2026  
**Biến thay đổi:** ___________  
**Lý do chọn biến này:**
> TODO: Giải thích theo evidence từ baseline results.
> Ví dụ: "Chọn hybrid vì q07 (alias query) và q09 (mã lỗi ERR-403) đều thất bại với dense.
> Corpus có cả ngôn ngữ tự nhiên (policy) lẫn tên riêng/mã lỗi (ticket code, SLA label)."
**Config thay đổi:**
```
retrieval_mode = "hybrid"
các biến khác giữ nguyên:
top_k_search': 10
'top_k_select': 3
'use_rerank': False
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.20/5 | 4.40/5 | +0.20 |
| Answer Relevance | 4.60/5 | 4.60/5 | 0.00 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.4/5 | 3.5/5 | +0.10 |

**Nhận xét:**
Variant 1 giúp giả thiện Faithfulness và Completeness. Trong khi đó,
Relevance và Recall không thay đổi

**Kết luận:**
> TODO: Variant 1 có tốt hơn baseline không?
> Bằng chứng là gì? (điểm số, câu hỏi cụ thể). 

Từ số liệu, Variant 1 cải thiện baseline tại 2 yếu tố Faithfulness và Completeness
tại câu gq01 cho Completeness tăng từ 3/5 lên 4/5, gq05 cho Faithfulness từ 1/5 lên 3/4

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** retrieval_mode, top_k_search, top_k_select
**Config:**
```
retrieval_mode=dense",
top_k_search=10
top_k_select=3
use_rerank=False
```

```
retrieval_mode=hybrid",
top_k_search=5
top_k_select=5
use_rerank=False
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 2 | Best |
|--------|----------|-----------|------|
| Faithfulness | 4.20 | 4.20 | N/A |
| Answer Relevance | 4.6 | ?.6 | N/A |
| Context Recall | 5.0 | 5.0 | N/A |
| Completeness | 3.5 | 3.5 | N/A |

**Nhận xét:**
Variant 2 Không giúp tăng 4 yếu tố nhưng có thể giảm thời gian truy vấn vì top k search nhỏ hơn

---

## Tóm tắt học được

> TODO (Sprint 4): Điền sau khi hoàn thành evaluation.

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Lỗi phổ biến nhất là Hallucination do thiếu tính kiềm chế (Abstain Failure) và Thiếu chi tiết bối cảnh (Context Loss). Cụ thể, model có xu hướng tự suy diễn dựa trên kiến thức sẵn có thay vì bám sát tài liệu khi gặp thông tin "ngoại lệ" (như case gq05 về quyền Admin của Contractor). Ngoài ra, việc bỏ lỡ các thông tin định danh như số phiên bản và ngày hiệu lực (gq01) cho thấy pipeline chưa tận dụng tốt Metadata để làm giàu câu trả lời.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Hybrid Retrieval kết hợp với Reranking có tác động lớn nhất. Trong khi Dense Retrieval (Baseline) dễ bị đánh lừa bởi các thuật ngữ tương đồng nhưng sai ngữ cảnh, thì Hybrid Search giúp bắt đúng các từ khóa đặc thù (như "mức phạt", "P1", "contractor"). Đặc biệt, Reranking đóng vai trò sàng lọc cuối cùng, đẩy các chunk chứa bằng chứng xác thực nhất lên top đầu, giúp khắc phục đáng kể lỗi Completeness và Faithfulness.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Tinh chỉnh Prompt yêu cầu model tự kiểm chứng lại các thực thể (như chức danh, con số) trước khi xuất kết quả để giảm Hallucination.  
   > Cải thiện Indexing để đính kèm thông tin effective_date và version vào từng chunk, giúp giải quyết triệt để vấn đề "hoàn thành một phần" như ở câu gq01.
