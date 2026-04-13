# Scorecard — Baseline

Nguồn dữ liệu: `day08/lab/logs/grading_run.json`  
Thời gian chạy: `2026-04-13T17:51:54.687240`

## Config

```text
label = baseline_dense
retrieval_mode = dense
top_k_search = 10
top_k_select = 3
use_rerank = False
```

## Average Scores

| Metric | Average |
|--------|---------|
| Faithfulness | 4.9 / 5 |
| Relevance | 4.8 / 5 |
| Context Recall | 4.67 / 5 |
| Completeness | 3.4 / 5 |

## Nhận xét nhanh

- Baseline rất ổn ở các câu đơn tài liệu như `gq03`, `gq04`, `gq08`, `gq09`, `gq10`.
- Điểm yếu lớn nhất là `gq06`: thiếu 1 nguồn kỳ vọng nên answer thiếu quy trình cấp quyền tạm thời.
- `gq05` retrieve đúng source nhưng answer tổng hợp sai ý chính về contractor và `Admin Access`.
- `gq07` có `Context Recall = N/A` vì bộ grading không khai báo `expected_sources` cho câu này.

## Chi tiết từng câu

| ID | Faithful | Relevant | Recall | Complete | Ghi chú ngắn |
|----|----------|----------|--------|----------|--------------|
| `gq01` | 5 | 5 | 5 | 3 | Đúng ý chính, thiếu version và effective date |
| `gq02` | 5 | 5 | 5 | 3 | Đúng VPN + 2 thiết bị, thiếu `Cisco AnyConnect` |
| `gq03` | 5 | 5 | 5 | 4 | Đúng, nhưng chưa nói rõ hai ngoại lệ |
| `gq04` | 5 | 5 | 5 | 4 | Đúng 110%, thiếu ý đây là tùy chọn |
| `gq05` | 5 | 5 | 5 | 2 | Sai ý chính: answer nói contractor không được cấp |
| `gq06` | 4 | 3 | 2 | 2 | Thiếu source `access-control-sop`, answer thiếu quy trình và thời hạn |
| `gq07` | 5 | 5 | N/A | 4 | Đúng hướng abstain, nhưng không có expected source để chấm recall |
| `gq08` | 5 | 5 | 5 | 4 | Đúng, thiếu chi tiết nộp qua HR Portal |
| `gq09` | 5 | 5 | 5 | 4 | Đúng 90 ngày + nhắc 7 ngày, thiếu URL/helpdesk |
| `gq10` | 5 | 5 | 5 | 4 | Đúng, thiếu chi tiết effective date của version 4 |
