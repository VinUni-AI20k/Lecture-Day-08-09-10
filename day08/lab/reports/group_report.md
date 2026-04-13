# Group Report — Day 08 Lab

> Nộp bởi Tech Lead hoặc Documentation Owner.
> Mục tiêu: tóm tắt các quyết định kỹ thuật cấp nhóm, số liệu đánh giá, và kết luận cuối cùng.
> Báo cáo nhóm nên khác với individual report: tập trung vào hệ thống và trade-off của nhóm, không kể lại công việc cá nhân.

## 1. Tổng quan dự án

**Tên hệ thống:** Internal Policy RAG Assistant (Day 08)

**Mục tiêu:**
> Nhóm xây dựng pipeline RAG nội bộ để tra cứu nhanh tài liệu policy/SOP/SLA/FAQ cho IT, CS và HR.
> Mục tiêu là trả lời có căn cứ từ tài liệu nội bộ, có citation nguồn và hạn chế hallucination khi gặp câu hỏi không có trong corpus.
> Nhóm chọn bài toán này vì phù hợp thực tế vận hành helpdesk/policy: nhiều tài liệu khác nhau, cần truy vấn nhanh và chính xác.

**Phạm vi dữ liệu:**
- 5 tài liệu đã index: `policy_refund_v4.txt`, `sla_p1_2026.txt`, `access_control_sop.txt`, `it_helpdesk_faq.txt`, `hr_leave_policy.txt`.
- Hệ thống trả lời tốt các câu factual có số liệu/quy định cụ thể và câu multi-section trong cùng domain (SLA, refund, access control, HR policy).

## 2. Phân vai trong nhóm

| Vai trò | Tên | Trách nhiệm chính |
|---------|-----|------------------|
| Tech Lead | Tống Tiến Mạnh | Nối pipeline end-to-end, quản lý merge và chạy demo |
| Retrieval Owner | Nguyễn Minh Hiếu; Nguyễn Tùng Lâm | Chunking, metadata, retrieval strategy, rerank |
| Eval Owner | Nguyễn Việt Long; Hà Huy Hoàng | Test questions, scorecard, A/B comparison |
| Documentation Owner | Nguyễn Quang Đăng | architecture.md, tuning-log.md, report |

## 3. Kiến trúc và quyết định kỹ thuật

### 3.1 Indexing

| Tham số | Giá trị cuối | Lý do |
|---------|-------------|-------|
| Chunk size | 400 tokens | Cân bằng giữa giữ đủ ngữ cảnh và không làm context quá dài |
| Overlap | 80 tokens | Giữ liên tục ngữ nghĩa giữa các chunk liền kề |
| Chunking strategy | Heading-based + fallback paragraph/size split | Ưu tiên ranh giới tự nhiên theo section để tăng chất lượng retrieve |
| Embedding model | text-embedding-3-small (OpenAI-compatible) | Ổn định, dễ tích hợp với retrieval dense hiện tại |
| Vector store | ChromaDB (PersistentClient, cosine) | Nhẹ, phù hợp bài lab, dễ inspect metadata/chunk |

### 3.2 Retrieval

**Baseline:**
- Strategy: Dense retrieval
- Top-k search: 10
- Top-k select: 3
- Rerank: False
- Query transform: None

**Variant tốt nhất của nhóm:**
- Strategy: Dense retrieval + LLM rerank
- Top-k search: 10
- Top-k select: 3
- Rerank: True
- Query transform: None

**Lý do chọn variant:**
> Baseline đã có context recall cao (5.00/5), nhưng thứ tự chunk đưa vào generation chưa tối ưu ở một số câu khó.
> Bật rerank cải thiện đồng thời Faithfulness, Relevance và Completeness trong khi giữ nguyên Context Recall.
> Theo scorecard, variant dense + rerank là cấu hình cân bằng tốt nhất để nộp.

### 3.3 Generation

| Tham số | Giá trị |
|---------|---------|
| LLM model | `openai-gpt-4o` (qua biến `LLM_MODEL`) |
| Temperature | 0 |
| Prompt strategy | Grounded prompt: evidence-only + abstain + citation + same-language response |

**Grounding strategy:**
> Prompt buộc model chỉ trả lời từ retrieved context và trích nguồn theo format [1], [2].
> Khi context không đủ, model phải abstain (ví dụ gq07 trong grading_run trả lời "Tôi không biết.") để tránh hallucination.

## 4. Evaluation

### 4.1 Scorecard tóm tắt

| Metric | Baseline | Variant tốt nhất | Delta |
|--------|----------|------------------|-------|
| Faithfulness | 4.60/5 | 4.70/5 | +0.10 |
| Answer Relevance | 3.00/5 | 3.20/5 | +0.20 |
| Context Recall | 5.00/5 | 5.00/5 | +0.00 |
| Completeness | 3.50/5 | 3.60/5 | +0.10 |

### 4.2 Câu hỏi tiêu biểu

**Câu cải thiện rõ nhất:**
- q04 (Refund): Relevant tăng từ 3 lên 4 sau khi bật rerank, cho thấy chunk có thông tin "110% store credit" được ưu tiên đúng hơn.
- q06 (SLA + Access escalation): Complete tăng từ 2 lên 3, cho thấy rerank hỗ trợ chọn evidence gần intent câu hỏi hơn.

**Câu còn yếu:**
- q06 vẫn yếu ở Relevance (1/5) do câu hỏi cross-doc multi-hop dài, cần tổng hợp chính xác nhiều mảnh evidence.
- q09 và q10 còn Completeness = 2 vì thiên về câu trả lời ngắn/an toàn, chưa mở rộng đủ ngữ cảnh phụ.

**Quan sát quan trọng:**
- Dense baseline đã đủ mạnh cho nhiều câu factual đơn tài liệu (q03, q04, q05).
- Rerank mang lại lợi ích rõ khi có nhiều chunk gần đúng và cần chọn đúng chunk trọng tâm trước generate.
- Với grading_run, pipeline xử lý tốt anti-hallucination ở gq07 bằng cách abstain thay vì bịa.

## 5. Kết luận nhóm

**Nhóm đã học được gì?**
> Context recall cao chưa đồng nghĩa answer quality cao; thứ tự evidence trước generation ảnh hưởng trực tiếp relevance/completeness.
> Rerank là biến tuning hiệu quả nhất trong bối cảnh hiện tại vì cải thiện 3/4 metric với chi phí thay đổi thấp.
> Grounded prompt + cơ chế abstain là bắt buộc để giảm rủi ro hallucination trong các câu không có dữ liệu.
> Evaluation theo scorecard giúp nhóm ra quyết định có bằng chứng thay vì chọn cấu hình theo cảm tính.

**Trade-off lớn nhất:**
> Trade-off chính là giữa độ an toàn và độ đầy đủ: cấu hình có rerank cho câu trả lời chắc chắn và đúng nguồn hơn, nhưng một số câu dài/multi-hop vẫn cần thêm cải tiến để tăng completeness.

**Quyết định cuối cùng để nộp:**
> Nhóm chọn `retrieval_mode="dense"` + `use_rerank=True` làm cấu hình nộp chính thức vì có kết quả tốt nhất trên scorecard: Faithfulness 4.70, Relevance 3.20, Context Recall 5.00, Completeness 3.60.

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
