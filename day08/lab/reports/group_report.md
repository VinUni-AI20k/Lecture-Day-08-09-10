# Group Report — Lab Day 08: RAG Pipeline

**Nhóm:** Team 62  
**Thành viên:**
- Ngô Hải Vân - Tech Lead
- Đỗ Minh Khiêm - Retrieval Owner
- Trần Đình Minh Vương - Eval Owner
- Phan Thanh Sang - Documentation Owner

**Ngày nộp:** 2026-04-13

---

## 1. Tổng quan hệ thống

Nhóm đã xây dựng RAG pipeline hoàn chỉnh với 4 sprints:
- Sprint 1: Indexing 29 chunks từ 5 tài liệu
- Sprint 2: Baseline với Dense retrieval + Grounded prompt
- Sprint 3: Variant với Hybrid retrieval (Dense + BM25 + RRF)
- Sprint 4: Evaluation với LLM-as-Judge

## 2. Quyết định kỹ thuật chính

### Chunking Strategy
- **Quyết định:** Section-based chunking theo heading "=== ... ==="
- **Lý do:** Giữ nguyên cấu trúc tự nhiên của tài liệu, không cắt giữa điều khoản
- **Tham số:** 400 tokens chunk size, 80 tokens overlap
- **Kết quả:** 29 chunks với metadata đầy đủ, không có chunk bị cắt giữa section

### Embedding Model
- **Quyết định:** OpenAI Embeddings (`text-embedding-3-small`) qua `OPENAI_API_KEY` của nhóm
- **Lý do:** Đồng bộ môi trường team, giảm sai khác local machine, chất lượng semantic retrieval ổn định hơn khi chạy eval
- **Trade-off:** Có chi phí API và phụ thuộc network, nhưng phù hợp mục tiêu demo/grading đồng nhất giữa các thành viên

### Retrieval Strategy
- **Baseline:** Dense (embedding similarity)
- **Variant:** Hybrid (Dense + BM25 + RRF với weights 0.6/0.4)
- **Lý do chọn Hybrid:** Corpus có cả natural language và keyword/mã lỗi
- **Kết quả:** Baseline tốt hơn Variant vì BM25 quá aggressive với keyword phổ biến

### Grounded Prompt
- **4 quy tắc:** Evidence-only, Abstain, Citation, Short/clear
- **Kết quả:** Faithfulness 4.60/5, abstain đúng 100% với câu không có docs

## 3. Kết quả Evaluation

### Metrics (Kết quả thực tế từ LLM-as-Judge)
| Metric | Baseline (Dense) | Variant (Hybrid) | Delta |
|--------|------------------|------------------|-------|
| Faithfulness | 4.50/5 | 4.30/5 | -0.20 |
| Answer Relevance | 4.30/5 | 4.50/5 | +0.20 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 ✅ |
| Completeness | 4.00/5 | 4.20/5 | +0.20 |

### Phân tích chi tiết

**Điểm mạnh của Baseline:**
- Context Recall hoàn hảo (5.00/5) - retrieve đúng 100% expected sources
- Faithfulness cao hơn variant (4.50 vs 4.30) - answer bám sát evidence hơn
- Abstain đúng 100% với câu không có docs (q09)

**Điểm mạnh và điểm yếu của Variant (Hybrid):**
- Tăng Relevance (+0.20) và Completeness (+0.20)
- Giảm Faithfulness (-0.20), đặc biệt ở câu alias/access control
- Ví dụ q07: variant trả lời đúng tên tài liệu nhưng judge đánh dấu có chi tiết chưa được hỗ trợ trực tiếp trong chunk

**Câu hỏi Variant kém hơn:**
- q07: Faithfulness 5→2 (alias mapping tốt hơn nhưng grounding chưa chặt)
- q03: cả baseline và variant đều bị judge phạt faithfulness ở một chi tiết phê duyệt level 3

**Root Cause:**
Hybrid với BM25 + RRF mang lại lợi ích keyword match nhưng cũng có rủi ro kéo nhiễu; khi keyword lặp lại nhiều trong corpus, cần tuning weight hoặc thêm rerank để giữ grounding.

**Kết luận:** Dense vẫn là baseline an toàn về faithfulness; Hybrid có tiềm năng nhưng cần fine-tuning BM25 weights/rerank trước khi dùng mặc định.

## 4. Challenges và Solutions

### Challenge 1: Trade-off giữa Faithfulness và Relevance
- **Vấn đề:** Hybrid cải thiện relevance/completeness nhưng giảm faithfulness
- **Root cause phát hiện:** 
  - BM25 match keyword quá aggressive với terms có frequency cao (P1, Level 3, remote)
  - Ví dụ q06: Query "Escalation P1" → BM25 match "P1" trong access control docs → retrieve sai context
  - Dense semantic search tốt hơn cho corpus có natural language nhiều
- **Lesson learned:** Phải chọn objective ưu tiên (faithfulness hay coverage) và test định lượng trước khi chốt cấu hình
- **Potential fix:** Giảm BM25 weight xuống 0.2, hoặc implement better Vietnamese tokenization

### Challenge 2: Completeness có thể cải thiện
- **Vấn đề:** Completeness 4.60/5, một số câu thiếu chi tiết phụ (q07, q10)
- **Root cause:** Top-3 chunks đôi khi không cover hết thông tin liên quan
- **Evidence:** q07 thiếu mention về tên cũ "Approval Matrix", q10 thiếu clarify về VIP policy
- **Potential fix:** 
  - Tăng top_k_select lên 5 chunks
  - Implement cross-encoder rerank để chọn chunks tốt hơn
  - Thêm query expansion cho alias terms

### Challenge 3: Alias queries và semantic gap
- **Vấn đề:** q07 "Approval Matrix" không match tốt với "Access Control SOP" (completeness 4/5)
- **Root cause:** Embedding model không capture được relationship giữa alias terms
- **Potential fix:** 
  - Thêm metadata field "aliases" vào chunks
  - Query expansion: "Approval Matrix" → ["Approval Matrix", "Access Control", "SOP"]
  - Fine-tune embedding model với domain-specific synonyms

### Challenge 4: LLM-as-Judge consistency
- **Vấn đề:** q03 có faithfulness score = 2 vì LLM judge cho rằng "IT Security" không có trong context, nhưng thực tế có
- **Root cause:** GPT-4o-mini đôi khi strict quá mức hoặc miss details trong long context
- **Lesson:** LLM-as-Judge cần validation, không thể 100% tin tưởng
- **Potential fix:** Sử dụng GPT-4 (stronger model) hoặc ensemble multiple judges

## 5. Nếu có thêm thời gian

1. **Query Expansion:** Generate alternative phrasings cho alias queries
2. **Better Tokenization:** Word segmentation cho tiếng Việt trong BM25
3. **Cross-encoder Rerank:** Cải thiện top-3 selection
4. **More Test Questions:** Edge cases và multi-hop questions
5. **Production Considerations:** Error handling, logging, monitoring

## 6. Phân công công việc

| Thành viên | Vai trò | Công việc chính |
|-----------|---------|-----------------|
| Ngô Hải Vân | Tech Lead | Sprint 1+2, pipeline integration |
| Đỗ Minh Khiêm | Retrieval Owner | Sprint 3, hybrid implementation |
| Trần Đình Minh Vương | Eval Owner | Sprint 4, LLM-as-Judge |
| Phan Thanh Sang | Documentation Owner | architecture.md, tuning-log.md |

## 7. Kết luận

Nhóm đã hoàn thành đầy đủ 4 sprints với pipeline chạy end-to-end bằng OpenAI API key của nhóm (`index.py -> rag_answer.py -> eval.py`). Baseline đạt faithfulness 4.50/5 và context recall 5.00/5; Variant đạt relevance/completeness tốt hơn nhẹ nhưng giảm faithfulness. Nhóm chọn baseline làm cấu hình ổn định và ghi nhận hướng tối ưu tiếp theo cho hybrid.

Hệ thống sẵn sàng cho grading questions và có thể scale cho production với một số cải tiến về error handling và monitoring.
