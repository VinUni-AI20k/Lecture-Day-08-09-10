# Kiến trúc pipeline — Lab Day 10

**Nhóm:** C401_B4  
**Cập nhật:** 15/04/2026

---

## 1. Sơ đồ luồng (bắt buộc có 1 diagram: Mermaid / ASCII)

```
graph TD
    Raw[data/raw/policy_export_dirty.csv] --> Ingest(ingest: load_raw_csv)
    Ingest --> Clean{"transform/cleaning_rules.py<br/>- allowlist doc_id<br/>- normalize effective_date<br/>- quarantine<br/>- fix refund 14->7"}
    
    Clean -->|Lỗi / Stale| Quar[artifacts/quarantine/quarantine_run_id.csv]
    Clean -->|Hợp lệ| Cleaned[artifacts/cleaned/cleaned_run_id.csv]
    
    Cleaned --> Valid{"quality/expectations.py<br/>(halt/warn)"}
    Valid -->|halt & không skip-validate| Halt[Dừng publish]
    Valid -->|pass / skip-validate| Embed(embed Chroma: upsert + prune)
    
    Embed --> DB[(chroma_db)]
    DB --> Serving([serving retrieval])
```

Telemetry/lineage:
- artifacts/logs/run_<run_id>.log
- artifacts/manifests/manifest_<run_id>.json
- freshness check đọc manifest (latest_exported_at, SLA giờ)


Ghi chú quan sát vận hành:
- `run_id` xuất hiện trong log, manifest, metadata vector và tên file artifacts.
- Freshness được đo sau khi ghi manifest (theo `latest_exported_at`, fallback `run_timestamp`).
- Quarantine là ranh giới publish: bản ghi lỗi không đi vào cleaned/embed.

---

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | Owner nhóm |
|------------|-------|--------|--------------|
| Ingest | `data/raw/*.csv` | Danh sách row thô trong bộ nhớ + log `raw_records` | Ingestion Owner |
| Transform | Row thô + rule clean | `cleaned_<run_id>.csv` và `quarantine_<run_id>.csv` | Cleaning/Quality Owner |
| Quality | Cleaned rows | Kết quả expectation (`warn`/`halt`) + quyết định dừng/đi tiếp | Cleaning/Quality Owner |
| Embed | Cleaned CSV đã qua validate | Upsert vào Chroma + prune id cũ + metadata `run_id` | Embed Owner |
| Monitor | Manifest + SLA | Trạng thái PASS/WARN/FAIL freshness + cảnh báo vận hành | Monitoring/Docs Owner |

---

## 3. Idempotency & rerun

> Mô tả: upsert theo `chunk_id` hay strategy khác? Rerun 2 lần có duplicate vector không?

---

## 4. Liên hệ Day 09

Liên hệ vận hành với Day 09:

- Day 10 chuẩn hóa tầng dữ liệu để retrieval ổn định trước khi agent orchestration dùng kết quả tìm kiếm.
- Canonical policy vẫn đi từ bộ docs nghiệp vụ CS + IT Helpdesk; Day 10 bổ sung lớp ingest/clean/validate trước khi embed.
- Khi rerun Day 10 thành công, collection Chroma được cập nhật theo snapshot mới, từ đó Day 09 retrieval nhận context đúng version (ví dụ refund 7 ngày, không dính chunk stale 14 ngày).

---

## 5. Rủi ro đã biết

- …
