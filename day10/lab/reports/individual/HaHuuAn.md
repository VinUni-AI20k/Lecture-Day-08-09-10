# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Hà Hữu An 
**Vai trò:** Embedding & Eval (RAG)  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `etl_pipeline.py` → `cmd_embed_internal()` — ChromaDB upsert, prune logic, log `embed_prune_removed`
- `eval_retrieval.py` — chạy retrieval eval golden questions, ghi CSV before/after
- `grading_run.py` — chạy grading questions, ghi JSONL
- `data/grading_questions.json` — tạo 3 câu `gq_d10_01`…`gq_d10_03`

**Kết nối với thành viên khác:**

Tôi nhận cleaned CSV từ Cleaning Specialist (qua Pipeline Lead), embed vào ChromaDB. Kết quả eval CSV là bằng chứng before/after mà Quality Owner và nhóm dùng trong `group_report.md`. Grading JSONL là deliverable bắt buộc cho giảng viên.

**Bằng chứng:**

- `embed_prune_removed=1` trong log sau pipeline chuẩn (prune 1 vector từ inject-bad run trước)
- `artifacts/eval/before_after_eval.csv` và `artifacts/eval/grading_run.jsonl`

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Thiết kế `grading_questions.json` — chọn `must_contain_any` và `must_not_contain`:**

Tôi cần đảm bảo `gq_d10_01` (refund window) phân biệt được inject-bad vs pipeline chuẩn. Nếu chỉ dùng `must_contain_any: ["7 ngày"]`, câu trả lời inject-bad cũng có thể pass vì vector store vẫn có chunk "7 ngày làm việc" từ row 1. Vì vậy tôi thêm `must_not_contain: ["14 ngày làm việc"]` — nếu chunk stale vẫn còn trong top-k, `hits_forbidden=true` ngay lập tức.

Đây là lý do SCORING ghi "quét toàn bộ top-k chunk ghép lại, không chỉ top-1": một query có thể trả top-1 đúng nhưng top-2 vẫn có chunk stale → agent nhìn thấy và bị mislead. `blob = " ".join(docs).lower()` trong `eval_retrieval.py` và `grading_run.py` xử lý đúng điều này.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Sau inject-bad run, chạy lại pipeline chuẩn và eval → `hits_forbidden` vẫn `yes` trên `q_refund_window` dù log báo `PIPELINE_OK`.

**Phát hiện:** Kiểm tra log: `embed_prune_removed=0` — prune không xoá gì. Nguyên nhân: inject-bad dùng `--run-id inject-bad`, tạo chunk_id khác với pipeline chuẩn (vì seq và text khác sau `--no-refund-fix`). Khi pipeline chuẩn upsert current_ids, prev_ids từ inject-bad vẫn tồn tại và `drop = prev_ids - current_ids` đúng ra phải có phần tử.

**Fix và nguyên nhân thật:** Pipeline chuẩn upsert với `chunk_id` mới (Rule 7 quarantine row 3 → sequence đổi) → `drop` = id cũ từ inject. Confirm: log lần 2 sau pipeline chuẩn ghi `embed_prune_removed=1`. Eval lại → `hits_forbidden=no`. Vấn đề là tôi đọc log sai lần đầu (nhìn nhầm vào log inject-bad cũ thay vì log pipeline chuẩn mới).

---

## 4. Bằng chứng trước / sau (80–120 từ)

`artifacts/eval/after_inject_bad.csv` (`run_id=inject-bad`):
```
q_refund_window,Khách hàng có bao nhiêu ngày...,policy_refund_v4,...14 ngày...,no,yes,,3
```

`artifacts/eval/before_after_eval.csv` (`run_id=2026-04-15T10-00Z`):
```
q_refund_window,Khách hàng có bao nhiêu ngày...,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc...,yes,no,,3
q_leave_version,...,hr_leave_policy,Nhân viên dưới 3 năm...12 ngày phép năm...,yes,no,yes,3
```

`contains_expected` đổi từ `no` → `yes`; `hits_forbidden` từ `yes` → `no` — xác nhận pipeline chuẩn giải quyết đúng cả 2 vấn đề.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ mở rộng `eval_retrieval.py` thêm cột `scenario` và hỗ trợ đọc nhiều collection Chroma (inject-bad và clean) trong một lần chạy, ghi 2 dòng per question thay vì phải chạy 2 file riêng. Điều này tạo bảng so sánh side-by-side dễ đọc hơn cho group report và giảm thời gian tổng hợp evidence Sprint 3.
