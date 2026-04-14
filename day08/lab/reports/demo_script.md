# Kịch bản demo hệ thống Day 08 (dễ hiểu, chi tiết)

## 1) Mục tiêu buổi demo

- Cho người xem thấy hệ thống chạy được end-to-end.
- Giải thích rõ 3 điểm cốt lõi:
  1. Truy xuất đúng ngữ cảnh từ tài liệu.
  2. Câu trả lời có trích dẫn và mở được tài liệu gốc.
  3. Pipeline biết abstain khi thiếu dữ liệu.

Thời lượng gợi ý: 8-12 phút.

---

## 2) Chuẩn bị trước khi demo (2-3 phút)

### A. Mở 2 terminal

Terminal 1 (API):

```powershell
cd ".\day08\lab"
uvicorn api_server:app --reload --host 127.0.0.1 --port 8010
```

Terminal 2 (UI):

```powershell
cd ".\day08\lab\rag-ui"
npm run dev -- -p 3001
```

### B. Kiểm tra nhanh

- Vào `http://127.0.0.1:8010/api/health` phải thấy API sống.
- Mở `http://localhost:3001/chat`.
- Bật panel phải (bảng theo dõi) nếu đang ẩn.

---

## 3) Luồng demo chính (theo thứ tự)

## Bước 1 - Demo câu hỏi cơ bản, có câu trả lời đúng

**Mục đích:** chứng minh pipeline trả lời được và có trích dẫn.

1. Bấm “Câu hỏi gợi ý từ bộ test” ở đầu khung chat.
2. Chọn câu: `SLA xử lý ticket P1 là bao lâu?`
3. Gửi câu hỏi.

**Điểm cần nói khi chạy:**
- Bên phải hiển thị từng bước pipeline theo thời gian thực.
- Câu trả lời có citation `[1]`.
- Bấm vào citation trong câu trả lời để xem thẻ chi tiết đoạn tài liệu.

## Bước 2 - Demo mở tài liệu gốc từ “Tài liệu tham chiếu”

**Mục đích:** chứng minh tính truy vết.

1. Ở panel phải, phần “Tài liệu tham chiếu”, bấm vào tài liệu số `[1]`.
2. Hệ thống mở tài liệu ở tab mới qua route nội bộ.

**Điểm cần nói:**
- Đây là bằng chứng câu trả lời bám theo tài liệu thực, không trả lời kiểu “đoán”.

## Bước 3 - Demo câu hỏi thiếu dữ liệu (abstain)

**Mục đích:** chứng minh anti-hallucination.

1. Gửi câu: `Mức phạt vi phạm SLA P1 là bao nhiêu?`
2. Kỳ vọng: hệ thống trả lời theo hướng “Không đủ dữ liệu trong tài liệu để trả lời.”

**Điểm cần nói:**
- Đây là hành vi mong muốn của RAG: thiếu bằng chứng thì không bịa.
- Nhánh TuAnh đã tăng cứng logic abstain (weak context guard + prompt rule).

## Bước 4 - Demo so sánh cấu hình retrieval

**Mục đích:** cho thấy nhóm có đánh giá biến thể, không làm cảm tính.

1. Mở “Cài đặt truy xuất”.
2. Cho xem các mode: Ngữ nghĩa / Từ khóa / Kết hợp.
3. Nói rõ cấu hình đang dùng để demo.

**Điểm cần nói:**
- Nhóm có scorecard baseline và variant.
- Có log tuning để giải thích vì sao chọn cấu hình hiện tại.

---

## 4) Kịch bản nói ngắn gọn (có thể đọc trực tiếp)

“Hệ thống của nhóm gồm 5 bước: phân tích câu hỏi, truy xuất tài liệu, lọc kết quả, ghép ngữ cảnh, rồi sinh câu trả lời.  
Điểm quan trọng là mọi câu trả lời đều có thể truy ngược về tài liệu gốc qua citation và phần tài liệu tham chiếu.  
Nếu tài liệu không có thông tin, hệ thống sẽ chủ động từ chối trả lời để tránh bịa dữ liệu.  
Nhóm cũng đã chạy baseline và variant, lưu scorecard và log để chứng minh quyết định cấu hình bằng số liệu.”

---

## 5) Tình huống dự phòng khi demo lỗi

- Nếu UI báo lỗi API:
  - kiểm tra lại API port `8010`
  - kiểm tra `rag-ui/.env.local` trỏ đúng `NEXT_PUBLIC_RAG_API_URL`
- Nếu mở tài liệu không ra:
  - kiểm tra file có trong `day08/lab/data/docs`
  - refresh lại UI để lấy source mới nhất
- Nếu câu trả lời trống:
  - gửi lại 1 câu easy trong bộ gợi ý để xác nhận pipeline còn sống

---

## 6) Chốt buổi demo

3 ý chốt trong 20-30 giây:

1. Hệ thống trả lời có bằng chứng (citation + mở tài liệu thật).
2. Hệ thống không bịa khi thiếu dữ liệu (abstain rõ ràng).
3. Nhóm có quy trình đánh giá cấu hình bằng scorecard, không chọn tham số theo cảm giác.

