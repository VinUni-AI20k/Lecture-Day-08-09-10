# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Phan Thanh Sang  
**Vai trò:** Ingestion & Schema Owner (Sprint 1)  
**Ngày nộp:** 2026-04-15

---

## Sprint 1 (60') — Ingest & schema

Trong Sprint 1, tôi tập trung vào 3 đầu việc chính: đọc dữ liệu raw, cập nhật source map ngắn trong tài liệu contract, và chạy pipeline với run_id riêng để tạo bằng chứng log.

### 1) Đọc dữ liệu raw

Tôi dùng nguồn chính là `data/raw/policy_export_dirty.csv` để mô phỏng export từ hệ nguồn. Bộ dữ liệu này có chủ đích chứa các tình huống lỗi vận hành thường gặp:
- duplicate chunk,
- thiếu ngày hiệu lực,
- doc_id lạ không thuộc catalog,
- xung đột version policy HR.

Việc đọc raw ở Sprint 1 giúp tôi xác nhận phạm vi lỗi đầu vào trước khi bàn sâu sang cleaning/expectations ở Sprint 2.

### 2) Điền source map trong docs/data_contract.md

Tôi đã hoàn thiện source map ngắn theo đúng yêu cầu "ít nhất 2 nguồn / failure mode / metric" trong `docs/data_contract.md` với 3 nguồn:
- CSV export policy,
- canonical docs,
- manifest publish.

Mỗi nguồn đều có failure mode và metric quan sát tương ứng. Ví dụ:
- CSV export policy theo dõi `raw_records`, `quarantine_records`, expectation fail count.
- Canonical docs theo dõi `unknown_doc_id` và `stale_hr_policy_effective_date`.
- Manifest publish theo dõi `freshness_check` PASS/WARN/FAIL.

Cách viết này giúp chuyển tài liệu từ mức mô tả chung sang mức có thể vận hành và điều tra incident.

### 3) Chạy Sprint 1 pipeline và lưu log

Lệnh đã chạy:

```bash
python etl_pipeline.py run --run-id sprint1
```

File log sinh ra: `artifacts/logs/run_sprint1.log`.

Các dòng bằng chứng DoD trong log:

```text
run_id=sprint1
raw_records=10
cleaned_records=6
quarantine_records=4
```

Ngoài các trường DoD bắt buộc, log còn cho thấy pipeline hoàn thành end-to-end:
- expectation halt đều pass,
- embed thành công (`embed_upsert count=6`),
- manifest được ghi (`manifest_sprint1.json`).

---

## Đánh giá kết quả Sprint 1

Sprint 1 đạt mục tiêu vì đã có đầy đủ chuỗi ingest + schema mapping + run evidence. Điểm quan trọng nhất tôi rút ra là: chỉ riêng việc có `run_id` và các chỉ số `raw/cleaned/quarantine` đã tạo được nền observability rất rõ cho các sprint sau. Khi có sai lệch retrieval, nhóm có thể truy ngược theo run cụ thể thay vì tranh luận cảm tính.

Tôi cũng ghi nhận freshness đang FAIL trên dữ liệu mẫu do timestamp export cũ. Đây là tình huống hợp lệ theo thiết kế bài lab để luyện triage dữ liệu stale, không phải lỗi chạy pipeline.

---

## Kế hoạch nối Sprint 2

Trong 60 phút tiếp theo, tôi sẽ giữ vai trò phối hợp với Cleaning/Quality Owner để:
- bổ sung rule có tác động đo được (tránh trivial),
- giữ rõ ranh giới warn vs halt,
- đảm bảo idempotent khi rerun nhiều lần.
