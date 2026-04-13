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
| Faithfulness | 3.80 /5 |
| Answer Relevance | 3.80 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 3.90 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
- q07 (Approval Matrix): Dự kiến Context Recall thấp do "Approval Matrix" là alias của "Access Control SOP". Dense embedding có thể không map chính xác nếu không có keyword matching. Tuy nhiên thực tế Recall vẫn đạt 5.0, chỉ có Completeness là cần cải thiện (2.0).
- q10 (Mã lỗi/Thông tin thiếu): Model trả lời an toàn nhưng đôi khi quá ngắn gọn.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Sparse (Sprint 3)

**Ngày:** 13/04/2026
**Biến thay đổi:** retrieval_mode = "hybrid"
**Lý do chọn biến này:**
Dựa trên giả thuyết rằng các câu hỏi chứa mã lỗi (ERR-...) hoặc alias/tên cũ (Approval Matrix) sẽ thất bại với Dense retrieval đơn thuần (do vector similarity không đủ mạnh để bắt các exact terms hoặc alias chưa được fine-tune). Hybrid retrieval kết hợp BM25 giúp đảm bảo recall cho các keyword chính xác này.

**Config thay đổi:**
```
retrieval_mode = "hybrid"   # Kết hợp Dense + BM25 (RRF)
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Sparse:**
| Metric | Baseline | Sparse | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 3.80/5 | 4.20/5 | +0.40 |
| Answer Relevance | 3.80/5 | 3.80/5 | 0.00 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.90/5 | 2.90/5 | -1.00 |

**Nhận xét:**
- Sparse (Hybrid) vẫn giữ được Context Recall tuyệt đối (5.0) nhưng điểm Faithfulness đã tăng lên, Completeness bị sụt giảm.
- Nguyên nhân chính là do "Noise Overload": Hybrid mang về nhiều chunk chứa keyword trùng khớp nhưng ngữ cảnh lân cận không sát với ý nghĩa câu hỏi, dẫn đến việc LLM bị phân tâm khi tổng hợp thông tin.

**Kết luận:**
- Với bộ dữ liệu hiện tại, Dense Retrieval (Baseline) đang hiệu quả hơn về mặt sinh văn bản chất lượng cao.
- Hybrid cần được tune thêm trọng số hoặc kết hợp Reranker để loại bỏ nhiễu trước khi đưa vào LLM.

---

## Hybird (Kế hoạch tiếp theo)

**Biến thay đổi:** Tích hợp Reranking (Cohere Rerank)  
**Config:**
```
use_rerank = True
rerank_model = "rerank-multilingual-v3.0"
```

**Scorecard Hybird:**
| Metric | Baseline | Sparse | Hybird | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 3.80 | 4.20 | 3.80 | Sparse |
| Answer Relevance | 3.80 | 3.80 | 3.80 | Hybird |
| Context Recall | 5.00 | 5.00 | 5.00 | Hybird |
| Completeness | 3.90 | 2.90 | 3.60 | Baseline |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Lỗi "Noise Overload" trong Hybrid Retrieval: BM25 lôi kéo các đoạn văn bản chứa từ khóa giống nhau nhưng không cùng chủ đề, gây loãng context cho LLM.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Chiến lược Retrieval (Dense vs Hybrid) và cách prompt xử lý dữ liệu bị nhiễu.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Thử nghiệm Reranking (Cross-Encoder) để lọc top 3 đoạn văn chất lượng nhất sau khi Hybrid Search mang về tập ứng viên rộng.
