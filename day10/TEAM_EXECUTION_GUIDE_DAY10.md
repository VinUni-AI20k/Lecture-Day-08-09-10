# Day10 Team Execution Guide - Hoàn thành tốt phần việc cá nhân

File này là hướng dẫn thực thi để mỗi thành viên hoàn thành đúng phần được giao trong `day10/team_task_allocation.md`, giảm chậm tiến độ và giảm đùn đẩy khi có lỗi.

## 1) Mục tiêu chung của cả nhóm

- Chạy được pipeline chuẩn: ingest -> clean -> validate -> embed -> freshness.
- Có bằng chứng before/after rõ ràng, không mô tả cảm tính.
- Mọi lỗi phải truy ra được owner qua `task_id` trong log.
- Mỗi người có commit đúng phạm vi, không sửa tràn sang phần người khác.

## 2) Nhịp làm việc đề xuất (4 sprint)

- Sprint 1 (Ingest + schema): chốt input và log raw.
- Sprint 2 (Clean + validate + embed): chốt rule/expectation, đảm bảo idempotent.
- Sprint 3 (Inject + eval): cố ý làm hỏng, đo trước/sau.
- Sprint 4 (Monitoring + docs + report): hoàn thiện runbook, checklist nộp.

## 3) Checklist bắt buộc cho từng cá nhân

Mỗi người trước khi nói "xong việc" phải tick đủ:

- [ ] Chỉ sửa file thuộc scope của mình theo `task_id`.
- [ ] Chạy test tối thiểu liên quan phần của mình.
- [ ] Có log hoặc artifact chứng minh thay đổi có tác động thật.
- [ ] Commit tách nhỏ, message rõ mục tiêu thay đổi.
- [ ] Tự đọc log `event_json` để chắc không còn lỗi do phần mình sở hữu.

## 4) Tiêu chuẩn Done theo task_id

## `D10-T01` - Ingestion/Schema (Tú Anh)
- File chính: `day10/lab/etl_pipeline.py`, `day10/lab/docs/data_contract.md`
- Done khi:
  - Pipeline đọc được raw ổn định, không vỡ path/schema cơ bản.
  - Log có `raw_records` đúng.
  - Data contract mô tả nguồn và kiểm tra chính.

## `D10-T02` - Cleaning/Transform (Được)
- File chính: `day10/lab/transform/cleaning_rules.py`
- Done khi:
  - Rule clean chạy ổn với dữ liệu bẩn mẫu.
  - Quarantine có ý nghĩa (không drop mù).
  - `cleaned_records` và `quarantine_records` phản ánh đúng tác động rule.

## `D10-T03` - Quality/Eval (Dũng)
- File chính: `day10/lab/quality/expectations.py`, `day10/lab/eval_retrieval.py`, `day10/lab/grading_run.py`
- Done khi:
  - Có expectation phân biệt warn/halt rõ.
  - Có before/after evidence đọc được.
  - JSONL grading đúng format và đủ dòng.

## `D10-T04` - Docs/Runbook (Nam)
- File chính: `day10/lab/docs/runbook.md`, `day10/lab/docs/pipeline_architecture.md`, `day10/lab/reports/*`
- Done khi:
  - Runbook đủ 5 phần (Symptom -> Prevention).
  - Kiến trúc mô tả đúng luồng thực tế.
  - Báo cáo bám artifact thật (run_id, log, eval).

## `D10-T05` - Monitoring/Integration (Tri Thanh)
- File chính: `day10/lab/monitoring/freshness_check.py`, `day10/lab/README.md`, `day10/lab/contracts/*`
- Done khi:
  - Freshness check PASS/WARN/FAIL được giải thích rõ.
  - Owner map `task_id -> owner` đầy đủ, dùng được.
  - Tích hợp toàn pipeline không gãy khi chạy end-to-end.

## 5) Lệnh tự kiểm tra trước khi giao việc

```bash
cd day10/lab
python etl_pipeline.py run --run-id self-check
python eval_retrieval.py --out artifacts/eval/self_check_eval.csv
python grading_run.py --out artifacts/eval/grading_run.jsonl
```

Nếu làm docs-only, vẫn phải đọc log + artifact từ run mới nhất để ghi đúng.

## 6) Cách tự bắt lỗi đúng owner (rất quan trọng)

Sau mỗi lần chạy pipeline, mở log trong `day10/lab/artifacts/logs/` và tìm `event_json=`.

Mỗi event có:
- `task_id`: phần việc gây lỗi/cảnh báo
- `owner`: người chịu trách nhiệm chính
- `level`: INFO/WARN/ERROR
- `event`: tên sự kiện
- `message`: nội dung chi tiết

Quy tắc xử lý:
- Nếu `level=ERROR`: owner sửa ngay trước khi merge.
- Nếu `level=WARN`: owner đánh giá rủi ro, ghi quyết định vào runbook/report.
- Không chuyển lỗi sang người khác nếu `task_id` thuộc phần mình.

## 7) Quy tắc commit để đạt điểm tốt

- Mỗi commit chỉ một ý chính.
- Khuyến nghị prefix:
  - `feat(day10-lab): ...`
  - `fix(day10-lab): ...`
  - `docs(day10-lab): ...`
  - `chore(day10-lab): ...`
- Mỗi commit nên gắn ngữ cảnh `task_id` trong mô tả (nếu có).

Ví dụ:
- `fix(day10-lab): harden date parsing for malformed exported_at (D10-T02)`
- `docs(day10-lab): complete incident runbook with real log evidence (D10-T04)`

## 8) Những lỗi hay làm mất điểm (tránh ngay)

- Sửa rule/expectation nhưng không tạo thay đổi đo được trong log/eval.
- Viết report không có `run_id` hoặc không khớp artifact thật.
- Commit lẫn sang file của owner khác gây conflict.
- Bỏ qua warning quan trọng nhưng không ghi lý do trong runbook.

## 9) Kịch bản phối hợp khi bị block

- Bước 1: chụp lỗi + copy dòng `event_json` liên quan.
- Bước 2: ping đúng owner theo `task_id`.
- Bước 3: nếu ảnh hưởng cross-task, mở issue ngắn gồm:
  - Impact
  - File liên quan
  - Cần owner nào phối hợp
- Bước 4: chỉ merge lại khi owner chính xác nhận đã pass self-check.

---

Mục tiêu cuối cùng: mỗi người tự chịu trách nhiệm trọn phần của mình, nhưng vẫn phối hợp nhanh nhờ cùng một chuẩn log và cùng một định nghĩa Done.
