# Scorecard — Variant

Nguồn dữ liệu: `day08/lab/logs/grading_run.json`  
Thời gian chạy: `2026-04-13T17:51:54.687240`

## Config

```text
label = variant_dense_router_prompt_v3
retrieval_mode = auto
top_k_search = 8
top_k_select = 4
use_rerank = False
```

## Average Scores

| Metric | Average |
|--------|---------|
| Faithfulness | 5.0 / 5 |
| Relevance | 4.8 / 5 |
| Context Recall | 5.0 / 5 |
| Completeness | 3.9 / 5 |

## Nhận xét nhanh

- Variant cải thiện rõ nhất ở `gq05` và `gq06`.
- `gq06` được sửa mạnh: retrieve đủ `2/2` nguồn kỳ vọng và answer đúng quy trình cấp quyền tạm thời.
- `gq05` không còn trả lời sai về contractor như baseline.
- Regression đáng chú ý nhất là `gq07`: relevance giảm còn `3/5`.
- `gq07` vẫn có `Context Recall = N/A` vì bộ grading không khai báo `expected_sources`.

## Chi tiết từng câu

| ID | Faithful | Relevant | Recall | Complete | Ghi chú ngắn |
|----|----------|----------|--------|----------|--------------|
| `gq01` | 5 | 5 | 5 | 4 | Tốt hơn baseline, đã có version/effective date của SLA mới |
| `gq02` | 5 | 5 | 5 | 3 | Giữ nguyên baseline, vẫn thiếu `Cisco AnyConnect` |
| `gq03` | 5 | 5 | 5 | 4 | Giữ nguyên baseline |
| `gq04` | 5 | 5 | 5 | 4 | Giữ nguyên baseline |
| `gq05` | 5 | 5 | 5 | 4 | Đã sửa đúng ý contractor có thể được cấp |
| `gq06` | 5 | 5 | 5 | 4 | Cải thiện lớn nhất, answer đúng quy trình và thời hạn 24 giờ |
| `gq07` | 5 | 3 | N/A | 4 | Đúng hướng “không có thông tin mức phạt”, nhưng relevance bị chấm thấp hơn |
| `gq08` | 5 | 5 | 5 | 4 | Giữ nguyên baseline |
| `gq09` | 5 | 5 | 5 | 4 | Giữ nguyên baseline |
| `gq10` | 5 | 5 | 5 | 4 | Giữ nguyên baseline |

## So với Baseline

| Metric | Baseline | Variant | Delta |
|--------|----------|---------|-------|
| Faithfulness | 4.9 | 5.0 | +0.1 |
| Relevance | 4.8 | 4.8 | +0.0 |
| Context Recall | 4.67 | 5.0 | +0.33 |
| Completeness | 3.4 | 3.9 | +0.5 |

Kết luận ngắn: variant hiện tốt hơn baseline trên bộ `grading_questions.json`, chủ yếu nhờ sửa được các câu cross-document khó như `gq06` và câu access control như `gq05`.
