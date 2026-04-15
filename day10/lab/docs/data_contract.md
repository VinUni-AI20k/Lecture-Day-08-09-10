# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Policy/SLA DB | CSV export qua batch script | Stale policy version (14 vs 7 ngày refund); sai format date | `no_stale_refund_window` (halt); `effective_date` ISO validation |
| HR System | CSV export qua batch script | Policy version conflict (10 vs 12 ngày phép); xung đột effective_date | `hr_leave_version_conflict` (warn); temporal overlap check |
| Helpdesk KB | CSV export (sporadic updates) | Missing chunk_text; unknown doc_id | `min_chunk_length` (warn); allowlist doc_id (halt) |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID stable sau clean, dùng để upsert và prune vector store |
| doc_id | string | Có | Mã tài liệu nguồn; chỉ cho phép các doc_id hợp lệ trong contract |
| chunk_text | string | Có | Nội dung chunk sau khi đã chuẩn hoá và sửa lỗi policy-version |
| effective_date | date | Có | Chuẩn hoá sang `YYYY-MM-DD`; non-ISO bị quarantine |
| exported_at | datetime | Có | Thời điểm xuất bản raw, dùng để kiểm tra freshness |

---

## 3. Quy tắc quarantine vs drop

- `unknown_doc_id`: raw export chứa doc_id không nằm trong allowlist; quarantine vì có thể là export lạ / catalog sai.
- `missing_effective_date` / `invalid_effective_date_format`: cần xử lý nguồn chứ không publish nhầm.
- `stale_hr_policy_effective_date`: HR leave policy cũ trước `2026-01-01` bị quarantine do conflict version.
- `missing_chunk_text`: dữ liệu thiếu phần nội dung không thể publish.
- `duplicate_chunk_text`: chunk duplicate bị quarantine để tránh insert vector trùng.

> Quarantine dataset lưu lại cho review và approval. Nếu cần merge, team data phải xác nhận source raw, sau đó cập nhật rule hoặc allowlist.

---

## 4. Phiên bản & canonical

- Policy refund canonical: `data/docs/policy_refund_v4.txt` — đây là source of truth cho cửa sổ hoàn tiền 7 ngày.
- HR leave canonical: `data/docs/hr_leave_policy.txt` — sử dụng chính sách 2026 và quarantine các chunk 10 ngày cũ.
- SLA canonical: `data/docs/sla_p1_2026.txt`
- Helpdesk KB canonical: `data/docs/it_helpdesk_faq.txt`

> Với Sprint 1, source map và canonical document giúp xác định dữ liệu nào được publish, dữ liệu nào cần quarantine, và vì sao raw export bị lỗi.
