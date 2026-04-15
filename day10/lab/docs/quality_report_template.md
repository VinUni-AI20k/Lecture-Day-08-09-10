# Quality report — Lab Day 10 (nhóm)

**run_id:** 2026-04-15T10-00Z  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (inject bad) | Sau (pipeline chuẩn) | Ghi chú |
|--------|-------------------|----------------------|---------|
| raw_records | 10 | 10 | Cùng file đầu vào |
| cleaned_records | 6 | 5 | Rule mới `quarantine_migration_error_marker` quarantine thêm row 3 |
| quarantine_records | 4 | 5 | Row 3 (lỗi migration) vào quarantine thay vì được fix |
| Expectation halt? | YES (refund_no_stale_14d_window, no_migration_error_marker) | NO (tất cả PASS) | inject dùng `--skip-validate` |

> **Chú thích:** "Trước" = chạy `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`.  
> "Sau" = chạy `python etl_pipeline.py run --run-id 2026-04-15T10-00Z` (pipeline chuẩn).

---

## 2. Before / after retrieval (bắt buộc)

**Câu hỏi then chốt:** refund window (`q_refund_window`)

**Trước (inject-bad — chunk stale "14 ngày" còn trong index):**
```
question_id,question,top1_doc_id,top1_preview,contains_expected,hits_forbidden,top1_doc_expected,top_k_used
q_refund_window,Khách hàng có bao nhiêu ngày...,policy_refund_v4,Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc...,no,yes,,3
```

**Sau (pipeline chuẩn — chunk stale bị quarantine/prune):**
```
q_refund_window,Khách hàng có bao nhiêu ngày...,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc...,yes,no,,3
```

**Merit — versioning HR (`q_leave_version`):**

**Trước (inject-bad — bản HR 2025 còn trong index nếu `--skip-validate`):**
```
q_leave_version,...,hr_leave_policy,Nhân viên dưới 3 năm kinh nghiệm được 10 ngày phép năm...,no,yes,no,3
```

**Sau (pipeline chuẩn — HR 2025 bị quarantine bởi `stale_hr_policy_effective_date`):**
```
q_leave_version,...,hr_leave_policy,Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm...,yes,no,yes,3
```

---

## 3. Freshness & monitor

Kết quả freshness sau pipeline chuẩn:
```
PASS {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 122.0, "sla_hours": 24.0}
```

> **Chú ý:** `latest_exported_at` = 2026-04-10 từ file raw mẫu → age ≈ 122h > 24h SLA → thực tế FAIL. Đây là dữ liệu mẫu cũ; trong production cần source system cập nhật `exported_at` theo ngày chạy thực tế.  
> SLA chọn 24h phù hợp với chu kỳ batch hàng ngày: PASS = dữ liệu mới nhất được publish trong ngày; WARN = nên có nhưng pipeline chưa fail; FAIL = urgent alert.

---

## 4. Corruption inject (Sprint 3)

**Kịch bản inject:**  
Chạy `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`:
- Flag `--no-refund-fix` → chunk chứa "14 ngày làm việc" **không bị fix** → vào cleaned với text sai.
- Flag `--skip-validate` → expectation `refund_no_stale_14d_window` FAIL nhưng pipeline tiếp tục embed.
- Kết quả: vector store có chunk "14 ngày làm việc" → `hits_forbidden=yes` trên `q_refund_window`.

**Cách phát hiện:**
- Log: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
- Log: `WARN: expectation failed but --skip-validate → tiếp tục embed`
- Eval CSV: `hits_forbidden=yes` trên `q_refund_window`

**Fix:** chạy lại pipeline chuẩn (không flag) → prune xoá vector cũ → eval trở về PASS.

---

## 5. Hạn chế & việc chưa làm

- `chunk_id` dùng seq tương đối trong run → thứ tự CSV thay đổi làm ID đổi → không stable giữa các source system khác nhau.
- Freshness SLA dùng `exported_at` của raw export; chưa đo boundary riêng cho ingest vs publish.
- Chưa có LLM-judge eval (chỉ keyword-based) — độ chính xác thấp với câu hỏi phức tạp hơn.
- Chưa test với bộ câu hỏi ≥ 5 slice (chỉ 4 câu golden).
