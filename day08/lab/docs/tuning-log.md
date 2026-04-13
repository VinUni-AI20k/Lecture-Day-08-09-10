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
embedding_backend = OpenAI text-embedding-3-small (via OPENAI_API_KEY)
llm_model = gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.50 /5 |
| Answer Relevance | 4.30 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 4.00 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
- `q09` (Insufficient Context): Relevance 1/5, Completeness 1/5 do câu trả lời chỉ "Tôi không biết."
- `q10` (Refund VIP): Relevance 2/5, Completeness 2/5 do thiếu nêu rõ "không có quy trình VIP riêng, vẫn theo quy trình chuẩn 3-5 ngày."

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt chưa ép model trả lời đầy đủ với câu thiếu ngữ cảnh đặc biệt (VIP, alias)
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** Retrieval strategy (Dense -> Hybrid)  
**Lý do chọn biến này:**
Corpus chứa nhiều từ khóa đặc thù (P1, Level 3, Approval Matrix, ERR-403) bên cạnh mô tả ngôn ngữ tự nhiên.
Hybrid (Dense + BM25) giúp tăng khả năng bắt exact match và alias, nhất là cho các câu hỏi dạng mã lỗi/tên cũ tài liệu.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.50/5 | 4.30/5 | -0.20 |
| Answer Relevance | 4.30/5 | 4.50/5 | +0.20 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 4.00/5 | 4.20/5 | +0.20 |

**Nhận xét:**
- Hybrid cải thiện nhóm câu thiếu ngữ cảnh (`q09`: baseline 1.75 -> variant 3.25 điểm trung bình/câu).
- Hybrid giảm faithfulness ở câu alias/access control (`q07`: faithfulness 5 -> 2), cho thấy BM25 kéo thêm chunk nhiễu.
- Tổng thể: variant không vượt trội baseline toàn diện, nhưng tốt hơn ở Relevance/Completeness.

**Kết luận:**
Khi chạy với OpenAI embeddings + OpenAI LLM judge, variant hybrid tạo trade-off rõ ràng:
- Tăng khả năng trả lời ở câu thiếu ngữ cảnh đặc thù.
- Giảm độ trung thành ở một số câu alias/keyword.
Baseline dense vẫn ổn định hơn về faithfulness.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** ___________  
**Config:**
```
# TODO
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.50 | 4.30 | TBD | Baseline |
| Answer Relevance | 4.30 | 4.50 | TBD | Variant 1 |
| Context Recall | 5.00 | 5.00 | TBD | Tie |
| Completeness | 4.00 | 4.20 | TBD | Variant 1 |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Misalignment giữa alias/keyword và semantic intent trong Hybrid retrieval làm giảm faithfulness ở một số câu.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Retrieval strategy (Dense vs Hybrid) có tác động lớn nhất, rõ nhất ở q07 và q09.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Bật cross-encoder rerank + giảm BM25 weight để giữ lợi thế recall mà không làm giảm faithfulness.
