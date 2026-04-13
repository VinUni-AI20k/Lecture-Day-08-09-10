# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13 (run `results_v1`)  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 300 tokens
overlap = 60 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "gpt-4o-mini"
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.60 /5 |
| Answer Relevance | 4.20 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 3.90 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> q10 (Refund VIP) - Faithfulness 1, Relevance 1, Completeness 1: mô hình abstain quá mạnh dù context có policy chung để trả lời.
> q07 (Approval Matrix) - Completeness 2: chỉ nêu tên cũ `Approval Matrix for System Access`, thiếu mapping sang tên mới `Access Control SOP`.
> q09 (ERR-403-AUTH) - Relevance 1, Completeness 3: trả lời kiểu "không đủ dữ liệu" đúng hướng abstain nhưng thiếu gợi ý xử lý thực tế (liên hệ IT Helpdesk/nhóm xác thực).

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt chưa đủ rule để xử lý "không có case riêng nhưng có policy chung"
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13 (run `results_v1`)  
**Biến thay đổi:** Dense -> Hybrid + Rerank (chưa tuned)  
**Lý do chọn biến này:**
> Baseline có dấu hiệu bỏ sót ngữ cảnh alias/tên gọi cũ-mới (q07) và trả lời thiếu chắc chắn ở các câu hỏi giàu keyword đặc thù. Vì vậy nhóm thử Hybrid (Dense + BM25) để tăng khả năng bắt exact term, đồng thời thêm rerank để giảm nhiễu trước khi build context.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
top_k_search = 10
top_k_select = 3
use_rerank = True
rrf_dense_weight = 0.6
rrf_sparse_weight = 0.4
rerank_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Các tham số còn lại giữ nguyên baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.60/5 | 4.50/5 | -0.10 |
| Answer Relevance | 4.20/5 | 4.20/5 | +0.00 |
| Context Recall | 5.00/5 | 5.00/5 | +0.00 |
| Completeness | 3.90/5 | 3.90/5 | +0.00 |

**Nhận xét:**
> Cải thiện nhẹ ở q07 (Completeness 2 -> 3) vì hybrid bắt tốt hơn cụm từ liên quan Approval Matrix.
> Giảm chất lượng ở q04 (Faithfulness 5 -> 4) và q06 (Completeness 5 -> 4) do rerank đôi lúc đẩy các chunk có wording gần query nhưng không phải chunk tốt nhất để trả lời theo expected answer.
> q10 vẫn là điểm nghẽn lớn (Faithfulness 1, Relevance 1, Completeness 1), cho thấy bài toán không chỉ nằm ở retrieval mà còn ở logic generation/grounding.

**Kết luận:**
> Variant 1 chưa tốt hơn baseline ở mức tổng thể. Dù recall giữ nguyên 5.00/5, Faithfulness giảm nhẹ và Completeness không tăng. Nhóm cần tune sâu hơn ở bước rerank và prompt để tránh kéo lệch context khi hybrid trả về nhiều candidate gần nghĩa.

---

## Variant 2

**Ngày:** 2026-04-13 (run `results_v2`)  
**Biến thay đổi:** Tuning rerank + source focus + grounded prompt  
**Config:**
```
retrieval_mode = "hybrid"
top_k_search = 10
top_k_select = 3
use_rerank = True
```

### Tuning 1: blended rerank score
```python
ce_scores = list(_rerank_model.predict(pairs))

    def _minmax(values: List[float]) -> List[float]:
        if not values:
            return values
        v_min = min(values)
        v_max = max(values)
        if abs(v_max - vmin) < 1e-9:
            return [1.0 for  in values]
        return [(v - v_min) / (v_max - v_min) for v in values]

    # Blend CE score với retrieval score gốc để tránh rerank "lật kèo" quá mạnh.
    base_scores = [float(c.get("score", 0.0)) for c in candidates]
    ce_norm = _minmax([float(s) for s in ce_scores])
    base_norm = _minmax(base_scores)

    alpha = 0.75  # ưu tiên CE, nhưng vẫn giữ tín hiệu retrieval
    ranked_items = []
    for chunk, ce_s, base_s in zip(candidates, ce_norm, base_norm):
        final_score = alpha * ce_s + (1 - alpha) * base_s
        ranked_items.append({**chunk, "score": float(final_score)})

    ranked_items.sort(key=lambda x: x["score"], reverse=True)

    # Ưu tiên source "trội" để giảm lẫn ngữ cảnh ngoài scope câu hỏi.
    source_totals: Dict[str, float] = {}
    for item in ranked_items:
        src = item.get("metadata", {}).get("source", "")
        source_totals[src] = source_totals.get(src, 0.0) + item["score"]

    dominant_source = max(source_totals, key=source_totals.get) if source_totals else None

    selected: List[Dict[str, Any]] = []
    if dominant_source:
        for item in ranked_items:
            if item.get("metadata", {}).get("source", "") == dominant_source:
                selected.append(item)
                if len(selected) >= top_k:
                    return selected

```

### Tuning 2: ưu tiên dominant source sau rerank
```python
dominant_source = max(source_totals, key=source_totals.get) if source_totals else None

    selected: List[Dict[str, Any]] = []
    if dominant_source:
        for item in ranked_items:
            if item.get("metadata", {}).get("source", "") == dominant_source:
                selected.append(item)
                if len(selected) >= top_k:
                    return selected
```
### Tuning 3: prompt rules cụ thể hơn
```yaml
Answer only from the retrieved context below. Do not use outside knowledge.

Decision rules:
1) If the context directly contains the requested information, answer directly with citation.
2) If the exact scenario is not explicitly documented, but a general policy/process in context clearly applies, say that the document does not specify a separate case and provide the applicable standard policy/process from context.
3) Only say "Không đủ dữ liệu trong tài liệu hiện có để trả lời câu hỏi này." when neither direct evidence nor an applicable general policy/process is available in the context.

Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Answer only what the question asks; do not add adjacent policy details unless they are required to answer.
Respond in the same language as the question.

Question: {query}

Context:
{context_block}

Answer:
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.60 | 4.50 | 4.80 | Variant 2 |
| Answer Relevance | 4.20 | 4.20 | 4.40 | Variant 2 |
| Context Recall | 5.00 | 5.00 | 5.00 | Tie |
| Completeness | 3.90 | 3.90 | 4.10 | Variant 2 |

**Nhận xét Variant 2:**
> Cải thiện rõ nhất ở q10 (Faithfulness 1 -> 4, Relevance 1 -> 3, Completeness 1 -> 4), đúng mục tiêu giảm lỗi "rerank kéo lệch + abstain quá mức".
> q04 cũng cải thiện Completeness (3 -> 5) nhờ source focus và prompt rule rõ hơn.
> Tuy nhiên vẫn còn câu giảm (q06 Completeness 4 -> 2, q07 Completeness 3 -> 2), cho thấy dominant source bias có thể làm mất bối cảnh phụ hoặc thông tin rename cũ-mới.

**Kết luận Variant 2:**
> Variant 2 là cấu hình tốt nhất trong 3 mốc thử nghiệm (Baseline -> Variant 1 -> Variant 2) theo xu hướng tổng thể và đặc biệt hiệu quả với các câu dễ fail do context drift. Dù chưa xử lý triệt để q07 và q06, đây là phương án nên chọn để nộp vì cân bằng tốt hơn giữa faithfulness, relevance và completeness.

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Không phải thiếu recall (vẫn 5.00), mà là lỗi chọn và dùng context: rerank có thể kéo lệch nguồn và generation có thể abstain sai khi policy chung vẫn đủ trả lời.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Cụm thay đổi ở bước hậu retrieval (blended rerank score + ưu tiên dominant source) kết hợp prompt rule rõ ràng có tác động lớn nhất, đặc biệt giảm lỗi nghiêm trọng ở q10.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Thêm rule alias/rename dictionary (`Approval Matrix for System Access` -> `Access Control SOP`) và áp dụng rerank diversification để giữ 1-2 chunk bổ trợ thay vì dồn toàn bộ top-k vào một nguồn dominant.
