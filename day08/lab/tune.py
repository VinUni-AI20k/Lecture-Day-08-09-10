# Baseline (đã được build trong file eval.py)


# Tune the RAG pipeline by experimenting with different chunking strategies, retriever strategies, and technical improvements.
## Baseline
EMBEDDING_MODEL = "google/embeddinggemma-300m"
RETRIEVAL = "dense"
RERANK = False
QUERY_TRANSFORM = False
# -> Chạy xong save lại kết quả để làm baseline cho các thử nghiệm tiếp theo

## Phase 1: Tune chunking
CHUNK_SIZE = [350, 500, 700]  # tokens (rule of thumbs: max input tokens of your LLM / 4)
CHUNK_OVERLAP = [50, 80, 120] # tokens (rule of thumbs: max input tokens of your LLM / 20)
### 1. giữ overlap=80, chạy với chunk_size = 350, 500, 700
### 2. lấy top-2 từ 1., tune overlap = 50, 80, 120
# -> Đưa ra best chunking strategy dựa trên kết quả đánh giá

## Phase 2: Tune retriever
## _split_by_size() vs _split_by_paragraph_recursive() vs _split_by_recursive_two_separators()
## Giữ cố định chunking tốt nhất từ Pha 1.
## Chạy dense, sparse, hybrid(0.5/0.5), hybrid(0.6/0.4), hybrid(0.7/0.3), tổng 5 run.
## Chọn retrieval mode tốt nhất theo metric ưu tiên.

## Phase 3: Technical improvements
### Run A: bật rerank (các biến khác giữ nguyên).
### Run B: bật query transform (các biến khác giữ nguyên).
### Run C: rerank + query transform (chỉ chạy nếu A hoặc B có lợi rõ).

# II. Retriever Strategy
## retrive_dense() vs retrieve_sparse() vs retrieve_hybrid()

# III. Technical improvements (chỉ bật sau khi retrieval ổn)
## rerank()
## query transform