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
| Completeness | 4.10 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
- `q09` (Insufficient Context): Relevance 1/5, Completeness 1/5 do câu trả lời chỉ "Tôi không biết."
- `q10` (Refund VIP): Relevance 2/5, Completeness 3/5 do đã nêu thiếu thông tin nhưng chưa nêu rõ đầy đủ quy trình chuẩn.

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
| Answer Relevance | 4.30/5 | 4.40/5 | +0.10 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 4.10/5 | 4.20/5 | +0.10 |

**Nhận xét:**
- Hybrid cải thiện nhóm câu thiếu ngữ cảnh (`q09`: baseline 1.75 -> variant 3.00 điểm trung bình/câu).
- Hybrid giảm faithfulness ở câu alias/access control (`q07`: faithfulness 5 -> 2), cho thấy BM25 kéo thêm chunk nhiễu.
- Tổng thể: variant không vượt trội baseline toàn diện, nhưng tốt hơn nhẹ ở Relevance/Completeness.

**Kết luận:**
Khi chạy với OpenAI embeddings + OpenAI LLM judge, variant hybrid tạo trade-off rõ ràng:
- Tăng khả năng trả lời ở câu thiếu ngữ cảnh đặc thù.
- Giảm độ trung thành ở một số câu alias/keyword.
Baseline dense vẫn ổn định hơn về faithfulness.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** Hybrid weighting (tăng dense weight, giảm sparse weight)  
**Config:**
```
retrieval_mode = "hybrid"
dense_weight = 0.8
sparse_weight = 0.2
top_k_search = 10
top_k_select = 3
use_rerank = False
```

**Trạng thái:** Chưa chạy thực nghiệm do giới hạn thời gian sprint; giữ lại như hướng tối ưu tiếp theo để giảm nhiễu BM25 nhưng vẫn giữ lợi ích keyword match.

**Tiêu chí thành công khi chạy Variant 2:**
- Faithfulness >= 4.50 (ít nhất bằng baseline).
- Relevance >= 4.40 (không thấp hơn Variant 1).
- Không xuất hiện regression nghiêm trọng ở nhóm Access Control (`q03`, `q07`).
- `q09` vẫn giữ khả năng xử lý câu thiếu context (không hallucinate).

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.50 | 4.30 | TBD | Baseline |
| Answer Relevance | 4.30 | 4.40 | TBD | Variant 1 |
| Context Recall | 5.00 | 5.00 | TBD | Tie |
| Completeness | 4.10 | 4.20 | TBD | Variant 1 |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**  
   > Lỗi phổ biến nhất là *retrieval noise* khi dùng hybrid: BM25 kéo thêm chunk chứa keyword đúng nhưng ngữ cảnh không thật sự khớp ý hỏi. Dấu hiệu rõ nhất là `q07` bị giảm faithfulness mạnh (baseline 5 -> variant 2), dù câu trả lời nhìn bề ngoài có vẻ liên quan.

2. **Biến nào có tác động lớn nhất tới chất lượng?**  
   > Biến có tác động lớn nhất là **retrieval strategy** (Dense vs Hybrid). Chỉ đổi biến này đã tạo trade-off rõ: Faithfulness giảm (4.50 -> 4.30) nhưng Relevance/Completeness tăng nhẹ (4.30 -> 4.40 và 4.10 -> 4.20), trong khi Context Recall giữ nguyên 5.00.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**  
   > Nhóm sẽ chạy Variant 2 theo đúng A/B rule: giữ hybrid nhưng giảm BM25 influence (`dense_weight=0.8`, `sparse_weight=0.2`), sau đó mới thử bật rerank. Mục tiêu là giữ lợi ích keyword/alias (đặc biệt cho `q09`) nhưng tránh tụt faithfulness ở nhóm Access Control (`q03`, `q07`).

---

## Quyết định chốt cho demo/nộp bài

- **Config chốt hiện tại:** Baseline Dense (`retrieval_mode="dense"`, `top_k_search=10`, `top_k_select=3`, `use_rerank=False`).
- **Lý do:** Baseline cho faithfulness ổn định nhất trên bộ 10 câu, đồng thời context recall đạt mức tối đa.
- **Hybrid được giữ như hướng tối ưu tiếp theo:** ưu tiên thử `dense_weight=0.8 / sparse_weight=0.2` và chỉ bật rerank sau khi kiểm soát được nhiễu retrieval.
- **Ưu tiên cải thiện kế tiếp:** tăng completeness cho câu policy đặc biệt (VIP/alias) mà không làm giảm grounding.
