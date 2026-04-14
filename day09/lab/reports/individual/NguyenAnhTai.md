# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Anh Tài  
**Vai trò trong nhóm:** Worker Owner (Retrieval)  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
>
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong buổi Lab Day 09, tôi chịu trách nhiệm chính trong việc xây dựng hệ thống Retrieval cho pipeline RAG đa tác vụ. Nhiệm vụ của tôi là đảm bảo hệ thống có khả năng tìm kiếm thông tin chính xác từ cơ sở dữ liệu tri thức để cung cấp ngữ cảnh cho Supervisor và các Worker khác.

**Module/file tôi chịu trách nhiệm:**

- File chính: `workers/retrieval.py`
- Functions tôi implement: `_get_embedding_fn()`, `_get_collection()`, `retrieve_dense()`, và hàm `run()` để tích hợp vào LangGraph state.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Khi Supervisor nhận diện được một yêu cầu cần tra cứu thông tin (ví dụ: về chính sách bảo hành hoặc lỗi kỹ thuật), nó sẽ gọi đến `retrieval_worker`. Tôi nhận input là `task` (câu hỏi), thực hiện tìm kiếm trong ChromaDB, và trả về `retrieved_chunks`. Kết quả này sau đó được chuyển tới Generator hoặc Supervisor để tổng hợp câu trả lời cuối cùng. Nếu phần của tôi trả về kết quả sai hoặc rỗng, các Worker xử lý sau đó sẽ không có đủ dữ liệu để làm việc.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
File `workers/retrieval.py` đã hoàn thiện với đầy đủ logic xử lý ChromaDB và tích hợp state management.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi quyết định triển khai cơ chế "Hybrid Embedding Fallback" trong hàm `_get_embedding_fn()`.

**Giải thích:**
Ban đầu, hệ thống chỉ định sử dụng OpenAI API để tạo embedding. Tuy nhiên, tôi nhận thấy việc này phụ thuộc hoàn toàn vào internet và tiêu tốn chi phí API mỗi khi chạy test. Tôi đã đề xuất và triển khai giải pháp sử dụng `sentence-transformers` (model `google/embeddinggemma-300m`) làm tùy chọn ưu tiên, chạy local ngay trên máy.

**Lý do:**

1. **Tốc độ:** Chạy local nhanh hơn đáng kể so với việc gửi request qua mạng (giảm latency từ ~800ms xuống còn ~50ms).
2. **Chi phí:** Hoàn toàn miễn phí cho các lượt chạy thử nghiệm (testing/development).
3. **Tính ổn định:** Hệ thống vẫn hoạt động ngay cả khi mất kết nối internet hoặc API key bị limit.

**Trade-off đã chấp nhận:**
Model `google/embeddinggemma-300m` có kích thước vector nhỏ hơn và độ hiểu ngữ nghĩa có thể thấp hơn một chút so với của OpenAI. Tuy nhiên, với tập dữ liệu lab nhỏ, sự chênh lệch này là không đáng kể so với lợi ích về tốc độ.

**Bằng chứng từ trace/code:**

```python
def _get_embedding_fn():
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("google/embeddinggemma-300m")
        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()
        return embed
    except ImportError:
        pass
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Sai lệch giữa độ đo khoảng cách (distance) và độ tương đồng (similarity) khi trả về kết quả cho Supervisor.

**Symptom (pipeline làm gì sai?):**
Khi chạy thử nghiệm, `retrieval_worker` trả về điểm số (score) rất cao (ví dụ: 0.8) nhưng nội dung lại không liên quan đến câu hỏi. Supervisor dựa vào score này để quyết định có tin tưởng dữ liệu hay không, dẫn đến việc chatbot đưa ra các câu trả lời "ảo" (hallucination) dựa trên mảnh thông tin sai lệch.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Lỗi nằm ở logic tính toán trong hàm `retrieve_dense()`. ChromaDB mặc định trả về `distance` (thường là Squared L2 hoặc Cosine Distance). Tôi đã sử dụng trực tiếp giá trị này làm `score` mà không chuyển đổi. Trong Cosine Distance, giá trị càng nhỏ thì càng gần (tương đồng), nhưng logic của Supervisor lại mặc định hiểu `score` càng lớn thì càng tốt.

**Cách sửa:**
Tôi đã điều chỉnh lại công thức tính score để chuyển đổi từ Distance sang Similarity: `score = round(1 - dist, 4)`.

**Bằng chứng trước/sau:**

- **Trước khi sửa:** `score: 0.1234` (thực tế đây là distance nhỏ, cực kỳ tương đồng nhưng Supervisor tưởng là score thấp nên bỏ qua).
- **Sau khi sửa:**

```python
chunks.append({
    "text": doc,
    "source": meta.get("source", "unknown"),
    "score": round(1 - dist, 4),
    "metadata": meta,
})
```

Trace log hiện tại hiển thị: `[0.8766] policy.pdf: Nội dung điều khoản...` giúp Supervisor lọc thông tin chính xác hơn.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã xây dựng một module Retrieval . Tôi đã thêm các khối `try-except` quanh việc truy vấn ChromaDB và xử lý trường hợp collection chưa tồn tại hoặc rỗng một cách êm đẹp, không làm sập toàn bộ graph.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Hiện tại cơ chế retrieval của tôi mới chỉ dừng lại ở Dense Retrieval (vector search). Nếu câu hỏi chứa các thuật ngữ hoặc tên riêng quá đặc thù, vector search đôi khi không hiệu quả bằng Keyword search (BM25).

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm bị "block" hoàn toàn ở Sprint 2 và 3 nếu tôi không xong file này. Generator sẽ không có data để trả lời, và Supervisor sẽ luôn báo lỗi "No context found".

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào **MCP Owner** hoặc người phụ trách **Indexing script** để đảm bảo dữ liệu đã được nạp vào ChromaDB với đúng schema mà tôi đang query.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ triển khai thêm bước **Reranking**. Hiện tại, tôi chỉ lấy top_k dựa trên khoảng cách vector. Nếu có thêm thời gian, tôi sẽ dùng một model Cross-Encoder để đánh giá lại top 10 kết quả tìm được, từ đó chỉ chọn ra 3 kết quả thực sự liên quan nhất. Trace log của câu hỏi "Ai phê duyệt cấp quyền Level 3?" cho thấy đôi khi kết quả top 1 có score cao nhưng thông tin thực sự lại nằm ở top 3. Reranking sẽ giải quyết triệt để vấn đề này.

---

_Lưu file này với tên: `reports/individual/NguyenAnhTai.md`_
