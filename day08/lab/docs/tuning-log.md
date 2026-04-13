# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens (~1600 ký tự)
overlap = 80 tokens (~320 ký tự)
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
embedding_model = text-embedding-3-small
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.40 /5 |
| Answer Relevance | 5.00 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 3.40 /5 |

**Per-Question Detail:**
| ID | Category | Faith. | Relev. | Recall | Compl. | Ghi chú |
|----|----------|--------|--------|--------|--------|---------|
| q01 | SLA | 5 | 5 | 5 | 3 | Thiếu phần "phản hồi 15 phút", chỉ nêu resolution 4h |
| q02 | Refund | 3 | 5 | 5 | 5 | Grounding ratio 66.67% — có vài từ không match trực tiếp |
| q03 | Access Control | 5 | 5 | 5 | 5 | Trả lời chính xác, đầy đủ 3 approver |
| q04 | Refund | 5 | 5 | 5 | 5 | Ngoại lệ kỹ thuật số nêu rõ ràng |
| q05 | IT Helpdesk | 5 | 5 | 5 | 5 | Match 100% expected answer |
| q06 | SLA | 5 | 5 | 5 | 5 | Trả lời cả escalation SOP và cross-doc quy trình cấp quyền P1 |
| q07 | Access Control | **1** | 5 | 5 | **1** | ⚠️ Dense THẤT BẠI — abstain sai. Đây là query alias "Approval Matrix" → pipeline trả "Không đủ dữ liệu" dù context đã retrieve đúng source. LLM không nhận ra alias |
| q08 | HR Policy | 5 | 5 | 5 | 3 | Thiếu điều kiện "sau probation" và "Team Lead phê duyệt" |
| q09 | Insufficient Context | 5 | 5 | N/A | 1 | ✅ Abstain đúng — không có ERR-403-AUTH trong docs |
| q10 | Refund | 5 | 5 | 5 | 1 | ⚠️ Abstain khi không nên. Docs có thông tin quy trình tiêu chuẩn nhưng pipeline trả "Không đủ dữ liệu" |

**Câu hỏi yếu nhất (điểm thấp):**
> 1. **q07** (Approval Matrix) — Faithfulness = 1, Completeness = 1. Dense retrieval thực ra **đã retrieve đúng source** (context recall = 5/5) nhưng LLM vẫn trả "Không đủ dữ liệu" vì query dùng tên cũ "Approval Matrix" mà prompt grounding quá nghiêm khắc, LLM không dám map alias → tên mới "Access Control SOP".
> 2. **q10** (Hoàn tiền VIP) — Completeness = 1. Pipeline abstain khi lẽ ra nên trả lời rằng "không có quy trình đặc biệt cho VIP, tất cả theo quy trình tiêu chuẩn". Đây là lỗi false abstain.
> 3. **q01** (SLA P1) — Completeness = 3. Trả lời chỉ nêu resolution 4h mà thiếu first response 15 phút. Chunk có cả 2 thông tin nhưng LLM chọn trả lời ngắn quá.
> 4. **q08** (Remote work) — Completeness = 3. Thiếu điều kiện kèm theo (probation, Team Lead phê duyệt).

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản → **Không phải vấn đề** (chunking theo heading hoạt động tốt)
- [ ] Indexing: Metadata thiếu effective_date → **Không phải vấn đề** (metadata parse đúng)
- [x] **Retrieval: Dense bỏ lỡ alias/tên cũ** → q07 LLM không nhận alias dù context recall đúng
- [ ] Retrieval: Top-k quá ít → **Không phải vấn đề** (top_k_search=10, context recall=5.00)
- [x] **Generation: Prompt grounding quá nghiêm** → q07 và q10 false abstain khi context có nhưng LLM không dám suy luận
- [ ] Generation: Context quá dài → lost in the middle → **Ít khả năng** (chỉ 3 chunks)
- [x] **Generation: LLM trả lời thiếu chi tiết** → q01, q08 thiếu thông tin phụ dù chunk có

---

## Variant 1 (Sprint 3) — Hybrid Retrieval

**Ngày:** 2026-04-13  
**Biến thay đổi:** `retrieval_mode` từ `"dense"` → `"hybrid"` (Dense + BM25 Sparse + RRF fusion)  
**Lý do chọn biến này:**
> Chọn hybrid vì phân tích baseline cho thấy:
> 1. **q07 (alias query)**: Dense retrieval đã retrieve đúng source nhưng vấn đề nằm ở generation. Tuy nhiên, hybrid có thể cải thiện ranking — BM25 match keyword "Approval Matrix" trực tiếp trong text "Ghi chú: Tài liệu này trước đây có tên Approval Matrix for System Access" → chunk chứa alias sẽ được rank cao hơn.
> 2. **Corpus đặc thù**: Có cả ngôn ngữ tự nhiên (policy mô tả quy trình) lẫn keyword kỹ thuật (SLA P1, Level 3, ERR-403). Dense mạnh ở semantic matching nhưng BM25 bổ trợ exact term matching.
> 3. **A/B Rule**: Chỉ đổi DUY NHẤT retrieval_mode, giữ nguyên tất cả tham số khác.

**Config thay đổi:**
```
retrieval_mode = "hybrid"     # ← BIẾN DUY NHẤT THAY ĐỔI
dense_weight = 0.6            # Weight cho dense trong RRF
sparse_weight = 0.4           # Weight cho sparse (BM25) trong RRF
rrf_k = 60                    # Hằng số RRF tiêu chuẩn
# Các tham số còn lại giữ nguyên như baseline
```

**⚠️ KẾT QUẢ THỰC TẾ: VARIANT CRASH**

Khi chạy `eval.py` với `VARIANT_CONFIG`, toàn bộ 10 câu đều **crash** với lỗi:
```
ERROR: No module named 'rank_bm25'
```

**Nguyên nhân**: Thư viện `rank-bm25` chưa được cài đặt (`pip install rank-bm25`). Hàm `retrieve_sparse()` import `from rank_bm25 import BM25Okapi` nhưng package không có trong môi trường.

**Scorecard Variant 1 (thực tế — crashed):**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.40/5 | 1.00/5 | -3.40 |
| Answer Relevance | 5.00/5 | 1.00/5 | -4.00 |
| Context Recall | 5.00/5 | 1.00/5 | -4.00 |
| Completeness | 3.40/5 | 1.00/5 | -2.40 |

> ⚠️ **Số liệu trên KHÔNG phản ánh chất lượng hybrid retrieval** mà phản ánh pipeline bị crash hoàn toàn do thiếu dependency.

**Nhận xét:**
> - **Variant 1 không chạy được** do thiếu cài đặt `rank-bm25`. Đây là lỗi environment setup, không phải lỗi logic code.
> - Code `retrieve_sparse()` và `retrieve_hybrid()` đã được implement đầy đủ: BM25 tokenization, RRF fusion với weighted ranks. Logic code đúng nhưng không test được.
> - Ngoài ra, `VARIANT_CONFIG` trong `eval.py` set `use_rerank=True`, nhưng hàm `rerank()` trong `rag_answer.py` **chưa implement cross-encoder** (chỉ trả `candidates[:top_k]`). Điều này có nghĩa rerank không tạo ra sự khác biệt nào.

**Phân tích kỳ vọng (nếu hybrid chạy đúng):**

Dựa trên logic code, hybrid retrieval **kỳ vọng cải thiện** ở:

| Câu hỏi | Baseline | Kỳ vọng Hybrid | Lý do |
|----------|----------|-----------------|-------|
| q07 (Approval Matrix) | Abstain sai (1/5 faithfulness) | Có thể cải thiện ranking | BM25 match exact "Approval Matrix" trong text → chunk chứa alias được rank cao hơn → LLM có context rõ hơn |
| q09 (ERR-403-AUTH) | Abstain đúng (5/5) | Giữ nguyên | Không có trong docs → cả dense và sparse đều không tìm thấy |
| q01 (SLA P1) | Completeness 3/5 | Có thể cải thiện | BM25 match "P1" chính xác → chunk SLA P1 rank cao hơn |

Tuy nhiên, hybrid cũng có **rủi ro**:
- BM25 whitespace tokenization đơn giản (không có stemming/stopword removal cho tiếng Việt) → có thể thêm noise
- Nếu sparse results trùng lặp nhiều với dense → RRF không tạo khác biệt đáng kể

**Kết luận:**
> - **Variant 1 KHÔNG thể đánh giá được** do crash toàn bộ vì thiếu dependency `rank-bm25`.
> - Về mặt code logic, hybrid retrieval (Dense + BM25 + RRF) đã được implement đúng theo slide: RRF fusion K=60, weighted dense 0.6 / sparse 0.4.
> - **Baseline vẫn là cấu hình hoạt động duy nhất** với kết quả khá tốt: Faithfulness 4.40, Relevance 5.00, Context Recall 5.00.
> - Điểm yếu chính của baseline nằm ở **Completeness (3.40/5)** — LLM trả lời đúng nhưng thiếu chi tiết, và **false abstain** ở q07 (alias) và q10 (VIP query).
> - **Khuyến nghị**: Cài `pip install rank-bm25`, chạy lại eval.py để có kết quả hybrid thực tế.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** Chưa thực hiện  
**Config:**
```
# Gợi ý nếu có thêm thời gian:
# 1. Cải thiện prompt để giảm false abstain (q07, q10)
# 2. Implement cross-encoder rerank thực sự
# 3. Thử query expansion cho alias queries
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.40 | N/A (crash) | N/A | Baseline |
| Answer Relevance | 5.00 | N/A (crash) | N/A | Baseline |
| Context Recall | 5.00 | N/A (crash) | N/A | Baseline |
| Completeness | 3.40 | N/A (crash) | N/A | Baseline |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > **False abstain** — LLM trả "Không đủ dữ liệu" khi thực ra context ĐÃ được retrieve đúng (context recall = 5/5). Hai trường hợp điển hình: q07 (alias query "Approval Matrix" → LLM không nhận ra đây là tên cũ của Access Control SOP dù chunk nói rõ) và q10 (query hỏi quy trình VIP → LLM abstain thay vì trả lời "không có quy trình đặc biệt, áp dụng quy trình tiêu chuẩn"). Nguyên nhân gốc: prompt grounding quá nghiêm khắc ("Do NOT guess, infer") khiến LLM sợ suy luận dù thông tin logic có trong context.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > **Prompt engineering** (cụ thể: mức độ "nghiêm khắc" của grounding instruction). Retrieval đã hoạt động rất tốt (Context Recall trung bình 5.00/5) nhưng generation vẫn có vấn đề (Completeness chỉ 3.40/5). Điểm bottleneck không nằm ở retrieval mà ở cách LLM diễn giải context. Ngoài ra, **dependency management** cũng critical — thiếu 1 package `rank-bm25` đã làm crash toàn bộ variant.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > 1. **Cài `rank-bm25` và chạy lại hybrid** để có kết quả A/B thực tế.
   > 2. **Điều chỉnh prompt**: Thay "Do NOT guess, infer" thành "You may make reasonable inferences from the context, but state when doing so." Kỳ vọng: giảm false abstain ở q07 và q10.
   > 3. **Implement rerank thực sự** bằng cross-encoder `ms-marco-MiniLM-L-6-v2` thay vì hàm pass-through hiện tại.
