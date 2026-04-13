# Group Report — RAG Prototype
**Nhóm:** Nhóm 6 người | **Ngày:** 2026-04-13

## 1. Tổng quan kiến trúc
Hệ thống là một trợ lý ảo RAG nội bộ dành cho khối CS (Customer Service) và IT Helpdesk. Trợ lý này giúp nhân viên truy xuất nhanh và trả lời chính xác các câu hỏi về chính sách, SLA, và quy trình cấp quyền dựa trên chứng cứ cụ thể (grounded evidence).

Hệ thống hoạt động theo pipeline: Đọc dữ liệu văn bản thô -> Trích xuất Metadata -> Cắt theo kỹ thuật Semantic Chunking -> Xây dựng index đồng thời lên ChromaDB (Dense) và BM25s (Sparse) -> Xử lý truy vấn bằng các chiến lược Hybrid Search -> Rerank qua CrossEncoder -> Kiểm tra threshold -> Gọi LLM tạo phản hồi đính kèm nguồn trích dẫn.

## 2. Quyết định kỹ thuật quan trọng
- **Semantic chunking vs character split (Khánh/Khải)**: Chọn Semantic split theo các heading để tránh phá vỡ ngữ cảnh riêng biệt của một điều khoản pháp lý hoặc tài liệu hướng dẫn.
- **Hybrid Search vs Dense only (Khải)**: (Đang chờ kết quả A/B Test ở Sprint 3).
- **Threshold abstain = 0.35 (Nhật)**: Đảm bảo khi tìm kiếm không ra context mong đợi (Ví dụ mã lỗi không xuất hiện), ứng dụng sẽ tự động nói "Không biết" thay vì tuỳ ý "Hallucinate" ra thông tin sai.
- **Trực quan hóa thuật toán với FastAPI/HTML UI (Sơn)**: Để chuẩn bị cho buổi bảo vệ dự án, nhóm đã dựng một giao diện Web app cho phép hiển thị **Trace Panel** (Chứa điểm RRF Score, CrossEncoder Score và Chunk cụ thể). Giúp giảng viên thấy rõ luồng xử lý bên dưới.

## 3. Kết quả RAGAS (Baseline Dense)
Trong phiên chạy Baseline bằng Dense Search, hệ thống cho các điểm số trung bình như sau:
- **Faithfulness:** 1.00/5
- **Answer Relevance:** 3.00/5
- **Context Recall:** 0.50/5
- **Completeness:** 3.00/5

*(Nhận xét sơ bộ: Hệ thống chưa lấy được context cần thiết [Recall=0.5] nên mức độ tin cậy [Faithfulness=1.00] đang rất thấp. Variant hướng đến giải quyết Context Recall)*

## 4. Phân tích câu hỏi đặc biệt
*(Sẽ được cập nhật sau 17:00 khi có `grading_questions.json`)*

## 5. Kết luận và hướng cải thiện
*(Sẽ được chốt sau khi hoàn thành chạy benchmark toàn bộ)*
