# Quality report — Lab Day 10 (nhóm)

**run_id:** 2026-04-15T08-27Z  
**Ngày:** 15/04/2026

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (inject-bad) | Sau (clean run) | Ghi chú |
|--------|-------------------|-----------------|---------|
| raw_records | 10 | 10 | Dùng cùng nguồn `policy_export_dirty.csv` |
| cleaned_records | 6 | 6 | Số record sạch giữ lại không đổi |
| quarantine_records | 4 | 4 | 4 record bị cách ly vì dữ liệu không đạt yêu cầu |
| Expectation halt? | Có (nhưng `--skip-validate`) | Không | `refund_no_stale_14d_window` fail ở run bad, còn clean run pass |

---

## 2. Before / after retrieval (bắt buộc)

> Evidence: `artifacts/eval/after_inject_bad.csv` (bad run) và `artifacts/eval/clean_run_eval.csv` (clean run).

**Câu hỏi then chốt:** refund window (`q_refund_window`)

**Trước:**
- `top1_doc_id`: `policy_refund_v4`
- `contains_expected`: yes
- `hits_forbidden`: yes

**Sau:**
- `top1_doc_id`: `policy_refund_v4`
- `contains_expected`: yes
- `hits_forbidden`: no

**Diễn giải:**
- Trước khi fix, pipe inject-bad giữ lại nội dung stale 14 ngày hoàn tiền nên `hits_forbidden=yes` dù vẫn tìm được chunk chứa câu trả lời đúng.
- Sau khi chạy clean run bình thường, `hits_forbidden=no` nghĩa là stale refund window đã được loại bỏ khỏi context embed, cải thiện chất lượng retrieval.

**Merit (khuyến nghị):** versioning HR — `q_leave_version`

**Trước:**
- `contains_expected`: yes
- `hits_forbidden`: no
- `top1_doc_expected`: yes

**Sau:**
- `contains_expected`: yes
- `hits_forbidden`: no
- `top1_doc_expected`: yes

**Diễn giải:**
- Với câu `q_leave_version`, cả hai run đều trả về đúng `hr_leave_policy` và không hit forbidden content.
- Đây là bằng chứng bổ sung rằng hệ thống giữ được version HR đúng khi không inject mục tiêu vào chính sách nghỉ phép.

---

## 3. Freshness & monitor

> Kết quả `freshness_check`: FAIL

- `latest_exported_at`: 2026-04-10T08:00:00
- `age_hours`: ~120 giờ
- `sla_hours` đã chọn: 24 giờ
- `reason`: `freshness_sla_exceeded`

**Giải thích:**
- Chúng tôi chọn SLA 24 giờ vì pipeline cần cập nhật dữ liệu khá tươi để đảm bảo thông tin policy/HR không lỗi thời.
- Hiện tại dữ liệu được export đã quá hạn, nên cần bổ sung quy trình cập nhật raw input thường xuyên hơn hoặc cảnh báo khi output stale.

---

## 4. Corruption inject (Sprint 3)

> Mô tả cố ý làm hỏng dữ liệu và cách phát hiện.

- Dùng lệnh:
  - `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`
- Corruption: giữ lại phiên bản hợp đồng refund 14 ngày (`--no-refund-fix`) và bỏ qua halt validation (`--skip-validate`).
- Mục tiêu: tạo một trường hợp stale refund window để kiểm tra retrieval `hits_forbidden`.
- Cách phát hiện: đánh giá retrieval với `eval_retrieval.py` và quan sát `hits_forbidden=yes` cho `q_refund_window` trong file `artifacts/eval/after_inject_bad.csv`.

---

## 5. Hạn chế & việc chưa làm

- Chỉ kiểm tra một kịch bản corruption chủ yếu liên quan đến refund window.
- Chưa có thêm kịch bản inject khác như duplicate, sai định dạng ngày hoặc doc_id lạ.
- Cần hoàn thiện thêm so sánh trực tiếp `before_after_eval.csv` nếu muốn báo cáo dạng one-file tổng hợp.
- Cần bổ sung thêm log/chứng cứ cho việc prunes embed và publish boundary trong báo cáo nhóm.
