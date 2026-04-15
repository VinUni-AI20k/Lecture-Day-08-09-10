# Kiến trúc pipeline — Lab Day 10

**Nhóm:** C401-Y3  
**Cập nhật:** 2026-04-15

---

## 1. Sơ đồ luồng

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ETL PIPELINE — DAY 10                        │
└─────────────────────────────────────────────────────────────────────┘

  [data/raw/policy_export_dirty.csv]
              │
              │  load_raw_csv()
              ▼
  ┌───────────────────────┐
  │   INGEST              │  • Đọc CSV vào bộ nhớ
  │   raw_records = N     │  • Ghi run_id + raw_records vào log
  └──────────┬────────────┘
             │
             │  clean_rows()
             ▼
  ┌───────────────────────┐        ┌──────────────────────────┐
  │   CLEAN / TRANSFORM   │──────▶ │  artifacts/quarantine/   │
  │   9 rules lọc dữ liệu │ xấu   │  quarantine_<run_id>.csv │
  │   cleaned_records = M │        └──────────────────────────┘
  └──────────┬────────────┘
             │                    ┌──────────────────────────┐
             │  write_cleaned_csv │  artifacts/cleaned/      │
             │────────────────────▶  cleaned_<run_id>.csv    │
             │                    └──────────────────────────┘
             │
             │  run_expectations()
             ▼
  ┌───────────────────────┐
  │   VALIDATE            │  • 8 bài kiểm tra tự động
  │   (expectations)      │  • severity: warn | halt
  │                       │  • FAIL + halt → PIPELINE_HALT
  └──────────┬────────────┘
             │  OK → tiếp tục
             │
             │  cmd_embed_internal()
             ▼
  ┌───────────────────────┐        ┌──────────────────────────┐
  │   EMBED               │        │  chroma_db/              │
  │   ChromaDB upsert     │──────▶ │  collection: day10_kb    │
  │   theo chunk_id       │        │  (upsert + prune)        │
  └──────────┬────────────┘        └──────────────────────────┘
             │
             │  check_manifest_freshness()
             ▼
  ┌───────────────────────┐        ┌──────────────────────────┐
  │   MANIFEST + FRESHNESS│        │  artifacts/manifests/    │
  │   PASS / WARN / FAIL  │──────▶ │  manifest_<run_id>.json  │◀─ [điểm đo freshness]
  └───────────────────────┘        └──────────────────────────┘
             │
             ▼
  ┌───────────────────────┐
  │   SERVING             │  • ChromaDB day10_kb phục vụ
  │   (Day 08/09 RAG)     │    retrieval cho agent Day 09
  └───────────────────────┘

  [run_id ghi trong log đầu tiên và trong manifest — dùng để trace artifact]
```

---

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | File chính |
|------------|-------|--------|------------|
| **Ingest** | `data/raw/policy_export_dirty.csv` | Danh sách rows trong bộ nhớ | `etl_pipeline.py` → `load_raw_csv()` |
| **Transform / Clean** | Rows thô | cleaned rows + quarantine rows | `transform/cleaning_rules.py` → `clean_rows()` |
| **Quality / Validate** | cleaned rows | Pass/Fail mỗi expectation, cờ `halt` | `quality/expectations.py` → `run_expectations()` |
| **Embed** | `cleaned_<run_id>.csv` | Vectors trong ChromaDB collection | `etl_pipeline.py` → `cmd_embed_internal()` |
| **Monitor** | `manifest_<run_id>.json` | PASS / WARN / FAIL + `age_hours` | `monitoring/freshness_check.py` |

---

## 3. Idempotency & rerun

Pipeline có thể chạy lại nhiều lần mà không gây ra vector trùng nhờ 2 cơ chế:

1. **Upsert theo `chunk_id`:** mỗi chunk có ID ổn định được tạo từ `sha256(doc_id | chunk_text | seq)`. ChromaDB nhận lệnh `upsert` — nếu ID đã tồn tại thì ghi đè, không tạo thêm bản mới.

2. **Prune ID cũ:** trước khi upsert, pipeline lấy toàn bộ ID đang có trong collection và xóa các ID không còn xuất hiện trong bản cleaned lần này (`embed_prune_removed`). Điều này đảm bảo vector cũ không còn "nằm lại" gây nhiễu retrieval.

**Kết quả:** chạy `python etl_pipeline.py run` 2 lần liên tiếp với cùng dữ liệu → collection không phình, số vector không đổi.

---

## 4. Liên hệ Day 09

- Pipeline Day 10 và agent Day 09 **dùng chung thư mục `data/docs/`** làm nguồn tài liệu gốc.
- ChromaDB collection `day10_kb` là nơi pipeline Day 10 ghi dữ liệu đã clean. Agent Day 09 có thể trỏ vào cùng collection này để truy vấn.
- Khi pipeline Day 10 publish một bản cleaned mới (upsert + prune), agent Day 09 **tự động đọc dữ liệu cập nhật** mà không cần restart — đây là lợi ích của việc dùng persistent vector store.

---

## 5. Rủi ro đã biết

- **Freshness FAIL thường xuyên:** CSV mẫu có `exported_at` cũ, tự nhiên vượt SLA 24h. Cần cập nhật `exported_at` hoặc điều chỉnh `FRESHNESS_SLA_HOURS` trong `.env`.
- **Quarantine nhiều → cleaned ít:** nếu bộ dữ liệu nguồn có nhiều lỗi, `cleaned_records` giảm mạnh → expectation `min_one_row` có thể FAIL.
- **Rule A chặn inject Sprint 3:** Rule `internal_migration_note` quarantine row 3 trước khi fix refund được áp dụng, khiến kịch bản `--no-refund-fix` không thấy sự thay đổi ở `q_refund_window`. Cần thêm dòng inject riêng không có migration marker.
- **Model SentenceTransformers cần mạng lần đầu:** `all-MiniLM-L6-v2` (~90MB) tải về khi chạy lần đầu.
