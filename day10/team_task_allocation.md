# Day10 - Phân công nhiệm vụ 5 thành viên (kèm auto-log owner khi lỗi)

## Mục tiêu
- Chia việc theo cụm file rõ ràng để tránh conflict khi merge.
- Mỗi phần có `task_id` cố định để truy vết lỗi.
- Khi pipeline cảnh báo/lỗi, log phải tự ghi `task_id` + `owner` để biết ai chịu trách nhiệm sửa.

## Thành viên
1. Hoang Kim Tri Thanh (2A202600372)
2. Dang Dinh Tu Anh (2A202600019)
3. Quach Gia Duoc (2A202600423)
4. Pham Quoc Dung (2A202600490)
5. Nguyen Thanh Nam (2A202600205)

## Nguyên tắc làm việc (giống Day08/09)
1. Mỗi người chỉ sửa file thuộc scope đã phân công.
2. Nếu cần sửa file owner khác: tạo issue trong nhóm, đồng bộ trước khi sửa.
3. Mỗi commit chỉ 1 việc nhỏ, commit message theo prefix `feat/fix/docs/chore(day10-lab): ...`.
4. Trước khi PR: chạy lại luồng chính `python etl_pipeline.py run` và lưu artifact.

## Phân công theo task_id (owner file rõ ràng)

| Task ID | Thành viên | Branch đề xuất | File được sửa (độc quyền chính) | Công việc chính |
|---|---|---|---|---|
| D10-T01 | Dang Dinh Tu Anh | feature/day10-tuanh-ingest | `day10/lab/etl_pipeline.py` (phần ingest), `day10/lab/docs/data_contract.md` | Ingest raw, schema mapping, log `raw_records`, kiểm tra input path |
| D10-T02 | Quach Gia Duoc | feature/day10-duoc-cleaning | `day10/lab/transform/cleaning_rules.py`, `day10/lab/artifacts/quarantine/` | Cleaning rules, dedupe, parse date, quarantine logic |
| D10-T03 | Pham Quoc Dung | feature/day10-dung-quality | `day10/lab/quality/expectations.py`, `day10/lab/eval_retrieval.py`, `day10/lab/grading_run.py` | Expectation suite warn/halt, before-after evidence, grading JSONL |
| D10-T04 | Nguyen Thanh Nam | chore/day10-nam-docs-monitoring | `day10/lab/docs/runbook.md`, `day10/lab/docs/pipeline_architecture.md`, `day10/lab/reports/*` | Runbook, docs vận hành, ghi nhận sự cố và action item |
| D10-T05 | Hoang Kim Tri Thanh | chore/day10-thanh-integration | `day10/lab/monitoring/freshness_check.py`, `day10/lab/contracts/*`, `day10/lab/README.md` | Freshness SLA, owner map contract, integration và chốt release |
| D10-T00 | Hoang Kim Tri Thanh | chore/day10-thanh-release-gate | `day10/team_task_allocation.md`, `day10/lab/artifacts/manifests/` | Điều phối, merge gate, triage cuối khi pipeline fail |

## Cơ chế auto-log owner khi lỗi (bắt buộc)

- Mapping owner nằm tại: `day10/lab/contracts/task_owner_map.json`.
- Mọi lỗi/cảnh báo trong pipeline phải có:
  - `task_id` (ví dụ `D10-T03`)
  - `owner` (tự resolve từ map)
  - `level` (`INFO/WARN/ERROR`)
  - `event` (tên sự kiện)
  - `message`
- Khi triage, chỉ cần tìm trong log theo `event_json=` để biết lỗi thuộc phần của ai.

### Quy ước gán task_id cho lỗi
- Ingest/raw/schema fail -> `D10-T01`
- Cleaning/quarantine/date parse fail -> `D10-T02`
- Expectation fail/halt, grading mismatch -> `D10-T03`
- Embed/upsert/idempotency/prune fail -> `D10-T05`
- Freshness SLA/manifest monitoring fail -> `D10-T05`
- Release/integration fail cuối luồng -> `D10-T00`

## Lệnh chạy và truy vết nhanh

```bash
cd day10/lab
python etl_pipeline.py run --run-id team-check
```

Sau khi chạy, đọc file log mới nhất trong `day10/lab/artifacts/logs/`:
- Tìm dòng chứa `event_json=` để thấy `task_id` và `owner`.
- Khi có incident, assign trực tiếp cho owner tương ứng, không tranh cãi phạm vi.

## Thứ tự merge để ít conflict
1. `D10-T01` (ingest) merge trước.
2. `D10-T02` (cleaning) merge sau khi ingest ổn định.
3. `D10-T03` (quality/eval) merge khi dữ liệu cleaned đã ổn.
4. `D10-T04` (docs/runbook) cập nhật theo run artifact thật.
5. `D10-T05` + `D10-T00` merge cuối để chốt monitoring + release gate.
