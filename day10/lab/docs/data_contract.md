# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/raw/policy_export_dirty.csv` | Batch CSV export theo run_id | Duplicate rows, ngày không ISO, doc_id ngoài allowlist, refund window stale 14 ngày | `quarantine_records`, expectation halt `no_stale_refund_window` |
| `data/docs/policy_refund_v4.txt` + `data/docs/sla_p1_2026.txt` + `data/docs/hr_leave_policy.txt` + `data/docs/it_helpdesk_faq.txt` | Canonical text snapshot để chuẩn hóa `doc_id` và mapping business rule | Drift nội dung giữa raw export và canonical docs (ví dụ HR 10 vs 12 ngày phép) | `cleaned_records`, `hits_forbidden` trong eval, freshness status |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | … |
| doc_id | string | Có | … |
| chunk_text | string | Có | … |
| effective_date | date | Có | … |
| exported_at | datetime | Có | … |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

- Record vi phạm schema/allowlist/format được đưa vào `artifacts/quarantine/quarantine_<run-id>.csv`.
- Record duplicate theo `chunk_text` được giữ bản mới nhất theo `exported_at`, bản cũ chuyển quarantine (không drop im lặng).
- Record có `doc_id` không nằm trong `allowed_doc_ids` bị quarantine để tránh nhiễm bẩn index.
- Quy trình approve merge lại: Cleaning/Quality Owner đề xuất fix rule, Pipeline Owner (Người A) rerun và so số liệu trước/sau trong `artifacts/logs` + `artifacts/manifests`.

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?

- Source of truth cho refund policy: `data/docs/policy_refund_v4.txt`.
- Cửa sổ hoàn tiền hợp lệ: 7 ngày (không chấp nhận stale 14 ngày trong cleaned output).
- Với HR leave policy, chỉ giữ version thỏa mốc hiệu lực theo contract (`hr_leave_min_effective_date`).
