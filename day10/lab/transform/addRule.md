# TÀI LIỆU THEO DÕI CÁC CLEANING RULES MỚI (DATA QUALITY GATEWAY)

**Người thực hiện:** Nguyễn Quốc Khánh (Cleaning Owner - Sprint 1 & 2)
**Mục tiêu file:** Giải thích chi tiết các rule đã thêm vào `transform/cleaning_rules.py` để các thành viên khác (đặc biệt là Khải, Nhật, Sơn) có thể keep track, viết Expectation và cập nhật vào Report Nhóm.

---

## TỔNG QUAN
Tôi đã phân tích file `data/raw/policy_export_dirty.csv` và kiến trúc Ingestion thực tế, qua đó bổ sung **6 Rule mới (gồm 3 rule theo yêu cầu Lab + 3 rule nâng cao)** tiếp nối sau 6 rule Baseline có sẵn. Dưới đây là chi tiết để team nắm thông tin:

---

## CHI TIẾT CÁC RULE ĐÃ THÊM

### 1. Rule 7: Xác thực định dạng ngày giờ `exported_at` (ISO-8601)
- **Làm gì:** Kiểm tra xem `exported_at` có bị rỗng hoặc sai định dạng time chuẩn (vd: `YYYY-MM-DDTHH:MM:SS`) hay không.
- **Tại sao thêm (Why):** Nếu trường này lỗi hoặc rỗng, khâu Monitoring ở cuối pipeline (do **Thành** phụ trách) sẽ bị sập khi đo lường độ trễ (Freshness Expectation).
- **Hành động:** Cách ly (Quarantine) với reason `missing_or_invalid_exported_at`.

### 2. Rule 8: Bộ lọc rác vô nghĩa (Low-Information Filter)
- **Làm gì:** Chặn các `chunk_text` quá ngắn (dưới 20 ký tự) hoặc chuỗi hoàn toàn không có chữ cái (toàn dấu cách, số ký hiệu).
- **Tại sao thêm (Why):** Nếu đưa các đoạn text vô nghĩa này (vd: `"   "`, `"123"`, `"FAQ"`) vào ChromaDB sẽ làm lãng phí token Embedding, tốn dung lượng DB và làm nhiễu ngữ cảnh (context) khi LLM sinh câu trả lời RAG.
- **Hành động:** Cách ly (Quarantine) với reason `chunk_text_too_short_or_trivial`.

### 3. Rule 9: Phát hiện lỗi Encoding & ký tự lạ (Corrupted Characters)
- **Làm gì:** Quét và bắt các ký tự lỗi Parser như BOM (`\ufeff`), Null Byte (`\x00`) bị kẹt ẩn trong text.
- **Tại sao thêm (Why):** Trong thực tế, dữ liệu dump từ DB/CMS cũ thường vướng tag ẩn. Nếu để LLM đọc phải các ký tự này, nó có thể sinh ra output lỗi phông chữ hoặc bị ảo giác (hallucination).
- **Hành động:** Cách ly (Quarantine) với reason `corrupted_text_encoding`.

### 4. Rule 10 (Nâng cao): Khắc phục lỗi Mapping - Thêm `access_control_sop`
- **Làm gì:** Bổ sung `"access_control_sop"` vào dict `ALLOWED_DOC_IDS`.
- **Tại sao thêm (Why):** Trong folder `data/docs` thực tế có 5 file chính sách chuẩn (bao gồm file SOP Truy cập hệ thống này). Nhưng cấu hình code cũ chỉ cho phép 4 file. Việc mở rộng dict này đảm bảo các policy quan trọng không bị Drop oan uổng bởi Rule 1. Mọi người lưu ý để đồng bộ hợp đồng dữ liệu!
- **Hành động:** Cập nhật biến tĩnh.

### 5. Rule 11 (Nâng cao): Chặn trần kích thước Token (Max Length Threshold)
- **Làm gì:** Kiểm tra giới hạn số lượng ký tự tối đa của một chunk. Nếu chunk dính liền nhau dài hơn 8000 ký tự sẽ bị chặn.
- **Tại sao thêm (Why):** Bảo vệ Server VectorDB và LLM. Một đoạn text siêu dài sẽ vượt quá "Context Window" của mô hình Embedding, gây ra lỗi Crash 500 nổ toàn bộ Pipeline khi nhúng.
- **Hành động:** Cách ly (Quarantine) với reason `chunk_text_too_long`.

### 6. Rule 12 (Nâng cao): Chuẩn hoá (Transform) - Gọt rửa thẻ HTML
- **Làm gì:** Dùng RegEx (`<[^>]+>`) quét qua nội dung và xóa sạch mọi thẻ HTML/XML.
- **Tại sao thêm (Why):** Các nguồn web parser thường để sót lại các tag như `<br>`, `<div>`. Rule này đứng ra "cạo sạch" rác hiển thị, giữ lại Text thuần túy thay vì vứt bỏ cả dòng data.
- **Hành động:** Transform/Chuẩn hoá (Biến đổi `fixed_text` trở nên sạch sẽ hơn, không đưa vào Quarantine).

---

## 📌 HƯỚNG DẪN PHỐI HỢP CHO TEAM

*   👉 **Gửi Khải (Quality Owner):** Khải có thể dựa vào các `reason` ở Rule 7, 8 hoặc 11 để viết code **Expectation**. (Ví dụ: Viết expectation bắt buộc `exported_at` không được Null).
*   👉 **Gửi Sơn (Docs Owner):** Đem 6 rule này (ít nhất là Rule 7, 8, 9) vào mục **Metric Impact** trong `group_report.md` nhé (Anh Khánh sẽ đo đếm số lượng bản ghi bị loại để Sơn điền bảng). Đồng thời Sơn nhớ update `data_contract.md` bổ sung nguồn dữ liệu thứ 5 là `access_control_sop`.
*   👉 **Gửi Nhật (Tech Lead):** Nhờ Nhật merge nhánh chứa file `cleaning_rules.py` mới này của Khánh và chạy thử Pipeline để chốt `run_id` nha!