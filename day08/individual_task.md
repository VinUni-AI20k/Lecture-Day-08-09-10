# Individual Task: Nguyễn Quốc Khánh (Retrieval Owner)

Tài liệu này tổng hợp checklist công việc, mục tiêu và output cụ thể cho Nguyễn Quốc Khánh trong dự án **RAG Prototype cho CS + IT Helpdesk (Day 08)**.

---

## 🎯 Mục tiêu chính
Tối ưu hóa khả năng truy xuất thông tin (Retrieval Quality) thông qua chiến lược chunking thông minh và tìm kiếm Hybrid (Dense + Sparse).

---

## 🚀 Lộ trình Sprint (4 x 60 phút)

### 🔧 SPRINT 1 — Xây dựng Index (60 phút)
**Mục tiêu:** Hoàn thiện pipeline tiền xử lý và cắt nhỏ dữ liệu (chunking).
- [x] **Implement `parse_metadata(content)`**: Sử dụng Regex để trích xuất `Source`, `Department`, `Effective Date` từ header tài liệu.
- [x] **Implement `split_into_chunks(content)`**: Thực hiện **Semantic Splitting** dựa trên các tiêu đề phần (`=== Title ===`). Tuyệt đối không dùng character split cứng.
- [x] **Xử lý Alias đặc biệt**: Gắn thêm alias (ví dụ: "approval matrix") vào metadata/content của file `access_control_sop.txt` để hỗ trợ BM25 search.
- [x] **Viết hàm `list_chunks()`**: Utility để in preview 10 chunks đầu tiên, kiểm tra xem metadata đã đúng format chưa.

### 🔍 SPRINT 2 — Baseline Retrieval (60 phút)
**Mục tiêu:** Xây dựng hệ thống tìm kiếm vector cơ bản (Dense Search).
- [x] **Implement `dense_search(query)`**: Thực hiện tìm kiếm tương đồng trên ChromaDB (top-k=5).
- [x] **Implement `format_citations()`**: Định dạng nguồn tham khảo `[1]`, `[2]` để hiển thị ở cuối câu trả lời.
- [x] **Smoke Test**: Kiểm tra thủ công với 3 câu hỏi (ví dụ: q01, q02) để đảm bảo có trả về source/metadata.

### ⚡ SPRINT 3 — Tuning & Hybrid Search (60 phút)
**Mục tiêu:** Cải thiện kết quả tìm kiếm cho các mã lỗi và thuật ngữ kỹ thuật.
- [ ] **Implement `hybrid_search()`**: Kết hợp kết quả từ Dense (Chroma) và Sparse (BM25S) bằng thuật toán **RRF (Reciprocal Rank Fusion)**.
- [ ] **Justify Hybrid**: Chuẩn bị lý do chọn Hybrid (ví dụ: Dense thường miss mã định danh chính xác như `ERR-403-AUTH`, BM25 sẽ "cứu" phần này).
- [ ] **A/B Test**: Phối hợp với Khải để ghi lại kết quả so sánh giữa Dense vs Hybrid vào `tuning-log.md`.

### 📊 SPRINT 4 — Báo cáo & Final Review (60 phút)
**Mục tiêu:** Tổng hợp kết quả và phân tích cá nhân.
- [ ] **Viết Báo cáo cá nhân (`reports/individual/khanh.md`)**:
    - Độ dài: 500 - 800 từ.
    - Cấu trúc: Theo đúng template có sẵn (5 phần).
- [ ] **Phân tích scorecard**: Chọn 1 câu hỏi thú vị (ví dụ câu liên quan đến Alias/BM25) để phân tích sâu vì sao Hybrid hiệu quả hơn.
- [ ] **Fix Bugs**: Chỉnh sửa mã nguồn theo review của Tech Lead trước khi nộp bài.

---

## 📦 Output (Sản phẩm bàn giao)
1. **Source Code**: Các hàm xử lý trong `index.py` và phần Retrieval trong `rag_answer.py`.
2. **File Báo cáo**: `day08/lab/reports/individual/khanh.md`.
3. **Commit History**: Phải có các commit với format `[Khanh][S{n}]` (Ví dụ: `[Khanh][S1] implement semantic chunking`).

---

## 💡 Lưu ý quan trọng
- **Quy tắc Abstain**: Nếu không tìm thấy thông tin trong context, hệ thống phải trả lời theo mẫu: *"Không tìm thấy thông tin về [chủ đề] trong tài liệu."* (Tuyệt đối không bịa thông tin).
- **Metadata Bắt buộc**: Mỗi chunk tạo ra phải có đủ các trường: `source`, `section`, `effective_date`.
- **Phối hợp**: Làm việc chặt chẽ với **Khải (Retrieval Owner Pair)** để build index BM25 và **Nhật (Tech Lead)** để chốt schema metadata.
- **Deadline**: Hoàn thành và push code trước **18:00**.

---
*Generated based on ROLE_INDIVIDUALS.md and lab/README.md*
