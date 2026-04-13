# Group Report — RAG Prototype
**Nhóm:** Nhóm 6 người | **Ngày:** 2026-04-13

## 1. Tổng quan kiến trúc
Hệ thống là một trợ lý ảo RAG nội bộ dành cho khối CS (Customer Service) và IT Helpdesk. Trợ lý này giúp nhân viên truy xuất nhanh và trả lời chính xác các câu hỏi về chính sách, SLA, và quy trình cấp quyền dựa trên chứng cứ cụ thể (grounded evidence).

Hệ thống hoạt động theo pipeline: Đọc dữ liệu văn bản thô -> Trích xuất Metadata -> Cắt theo kỹ thuật Semantic Chunking -> Xây dựng index đồng thời lên ChromaDB (Dense) và BM25s (Sparse) -> Xử lý truy vấn bằng các chiến lược Hybrid Search -> Rerank qua CrossEncoder -> Kiểm tra threshold -> Gọi LLM tạo phản hồi đính kèm nguồn trích dẫn.

## 2. Quyết định kỹ thuật quan trọng
- **Semantic chunking vs character split (Khánh/Khải)**: Chọn Semantic split theo các heading để tránh phá vỡ ngữ cảnh riêng biệt của một điều khoản pháp lý hoặc tài liệu hướng dẫn.
- **Hybrid Search vs Dense only (Khải)**: Chọn **Hybrid Search**. Kết quả A/B Test cho thấy Hybrid giúp tăng Recall đáng kể cho các câu hỏi chứa keyword kỹ thuật mà Dense model bị bỏ lỡ.
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
- **Câu gq07 (Abstain Case)**: Hệ thống đã thực hiện tốt việc từ chối trả lời (Abstain) khi gặp câu hỏi về mức phạt (không có trong tài liệu), tránh được rủi ro bịa đặt thông tin (Hallucination).
- **Câu gq01 (Technical Term)**: Nhờ có BM25s trong Hybrid Search, hệ thống truy xuất chính xác các điều khoản về SLA P1 dựa trên từ khóa "P1" mà Embedding model đôi khi coi là nhiễu.

## 5. Kết luận và hướng cải thiện
Hệ thống RAG Prototype đã đạt được mục tiêu đề ra: trả lời có căn cứ xác thực và hạn chế tối đa việc bịa đặt thông tin nhờ thiết lập Threshold và Hybrid Search.

**Hướng cải thiện:**
1. Mở rộng tập dữ liệu sang các định dạng PDF phức tạp hơn.
2. Tối ưu hóa Reranker để xử lý context dài tốt hơn.
3. Tích hợp tính năng Feedback vòng lặp để thu thập đánh giá từ chính nhân viên CS/IT.
