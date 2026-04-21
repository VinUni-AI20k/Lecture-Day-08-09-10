# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** cập nhật theo nhóm  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| 2A202600312 Trần Thanh Phong | Ingestion / Raw Owner | tranthanhphong66234@gmail.com |
| 2A202600064 Hoàng Đinh Duy Anh | Cleaning & Quality Owner | dduyanhhoang@gmail.com |
| 2A202600486 Nguyễn Tiến Huy Hoàng | Embed & Idempotency Owner | hoang.nth17@gmail.com |
| 2A202600497 Trần Nhật Vĩ | Monitoring / Docs Owner | vitrannhat@gmail.com |

**Ngày nộp:** 2026-04-15  
**Repo:** cập nhật link repo nhóm  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

**Tóm tắt luồng:**

Nhóm dùng nguồn raw `data/raw/policy_export_dirty.csv` làm input cho toàn bộ pipeline Day10.  
Luồng chuẩn gồm 5 bước: ingest (đọc CSV) -> clean/quarantine (`transform/cleaning_rules.py`) -> validate (`quality/expectations.py`) -> embed + prune Chroma -> ghi manifest và chạy freshness check.

Ở run clean `run_id=2026-04-15T09-45Z`, pipeline ghi `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`.  
Kết quả expectation pass toàn bộ 8 checks, trong đó các check quan trọng là:
- `refund_no_stale_14d_window` (halt),
- `hr_leave_no_stale_10d_annual` (halt),
- `all_doc_ids_in_allowlist` (halt).

`run_id` và các metric trên được ghi đồng thời trong log console và `artifacts/manifests/manifest_<run_id>.json`, giúp truy vết artifact theo từng lần chạy.  
Thiết kế này giúp nhóm kiểm tra được boundary giữa clean và publish, đồng thời phát hiện nhanh trường hợp data stale hoặc policy conflict trước khi feed xuống tầng serving (Day08/Day09).

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

`python etl_pipeline.py run && python eval_retrieval.py --out artifacts/eval/before_after_eval.csv`

---

## 2. Cleaning & expectation (150–200 từ)

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| Rule7 sanitize BOM/control chars | Chunk có thể mang BOM/ký tự control gây nhiễu embed | Text được sanitize trước embed, không sinh thêm noise chunk | `transform/cleaning_rules.py`, cleaned CSV |
| Rule8 quarantine short chunk (<8) | Row stub kiểu `N/A` có thể đi qua clean | Stub bị chặn với reason `chunk_text_too_short_after_strip` | `transform/cleaning_rules.py`, quarantine CSV |
| Rule9 parse `YYYY/MM/DD` | Dòng dạng year-first slash bị quarantine sai | Date được normalize sang ISO và giữ lại cho clean | `_normalize_effective_date()` trong code |
| E7 `chunk_max_length_2000` (warn) | Không có cảnh báo chunk quá dài | Có cảnh báo sớm parse/merge lỗi nhưng không dừng pipeline | `quality/expectations.py` |
| E8 `all_doc_ids_in_allowlist` (halt) | Chỉ dựa vào Rule1 ở transform | Có lớp phòng thủ thứ 2 ở validate | `quality/expectations.py` |

**Rule chính (baseline + mở rộng):**

- Baseline: allowlist `doc_id`, normalize `effective_date`, quarantine HR stale (<2026-01-01), dedupe, fix stale refund 14->7.
- Mở rộng: sanitize BOM/control chars, chặn short chunk sau strip, nhận thêm format `YYYY/MM/DD`.
- Rule refund vẫn giữ ở đường clean để đảm bảo policy canonical là "7 ngày làm việc".

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Run inject (`run_id=inject-bad`) dùng `--no-refund-fix --skip-validate` làm E3 fail:
`refund_no_stale_14d_window: FAIL (violations=1)`.  
Do có `--skip-validate`, pipeline vẫn publish để tạo evidence "bad snapshot".  
Sau đó rerun clean (không flags) để E3 pass và loại chunk stale khỏi index (`embed_prune_removed=1`).

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject:**

Nhóm chủ đích inject lỗi bằng lệnh:
`python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`.

Mục tiêu:
- Bỏ Rule refund fix để chunk "14 ngày làm việc" đi vào cleaned.
- Bỏ halt validation để pipeline vẫn embed dữ liệu lỗi.
- Quan sát tác động ở retrieval thay vì dừng tại validation.

**Kết quả định lượng (từ CSV / bảng):**

Theo `artifacts/eval/after_inject_bad.csv`, câu `q_refund_window` có:
- `contains_expected=yes`
- `hits_forbidden=yes`

Nghĩa là dù context có chunk đúng ("7 ngày"), top-k vẫn chứa chunk stale "14 ngày", tạo mâu thuẫn cho answer layer.

Sau khi chạy lại pipeline clean (`run_id=2026-04-15T09-45Z`), file `artifacts/eval/before_after_eval.csv` cho thấy:
- `q_refund_window`: `contains_expected=yes`, `hits_forbidden=no`
- `q_leave_version`: vẫn `contains_expected=yes`, `top1_doc_expected=yes` (Rule HR stale hoạt động ổn định).

Kết luận: pipeline clean đã loại được stale chunk trên toàn top-k context, không chỉ tối ưu top-1.

---

## 4. Freshness & monitoring (100–150 từ)

Nhóm đặt SLA mặc định `24h` và chạy check qua `python etl_pipeline.py freshness --manifest ...`.  
Với dataset mẫu, cả run inject và run clean đều trả `freshness_check=FAIL` vì `latest_exported_at=2026-04-10T08:00:00`, chạy vào 2026-04-15 nên `age_hours ~121.7`.

Diễn giải của nhóm:
- `PASS`: snapshot còn trong SLA, an toàn để publish.
- `WARN`: gần chạm SLA, cần theo dõi.
- `FAIL`: vượt SLA, cần cảnh báo "data stale" hoặc xác nhận đây là dataset demo.

Trong lab này, FAIL là hành vi đúng với dữ liệu cũ có chủ đích; trong production cần set SLA theo chu kỳ ingest thực tế (ví dụ daily/weekly).

_________________

---

## 5. Liên hệ Day 09 (50–100 từ)

Dữ liệu Day10 có thể phục vụ trực tiếp Day09 vì cùng domain CS + IT Helpdesk.  
Điểm giá trị nhất là Day10 thêm lớp observability (`run_id`, manifest, quality report), nên khi Day09 trả sai có thể truy nguyên nhanh do stale version hay do routing/synthesis.  
Nhóm giữ collection riêng `day10_kb` để tách vòng đời test Day10 với Day09, rồi sync sang Day09 collection khi cần demo orchestration.

_________________

---

## 6. Rủi ro còn lại & việc chưa làm

- Đã tạo `artifacts/eval/grading_run.jsonl` (3 dòng `gq_d10_01..03`) và qua `instructor_quick_check.py`; cần giữ đồng bộ artifact này với lần pipeline clean cuối trước khi nộp.
- Freshness hiện đo 1 boundary; chưa có dual-boundary ingest + publish.
- Chưa thêm LLM-judge cho quality eval (hiện dùng retrieval/keyword signals).
