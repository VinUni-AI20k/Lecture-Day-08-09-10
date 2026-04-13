# Group Report — Day 08 RAG Pipeline

## Tóm tắt

Nhóm xây dựng một pipeline RAG nội bộ cho khối CS + IT Helpdesk, gồm 4 sprint: indexing, retrieval, tuning và evaluation. Hệ thống sử dụng ChromaDB cho vector store, embedding local `Alibaba-NLP/gte-multilingual-base`, và LLM Groq làm mặc định với fallback OpenAI.

## Kết quả chính

- **Sprint 1:** Hoàn thành preprocess, chunking theo heading/paragraph, gắn metadata và index 5 tài liệu.
- **Sprint 2:** Hoàn thành retrieval dense và grounded answer có citation.
- **Sprint 3:** Thử 3 biến tuning riêng: hybrid, rerank, query transform.
- **Sprint 4:** Chạy scorecard cho 10 câu hỏi test và lưu kết quả vào `results/` và `logs/`.

## Quan sát từ evaluation

- Baseline dense đã đạt recall rất cao trên bộ test nhỏ, nên hybrid không cải thiện nhiều.
- Rerank cho kết quả tốt nhất về faithfulness/completeness nhưng latency tăng rõ rệt.
- Query transform giúp một số câu alias nhưng latency cũng cao hơn baseline.
- Hybrid là cấu hình cân bằng nhất nếu ưu tiên chi phí/token và độ ổn định.

## Deliverables đã hoàn thành

- `index.py`
- `rag_answer.py`
- `eval.py`
- `results/scorecard_baseline.md`
- `results/scorecard_variant.md`
- `results/scorecard_rerank.md`
- `results/scorecard_query_transform.md`
- `docs/architecture.md`
- `docs/tuning-log.md`
- `logs/scorecard_ab_hybrid.json`
- `logs/scorecard_ab_rerank.json`
- `logs/scorecard_ab_query_transform.json`
- `logs/retrieval_comparison.json`

## Kết luận

Pipeline chạy được end-to-end và đáp ứng yêu cầu Sprint 1–4. Trong bộ test hiện tại, rerank là biến cải thiện chất lượng rõ nhất, còn hybrid là lựa chọn mặc định an toàn nhất cho triển khai thường xuyên.
