# Tuning Log — RAG Pipeline (Day 08 Lab)

> Ghi lại mỗi thay đổi và kết quả quan sát được.
> Lưu ý: lần chạy hiện tại trong `results/eval.json` là một run gộp baseline + variant, nên một số mục về ngày chạy riêng từng cấu hình chỉ xác định được ở mức ngày của file log.

---

## Baseline (Sprint 2)

**Ngày:** `2026-04-13` (theo `results/eval.json`)  
**Config:**

```text
retrieval_mode = "dense"
chunk_size = 280 tokens
overlap = 50 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Baseline:**


| Metric           | Average Score |
| ---------------- | ------------- |
| Faithfulness     | 4.9 /5        |
| Answer Relevance | 4.8 /5        |
| Context Recall   | 4.67 /5       |
| Completeness     | 3.4 /5        |


**Câu hỏi yếu nhất (điểm thấp):**

- `gq06` — baseline chỉ retrieve được `1/2` expected sources, thiếu `it/access-control-sop.md`, nên câu trả lời không đầy đủ quy trình cấp quyền tạm thời và thời hạn `24 giờ`.
- `gq05` — retrieve đúng source nhưng answer kết luận sai rằng contractor không được cấp `Admin Access`; completeness chỉ `2/5`.
- `gq01` và `gq02` — câu trả lời đúng trọng tâm nhưng thiếu chi tiết quan trọng như version/effective date (`gq01`) và tên phần mềm VPN `Cisco AnyConnect` (`gq02`).

**Giả thuyết nguyên nhân (Error Tree):**

- Indexing: Chunking cắt giữa điều khoản
- Indexing: Metadata thiếu effective_date
- Retrieval: Dense bỏ lỡ exact keyword / alias
- Retrieval: Top-k quá ít → thiếu evidence
- Generation: Prompt không đủ grounding
- Generation: Context quá dài → lost in the middle

Giải thích:

- `gq06` là bằng chứng rõ nhất cho việc baseline chưa lấy đủ evidence ở bước retrieval.
- `gq05` cho thấy dù source đã đúng, answer vẫn suy luận sai; đây là lỗi generation/prompt nhiều hơn lỗi index.

---

## Variant 1 (Sprint 3)

**Ngày:** `2026-04-13` (theo `results/eval.json`)  
**Biến thay đổi:** `Nâng cấp bước retrieve và generate bằng router, prompt mới, query expansion và source filter`  
**Lý do chọn biến này:**
Baseline yếu nhất ở `gq06` vì thiếu source và thiếu nhiều vế câu trả lời, còn `gq05` sai ở bước tổng hợp answer dù source đúng. Vì vậy nhóm chuyển từ dense thuần sang một variant giữ dense làm nền nhưng thêm `auto` router, query expansion, source/domain filter, tăng `top_k_select`, và prompt v3 để cải thiện cả retrieval lẫn completeness.

**Config thay đổi:**

```text
retrieval_mode = "auto"
top_k_search = 8
top_k_select = 4
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Variant 1:**


| Metric           | Baseline | Variant 1 | Delta |
| ---------------- | -------- | --------- | ----- |
| Faithfulness     | 4.9/5    | 5.0/5     | +0.1  |
| Answer Relevance | 4.8/5    | 4.8/5     | +0.0  |
| Context Recall   | 4.67/5   | 5.0/5     | +0.33 |
| Completeness     | 3.4/5    | 3.9/5     | +0.5  |


**Nhận xét:**

- Cải thiện rõ nhất ở `gq06`: average per-question tăng từ `2.75` lên `4.75`, vì variant đã retrieve đủ `2/2` expected sources và trả lời đúng quy trình cấp quyền tạm thời.
- `gq05` cũng tốt hơn: answer đổi từ “không cấp cho contractor” sang “có thể cấp”, đúng hơn với expected answer.
- `gq01` tốt hơn nhẹ vì variant bổ sung được version và effective date của SLA mới.
- Các câu `gq02`, `gq03`, `gq04`, `gq08`, `gq09`, `gq10` gần như giữ nguyên.
- `gq07` là regression chính: baseline average `4.67`, variant còn `4.0`; variant vẫn trả lời đúng hướng “không có thông tin mức phạt”, nhưng relevance bị chấm thấp hơn.

**Kết luận:**
Variant 1 tốt hơn baseline trên bộ `grading_questions.json`, với cải thiện lớn nhất ở `Context Recall` và `Completeness`. Bằng chứng rõ nhất là `gq06` và `gq05` được sửa đáng kể, trong khi chỉ có một regression đáng chú ý ở `gq07`.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** `Chưa có dữ liệu`  
**Config:**

```text
Chưa chạy Variant 2 trong các file kết quả hiện có.
```

**Scorecard Variant 2:**


| Metric           | Baseline | Variant 1 | Variant 2 | Best      |
| ---------------- | -------- | --------- | --------- | --------- |
| Faithfulness     | 4.9      | 5.0       | N/A       | Variant 1 |
| Answer Relevance | 4.8      | 4.8       | N/A       | Tie       |
| Context Recall   | 4.67     | 5.0       | N/A       | Variant 1 |
| Completeness     | 3.4      | 3.9       | N/A       | Variant 1 |


---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
  > Trên baseline hiện tại, lỗi phổ biến nhất là retrieve chưa đủ evidence cho câu hỏi nhiều vế hoặc cross-document, sau đó model trả lời thiếu ý hoặc tổng hợp sai dù đã có một phần source đúng.
2. **Biến nào có tác động lớn nhất tới chất lượng?**
  > Gói thay đổi ở Variant 1 tác động mạnh nhất là `query router + query expansion/source filter`, vì nó cải thiện rõ `Context Recall` và kéo `gq06` từ case lỗi nặng thành gần đúng hoàn toàn.
3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
  > Chạy một `Variant 2` tách riêng từng thay đổi thay vì gộp cả gói, ưu tiên so sánh độc lập giữa `prompt v3` và `router/filter`, để biết chính xác thành phần nào tạo ra phần lớn cải thiện.

---

