# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Nhóm 11  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Lê Hoàng Long | Ingestion / Raw Owner (Lead) | 26ai.longlh@vinuni.edu.vn |
| Đỗ Văn Quyết| Ingestion / Raw Owner (Contract) | 26ai.quyetdv@vinuni.edu.vn |
| Hoàng Văn Kiên | Cleaning & Quality Owner (Rules) | 26ai.kienhv@vinuni.edu.vn |
| Lê Thị Phương | Cleaning & Quality Owner (Expectations) | 26ai.phuonglt@vinuni.edu.vn |
| Hà Hữu An | Embed & Idempotency Owner | 26ai.anhh@vinuni.edu.vn |
| Hồ Thị Tố Nhi | Monitoring / Docs Owner | 26ai.nhihtt@vinuni.edu.vn |

**Ngày nộp:** 2026-04-15  
**Repo:** VinUni-AI20k/Lecture-Day-08-09-10 (branch main, folder Nhom11-402-Day10)  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

Pipeline Day 10 xử lý raw export CSV (`data/raw/policy_export_dirty.csv`) qua 4 giai đoạn: **Ingest → Transform → Quality → Embed**. File CSV raw mô phỏng export từ hệ thống nguồn với 10 dòng, bao gồm nhiều loại lỗi: duplicate chunk, cửa sổ hoàn tiền sai (14 ngày thay vì 7 ngày), bản HR cũ năm 2025, doc_id ngoài allowlist, ngày hiệu lực sai format (dd/MM/yyyy), và marker "lỗi migration".

`etl_pipeline.py run` đọc CSV → gọi `clean_rows()` để produce (cleaned list, quarantine list) → chạy `run_expectations()` → nếu không halt thì embed vào ChromaDB (upsert theo `chunk_id`, prune vector cũ) → ghi manifest + freshness check.

`run_id` được sinh tự động theo UTC timestamp (hoặc truyền `--run-id`). Log được ghi song song ra stdout và `artifacts/logs/run_<run_id>.log`. Manifest JSON tại `artifacts/manifests/manifest_<run_id>.json` chứa đủ `raw_records`, `cleaned_records`, `quarantine_records`, `run_id`, `latest_exported_at`.

**Lệnh chạy pipeline chuẩn:**
```bash
python etl_pipeline.py run --run-id 2026-04-15T10-00Z
```

**run_id** trong manifest: `2026-04-15T10-00Z`  
**Artifact:** `artifacts/manifests/manifest_2026-04-15T10-00Z.json`

---

## 2. Cleaning & expectation (150–200 từ)

Baseline đã có 6 rule (allowlist doc_id, parse ngày ISO, HR stale date, empty text, deduplicate, fix refund). Nhóm bổ sung **3 rule mới** và **2 expectation mới**:

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `quarantine_migration_error_marker` (Rule 7) | cleaned=6, quarantine=4 (baseline) | cleaned=5, quarantine=5 | `artifacts/manifests/manifest_2026-04-15T10-00Z.json`; row 3 CSV → quarantine với `reason=migration_error_marker_detected` |
| `quarantine_stale_sla_effective_date` (Rule 4) | không ảnh hưởng bộ mẫu | quarantine+1 khi inject sla_p1_2026 với date=2025-06-01 | Inject row `sla_p1_2026,2025-06-01,...` → quarantine `reason=stale_sla_effective_date` |
| `normalize_whitespace_in_chunk_text` (Rule 5) | dedup hoạt động đúng với text chuẩn | Khi inject text có "  extra   space  " duplicate sẽ bị bắt | Inject 2 rows có text khác nhau chỉ về whitespace → `duplicate_chunk_text` |
| E7 `no_migration_error_marker_in_cleaned` | N/A pipeline chuẩn | FAIL khi chạy `--no-refund-fix --skip-validate` + inject row "lỗi migration" | Log: `expectation[no_migration_error_marker_in_cleaned] FAIL (halt)` khi inject |
| E8 `sla_doc_effective_date_min_2026` | PASS bộ mẫu | WARN khi inject sla_p1_2026 date<2026 + `--skip-validate` | Log: `expectation[sla_doc_effective_date_min_2026] FAIL (warn)` |

**Rule chính (baseline + mở rộng):**

- **R1** allowlist doc_id → quarantine `unknown_doc_id` (row 9 trong sample)
- **R2** parse effective_date → normalize dd/MM/yyyy → YYYY-MM-DD (row 10)
- **R3** HR stale date < 2026-01-01 → quarantine (row 7)
- **R4 (new)** SLA stale date < 2026-01-01 → quarantine
- **R5 (new)** normalize whitespace trong chunk_text
- **R6** empty chunk_text → quarantine (row 5)
- **R7 (new)** "lỗi migration" marker → quarantine (row 3; thay vì fix như baseline)
- **R8** deduplicate theo norm_text (row 2)
- **R9** fix refund 14→7 ngày (áp dụng khi `apply_refund_window_fix=True`)

**Ví dụ expectation fail và cách xử lý:**

Khi chạy `--no-refund-fix --skip-validate`, expectation E3 (`refund_no_stale_14d_window`) FAIL halt vì chunk với "14 ngày làm việc" lọt vào cleaned. Pipeline log: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`. Xử lý: rerun pipeline chuẩn (không flag) → R9 fix text hoặc R7 quarantine row lỗi migration → E3 PASS.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject (Sprint 3):**

Chạy lệnh inject: `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`

Điều này để chunk "Yêu cầu hoàn tiền được chấp nhận trong vòng **14 ngày làm việc**..." (row 3) vào ChromaDB mà KHÔNG bị fix thành 7 ngày. Ngoài ra row 7 (HR 2025 "10 ngày phép") bị quarantine bởi rule HR stale date — đây là rule baseline nên bản HR cũ không lọt qua. Tuy nhiên chunk "lỗi migration" với 14 ngày vẫn được embed.

Sau inject, chạy `python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv`.

**Kết quả định lượng (từ CSV):**

| question_id | Inject-bad | Pipeline chuẩn | Thay đổi |
|-------------|-----------|----------------|----------|
| q_refund_window | `contains_expected=no`, `hits_forbidden=yes` | `contains_expected=yes`, `hits_forbidden=no` | Chunk 14 ngày bị loại → 7 ngày duy nhất còn lại |
| q_leave_version | `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes` | `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes` | Không thay đổi (HR cũ đã bị quarantine bởi stale date rule cả 2 trường hợp) |
| q_p1_sla | `contains_expected=yes` | `contains_expected=yes` | Ổn định |
| q_lockout | `contains_expected=yes` | `contains_expected=yes` | Ổn định |

Sau khi rerun pipeline chuẩn, `python etl_pipeline.py run --run-id 2026-04-15T10-00Z`, embed prune xoá vector cũ (`embed_prune_removed=1`), và eval trở về tất cả PASS.

**File eval:**
- Before/inject: `artifacts/eval/after_inject_bad.csv`
- After/clean: `artifacts/eval/before_after_eval.csv`

---

## 4. Freshness & monitoring (100–150 từ)

SLA chọn **24 giờ** phù hợp chu kỳ batch hàng ngày (export từ Policy DB). Ý nghĩa:

- **PASS** (`age_hours ≤ 24`): dữ liệu mới nhất đã được ingest và publish trong ngày — agent có thể tin tưởng corpus.
- **WARN**: hiện tại module chỉ có PASS/FAIL; có thể mở rộng thêm WARN (ví dụ: 12h ≤ age < 24h) để alert sớm trước khi vi phạm SLA.
- **FAIL** (`age_hours > 24`): export đã cũ hơn 1 ngày → cần alert ngay để investigate source system.

Với bộ mẫu hiện tại (`latest_exported_at = 2026-04-10T08:00:00`, ngày lab = 2026-04-15): `age_hours ≈ 122h` → **FAIL** (dữ liệu mẫu cố ý cũ để demo kịch bản freshness fail). Trong production, source system sẽ cập nhật `exported_at` theo ngày chạy thực → freshness PASS.

Lệnh kiểm tra: `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_2026-04-15T10-00Z.json`

---

## 5. Liên hệ Day 09 (50–100 từ)

Pipeline Day 10 cung cấp corpus sạch hơn so với Day 08/09 vì dữ liệu đi qua cleaning pipeline trước khi embed. Collection ChromaDB `day10_kb` là bản "đã kiểm soát chất lượng" — không còn chunk HR 2025 sai version hay chunk refund 14 ngày. Agent Day 09 (multi-agent) có thể chuyển sang dùng collection này làm retrieval backend để đảm bảo các policy tool nhận đúng version. Hiện tại Day 08/09 vẫn dùng corpus riêng từ `data/docs/*.txt` — cần cấu hình `CHROMA_COLLECTION=day10_kb` để tích hợp.

---

## 6. Rủi ro còn lại & việc chưa làm

- `chunk_id` tính theo seq tương đối → không stable nếu source thay đổi thứ tự dòng giữa các batch.
- Freshness đo 1 boundary (publish); chưa đo boundary ingest → publish riêng.
- Chưa có LLM-judge eval — chỉ keyword-based, có thể bỏ sót edge case câu trả lời đúng nhưng diễn đạt khác.
- Rule versioning chưa đọc cutoff từ `data_contract.yaml` (hard-code `"2026-01-01"`) — Distinction criterion chưa đạt đầy đủ.
