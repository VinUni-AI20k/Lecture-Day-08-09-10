# Tuning Log - Lab Day 08 RAG Optimization

Tài liệu ghi lại các thực nghiệm so sánh giữa các cấu hình Pipeline khác nhau.

## Thực nghiệm 1: Baseline (Dense Only) vs Variant (Hybrid + MMR)

### Cấu hình Baseline:
- **Retrieval**: Dense Search (top-10 search, top-3 select)
- **MMR**: Không
- **Prompt**: Standard Grounded Prompt

### Cấu hình Variant:
- **Retrieval**: Hybrid Search (Dense 0.6 + Sparse 0.4) sử dụng RRF.
- **MMR**: Có (lambda=0.5) để đa dạng hóa top-3 final chunks.

### Kết quả dự kiến (Dựa trên Logic):
- **SLA P1 Question**: Cả hai đều tốt, nhưng Hybrid có ưu thế hơn ở các từ khóa "P1", "SLA".
- **Refund VIP Question**: Hybrid giúp lấy được tài liệu chính xác nhanh hơn nếu truy vấn chứa keyword cụ thể.
- **ERR-403-AUTH**: Đây là "stress test". Cả hai hệ thống đều phải vượt qua bài kiểm tra "Abstain" (nói không biết) để đảm bảo không bị Hallucination.

## Phân tích chuyên sâu

### Tại sao chọn Hybrid (RRF)?
Văn bản nội bộ IT/HR thường chứa nhiều mã lỗi (ERR-XXX) và thuật ngữ chuyên ngành. Dense Search đơn thuần đôi khi bị "lạc" bởi các từ tương đồng nhưng không đúng mã. Hybrid Search khắc phục điều này bằng Keyword matching thông qua thuật toán RRF để cân bằng thứ hạng.

### Tại sao dùng MMR thay vì Rerank?
Vì lý do tối ưu tài nguyên và tốc độ, MMR được lựa chọn để thay thế Reranking. MMR giúp đảm bảo các đoạn văn bản trong prompt không bị trùng lặp ý nghĩa, từ đó cung cấp nhiều thông tin hữu ích hơn cho LLM mà không cần cài đặt các thư viện Deep Learning nặng nề.
