# Kiến trúc pipeline — Lab Day 10

**Nhóm:** Team 62  
**Cập nhật:** 2026-04-15

---

## 1. Sơ đồ luồng (bắt buộc có 1 diagram: Mermaid / ASCII)

```
┌─────────────────┐
│  Raw Export     │  ← data/raw/policy_export_dirty.csv
│  (CSV/API/DB)   │     exported_at timestamp
└────────┬────────┘
         │ [freshness check boundary 1: ingest]
         ▼
┌─────────────────┐
│  Ingest         │  ← load_raw_csv()
│  + run_id gen   │     run_id = timestamp / custom
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Transform      │  ← cleaning_rules.py
│  (Clean)        │     • Allowlist doc_id
│                 │     • Normalize effective_date (ISO)
│                 │     • Quarantine HR stale (<2026-01-01)
│                 │     • Fix refund 14→7 days
│                 │     • Dedupe chunk_text
│                 │     • Strip BOM, short chunk, missing exported_at
└────┬────────┬───┘
     │        │
     │        └──────────────┐
     ▼                       ▼
┌─────────────┐      ┌──────────────┐
│  Cleaned    │      │  Quarantine  │
│  CSV        │      │  CSV         │
└─────┬───────┘      └──────────────┘
      │
      ▼
┌─────────────────┐
│  Quality        │  ← expectations.py
│  (Validate)     │     • min_one_row (halt)
│                 │     • no_empty_doc_id (halt)
│                 │     • refund_no_stale_14d_window (halt)
│                 │     • chunk_min_length_8 (warn)
│                 │     • effective_date_iso (halt)
│                 │     • hr_leave_no_stale_10d_annual (halt)
│                 │     • exported_at_all_populated (warn)
│                 │     • chunk_text_min_length_20 (warn)
└────────┬────────┘
         │ [halt if severity=halt fails]
         ▼
┌─────────────────┐
│  Embed          │  ← ChromaDB
│  (Vector Store) │     • Upsert by chunk_id (idempotent)
│                 │     • Prune old vectors not in cleaned
│                 │     • Collection: day10_kb
└────────┬────────┘
         │ [freshness check boundary 2: publish]
         ▼
┌─────────────────┐
│  Manifest       │  ← artifacts/manifests/manifest_<run_id>.json
│  + Freshness    │     • run_id, run_timestamp
│  Check          │     • raw_records, cleaned_records, quarantine_records
│                 │     • latest_exported_at
│                 │     • SLA check (24h default)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Serving        │  ← Day 08/09 retrieval
│  (Agent/RAG)    │     • Query vector store
│                 │     • Return top-k chunks
└─────────────────┘
```

---

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | Owner nhóm |
|------------|-------|--------|--------------|
| Ingest | Raw CSV export từ nguồn | List[Dict] raw rows + run_id | Ingestion Owner |
| Transform | Raw rows | Cleaned CSV + Quarantine CSV + stats | Cleaning & Quality Owner |
| Quality | Cleaned rows | Expectation results + halt flag | Cleaning & Quality Owner |
| Embed | Cleaned CSV | ChromaDB collection (upserted) | Embed & Idempotency Owner |
| Monitor | Manifest JSON | Freshness status (PASS/WARN/FAIL) | Monitoring / Docs Owner |

---

## 3. Idempotency & rerun

**Strategy:** Upsert theo `chunk_id` (stable hash: `doc_id + chunk_text + seq`).

**Rerun behavior:**
- Lần 1: Insert 6 vectors → collection count = 6
- Lần 2 (cùng data): Upsert 6 vectors → collection count = 6 (không duplicate)
- Lần 3 (data thay đổi): Upsert new vectors + prune old IDs → collection count = số cleaned mới

**Evidence:** Log ghi `embed_collection_before` và `embed_collection_after` để chứng minh idempotent.

**Prune strategy:** Sau mỗi run, xóa các `chunk_id` không còn trong cleaned CSV để tránh "mồi cũ" làm fail grading.

---

## 4. Liên hệ Day 09

Pipeline này cung cấp corpus cho retrieval trong Day 09 multi-agent system:

- **Cùng nguồn:** `data/docs/` chứa 5 file policy (access_control_sop, hr_leave_policy, it_helpdesk_faq, policy_refund_v4, sla_p1_2026)
- **Export flow:** Day 10 mô phỏng "export từ DB/API" → CSV raw → clean → embed
- **Collection:** Day 10 dùng `day10_kb` collection (có thể khác Day 09 nếu Day 09 dùng collection riêng)
- **Tích hợp:** Sau khi Day 10 embed xong, Day 09 agent có thể query cùng collection để lấy context mới nhất

**Lợi ích:** Day 10 đảm bảo data quality (freshness, validation, no stale version) trước khi Day 09 agent sử dụng.

---

## 5. Rủi ro đã biết

- **Freshness SLA:** CSV mẫu có `exported_at = 2026-04-10` → FAIL với SLA 24h (hiện tại 2026-04-15). Cần cập nhật timestamp hoặc điều chỉnh SLA.
- **Quarantine approval:** Hiện tại quarantine chỉ log, chưa có workflow approve/merge lại.
- **Schema drift:** Nếu nguồn thêm cột mới, cleaning_rules cần cập nhật allowlist.
- **Embed cost:** Rerun toàn bộ corpus mỗi lần → tốn tài nguyên. Cần incremental embed cho production.
- **Version conflict:** Nếu có nhiều version policy cùng lúc, cần thêm logic chọn version canonical.
