# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Khương Quang Vinh  
**Vai trò:** Expectations & Data Quality Owner 
**Ngày nộp:** 15/04/2026  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào?

**File / module:**

- `quality/expectations.py` — Toàn bộ expectation suite (E1–E10)
- Phối hợp với `transform/cleaning_rules.py` để xác nhận các rule clean đảm bảo expectation pass

Tôi chịu trách nhiệm xây dựng và mở rộng expectation suite trong `quality/expectations.py`. Baseline ban đầu đã có 6 expectation E1–E6. Tôi bổ sung thêm **4 expectation mới** E7–E10 nhằm bao phủ các failure mode còn thiếu: doc_id ngoài allowlist lọt qua clean, chunk_text rỗng đi vào embed, xung đột version policy trong cùng batch, và trường `exported_at` sai format ISO 8601. Mỗi expectation đều có `metric_impact` được ghi rõ trong comment code, ràng buộc với kịch bản inject cụ thể có thể tái hiện.

**Kết nối với thành viên khác:**

Phối hợp với Member 2 (Cleaning Owner) để đảm bảo `cleaning_rules.py` đã có các rule tương ứng cho từng expectation halt mới: rule `unknown_doc_id` (→ E7), rule `missing_chunk_text` (→ E8), rule `stale_hr_policy_effective_date` (→ E9). Khi cả hai module đồng bộ, run chuẩn đạt 10/10 expectation OK.

**Bằng chứng (commit / comment trong code):**

Header docstring `expectations.py` ghi rõ vai trò: *"Bổ sung (Member 1 — Quality Owner): E7–E10"*. Log `run_sprint2-clean` (`artifacts/logs/run_sprint2-clean.log`) xác nhận tất cả 10 expectation pass.

---

## 2. Một quyết định kỹ thuật

**Quyết định: phân tầng severity `halt` vs `warn` cho từng expectation**

Khi thiết kế E7–E10, tôi phải chọn severity phù hợp thay vì đặt tất cả là `halt`. Nguyên tắc tôi áp dụng: 
- `halt` nếu lỗi làm hỏng chất lượng nội dung truy vấn
- `warn` nếu lỗi chỉ ảnh hưởng metadata/monitoring

- **E7 `doc_id_in_allowlist` → halt**: doc lạ lọt vào embed tạo ra vector nhiễu, top-k retrieval trả về nội dung không thuộc scope hỗ trợ — ảnh hưởng trực tiếp độ chính xác.
- **E8 `chunk_text_not_empty` → halt**: text rỗng tạo zero/noise vector, làm lệch cosine similarity của toàn bộ collection.
- **E9 `no_conflicting_version_policy` → halt**: hai bản `hr_leave_policy` với `effective_date` khác nhau trong cùng batch gây mâu thuẫn — câu hỏi về phép năm có thể trả về đồng thời "10 ngày" (cũ) và "12 ngày" (mới).
- **E10 `exported_at_iso8601_format` → warn**: trường này không ảnh hưởng nội dung retrieval, chỉ làm freshness check tính sai `age_hours`. Pipeline vẫn nên chạy tiếp để không block embed vì metadata.

Quyết định này giúp pipeline không quá nhạy (quá nhiều halt làm CI/CD tắc) mà vẫn bảo vệ đúng tầng dữ liệu quan trọng.

---

## 3. Một lỗi hoặc anomaly đã xử lý

**Anomaly: `policy_refund_v4` chứa cửa sổ hoàn tiền sai (14 ngày thay vì 7 ngày)**

**Triệu chứng:** Trong `data/raw/policy_export_dirty.csv`, dòng chunk_id=3 chứa text *"14 ngày làm việc kể từ xác nhận đơn (ghi chú: bản sync cũ policy-v3 — lỗi migration)"*. Đây là artifact của migration từ policy-v3 sang v4 — chunk cũ bị sync nhầm vào export.

**Metric phát hiện:** Expectation E3 `refund_no_stale_14d_window` (severity halt). Khi chạy với flag `--no-refund-fix` (inject bad):

```
run_id=sprint2-inject-bad
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
PIPELINE_HALT: expectation suite failed (halt).
```

Pipeline dừng tại đây, không đi đến bước embed — ngăn vector cũ phát tán vào collection.

**Fix:** Rule `apply_refund_window_fix` trong `cleaning_rules.py` detect chuỗi `"14 ngày làm việc"` trong `policy_refund_v4` và thay bằng `"7 ngày làm việc"`, đồng thời append tag `[cleaned: stale_refund_window]` vào cuối chunk để traceable. Sau fix, E3 pass và pipeline tiếp tục bình thường.

---

## 4. Bằng chứng trước / sau

**Run chuẩn `sprint2-clean` (tất cả expectation PASS):**

```
run_id=sprint2-clean
raw_records=10  |  cleaned_records=6  |  quarantine_records=4
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
expectation[doc_id_in_allowlist]        OK (halt) :: unauthorized_count=0
expectation[chunk_text_not_empty]       OK (halt) :: empty_chunk_text_count=0
expectation[no_conflicting_version_policy] OK (halt) :: conflicting_docs=0
embed_upsert count=6 collection=day10_kb
PIPELINE_OK
```

**Run inject `sprint2-inject-bad` (`--no-refund-fix` → HALT):**

```
run_id=sprint2-inject-bad
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
PIPELINE_HALT: expectation suite failed (halt).
```

So sánh: raw_records=10 giống nhau ở cả hai run, nhưng với `--no-refund-fix`, chunk stale 14 ngày không bị fix → lọt vào cleaned → E3 bắt → pipeline dừng trước bước embed. Cleaning đúng → 0 violations → embed 6 chunks sạch vào `day10_kb`.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ bổ sung **expectation thống kê phân phối chunk length** bằng cách tính percentile p5/p95 của `len(chunk_text)` và cảnh báo (warn) nếu p5 < 20 ký tự hoặc p95 > 2000 ký tự thay cho ngưỡng cứng 8 ký tự hiện tại. 
