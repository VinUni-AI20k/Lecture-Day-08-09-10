# Data contract — Lab Day 10

Tài liệu này được đồng bộ từ [lab/contracts/data_contract.yaml]

- Version: 1.0
- Dataset: kb_chunk_export
- Owner team: C401_B4

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/docs/policy_refund_v4.txt` | File export -> CSV raw -> ETL run | Cửa sổ refund stale (14 ngày thay vì 7 ngày) | Expectation halt: no_stale_refund_window |
| `data/docs/sla_p1_2026.txt` | File export -> CSV raw -> ETL run | Sai/mất ngày hiệu lực khi map schema | Freshness FAIL khi quá SLA; tăng quarantine_records |
| `data/docs/it_helpdesk_faq.txt` | File export -> CSV raw -> ETL run | Trùng nội dung chunk, chất lượng retrieval giảm | Quality rule warn: no_duplicate_chunk_text |
| `data/docs/hr_leave_policy.txt` | File export -> CSV raw -> ETL run | Lẫn bản policy cũ (effective_date < 2026-01-01) | Quarantine theo policy_versioning + theo dõi quarantine_records |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| `chunk_id` | string | Có | ID ổn định sau clean (thường hash hoặc doc_id + seq) |
| `doc_id` | string | Có | Khóa logic tài liệu nguồn (vd: policy_refund_v4) |
| `chunk_text` | string | Có | Nội dung chunk; ràng buộc min_length = 8 |
| `effective_date` | date | Có | Ngày hiệu lực chuẩn hóa để lọc version và truy vết |
| `exported_at` | datetime | Có | Mốc thời gian export của record từ nguồn |

Ràng buộc chất lượng chính:

- `no_duplicate_chunk_text`: severity warn
- `no_stale_refund_window`: severity halt

---

## 3. Quy tắc quarantine vs drop

Luồng xử lý record bị flag:

- Record vi phạm rule/expectation không bị ghi vào cleaned publish ngay.
- Record được đưa sang file quarantine để điều tra và sửa nguồn trước khi rerun.
- Trường hợp vi phạm severity halt (no_stale_refund_window), pipeline phải dừng publish.

Chính sách vận hành nhóm:

- Nơi lưu quarantine: artifacts/quarantine/*.csv
- Nơi lưu cleaned chính thức: artifacts/cleaned/*.csv
- Người phê duyệt merge lại dữ liệu sau khi xử lý: owner_team C401_B4 (Data/Quality owner của sprint)

---

## 4. Phiên bản & canonical

Canonical sources theo contract:

- policy_refund_v4 -> data/docs/policy_refund_v4.txt
- sla_p1_2026 -> data/docs/sla_p1_2026.txt
- it_helpdesk_faq -> data/docs/it_helpdesk_faq.txt
- hr_leave_policy -> data/docs/hr_leave_policy.txt

Source of truth cho refund policy:

- File canonical: data/docs/policy_refund_v4.txt
- Quy ước version đúng: hoàn tiền trong 7 ngày làm việc
- Bất kỳ nội dung còn chứa cửa sổ 14 ngày được xem là stale và phải fail expectation halt

Versioning policy bổ sung:

- hr_leave_min_effective_date: 2026-01-01
- Chỉ cho phép doc_id trong allowlist:
	- policy_refund_v4
	- sla_p1_2026
	- it_helpdesk_faq
	- hr_leave_policy

Freshness SLA:

- measured_at: publish
- sla_hours: 24
- alert_channel: cần được điền theo kênh cảnh báo thực tế của nhóm
