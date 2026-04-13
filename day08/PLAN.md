# RAG Pipeline Blueprint — Kiến trúc Đầy Đủ

> Thiết kế bám sát bộ tài liệu 5 files + 10 test questions

---

## Tổng quan kiến trúc

Hệ thống RAG được chia thành **5 tầng** xử lý tuần tự, với một feedback loop từ tầng Evaluation trở lại để cải thiện liên tục:

```
① Document Ingestion → ② Hybrid Indexing → ③ Retrieval Pipeline → ④ Augmentation + Generation → ⑤ Evaluation
        ↑______________________________________________feedback loop___________________________________|
```

---

## ① Document Ingestion

### Đặc điểm bộ tài liệu

Mỗi file `.txt` đã có sẵn metadata header có cấu trúc rõ ràng:

```
Source: support/sla-p1-2026.pdf
Department: IT
Effective Date: 2026-01-15
Access: internal
```

Đây là tài sản quý — cần extract toàn bộ và lưu cùng mỗi chunk dưới dạng metadata.

### Chiến lược Chunking

Sử dụng **semantic section splitting** theo dấu phân cách `=== ... ===` có sẵn trong file, thay vì sliding window cứng nhắc. Mỗi section (~150–400 token) đã là một đơn vị ngữ nghĩa hoàn chỉnh.

| Tham số | Giá trị gợi ý |
|---|---|
| Chunk size | ~512 tokens |
| Overlap | 64 tokens |
| Split strategy | Section-based (theo `===`) |

### Schema Metadata mỗi chunk

```json
{
  "source": "support/sla-p1-2026.pdf",
  "department": "IT",
  "effective_date": "2026-01-15",
  "section": "Phần 2: SLA theo mức độ ưu tiên",
  "category": "SLA",
  "aliases": [],
  "chunk_index": 2
}
```

> **Lưu ý đặc biệt — q07 (alias):** File `access_control_sop.txt` có dòng _"Tài liệu này trước đây có tên 'Approval Matrix for System Access'"_. Chunk này cần được index với metadata `aliases: ["approval matrix", "approval matrix for system access"]` để bắt được query dùng tên cũ.

### Embedding Model

Với nội dung tiếng Việt, chọn một trong hai:

- **`intfloat/multilingual-e5-large`** — open source, chạy được local, tốt cho tiếng Việt
- **`text-embedding-3-large`** (OpenAI) — chất lượng cao hơn, API-based, có chi phí

---

## ② Hybrid Indexing

Đây là điểm mấu chốt để giải quyết **toàn bộ 10 câu hỏi**, bao gồm cả các trường hợp đặc biệt. Cần **hai index chạy song song**:

### Vector DB — Dense Semantic Search

Dùng cho: câu hỏi ngữ nghĩa, paraphrase, câu hỏi không có keyword chính xác.

- **Giải quyết:** q01, q02, q03, q04, q05, q06, q08, q10
- **Stack:** Qdrant (khuyến nghị) / Chroma / Weaviate

### BM25 Index — Keyword & Alias Search

Dùng cho: từ kỹ thuật chính xác, tên cũ của tài liệu, mã lỗi.

- **Giải quyết:** q07 (alias "Approval Matrix"), q09 ("ERR-403-AUTH")
- **Stack:** BM25S (Python, nhẹ) / Elasticsearch (production scale)

### Metadata Filter Layer

Trước khi search, áp dụng pre-filter theo department hoặc category nếu query có context rõ (ví dụ: query về HR → chỉ search trong `hr_leave_policy`). Giảm noise và tăng precision.

---

## ③ Retrieval Pipeline

### Bước 1 — Query Rewriting

Trước khi search, mở rộng query bằng LLM để tăng recall:

```
Q gốc: "tài khoản bị khóa sau bao nhiêu lần?"
Q mở rộng: ["tài khoản bị khóa", "đăng nhập sai", "login failed", "account lock", "lần đăng nhập"]
```

Kỹ thuật bổ sung: **HyDE (Hypothetical Document Embeddings)** — dùng LLM generate đoạn trả lời giả định, embed đoạn đó và dùng để search thay vì embed câu hỏi gốc. Hiệu quả đặc biệt với câu hỏi ngắn hoặc mơ hồ.

### Bước 2 — Hybrid Retrieval với RRF

Chạy cả dense và sparse retrieval song song, merge kết quả bằng **Reciprocal Rank Fusion (RRF)**:

```
RRF_score(chunk) = Σ  1 / (k + rank_i)    với k = 60
```

Lấy top-10 chunks từ merged list để đưa sang bước reranking.

### Bước 3 — Reranking

Dùng CrossEncoder hoặc Cohere Rerank để tính relevance score chính xác hơn giữa (query, chunk), cắt từ top-10 xuống còn **top-3 chunks** thực sự liên quan nhất.

- **Stack:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (local) hoặc `cohere.rerank-v3` (API)

### Bước 4 — Context Check & Abstain Logic

Kiểm tra score của top chunk. Nếu relevance score thấp hơn threshold (ví dụ < 0.4), **không đưa vào LLM** — thay vào đó trả về câu abstain chuẩn.

```python
if top_score < THRESHOLD:
    return "Không tìm thấy thông tin về [{query_topic}] trong tài liệu hiện có."
```

> **Giải quyết q09 (ERR-403-AUTH):** Không có chunk nào trong 5 tài liệu chứa thông tin này → abstain đúng chuẩn, tránh hallucination.

---

## ④ Augmentation + Generation

### Prompt Builder

Mỗi request được xây dựng prompt gồm 3 phần:

```
[SYSTEM PROMPT]
Bạn là trợ lý hỗ trợ nội bộ. Chỉ trả lời dựa trên context được cung cấp bên dưới.
Nếu không tìm thấy thông tin trong context, trả lời:
"Không tìm thấy thông tin về [X] trong tài liệu hiện có."
Luôn cite source theo format: [Nguồn: source_path]
Không suy diễn hoặc thêm thông tin ngoài context.

[CONTEXT]
--- Chunk 1 [Nguồn: support/sla-p1-2026.pdf] ---
{chunk_text_1}

--- Chunk 2 [Nguồn: policy/refund-v4.pdf] ---
{chunk_text_2}

[QUESTION]
{user_query}
```

### LLM Generation

| Tham số | Giá trị |
|---|---|
| Model | Claude Sonnet / GPT-4o / Gemini 1.5 Pro |
| Temperature | 0 (deterministic, grounded) |
| Max tokens | 512–1024 |
| Grounding | Strict — chỉ dựa trên context |

### Answer + Citation Format

Output chuẩn gồm:
- Câu trả lời ngắn gọn, trực tiếp
- Citation rõ nguồn (`[Nguồn: ...]`)
- Confidence score (nếu cần)

**Ví dụ output cho q10 (VIP refund):**

> Tài liệu chính sách hoàn tiền (policy/refund-v4.pdf) không đề cập đến quy trình đặc biệt cho khách hàng VIP. Theo chính sách hiện hành, tất cả yêu cầu hoàn tiền đều theo cùng quy trình tiêu chuẩn trong 3–5 ngày làm việc. `[Nguồn: policy/refund-v4.pdf — Điều 4]`

---

## ⑤ Evaluation với RAGAS

Bộ 10 câu hỏi test là **evaluation set hoàn hảo** — đã có `expected_answer` và `expected_sources` đầy đủ.

### Metrics chính

| Metric | Đo cái gì | Target |
|---|---|---|
| **Faithfulness** | Answer có dựa trên retrieved context không (không hallucinate) | > 0.90 |
| **Answer Relevancy** | Answer có trả lời đúng câu hỏi không | > 0.85 |
| **Context Precision** | Retrieved chunks có chứa câu trả lời không | > 0.80 |
| **Context Recall** | Có bỏ sót chunk quan trọng không | > 0.80 |
| **Abstain Accuracy** | Hệ thống có biết "không biết" khi không có context không | = 1.0 |

### Mapping test cases → metrics quan trọng nhất

| Test case | Loại | Metric cần chú ý |
|---|---|---|
| q01, q02, q05, q08 | Standard easy | Answer Relevancy, Faithfulness |
| q03, q04, q06 | Standard medium | Context Precision |
| q07 | Alias / tên cũ | Context Recall (có tìm được chunk alias không) |
| q09 | Insufficient context | **Abstain Accuracy** |
| q10 | Grounding (VIP gap) | Faithfulness (không được bịa thêm VIP policy) |

### Chạy evaluation

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall

results = evaluate(
    dataset=test_dataset,  # 10 câu từ test_questions.json
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)
print(results)
```

---

## Stack gợi ý

### Quick Start (prototype)

```
LangChain + Chroma + BM25S + Claude Sonnet + RAGAS
```

### Production

```
LlamaIndex + Qdrant + Elasticsearch + Cohere Rerank + Claude Sonnet + RAGAS + LangSmith (tracing)
```

### Self-hosted / Cost-sensitive

```
Haystack + Qdrant + BM25S + multilingual-e5-large + Ollama (Llama 3) + RAGAS
```

---

## Roadmap triển khai

| Giai đoạn | Việc cần làm | Thời gian ước tính |
|---|---|---|
| **Phase 1** | Ingestion pipeline + chunking + metadata extract | 1–2 ngày |
| **Phase 2** | Hybrid index (vector + BM25) | 1 ngày |
| **Phase 3** | Retrieval pipeline (rewrite + RRF + rerank) | 2–3 ngày |
| **Phase 4** | Prompt builder + LLM integration + abstain logic | 1–2 ngày |
| **Phase 5** | Evaluation với RAGAS trên 10 test cases | 1 ngày |
| **Phase 6** | Tune threshold, chunk size, reranking dựa trên kết quả | Ongoing |

---

*Document generated from RAG design session — April 2026*