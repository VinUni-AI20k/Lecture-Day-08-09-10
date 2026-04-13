# Group Report — Day 08 Lab

> Nộp bởi Tech Lead hoặc Documentation Owner.
> Mục tiêu: tóm tắt các quyết định kỹ thuật cấp nhóm, số liệu đánh giá, và kết luận cuối cùng.
> Báo cáo nhóm nên khác với individual report: tập trung vào hệ thống và trade-off của nhóm, không kể lại công việc cá nhân.

## 1. Tổng quan dự án

**Tên hệ thống:** TODO

**Mục tiêu:**
> TODO: Hệ thống giải quyết vấn đề gì? Dùng cho ai? Vì sao nhóm chọn bài toán này?

**Phạm vi dữ liệu:**
- TODO: Liệt kê các tài liệu được index
- TODO: Nêu loại câu hỏi mà hệ thống phải trả lời tốt nhất

## 2. Phân vai trong nhóm

| Vai trò | Tên | Trách nhiệm chính |
|---------|-----|------------------|
| Tech Lead | TODO | Nối pipeline end-to-end, quản lý merge và chạy demo |
| Retrieval Owner | TODO | Chunking, metadata, retrieval strategy, rerank |
| Eval Owner | TODO | Test questions, scorecard, A/B comparison |
| Documentation Owner | TODO | architecture.md, tuning-log.md, report |

## 3. Kiến trúc và quyết định kỹ thuật

### 3.1 Indexing

| Tham số | Giá trị cuối | Lý do |
|---------|-------------|-------|
| Chunk size | TODO | TODO |
| Overlap | TODO | TODO |
| Chunking strategy | TODO | TODO |
| Embedding model | TODO | TODO |
| Vector store | TODO | TODO |

### 3.2 Retrieval

**Baseline:**
- Strategy: TODO
- Top-k search: TODO
- Top-k select: TODO
- Rerank: TODO
- Query transform: TODO

**Variant tốt nhất của nhóm:**
- Strategy: TODO
- Top-k search: TODO
- Top-k select: TODO
- Rerank: TODO
- Query transform: TODO

**Lý do chọn variant:**
> TODO: Giải thích ngắn gọn dựa trên evidence từ scorecard và tuning log.

### 3.3 Generation

| Tham số | Giá trị |
|---------|---------|
| LLM model | TODO |
| Temperature | TODO |
| Prompt strategy | TODO |

**Grounding strategy:**
> TODO: Hệ thống ép citation như thế nào? Khi nào abstain?

## 4. Evaluation

### 4.1 Scorecard tóm tắt

| Metric | Baseline | Variant tốt nhất | Delta |
|--------|----------|------------------|-------|
| Faithfulness | TODO | TODO | TODO |
| Answer Relevance | TODO | TODO | TODO |
| Context Recall | TODO | TODO | TODO |
| Completeness | TODO | TODO | TODO |

### 4.2 Câu hỏi tiêu biểu

**Câu cải thiện rõ nhất:**
- TODO: question id + lý do

**Câu còn yếu:**
- TODO: question id + lý do

**Quan sát quan trọng:**
- TODO: Ví dụ, dense tốt ở câu nào, hybrid/rerank tốt ở câu nào

## 5. Kết luận nhóm

**Nhóm đã học được gì?**
> TODO: Tóm tắt 2-4 ý chính về retrieval, rerank, prompt, evaluation.

**Trade-off lớn nhất:**
> TODO: Ví dụ, tăng recall nhưng giảm relevance, hoặc giữ faithfulness nhưng mất completeness.

**Quyết định cuối cùng để nộp:**
> TODO: Chọn config nào cho grading_questions và vì sao.

## 6. Phụ lục ngắn

### 6.1 Files quan trọng
- [docs/architecture.md](../docs/architecture.md)
- [docs/tuning-log.md](../docs/tuning-log.md)
- [results/scorecard_baseline.md](../results/scorecard_baseline.md)
- [results/scorecard_variant.md](../results/scorecard_variant.md)

### 6.2 Ghi chú nộp bài
- Chỉ commit `reports/group_report.md` và `reports/individual/[ten].md` sau 18:00.
- Ghi rõ config tốt nhất của nhóm trong report.
- Nội dung phải khớp với scorecard và tuning log.
