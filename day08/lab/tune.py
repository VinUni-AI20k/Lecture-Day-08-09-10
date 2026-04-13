# Baseline


# Tune the RAG pipeline by experimenting with different chunking strategies, retriever strategies, and technical improvements.
EMBEDDING_MODEL = "google/embeddinggemma-300m"
CHUNK_SIZE = [350, 500, 700]  # tokens (rule of thumbs: max input tokens of your LLM / 4)
CHUNK_OVERLAP = [50, 80, 120] # tokens (rule of thumbs: max input tokens of your LLM / 20)
...
# I. Chunking strategy
## _chunk_by_size() vs _chunk_by_size_with_paragraph() vs _chunk_by_size_with_paragraph_and_separator()

# II. Retriever Strategy
## retrive_dense() vs retrieve_sparse() vs retrieve_hybrid()

# III. Technical improvements (chỉ bật sau khi retrieval ổn)
## rerank()
## query transform