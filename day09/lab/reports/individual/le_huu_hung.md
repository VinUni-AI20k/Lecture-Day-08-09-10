# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lê Hữu Hưng  
**Vai trò trong nhóm:** Worker Owner — Retrieval Worker  
**Ngày nộp:** 14/04/2026  

---

## 1. Tôi phụ trách phần nào?

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/retrieval.py`
- Functions tôi implement: `_get_embedding_fn()`, `_chunk_text()`, `_get_collection()`, `build_index()`, `retrieve_dense()`, `run(state)`

Tôi đảm nhận toàn bộ pipeline dense retrieval từ bước đọc tài liệu thô cho đến khi trả về danh sách chunks có score về `AgentState`. Cụ thể: đọc 5 file `.txt` từ `data/docs/`, chia chunks bằng sliding window, embed bằng Sentence Transformers, nạp vào ChromaDB persistent collection `day09_docs`, và xử lý query thời gian chạy trong `retrieve_dense()`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Output của tôi (`retrieved_chunks`, `retrieved_sources`) được `synthesis_worker` (Đỗ Minh Phúc) đọc trực tiếp để build context string và tính citation. Contract được thống nhất từ Sprint 1 qua `contracts/worker_contracts.yaml` — tôi ghi vào `state["retrieved_chunks"]` đúng format `{"text", "source", "score", "metadata"}`, Phúc không cần biết ChromaDB hay Sentence Transformers hoạt động thế nào bên trong.

**Bằng chứng:** `workers/retrieval.py` — toàn bộ functions đều do tôi viết trong Sprint 2. Standalone test chạy được với `python workers/retrieval.py`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định: Dùng word-based sliding window chunking (300 words, 50 overlap) thay vì paragraph-aware chunking.**

Day 08 của nhóm dùng paragraph-aware chunking (400 tokens, 80 overlap) — chia theo dấu xuống dòng đôi `\n\n` để giữ nguyên cấu trúc đoạn văn. Tôi cân nhắc 2 lựa chọn:

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Paragraph-aware (Day 08) | Giữ nguyên cấu trúc ngữ nghĩa, chunk ít bị cắt giữa câu | Kích thước chunk không đều, doc format phải đủ chuẩn |
| **Word-based sliding window (chọn)** | Kích thước đồng đều, dễ kiểm soát, không phụ thuộc format doc | Có thể cắt giữa câu ở ranh giới chunk |

Tôi chọn word-based vì tài liệu IT Helpdesk (`sla_p1_2026.txt`, `access_control_sop.txt`) có cấu trúc section rõ ràng với header `===`. Sliding window đảm bảo overlap 50 words — nếu câu trả lời nằm ở ranh giới 2 chunk, chunk sau vẫn lấy lại 50 words cuối của chunk trước, giảm thiểu mất context.

**Trade-off đã chấp nhận:** Một số chunk đầu/cuối section có thể lẫn header của section khác. Thực tế không ảnh hưởng retrieval vì ChromaDB cosine similarity vẫn score đúng theo semantic.

**Bằng chứng từ code:**

```python
# workers/retrieval.py — _chunk_text()
def _chunk_text(text: str, source: str, chunk_size: int = 300, overlap: int = 50) -> list:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    words = " ".join(lines).split()  # flatten toàn bộ text thành word list

    i = 0
    while i < len(words):
        chunk_words = words[i : i + chunk_size]
        chunk_text = " ".join(chunk_words).strip()
        if len(chunk_text) > 30:   # bỏ qua chunk quá ngắn (header rỗng)
            chunks.append({...})
        i += chunk_size - overlap  # stride = 250 words, overlap = 50 words
```

Kết quả: 5 docs → tổng cộng đủ chunks để trace `run_20260414_174757.json` retrieve được `access_control_sop.txt__chunk1` với score 0.6739 — đúng chunk chứa quy trình escalation Level 3.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi: ChromaDB crash khi `top_k > collection.count()`**

**Symptom:**  
Khi chạy `retrieve_dense()` với `top_k=3` trên collection mới build chỉ có 2 chunks (test với doc nhỏ), ChromaDB raise exception:
```
chromadb.errors.InvalidArgumentError: 
  n_results (3) cannot be greater than the number of elements in the index (2)
```
Pipeline dừng hẳn, `retrieved_chunks` không có giá trị nào, synthesis không có gì để tổng hợp.

**Root cause:**  
`collection.query(n_results=top_k, ...)` của ChromaDB không tự giới hạn — nếu `top_k` lớn hơn số document thực tế trong collection, nó raise error thay vì trả về tất cả document có.

**Cách sửa:**  
Thêm một dòng `min()` trước khi gọi query:

```python
# Trước khi sửa:
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=top_k,   # crash nếu top_k > collection.count()
    ...
)

# Sau khi sửa:
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=min(top_k, collection.count()),  # safe
    ...
)
```

**Bằng chứng trước/sau:**  
- Trước: `python workers/retrieval.py` với collection 2 chunks → exception, exit code 1.
- Sau: trả về 2 chunks bình thường, log `"retrieved 2 chunks"`. Collection production hiện tại có đủ chunks nên không gặp lại, nhưng fix này quan trọng cho môi trường test/staging khi chạy với tập doc nhỏ.

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**  
Thiết kế embedding fallback chain (`_get_embedding_fn()`) là quyết định tôi hài lòng nhất: ưu tiên Sentence Transformers offline, fallback sang OpenAI nếu có key, fallback cuối cùng là random embedding có warning. Nhờ đó pipeline chạy được trong mọi môi trường — không cần API key để test, không cần mạng để demo. Trong 36 trace thực tế, không có run nào fail ở bước embedding.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**  
Tôi không implement reranking. Day 08 dùng Dense+Rerank pipeline với cross-encoder để cải thiện precision, Day 09 của tôi chỉ có dense retrieval đơn thuần. Một số câu hỏi retrieve được chunk có score chênh nhau ít (0.67 vs 0.59), reranker sẽ giúp chọn đúng chunk hơn.

**Nhóm phụ thuộc vào tôi ở đâu?**  
`synthesis_worker` và `policy_tool_worker` đều cần `retrieved_chunks` từ tôi. Nếu `retrieval.py` chưa xong hoặc ChromaDB chưa được build index, cả pipeline sẽ trả về câu trả lời rỗng. Vì vậy tôi cũng viết `build_index()` với flag `--build`/`--force` để team dễ khởi tạo môi trường.

**Phần tôi phụ thuộc vào thành viên khác:**  
Tôi cần `AgentState` TypedDict từ Nam (Sprint 1) để biết field nào cần đọc/ghi. Cũng cần `contracts/worker_contracts.yaml` để đảm bảo output format khớp với synthesis.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thêm **reranking** vào `retrieve_dense()`. Trace `run_20260414_174518.json` (Flash Sale hoàn tiền) cho thấy chunk từ `it_helpdesk_faq.txt` được retrieval trả về với score 0.5867 dù không liên quan đến câu hỏi — nằm cạnh chunk `policy_refund_v4.txt` score 0.6402. Một cross-encoder reranker nhỏ (VD: `cross-encoder/ms-marco-MiniLM-L-6-v2`) sẽ loại chunk nhiễu này ra, giúp synthesis chỉ nhận context thực sự liên quan và tăng confidence.

---

*File: `reports/individual/le_huu_hung.md`*
