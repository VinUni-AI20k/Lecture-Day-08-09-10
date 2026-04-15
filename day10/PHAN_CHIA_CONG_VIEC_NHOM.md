# Kế hoạch thực hiện toàn diện - Lab Day 10 (4 Sprints)

Hệ thống xử lý dữ liệu tin cậy cho Agent với 7 thành viên.

## 1. Phân bổ nhân sự & Vai trò
- **Dũng (Lead)**: Tích hợp hệ thống & Orchestrator (Quản lý `etl_pipeline.py`).
- **Tuấn & Quang**: Team Transformation (Xử lý dữ liệu & Inject Corruption).
- **Hải & Long**: Team Quality & Observability (Kiểm soát & Giám sát).
- **Thuận**: Vector DB Specialist (ChromaDB, Idempotency & Pruning).
- **Huy**: Evaluation Lead (Chứng minh hiệu quả bằng con số).

---

## 2. Lộ trình thực hiện chi tiết

### Sprint 1: Ingest & Schema (0-60')
*Mục tiêu: Đọc được dữ liệu thô, định nghĩa Schema và bộ câu hỏi Golden.*

| Thành viên | Nhiệm vụ cụ thể | Sản phẩm |
|------------|-----------------|----------|
| **Dũng** | Thiết lập khung `etl_pipeline.py`, logic sinh `run_id` và cơ chế Logging. | Pipeline Skeleton |
| **Quang** | Mở rộng `policy_export_dirty.csv` với 5 dòng lỗi thô ban đầu. | Raw Data v1 |
| **Tuấn** | Viết hàm `load_raw_csv` và quy định Schema chuẩn cho Cleaned data. | Ingest logic |
| **Hải** | Khai báo Source Map (3 nguồn) trong `docs/data_contract.md`. | Source Map Draft |
| **Long** | Khởi tạo `data_contract.yaml` với các thông tin Owner và Metadata cơ bản. | Contract Base |
| **Thuận** | Setup `.env`, cấu trúc thư mục `chroma_db` và hàm kết nối collection. | DB Config |
| **Huy** | Soạn thảo bộ 3-4 câu hỏi Golden Retrieval trong `test_questions.json`. | Golden Set |

### Sprint 2: Clean + Validate + Embed (60-120')
*Mục tiêu: Xây dựng bộ lọc dữ liệu và nạp vào Vector DB không trùng lặp.*

| Thành viên | Nhiệm vụ nâng cao | Sản phẩm |
|------------|-------------------|----------|
| **Tuấn** | Viết ≥ 6 rules làm sạch trong `cleaning_rules.py` (ISO date, HR version...). | Cleaning Rules |
| **Quang** | Xử lý logic `Quarantine`: Đẩy record lỗi ra CSV riêng kèm lý do chi tiết. | Quarantine Logic |
| **Hải** | Thiết lập bộ `expectations.py` để chặn đứng dữ liệu bẩn (Halt/Warn). | Validation Suite |
| **Long** | Định nghĩa SLA Freshness và Alert Channel trong `data_contract.yaml`. | SLA Config |
| **Thuận** | Viết hàm `Upsert` (theo hash) và **Logic Prune** (xóa vector cũ). | Idempotent code |
| **Huy** | Xây dựng script `eval_retrieval.py` để sẵn sàng đo lường. | Eval Script |
| **Dũng** | Tích hợp toàn bộ code của Tuấn, Hải, Thuận vào luồng `run`. | Pipeline V1 |

### Sprint 3: Stress Test & Evidence (120-180')
*Mục tiêu: "Phá" dữ liệu để chứng minh khả năng phát hiện lỗi của hệ thống.*

| Thành viên | Nhiệm vụ cụ thể | Sản phẩm |
|------------|-----------------|----------|
| **Quang** | Tạo kịch bản "Inject Corruption" cực khó: Duplicate chéo, lỗi encoding. | Dirty Scenarios |
| **Tuấn** | Hỗ trợ Quang tạo file CSV "siêu bẩn" để stress test pipeline. | Stress Test CSV |
| **Huy** | Chạy Eval cho 2 kịch bản: Trước fix (bẩn) và Sau fix (sạch). | `before_after_eval.csv` |
| **Hải** | Chứng minh `expectation halt` dừng được pipeline khi dữ liệu bị "phá". | Quality Evidence |
| **Long** | Vẽ sơ đồ Mermaid vào `docs/pipeline_architecture.md`. | Architecture Diagram |
| **Thuận** | Kiểm tra Log để verify số lượng vector được Upsert/Prune. | Idempotency Logs |
| **Dũng** | Verify tính nhất quán của `run_id` xuyên suốt các artifacts. | Traceability |

### Sprint 4: Monitoring & Final Reports (180-240')
*Mục tiêu: Hoàn thiện giám sát và đóng gói báo cáo.*

| Thành viên | Nhiệm vụ cụ thể | Sản phẩm |
|------------|-----------------|----------|
| **Long** | Hoàn thiện `freshness_check.py` và viết `runbook.md`. | Monitor & Runbook |
| **Hải** | Hoàn thiện `quality_report.md` với các diễn giải về số liệu. | Quality Report |
| **Huy** | Phân tích sâu kết quả `hits_forbidden` và `top1_doc_expected`. | Performance Analyst |
| **Quang/Tuấn** | Hoàn thiện báo cáo cá nhân, tập trung vào phần Transformation. | Individual Reports |
| **Thuận** | Chạy thử pipeline lần cuối (Rerun test) để confirm 0% duplicate. | Final DB Proof |
| **Dũng** | Tổng hợp `group_report.md` và kiểm tra `requirements.txt`. | Final Package |

---

## 3. Định nghĩa "Xong" (DoD) cấp Distinction
1. **Dữ liệu**: `hits_forbidden=no` trên mọi câu hỏi Golden.
2. **Vận hành**: Rerun 3 lần, collection count không đổi (Idempotency).
3. **Giám sát**: `freshness_check` báo FAIL khi nạp file mẫu cũ.
4. **Tài liệu**: Có sơ đồ kiến trúc, runbook sự cố và báo cáo Before/After rõ ràng.

## 4. Cơ chế phối hợp
- Sub-team **Transformation** (Tuấn, Quang) cung cấp dữ liệu sạch cho **Thuận**.
- Sub-team **Quality** (Hải, Long) cung cấp luật chặn cho **Dũng**.
- **Huy** làm trọng tài đánh giá kết quả của toàn nhóm.
