# Báo cáo cá nhân — Lab Day 10

**Họ tên:** Trần Tiến Dũng
**Vai trò:** Embed & Idempotency Owner (Sprint 2 — embed layer)
**Ngày nộp:** 16/04/2026

---

## 1. Phần phụ trách cụ thể

| File | Nội dung |
|------|----------|
| `etl_pipeline.py` | Thêm logging idempotency: `embed_collection_before`, `embed_collection_after`, `embed_idempotent`; nâng default top-k lên 5 |
| `eval_retrieval.py` | Thêm `--scenario` flag (cột scenario trong CSV output), `--collection-info` flag (in vector count trước query), default top-k=5, summary pass/fail cuối run |

---

## 2. Idempotency — cơ chế và bằng chứng

### Cơ chế

Pipeline embed dùng ChromaDB `upsert` theo `chunk_id` (hash ổn định từ `doc_id|chunk_text|seq`). Khi rerun cùng data, `upsert` ghi đè đúng document cũ thay vì tạo bản duplicate.

Ngoài upsert, pipeline còn có bước **prune**: sau khi upsert, tập `chunk_id` hiện tại được so sánh với toàn bộ ID trong collection. ID nào có trong collection nhưng không có trong batch hiện tại -> `delete` (chunk stale từ run trước).

### Bằng chứng trong log

```
embed_collection_before=7
embed_collection_after=7 (expected=7)
embed_idempotent=true (rerun không làm tăng collection size)
```

Chạy pipeline 2 lần liên tiếp: `embed_collection_before` và `embed_collection_after` đều = 7 → rerun không tạo thêm vector.

### Ứng dụng với inject scenario

Khi inject bad run (`van-inject-bad`) đưa chunk "14 ngày làm việc" vào collection, pipeline restore (`van-restored`) prune chunk stale đó:

```
embed_prune_removed=1
```

Đây là bằng chứng idempotency kết hợp với correctness: không chỉ "không tăng count" mà còn "xóa sạch dữ liệu cũ sai".

---

## 3. Cải tiến `eval_retrieval.py`

### `--scenario` flag

Thêm cột `scenario` vào CSV output để tag từng lần chạy eval:

```bash
python eval_retrieval.py --scenario after_fix --out artifacts/eval/eval_after_fix.csv
python eval_retrieval.py --scenario after_inject --out artifacts/eval/eval_after_inject.csv
```

Backwards compatible: nếu không truyền `--scenario`, cột `scenario` bị bỏ khỏi CSV (dùng `extrasaction="ignore"` trong DictWriter).

### `--collection-info` flag

In số vector trong collection trước khi query:

```
collection=day10_kb vector_count=7
```

Cho phép verify nhanh rằng embed đã chạy và collection có đủ data trước khi đọc eval result.

### Summary pass/fail

Sau mỗi lần chạy in:

```
Summary: 4/4 pass (contains_expected=yes AND hits_forbidden=no), 0 fail
```

Nếu có FAIL, in thêm chi tiết từng câu — giúp debug nhanh hơn khi chạy inject scenario.

---

## 4. Before / after retrieval eval

| Scenario | Pass/Total | Ghi chú |
|----------|------------|---------|
| `before_fix` | 4/4 | Baseline — pipeline sạch |
| `after_inject` | 3/4 | `q_refund_window` FAIL — `hits_forbidden=yes` (chunk "14 ngày" trong top-k) |
| `after_fix` | 4/4 | Restore — prune xóa chunk stale |

---

## 5. Cải tiến nếu có thêm 2 giờ

Thêm time-series logging cho `embed_collection_before/after` vào manifest: lưu lịch sử collection size theo `run_id` để có thể vẽ trend và phát hiện leak (collection tăng dần theo thời gian dù data không đổi).