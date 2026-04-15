# Báo cáo cá nhân — Lab Day 10

**Họ tên:** Ngô Hải Văn
**Vai trò:** Inject & Evidence Owner (Sprint 3)
**run_id tham chiếu:** van-clean-1 · van-inject-bad · van-restored

---

## 1. Phần phụ trách cụ thể

| File | Nội dung |
|------|----------|
| `etl_pipeline.py` | Fix curly quotes (38 ký tự `"` `"` → `"`) khiến SyntaxError; thêm unpack `clean_stats` từ `clean_rows()` để log `cleaning_bom_stripped` |
| `transform/cleaning_rules.py` | Thay đổi return type thành `Tuple[..., Dict[str, int]]` để trả về `stats = {"bom_stripped": N}` |
| `data/raw/policy_export_dirty.csv` | Fix ký tự `\ufe0f` (variation selector) → `\ufeff` (BOM thật) ở row 13 để Rule 9 của Khiêm trigger được |
| `docs/quality_report.md` | Viết mới từ template — 3 scenario, bảng before/after, giải thích freshness FAIL |
| `artifacts/eval/eval_before_inject.csv` | Eval baseline (scenario=before_fix, 4/4 pass) |
| `artifacts/eval/eval_after_inject.csv` | Eval sau inject (scenario=after_inject, 3/4 pass — q_refund_window hits_forbidden=yes) |
| `artifacts/eval/eval_after_fix.csv` | Eval sau restore (scenario=after_fix, 4/4 pass) |

---

## 2. Quyết định kỹ thuật: dùng `--skip-validate` có chủ đích

Khi inject corruption (`--no-refund-fix`), expectation E3 (`refund_no_stale_14d_window`) fail với severity `halt` — pipeline sẽ dừng trước bước embed. Để tạo được evidence "retrieval xấu sau inject", cần bypass halt bằng `--skip-validate`.

Quyết định: chấp nhận dùng `--skip-validate` **chỉ trong Sprint 3 demo** và ghi rõ trong manifest (`"skipped_validate": true`). Trong production, không bao giờ dùng flag này mà phải fix data trước khi embed. Log pipeline cũng in cảnh báo `WARN: expectation failed but --skip-validate` để phân biệt run demo với run chuẩn.

---

## 3. Sự cố / anomaly phát hiện

**Sự cố:** Row 13 trong `policy_export_dirty.csv` được Khiêm thêm để test Rule 9 (BOM strip), nhưng ký tự đầu là `\ufe0f` (Unicode Variation Selector-16, hex `0xFE0F`) thay vì `\ufeff` (BOM thật, hex `0xFEFF`). Hai ký tự chỉ khác nhau 1 bit nhưng có nghĩa hoàn toàn khác.

**Phát hiện:** Chạy `python3 -c "print(hex(ord(text[0])))"` trên nội dung row 13 → `0xfe0f`, không phải `0xfeff`. `bom_count` luôn = 0 dù pipeline chạy xong.

**Fix:** Thay `\ufe0f` → `\ufeff` bằng Python script. Sau fix: `cleaning_bom_stripped=1` xuất hiện trong log của mọi run.

---

## 4. Before / after (trích log và CSV)

**Before inject** (`run_id=van-clean-1`):
```
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
```
`q_refund_window`: `contains_expected=yes`, `hits_forbidden=no`

**After inject** (`run_id=van-inject-bad`):
```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed
```
`q_refund_window`: `contains_expected=yes`, `hits_forbidden=yes` ← chunk "14 ngày làm việc" xuất hiện trong top-5

**After fix** (`run_id=van-restored`):
```
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
embed_prune_removed=1
```
`q_refund_window`: `contains_expected=yes`, `hits_forbidden=no` ← restored

---

## 5. Cải tiến nếu có thêm 2 giờ

Thêm inject riêng cho HR version: đưa lại chunk "10 ngày phép năm" vào CSV với `effective_date=2026-02-01` (bỏ qua Rule 3 cutoff bằng cách sửa date check) để `q_leave_version` cũng có evidence `hits_forbidden=yes` → tăng bộ chứng cứ cho Merit criterion `gq_d10_03`.
