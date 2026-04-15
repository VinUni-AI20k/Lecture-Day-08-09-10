# Quality report — Lab Day 10 (nhóm)

**run_id (clean):** 2026-04-15T09-45Z
**run_id (inject):** inject-bad
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | inject-bad | clean (2026-04-15T09-45Z) | Ghi chú |
|---|---|---|---|
| raw_records | 10 | 10 | Cùng nguồn CSV |
| cleaned_records | 6 | 6 | Số lượng không đổi — inject chỉ thay đổi nội dung chunk, không số lượng |
| quarantine_records | 4 | 4 | Cùng quarantine — Rules 1–4 không bị ảnh hưởng bởi --no-refund-fix |
| Expectation suite (halt condition) | Halt condition triggered, but skipped — E3 FAIL (`refund_no_stale_14d_window`, violations=1); pipeline tiếp tục do `--skip-validate` | NO — tất cả 8 expectations OK | --skip-validate cho phép pipeline tiếp tục dù có lỗi expectation |
| embed_prune_removed | 1 (clean→stale) | 1 (stale→clean) | Idempotency hoạt động đúng: mỗi run thay thế chunk cũ bằng chunk mới |

---

## 2. Before / after retrieval (bắt buộc)

File tham chiếu:
- Before (dirty): `artifacts/eval/after_inject_bad.csv`
- After (clean): `artifacts/eval/before_after_eval.csv`

### Câu hỏi then chốt: refund window (`q_refund_window`)

**Trước (inject-bad):**
```
q_refund_window, contains_expected=yes, hits_forbidden=yes, top_k=3
top1_preview: "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."
```
Mặc dù top-1 là chunk đúng ("7 ngày"), nhưng chunk stale "14 ngày làm việc" vẫn xuất hiện trong top-3 context. LLM nhận cả hai version mâu thuẫn — kết quả không đoán được.

**Sau (clean):**
```
q_refund_window, contains_expected=yes, hits_forbidden=no, top_k=3
top1_preview: "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."
```
Chunk stale đã bị prune (`embed_prune_removed=1`). Chỉ còn version đúng trong toàn bộ top-3.

### Merit: versioning HR — `q_leave_version`

**Trước (inject-bad):**
```
q_leave_version, contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes
```
**Sau (clean):**
```
q_leave_version, contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes
```
Bản HR cũ ("10 ngày phép năm", effective_date=2025-01-01) đã bị quarantine bởi Rule 3 từ Sprint 1 — không bao giờ vào vector store. Merit condition met ở cả hai scenario.

---

## 3. Freshness & monitor

`freshness_check=FAIL` trên cả hai run:
```json
{"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 121.7, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Giải thích:** CSV mẫu có `exported_at=2026-04-10T08:00:00`, chạy vào 2026-04-15 → age ~121 giờ, vượt SLA 24h.
FAIL là **hành vi đúng** cho data mẫu — trong thực tế, SLA sẽ được đặt phù hợp với chu kỳ ingest (ví dụ `FRESHNESS_SLA_HOURS=168` cho weekly batch), hoặc `exported_at` sẽ là timestamp thực của lần export mới nhất.

---

## 4. Corruption inject (Sprint 3)

**Kịch bản:** chạy pipeline với `--no-refund-fix --skip-validate`.

- `--no-refund-fix`: bỏ qua Rule 6, để chunk "14 ngày làm việc" (từ row 3 của CSV — ghi chú "bản sync cũ policy-v3 — lỗi migration") đi thẳng vào ChromaDB.
- `--skip-validate`: bỏ qua halt khi E3 (`refund_no_stale_14d_window`) fail, cho phép pipeline embed dữ liệu lỗi có chủ đích.
- `embed_prune_removed=1`: chunk sạch từ run trước bị prune, chunk stale chiếm chỗ.

**Hậu quả đo được:** `q_refund_window` chuyển từ `hits_forbidden=no` → `hits_forbidden=yes`. Cả hai version (7 ngày và 14 ngày) xuất hiện đồng thời trong top-3 context — mâu thuẫn trực tiếp.

**Fix:** chạy lại `etl_pipeline.py run` (không có flags) → Rule 6 fix chunk, E3 pass, `embed_prune_removed=1` loại chunk stale, `hits_forbidden` trở về `no`.

---

## 5. Hạn chế & việc chưa làm

- Eval hiện tại chỉ dùng keyword match — không đo actual LLM answer quality (chỉ cần `hits_forbidden=yes` để biết context bị nhiễm).
- `freshness_check` chỉ đo ở 1 boundary (publish). Dual-boundary (ingest + publish) chưa implement.
- Bộ câu hỏi test nhỏ (4 câu) — mở rộng thêm slice test cho các policy khác nếu có thêm thời gian.
