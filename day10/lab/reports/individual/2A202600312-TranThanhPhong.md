# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trần Thanh Phong  
**Vai trò:** Ingestion / Raw Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài:** ~500 từ

---

## 1. Tôi phụ trách phần nào?

Trong Day10 tôi phụ trách phần ingest raw và chuẩn hóa đầu vào trước khi chuyển sang cleaning. File tôi làm việc chính là `transform/cleaning_rules.py` (hàm `load_raw_csv`) và `etl_pipeline.py` ở các bước đọc dữ liệu, đếm số lượng record, ghi log run và xuất artifact theo `run_id`.

Nhiệm vụ của tôi là bảo đảm nhóm luôn có đường chạy ổn định từ `data/raw/policy_export_dirty.csv` ra các chỉ số nền (`raw_records`, `cleaned_records`, `quarantine_records`) để các bạn phụ trách clean/quality/embed có dữ liệu đo trước-sau. Tôi cũng hỗ trợ chuẩn hóa quy ước đặt tên file artifact (`cleaned_<run_id>.csv`, `quarantine_<run_id>.csv`, `manifest_<run_id>.json`) để các báo cáo không bị lệch giữa các lần chạy.

Tôi làm việc trực tiếp với Cleaning Owner để xác nhận schema cột input không bị thiếu (`doc_id`, `chunk_text`, `effective_date`, `exported_at`) và với Monitoring Owner để bảo đảm `manifest` đủ dữ liệu freshness check.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng của tôi là giữ toàn bộ metric ingest trong log theo `run_id` thay vì chỉ ghi vào cuối pipeline. Lý do là khi pipeline fail ở bước validate hoặc embed, nhóm vẫn cần biết raw input của run đó có vấn đề về volume hay không.

Việc gắn `run_id` nhất quán cho cả log và artifact giúp nhóm truy vết chính xác: nếu `raw_records` thay đổi bất thường hoặc bằng 0, có thể khoanh vùng lỗi ngay tại ingest; nếu raw ổn nhưng sau đó fail, mới chuyển sang kiểm tra rule/expectation. Cách này giảm thời gian debug vì không cần suy đoán dữ liệu đầu vào.

Theo tôi, đây là nguyên tắc observability đúng với Day10: đo từ boundary ingest trước khi phân tích model/retrieval.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly tôi gặp là có thời điểm nhóm chạy nhiều lần liên tiếp nhưng report và artifact bị lẫn run, khó chứng minh before/after. Triệu chứng là file eval và manifest không cùng `run_id`, khiến đối chiếu kết quả mất thời gian.

Cách xử lý của tôi là buộc quy trình chạy theo thứ tự rõ ràng:
1. Chạy `etl_pipeline.py run` để sinh `manifest_<run_id>.json`.
2. Chạy eval/grading dựa trên snapshot vừa publish.
3. Trích dẫn artifact cùng `run_id` trong report.

Sau khi thống nhất quy trình này, nhóm chốt được run clean cuối `2026-04-15T10-30Z` với số liệu ổn định `raw=10`, `clean=6`, `quarantine=4`, và grading JSONL pass quick check.

---

## 4. Bằng chứng trước / sau

Bằng chứng tôi dùng để xác nhận ingest ổn định:
- Run inject và run clean đều có `raw_records=10`, chứng minh dữ liệu đầu vào không đổi, thay đổi nằm ở rule/validate.
- Manifest clean cuối: `artifacts/manifests/manifest_2026-04-15T10-30Z.json` có đủ chỉ số ingest + publish.

Ví dụ trích từ run clean:
- `run_id=2026-04-15T10-30Z`
- `raw_records=10`
- `cleaned_records=6`
- `quarantine_records=4`

Nhờ các chỉ số này, nhóm có thể nói chắc chắn rằng cải thiện chất lượng đến từ cleaning/expectation chứ không phải do thay đổi nguồn raw.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi muốn thêm kiểm tra schema drift ngay khi ingest (ví dụ thiếu cột hoặc cột lạ so với contract) và log thành một expectation riêng. Cải tiến này giúp phát hiện sớm lỗi dữ liệu nguồn trước khi chạy các bước clean/validate sâu hơn.
