# Architecture — RAG Pipeline (Day 08 Lab)

> Deliverable của Documentation Owner.

## 1. Tổng quan kiến trúc

```
[Raw Docs]
    ↓
[index.py: Preprocess → Chunk → Embed → Store]
    ↓
[ChromaDB Vector Store]
    ↓
[rag_answer.py: Query → Retrieve → Rerank → Generate]
    ↓
[Grounded Answer + Citation]
```

**Mô tả ngắn gọn:**
> Nhóm xây dựng một trợ lý ảo nội bộ dành riêng cho đội ngũ Chăm sóc khách hàng (CS) và IT Helpdesk. Hệ thống sử dụng kiến trúc truy xuất thông tin RAG để trích xuất và giải đáp chính xác các câu hỏi của nhân viên, ví dụ như câu hỏi về chính sách, SLA, và quy trình vận hành từ nguồn dữ liệu nội bộ. Giải pháp này giúp nhân viên loại bỏ thời gian tra cứu tài liệu thủ công, đảm bảo tính nhất quán trong luồng hỗ trợ và tối ưu hóa tốc độ xử lý ticket.

---

## 2. Indexing Pipeline (Sprint 1)

### Tài liệu được index
| File | Nguồn | Department | Số chunk |
|------|-------|-----------|---------|
| `policy_refund_v4.txt` | policy/refund-v4.pdf | CS | 6 |
| `sla_p1_2026.txt` | support/sla-p1-2026.pdf | IT | 5 |
| `access_control_sop.txt` | it/access-control-sop.md | IT Security | 8 |
| `it_helpdesk_faq.txt` | support/helpdesk-faq.md | IT | 6 |
| `hr_leave_policy.txt` | hr/leave-policy-2026.pdf | HR | 5 |

### Quyết định chunking
| Tham số | Giá trị | Lý do |
|---------|---------|-------|
| Chunk size | 500 tokens | Kích thước tối ưu giúp cân bằng hiệu suất truy xuất. Mức này đủ lớn để bao trọn một bước quy trình hoặc một đoạn chính sách (tránh đứt gãy ngữ cảnh), đồng thời đủ nhỏ để hạn chế nhiễu thông tin (noise), ngoài ra còn duy trì độ chính xác cao khi xử lý các câu hỏi FAQ ngắn. |
| Overlap | 50 tokens | Độ dài đủ để bảo toàn các cấu trúc điều kiện nguyên nhân - kết quả vắt ngang giữa hai chunk, giúp LLM tổng hợp logic chính xác mà không làm lãng phí không gian lưu trữ của Vector Database. |
| Chunking strategy | Heading-based | Chunking strategy này tận dụng cấu trúc phân cấp tự nhiên của tài liệu chính sách để đảm bảo 100% nội dung của một điều khoản hoặc một cặp câu hỏi FAQ được giữ nguyên vẹn trong một chunk duy nhất, không bị cắt vụn |
| Metadata fields | source, section, effective_date, department, access | Phục vụ filter, freshness, citation |

### Embedding model
- **Model**: gemini-embedding-2-preview
- **Vector store**: ChromaDB (PersistentClient)
- **Similarity metric**: Cosine

---

## 3. Retrieval Pipeline (Sprint 2 + 3)

### Baseline (Sprint 2)
| Tham số | Giá trị |
|---------|---------|
| Strategy | Dense (embedding similarity) |
| Top-k search | 10 |
| Top-k select | 3 |
| Rerank | Không |

### Variant (Sprint 3)
| Tham số | Giá trị | Thay đổi so với baseline |
|---------|---------|------------------------|
| Strategy | dense | Không đổi |
| Top-k search | 10 | Không đổi |
| Top-k select | 3 | Không đổi |
| Rerank | Cross-encoder | Thêm rerank |
| Query transform | Không có | Không có |

**Lý do chọn variant này:**
> Bổ sung Rerank (Cross-encoder) để khắc phục điểm yếu "thiếu độ chính xác vi mô" của Dense Search. Trong tài liệu Helpdesk, các chính sách có từ khóa gần giống nhau sẽ có vector rất sát nhau, dễ bị truy xuất nhầm. Cross-encoder sẽ so khớp chéo (cross-attention) từng từ giữa câu hỏi và Top 10 chunk thô, từ đó chấm điểm và chọn ra 3 chunk chính xác tuyệt đối trước khi đưa cho LLM.

---

## 4. Generation (Sprint 2)

### Grounded Prompt Template
```
You are an assistant that answers questions based ONLY on the retrieved context.
Strict rules:
1. Use only the information provided in the context.
2. If the context is insufficient to answer with certainty, respond exactly with: "Không đủ dữ liệu."
3. Do not make assumptions or fabricate any information.
4. When providing an answer, include citations using chunk indices such as [1], [2].
5. When possible, include the corresponding source/section from the cited chunks.
6. Keep the answer concise, clear, and in the same language as the question.

Question:
{query}

Context:
{context_block}

Answer:
```

### LLM Configuration
| Tham số | Giá trị |
|---------|---------|
| Model | gmeini-2.5-flash |
| Temperature | 0 (để output ổn định cho eval) |
| Max tokens | 512 |

---

## 5. Failure Mode Checklist

> Dùng khi debug — kiểm tra lần lượt: index → retrieval → generation

| Failure Mode | Triệu chứng | Cách kiểm tra |
|-------------|-------------|---------------|
| Index lỗi | Không truy xuất được đoạn văn bản của `it-helpdesk-faq.md`, kết quả chia chunk trả về text rỗng | In ra hàm `doc()` trong function `build_index()` file index.py để check xem tất cả các documents đã được truy xuất nội dung đầy đủ chưa |
| Index lỗi | Chunk bị lặp lại | In ra nội dung từng chunk bằng function `list_chunks()` |

---

