# RAG Workflow: Retrieve → Rerank → Generate

## 1. Retrieve
- Chọn phương pháp retrieval theo `retrieval_mode`:
  - `dense` → gọi `retrieve_dense(query, top_k=top_k_search)`
  - `sparse` → gọi `retrieve_sparse(query, top_k=top_k_search)`
  - `hybrid` → gọi `retrieve_hybrid(query, top_k=top_k_search)`
- `retrieve_dense()`:
  - lấy embedding của query
  - query ChromaDB
  - trả về top chunks kèm metadata, text, score
- `retrieve_sparse()`:
  - dùng BM25 trên corpus chunk
  - trả về top chunks theo điểm keyword matching
- `retrieve_hybrid()`:
  - chạy đồng thời dense và sparse
  - gộp kết quả bằng Reciprocal Rank Fusion (RRF)
  - tính score tổng hợp từ dense_rank và sparse_rank
  - trả về top kết quả cuối cùng

## 2. Rerank (tùy chọn)
- Nếu `use_rerank=True`, gọi `rerank(query, candidates, top_k=top_k_select)`
- Mục đích:
  - đánh giá lại độ liên quan của từng chunk với query
  - giữ top chunk tốt nhất vào prompt

## 3. Generate
- Chọn ra `top_k_select` chunks cuối cùng:
  - nếu không rerank thì dùng `candidates[:top_k_select]`
  - nếu rerank thì dùng kết quả rerank
- `build_context_block(chunks)`:
  - tạo block context gồm mỗi chunk có `[i] source | section | score`
  - nối text vào block
- `build_grounded_prompt(query, context_block)`:
  - xây dựng prompt yêu cầu:
    - chỉ trả lời từ context
    - abstain nếu thiếu dữ liệu
    - trích dẫn source
    - giữ ngắn, rõ ràng
- `call_llm(prompt)`:
  - gọi OpenAI chat completion với `temperature=0`
  - trả về câu trả lời grounded từ LLM

## 4. Kết quả trả về
- Hàm `rag_answer(...)` trả về dict gồm:
  - `query`
  - `answer`
  - `sources`
  - `chunks_used`
  - `config`

## Ghi chú
- `retrieve` là bước tìm candidate rộng
- `rerank` là bước tinh lọc candidate nếu bật
- `generate` là bước dùng prompt + context để sinh câu trả lời cuối cùng
