# Báo cáo cá nhân - Nam

**Họ và tên:** Nam  
**Vai trò:** Ingestion Owner  
**Ngày nộp:** 2026-04-15

## 1. Tôi phụ trách phần nào?

Tôi phụ trách phần ingest và manifest trong `etl_pipeline.py`: đọc raw CSV, ghi log thống kê đầu vào, tạo manifest chuẩn và đảm bảo pipeline có thể chạy theo run_id cụ thể cho Sprint 1/3/4. Tôi cũng bổ sung luồng đọc contract (`--contract`) để truyền cấu hình versioning xuống cleaning layer, từ đó giữ đồng nhất giữa code và `contracts/data_contract.yaml`.

Tôi phối hợp trực tiếp với Cao để map các cột raw cần thiết cho cleaning và expectation. Với Ly, tôi thống nhất các trường observability bắt buộc trong manifest (`raw_records`, `cleaned_records`, `quarantine_records`, `latest_raw_exported_at`, `latest_cleaned_exported_at`) để runbook và quality report bám số liệu đúng.

Bằng chứng:
- `artifacts/manifests/manifest_sprint4-final.json`
- `artifacts/manifests/manifest_sprint3-inject.json`
- `artifacts/logs/run_sprint4-final.log`

## 2. Một quyết định kỹ thuật

Tôi chọn chiến lược ghi manifest đủ giàu thông tin thay vì chỉ log text: thêm `raw_path`, `contract_path`, `latest_raw_exported_at`, `latest_cleaned_exported_at`, flags `no_refund_fix`, `skipped_validate`, và config áp dụng (`refund_window_days`, `hr_leave_min_effective_date`).  
Lợi ích:
- Cho phép tái lập chính xác run khi debug.
- Đủ dữ liệu để monitor freshness ở 2 boundary.
- Hạn chế tranh cãi "run nào tạo artifact nào" khi nộp bài.

Ngoài ra tôi thêm `--contract` để code không khóa cứng vào một contract duy nhất, giúp nhóm dễ thử nghiệm các biến thể mà không sửa code.

## 3. Một lỗi/anomaly đã xử lý

Anomaly tôi xử lý là lỗi path khi truyền `--raw` bằng relative path ngoài thư mục gốc của script, khiến `Path.relative_to(ROOT)` ném `ValueError` và không ghi được manifest inject.  
Fix:
- Chuẩn hóa `raw_path`/`contract_path` bằng `.resolve()`.
- Dùng helper `_safe_relpath()` để fallback về absolute path nếu không relative được.

Kết quả sau fix:
- `manifest_sprint3-inject.json` được ghi đầy đủ.
- Luồng inject không còn crash giữa chừng.
- Toàn bộ artifact (`cleaned`, `quarantine`, `manifest`) được tạo ổn định cho run inject.

## 4. Bằng chứng trước/sau

Trước fix path:
- Inject run có thể dừng sau bước embed, thiếu manifest hoặc thiếu trường path chuẩn.

Sau fix path:
- `manifest_sprint3-inject.json` có `raw_path=data\\raw\\policy_export_inject.csv`.
- `manifest_sprint4-final.json` có đầy đủ trường contract/config để audit.
- Chỉ số run sạch: `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`.

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ thêm checksum cho raw input vào manifest (ví dụ SHA256 theo file) để chứng minh rõ "artifact nào được tạo từ đúng snapshot dữ liệu nào". Điều này hữu ích khi nhiều run dùng cùng run_id hoặc khi có replay.
