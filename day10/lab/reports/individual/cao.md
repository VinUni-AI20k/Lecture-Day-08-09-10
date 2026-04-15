# Báo cáo cá nhân - Cao

**Họ và tên:** Cao  
**Vai trò:** Cleaning / Quality Owner  
**Ngày nộp:** 2026-04-15

## 1. Tôi phụ trách phần nào?

Tôi chịu trách nhiệm chính cho lớp transform và quality: `transform/cleaning_rules.py`, `quality/expectations.py`, cùng phần định nghĩa contract liên quan đến policy versioning và keyword guard trong `contracts/data_contract.yaml`. Tôi phối hợp với Nam để bảo đảm ingest cung cấp đủ cột cho cleaning (`doc_id`, `chunk_text`, `effective_date`, `exported_at`), phối hợp với Tuấn để đảm bảo output cleaned ổn định cho idempotent upsert, và phối hợp với Ly để đưa reason/metric vào docs và runbook.

Bằng chứng chính nằm ở các run:
- `run_sprint3-inject.log`: có `expectation[refund_no_stale_14d_window] FAIL (halt)` đúng kịch bản inject.
- `run_sprint4-final.log`: toàn bộ expectation pass, chứng minh dữ liệu sạch.
- `quarantine_sprint3-inject.csv`: có các reason mới do rule tôi thêm.

## 2. Một quyết định kỹ thuật

Quyết định quan trọng nhất của tôi là chuyển các ngưỡng versioning từ hard-code sang contract/env. Cụ thể:
- `hr_leave_min_effective_date` lấy từ `contracts/data_contract.yaml` (cho phép override env).
- `refund_window_days` cũng lấy từ contract/env thay vì cố định trong code.

Lý do: nếu hard-code trong code, mỗi lần policy đổi version cần sửa logic trực tiếp và dễ gây lệch giữa code và tài liệu. Khi đưa vào contract, kiểm soát thay đổi rõ hơn và dễ audit. Đây là điều kiện Distinction của lab (rule versioning không hard-code). Trên inject run, rule `effective_date_after_exported_at` và `stale_hr_policy_effective_date` thể hiện rõ tính nhất quán dữ liệu theo mốc versioning.

## 3. Một lỗi/anomaly đã xử lý

Tôi gặp lỗi ban đầu ở rule topic keyword: phiên bản đầu quá chặt cho `policy_refund_v4`, làm các dòng hợp lệ bị quarantine sai và kéo retrieval xuống thấp. Triệu chứng là eval và grading có lúc tụt do không còn đủ chunk refund đúng. Tôi sửa bằng cách nới keyword map cho `policy_refund_v4` để nhận cả cụm `"ngày làm việc"` ngoài `"hoàn tiền"`.

Sau sửa:
- `quarantine_sprint4-final.csv` không còn `topic_keyword_mismatch` cho dòng hợp lệ.
- `grading_run.jsonl` đạt `gq_d10_01/gq_d10_02/gq_d10_03` theo criteria.

Anomaly có chủ đích trong inject được giữ lại:
- `topic_keyword_mismatch` (dòng bảo trì nội bộ đặt sai doc_id policy_refund).
- `invalid_exported_at_format`.
- `effective_date_after_exported_at`.

## 4. Bằng chứng trước/sau

Run inject `sprint3-inject`:
- `quarantine_records=6`, `cleaned_records=3`.
- `q_refund_window`: `hits_forbidden=yes`.
- `q_leave_version`: `contains_expected=no`, `top1_doc_expected=no`.

Run sạch `sprint4-final`:
- `quarantine_records=4`, `cleaned_records=6`.
- `q_refund_window`: `contains_expected=yes`, `hits_forbidden=no`.
- `q_leave_version`: `contains_expected=yes`, `top1_doc_expected=yes`.

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ tách expectation thành 2 layer:
1) schema/data-quality checks (pydantic hoặc GE),
2) semantic policy checks (refund/leave version) với report riêng theo từng doc_id.
Điều này giúp phân biệt rõ lỗi kỹ thuật (format/schema) và lỗi nghiệp vụ (stale policy).
