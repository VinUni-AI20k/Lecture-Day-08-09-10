# Architecture Document - RAG Pipeline Lab Day 08

Hệ thống RAG được thiết kế để phục vụ nhu cầu tra cứu nội bộ (IT/HR Helpdesk) với độ chính xác cao và khả năng trích dẫn nguồn minh bạch.

## 1. Indexing Pipeline
- **Preprocessing**: Sử dụng Regex để bóc tách metadata (Source, Department, Effective Date, Access) từ header của tài liệu văn bản. Tài liệu được làm sạch các dòng trống thừa.
- **Chunking Strategy**: 
    - Phương pháp: Paragraph-based chunking.
    - Logic: Cắt văn bản tại ranh giới đoạn văn (`\n\n`) để giữ tính trọn vẹn của ý nghĩa.
    - Cấu hình: Chunk size khoảng 1600 ký tự (~400 tokens), Overlap 320 ký tự để duy trì ngữ cảnh giữa các đoạn liền kề.
- **Embedding**: Sử dụng mô hình `text-embedding-3-small` của OpenAI.
- **Vector Store**: ChromaDB (Persistent) với cấu hình `hnsw:space: cosine`.

## 2. Retrieval Strategies
Hệ thống hỗ trợ 3 chế độ tìm kiếm:
- **Dense Retrieval**: Sử dụng vector similarity để tìm các đoạn văn có ý nghĩa gần gũi nhất với câu hỏi.
- **Sparse Retrieval**: Sử dụng thuật toán BM25 (thư viện `rank-bm25`) để tìm kiếm chính xác theo từ khóa/mã lỗi.
- **Hybrid Search (Strategy)**: Kết hợp Dense và Sparse để tận dụng ý nghĩa ngữ nghĩa và độ chính xác của từ khóa.
- **Reciprocal Rank Fusion - RRF (Method)**: Sử dụng thuật toán RRF để trộn và xếp hạng lại kết quả từ hai phương pháp trên.

## 3. Diversity with MMR
- **MMR (Maximal Marginal Relevance)**: Được sử dụng để lựa chọn tập hợp top-k chunks đa dạng nhất, tránh trùng lặp thông tin retrieved khi đưa vào prompt.

## 4. Generation & Grounding
- **LLM**: OpenAI `gpt-4o-mini`.
- **System Prompt**: 
    - Ép buộc mô hình chỉ sử dụng `Context` được cung cấp.
    - Cấm tuyệt đối việc tự bịa thông tin (Hallucination).
    - Quy chuẩn định dạng trích dẫn `[n]` và danh sách nguồn cuối câu trả lời.

## 5. Evaluation
- **Framework**: Tự xây dựng scorecard chấm điểm 1-5.
- **Judge**: Sử dụng mô hình **LLM-as-Judge** để tự động hóa việc chấm điểm Faithfulness, Relevance và Completeness dựa trên rubric định sẵn.
