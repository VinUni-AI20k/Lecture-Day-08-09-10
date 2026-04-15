# Kiến trúc pipeline - Lab Day 10

**Nhóm:** Team Day10-CS-IT  
**Cập nhật:** 2026-04-15

## 1. Sơ đồ luồng

```text
raw CSV export
  -> ingest log (run_id, raw_records, latest_raw_exported_at)
  -> transform.clean_rows
      -> cleaned CSV
      -> quarantine CSV
  -> quality.run_expectations (warn/halt)
  -> embed upsert (chunk_id) + prune stale ids
  -> manifest JSON
  -> freshness check (ingest boundary + publish boundary)
  -> retrieval serving (Day 08/09 agents)
```

Artifact boundaries:
- Quarantine boundary: `artifacts/quarantine/quarantine_<run_id>.csv`
- Publish boundary: `artifacts/cleaned/cleaned_<run_id>.csv` + Chroma collection
- Observability boundary: `artifacts/manifests/manifest_<run_id>.json` + `artifacts/logs/run_<run_id>.log`

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | Owner |
|---|---|---|---|
| Ingest | `data/raw/*.csv` | `raw_records`, `latest_raw_exported_at` | Nam |
| Transform | raw rows | cleaned rows + quarantine reasons | Cao |
| Quality | cleaned rows | expectation logs + halt/warn | Cao |
| Embed | cleaned CSV | Chroma upsert + prune stale vectors | Tuấn |
| Monitor | manifest + logs | freshness_ingest/publish + runbook | Ly |

## 3. Idempotency và rerun

Chiến lược idempotent:
- `chunk_id` được tạo ổn định từ `doc_id|chunk_text|seq`.
- Embed dùng `upsert(ids=chunk_id)` để không tạo duplicate trên rerun.
- Trước upsert, pipeline prune các `ids` không còn trong cleaned snapshot để cắt stale vector.

Bằng chứng:
- Log `run_sprint4-final.log` có `embed_upsert count=6`.
- Log inject có `embed_prune_removed=4` khi rollback từ data xấu về data sạch.

## 4. Liên hệ Day 09

Collection `day10_kb` là nguồn retrieval cho agent Day 09 khi cần câu trả lời policy/FAQ cập nhật.
Khi pipeline Day 10 chạy xong, Day 09 dùng cùng Chroma path (`./chroma_db`) nhưng query collection mới để đảm bảo "đọc đúng version dữ liệu đã publish".

## 5. Rủi ro đã biết

- Freshness đang `FAIL` trên sample vì `exported_at` cũ hơn SLA 24h (đúng theo dữ liệu lab).
- Embedding model local có thể tải chậm nếu máy chưa cache `all-MiniLM-L6-v2`.
- Nếu inject bypass validate (`--skip-validate`), retrieval có thể nhiễm stale context cho top-k.
