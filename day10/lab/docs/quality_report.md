
# Quality report — Lab Day 10 (nhóm)

**run_id:** sprint3_clean 
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số             | Trước (sprint3_clean) | Sau (inject-bad) | Ghi chú                                                 |
| ------------------ | --------------------- | ---------------- | ------------------------------------------------------- |
| raw_records        | 10                    | 10               | Dữ liệu đầu vào giữ nguyên                              |
| cleaned_records    | 6                     | (tăng)           | inject-bad bỏ qua validate nên giữ lại nhiều record hơn |
| quarantine_records | 4                     | (giảm)           | dữ liệu lỗi không bị đưa vào quarantine                 |
| Expectation halt?  | No (tất cả OK)        | Skipped          | inject-bad bỏ qua toàn bộ validation                    |

---

## 2. Before / after retrieval (bắt buộc)

> File eval:

* `artifacts/eval/before_after_eval.csv`


---

### Câu hỏi then chốt: refund window (`q_refund_window`)

**Trước (sprint3_clean):**

* Retrieval chỉ chứa policy hợp lệ:

  > "refund within 7 working days"
* Không tồn tại chunk sai (14 ngày)
* `hits_forbidden = 0`
* Context sạch, không có conflict

**Sau (inject-bad):**

* Do sử dụng `--no-refund-fix` và `--skip-validate`, policy sai (14 ngày) không bị loại
* Retrieval có thể chứa:

  > "refund within 14 working days"
* Hoặc lẫn cả 7 ngày và 14 ngày trong top-k
* `hits_forbidden > 0`

 Kết luận:

* Dữ liệu bẩn làm nhiễu retrieval
* Agent có nguy cơ trả lời sai hoặc dựa trên context không hợp lệ

---

### Merit (khuyến nghị): versioning HR — `q_leave_version`

**Trước:**

* Retrieval chỉ chứa:

  > "12 days of annual leave"
* Policy cũ (10 ngày) đã bị loại bỏ
* `hits_forbidden = 0`

**Sau:**

* Policy cũ (10 ngày) được giữ lại do skip validation
* Retrieval có thể chứa:

  > "10 days of annual leave"
* `hits_forbidden` tăng

 Kết luận:

* Conflict version làm giảm độ tin cậy của hệ thống retrieval

---

## 3. Freshness & monitor

Kết quả `freshness_check`:

* Status: **FAIL**
* latest_exported_at: 2026-04-10T08:00:00
* age_hours: 122.115 giờ
* SLA: 24 giờ

 Giải thích:

* Dữ liệu đã vượt quá SLA (hơn 5 ngày)
* Pipeline phát hiện đúng tình trạng stale data

 Ý nghĩa:

* Dù dữ liệu đã được clean và validate, vẫn không đảm bảo tính cập nhật
* Monitoring (freshness check) là cần thiết để tránh AI sử dụng dữ liệu lỗi thời

---

## 4. Corruption inject (Sprint 3)

Nhóm đã cố ý làm hỏng dữ liệu bằng các cách:

* Thêm **duplicate record**
* Thêm **stale refund policy (14 ngày thay vì 7 ngày)**
* Thêm **stale HR policy (10 ngày thay vì 12 ngày)**
* Thêm **doc_id không hợp lệ**
* Thêm **lỗi format ngày (non-ISO / missing)**

Trong kịch bản inject-bad:

* Pipeline chạy với:

  * `--no-refund-fix`
  * `--skip-validate`
* Dữ liệu bẩn không bị loại bỏ và được embed trực tiếp vào vector store

Cách phát hiện:

* `cleaned_records` tăng, `quarantine_records` giảm
* Expectation không còn enforce
* Retrieval xuất hiện `hits_forbidden`
* Context chứa nhiều version conflict

 Điều này chứng minh:

* Cleaning và validation là bắt buộc
* Nếu bỏ qua pipeline, hệ thống AI sẽ sử dụng dữ liệu sai

---

## 5. Hạn chế & việc chưa làm

* Chưa có cơ chế resolve conflict version (chỉ loại bỏ, chưa hợp nhất)
* Chưa có alert tự động khi freshness FAIL
* Retrieval evaluation vẫn dựa trên keyword, chưa dùng semantic scoring
* Chưa áp dụng versioning theo thời gian (time-based filtering)
* Chưa có cơ chế rollback dữ liệu khi phát hiện inject lỗi

---
