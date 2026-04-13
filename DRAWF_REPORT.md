# Báo cáo nháp
Dùng để các thành viên trong nhóm  trò chuyện, thống nhất và notes. Chức năng tương tự Work-logging.

## Thống nhất TechStack

* LLM: gemini-3.1-flash-lite-preview
* Embedding: SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
* Vector DB: Qdrant
* Reranker: (Không dùng)
* Framework: LangChain - LangGraph, FastAPI, Uvicorn
* Monitoring: LangSmith

## Phân vai

| Vai trò | Trách nhiệm chính | Sprint lead | Phân công |
|---------|------------------|------------|-----------|
| **Tech Lead** | Giữ nhịp sprint, nối code end-to-end | 1, 2 | Bùi Trọng Anh |
| **Retrieval Owner** | Chunking, metadata, retrieval strategy, rerank | 1, 3 | Nguyễn Bằng Anh |
| **Eval Owner** | Test questions, expected evidence, scorecard, A/B | 3, 4 | Đỗ Thị Thùy Trang |
| **Documentation Owner** | architecture.md, tuning-log, báo cáo nhóm | 4 | Bùi Trọng Anh |