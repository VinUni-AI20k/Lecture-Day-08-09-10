# Tuning Log — RAG Pipeline (Day 08 Lab)

> A/B Rule: Mỗi variant chỉ đổi MỘT biến so với baseline (Variant 1 và Variant 2). Variant 3 là tổ hợp hai biến. Config grading cuối cùng = **Variant 1 (Dense + Rerank)**.
>
> **Ghi chú về độ ổn định số đo:** LLM-as-Judge (`gpt-4o-mini`, temperature=0) vẫn dao động ±0.10 giữa các lần chạy. Các bảng dưới đều được đo trong cùng phiên `python ablation.py` (Baseline, V1, V2, V3) sau khi đã fix bug `retrieve_sparse` (xem ghi chú cuối file).

---

## Baseline (Sprint 2)

**Ngày:** 13/04/2026
**Config:**

```python
retrieval_mode = "dense"
chunk_size = 400      # tokens (~1600 chars, paragraph-aware splitter)
overlap = 80          # tokens (~320 chars)
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "gpt-4o-mini"
```

**Scorecard Baseline:**

| Metric           | Average Score |
| ---------------- | ------------- |
| Faithfulness     | 4.20 / 5      |
| Answer Relevance | 4.20 / 5      |
| Context Recall   | 5.00 / 5      |
| Completeness     | 4.00 / 5      |

**Câu hỏi yếu nhất (điểm thấp):**

> - q09 (ERR-403-AUTH) — Faithfulness/Relevance = 1/5: Câu hỏi không có trong dataset, mô hình `abstain` đúng nhưng bị judge chấm thấp do không đáp ứng nội dung kỳ vọng.
> - q10 (Hoàn tiền VIP) — Relevance = 1/5: Kỳ vọng có quy trình VIP nhưng thực tế là standard, mô hình trả lời chung chung.
> - q04 (Refund — sản phẩm số) — Completeness = 3/5: Bỏ sót điều kiện ngoại lệ với license/subscription.

**Giả thuyết nguyên nhân (Error Tree):**

- [ ] Indexing: Chunking cắt giữa điều khoản (đã giảm thiểu nhờ paragraph-aware splitter)
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias (mã lỗi, tên tài liệu)
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Top-3 chunks có thể chứa noise → answer thiếu chính xác

---

## Variant 1 — Rerank-only (Sprint 3)

**Biến thay đổi (đúng 1 biến):** `use_rerank = False → True`
**Lý do chọn biến này:**

> Baseline cho thấy retriever đã mang đủ evidence (Context Recall = 5.00). Vấn đề là trong top-3 chunks đưa vào LLM context vẫn có chunk nhiễu (ảnh hưởng Faithfulness và Completeness ở q04). CrossEncoder rerank chấm lại từng cặp `(query, chunk)` trên top-10 candidates → giữ top-3 thật sự liên quan → kỳ vọng tăng Faithfulness và Relevance mà không cần đụng tới retrieval pipeline.

**Config thay đổi:**

```python
retrieval_mode = "dense"     # giữ nguyên
use_rerank = True            # ← biến duy nhất thay đổi
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**

| Metric           | Baseline | Variant 1    | Delta     |
| ---------------- | -------- | ------------ | --------- |
| Faithfulness     | 4.20 / 5 | **4.30 / 5** | **+0.10** |
| Answer Relevance | 4.20 / 5 | **4.50 / 5** | **+0.30** |
| Context Recall   | 5.00 / 5 | 5.00 / 5     | 0.00      |
| Completeness     | 4.00 / 5 | 4.00 / 5     | 0.00      |

**Nhận xét:**

> Variant 1 cải thiện cả Faithfulness (+0.10) và Relevance (+0.30) mà không giảm metric nào. Rerank lọc bớt chunks tangentially-related khỏi top-3 → answer bám evidence chặt hơn và đúng trọng tâm câu hỏi hơn. Cải thiện rõ nhất ở q10 (hoàn tiền VIP) — rerank loại được chunks không liên quan giúp model trả lời thẳng "không có quy trình VIP riêng" thay vì lan man.

**Kết luận:** Rerank là biến đòn bẩy hiệu quả nhất với chi phí thấp (chỉ thêm 1 lần CrossEncoder.predict cho 10 candidates). **Variant 1 thắng baseline rõ ràng.**

---

## Variant 2 — Hybrid-only (Sprint 3)

**Biến thay đổi (đúng 1 biến):** `retrieval_mode = "dense" → "hybrid"`
**Lý do chọn biến này:**

> Để kiểm chứng giả thuyết "Dense bỏ lỡ keyword chính xác (mã lỗi ERR-403-AUTH, alias tài liệu)", thêm BM25 sparse retrieval và fuse bằng Reciprocal Rank Fusion (weights 0.6 dense / 0.4 sparse). Kỳ vọng tăng Context Recall và Faithfulness ở các câu có keyword đặc thù.

**Config thay đổi:**

```python
retrieval_mode = "hybrid"    # ← biến duy nhất thay đổi
use_rerank = False           # giữ nguyên
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 2:**

| Metric           | Baseline | Variant 2    | Delta     |
| ---------------- | -------- | ------------ | --------- |
| Faithfulness     | 4.20 / 5 | 4.20 / 5     | 0.00      |
| Answer Relevance | 4.20 / 5 | 4.20 / 5     | 0.00      |
| Context Recall   | 5.00 / 5 | 5.00 / 5     | 0.00      |
| Completeness     | 4.00 / 5 | **3.80 / 5** | **−0.20** |

**Nhận xét:**

> Hybrid không cải thiện được metric nào, thậm chí Completeness giảm nhẹ (−0.20). Nguyên nhân chẩn đoán:
>
> 1. Corpus nhỏ (29 chunks từ 5 docs) — Dense đã cover đủ; thêm sparse không bổ sung evidence mới.
> 2. BM25 dùng `text.lower().split()` để tokenize tiếng Việt — không xử lý dấu/từ ghép → score sparse nhiễu, kéo top-3 fused lệch khỏi chunk tốt nhất.
> 3. RRF dồn rank của chunks cùng xuất hiện ở 2 list lên top, nhưng chunks có rank dense thấp lại bị giảm priority → mất 1 chunk ngữ cảnh phụ → Completeness giảm.

**Kết luận:** Hybrid **không phù hợp** với corpus tiếng Việt nhỏ này. Để hybrid có lợi cần: (a) tokenizer tiếng Việt chuẩn (pyvi/underthesea), (b) corpus đủ lớn để keyword match có ý nghĩa thống kê.

---

## Variant 3 — Hybrid + Rerank (kiểm thử tổ hợp 2 biến)

**Biến thay đổi:** Đồng thời 2 biến (`retrieval_mode = hybrid`, `use_rerank = True`).

> ⚠️ Không tuân thủ A/B 1-biến — chỉ dùng để đánh giá tổ hợp tốt nhất cho `run_grading.py`. Phần phân tích A/B chính thức nằm ở Variant 1 và Variant 2.

**Bảng so sánh tổng:**

| Metric           | Baseline | V1 (Rerank) | V2 (Hybrid) | **V3 (Hybrid+Rerank)** | Best |
| ---------------- | -------- | ----------- | ----------- | ---------------------- | ---- |
| Faithfulness     | 4.20     | **4.30**    | 4.20        | 4.10                   | V1   |
| Answer Relevance | 4.20     | **4.50**    | 4.20        | 4.30                   | V1   |
| Context Recall   | 5.00     | 5.00        | 5.00        | 5.00                   | Tie  |
| Completeness     | 4.00     | 4.00        | 3.80        | 4.00                   | Tie  |

**Nhận xét:**

> Ngược với kỳ vọng, V3 không cộng dồn lợi ích của V1 và V2 — Faithfulness và Relevance đều thấp hơn V1. Lý do: hybrid đưa thêm chunks BM25 nhiễu vào top-10, rerank dù lọc lại nhưng vẫn phải chọn giữa pool chất lượng kém hơn so với pool dense thuần.

**Quyết định chốt cấu hình grading:** Dùng **Variant 1 (Dense + Rerank)** — số liệu tốt nhất trên test set, A/B đã isolate biến rõ ràng.

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**

   > Hai loại lỗi nổi bật: (a) câu hỏi ngoài luồng (q09 ERR-403-AUTH) — model abstain đúng nhưng bị judge phạt vì không đáp ứng nội dung kỳ vọng (đây là hành vi đúng, không phải bug); (b) câu hỏi cần ngoại lệ chi tiết (q04 license refund) — model bỏ sót điều kiện phụ vì chunks top-3 chỉ chứa policy chính, thiếu chunk exception.

2. **Biến nào có tác động lớn nhất tới chất lượng?**

   > **`use_rerank`** là biến đòn bẩy thực sự (+0.10 Faithfulness, +0.30 Relevance). Trái với giả thuyết ban đầu, `retrieval_mode = hybrid` **không cải thiện** trên corpus nhỏ tiếng Việt (vì BM25 tokenize ngây thơ và dense đã cover gần đủ). Bài học: không phải kỹ thuật "advanced" nào cũng phù hợp — phải đo trên corpus thực tế.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**

   > Hai hướng theo độ ưu tiên points-per-effort:
   >
   > - **Query Transform (HyDE)**: viết lại câu hỏi thành mô tả giả định trước khi embed → cải thiện q10 (câu hỏi mơ hồ về VIP).
   > - **Tokenizer tiếng Việt cho BM25** (`pyvi` hoặc `underthesea`): nếu corpus mở rộng, hybrid sẽ thực sự có giá trị.
   > - Cải thiện indexer: extract mã lỗi/alias vào metadata để retrieve_sparse bắt được câu kiểu q09.

---
