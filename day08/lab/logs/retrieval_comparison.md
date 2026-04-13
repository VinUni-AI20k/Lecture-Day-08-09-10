# Retrieval Comparison

Generated: 2026-04-13T17:29:46.437833

Test questions: 10

Best strategy: hybrid_rrf


## Strategy Summary

| Strategy | Recall@3 | Top1 | MRR | Avg prompt tokens | Query variants |
|---|---:|---:|---:|---:|---:|
| baseline_dense | 100.0% | 88.9% | 0.94 | 322 | 1.0 |
| hybrid_rrf | 100.0% | 88.9% | 0.94 | 321 | 1.0 |
| rerank_dense | 100.0% | 88.9% | 0.94 | 339 | 1.0 |
| query_transform_dense | 100.0% | 77.8% | 0.89 | 335 | 2.8 |

## Error Tree

| Failure Mode | Pipeline Stage | Root Cause | Recommended Fix |
|---|---|---|---|
| Câu trả lời sai sự thật | Generation | Prompt chưa đủ grounding hoặc model tự suy diễn ngoài context | Tăng citation constraint, thêm abstain rule và giảm temperature |
| Hallucination (trả lời không có trong context) | Generation / Retrieval | Context thiếu evidence, top_k quá thấp hoặc prompt cho phép bịa | Dùng hybrid + rerank, tăng top_k_search, ép answer-only-from-context |
| Câu trả lời thiếu chi tiết quan trọng | Retrieval / Chunking | Chunk quá ngắn/quá dài, missing evidence hoặc select top-k chưa đủ | Semantic chunking, hybrid search, tăng select/rerank, kiểm tra overlap |
| Context truy xuất không liên quan | Retrieval | Dense search bỏ lỡ keyword/alias, sparse không được fuse tốt | Hybrid RRF, query transform, kiểm tra alias và weight dense/sparse |
| Phản hồi chậm (> 5 giây) | Retrieval / Rerank / Generation | Reranker nặng, query transform quá nhiều variants, model load lặp lại | Cache reranker, giới hạn số variants, ưu tiên hybrid không rerank cho baseline |