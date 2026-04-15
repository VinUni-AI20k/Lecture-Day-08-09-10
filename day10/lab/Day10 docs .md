Bạn nói đúng — phần trước mình mới mô tả chi tiết 2 vai trò mà chưa hoàn thiện đầy đủ cho **nhóm 5 người**. Dưới đây là phương án phân chia **đầy đủ và tối ưu theo README và SCORING**, đảm bảo mỗi thành viên có trách nhiệm rõ ràng và đóng góp vào các tiêu chí chấm điểm.

---

## **✅ Tổng quan phân chia cho nhóm 5 người**

Dựa trên cấu trúc pipeline và rubric chấm điểm, nhóm nên được chia thành **5 vai trò chính**:

| Thành viên | Vai trò | Mục tiêu chính | Sprint chính |
| ----- | ----- | ----- | ----- |
| **Member 1** | ETL & Pipeline Owner | Đảm bảo pipeline chạy end-to-end | Sprint 1–4 |
| **Member 2** | Cleaning Rules Owner | Xây dựng và mở rộng các quy tắc làm sạch dữ liệu | Sprint 1–3 |
| **Member 3** | Expectations & Data Quality Owner | Xây dựng expectation suite và validation | Sprint 2–3 |
| **Member 4** | Embedding & Retrieval Evaluation Owner | Quản lý vector store và đánh giá before/after | Sprint 2–3 |
| **Member 5** | Monitoring, Documentation & Reporting Owner | Freshness, data contract, runbook và báo cáo | Sprint 4 |

Cách chia này bám sát các thành phần của lab: **ETL → Cleaning → Validation → Embed → Observability**, đồng thời đảm bảo tất cả các tiêu chí chấm điểm đều có người chịu trách nhiệm.

---

## **👤 Member 1 — ETL & Pipeline Owner**

### **🎯 Vai trò**

Chịu trách nhiệm vận hành toàn bộ pipeline và đảm bảo luồng **ingest → clean → validate → embed** hoạt động ổn định.

### **🛠️ Nhiệm vụ**

* Quản lý file `etl_pipeline.py`.  
* Thiết lập môi trường (`requirements.txt`, `.env`).  
* Đảm bảo pipeline chạy thành công với lệnh:

   python etl\_pipeline.py run

* Kiểm tra và ghi log:  
  * `run_id`  
  * `raw_records`  
  * `cleaned_records`  
  * `quarantine_records`  
* Tạo và kiểm tra `manifest.json`.  
* Tích hợp các phần do các thành viên khác phát triển.

  ### **📦 Deliverables**

* `etl_pipeline.py`  
* `artifacts/logs/*`  
* `artifacts/manifests/*`  
  ---

  ## **👤 Member 2 — Cleaning Rules Owner**

  ### **🎯 Vai trò**

Xây dựng và mở rộng các **cleaning rules** nhằm cải thiện chất lượng dữ liệu.

### **🛠️ Nhiệm vụ**

* Làm việc chính với `transform/cleaning_rules.py`.  
* Thêm **ít nhất 3 cleaning rules mới** (không trivial).  
* Đảm bảo các rule có **tác động đo được** như:  
  * Tăng `quarantine_records`  
  * Giảm duplicate  
  * Chuẩn hóa định dạng dữ liệu  
* Phối hợp với Member 4 để chứng minh hiệu quả qua retrieval.

  ### **📦 Deliverables**

* `transform/cleaning_rules.py`  
* Bảng `metric_impact` trong `reports/group_report.md`.

  ### **💡 Ví dụ rule**

* Chuẩn hóa định dạng ngày tháng.  
* Phát hiện và loại bỏ duplicate xung đột.  
* Quarantine các bản ghi thiếu `doc_id`.  
* Loại bỏ ký tự BOM hoặc khoảng trắng bất thường.  
  ---

  ## **👤 Member 3 — Expectations & Data Quality Owner**

  ### **🎯 Vai trò**

Đảm bảo chất lượng dữ liệu thông qua **expectation suite** và validation.

### **🛠️ Nhiệm vụ**

* Làm việc với `quality/expectations.py`.  
* Thêm **ít nhất 2 expectation mới** với mức độ `warn` và `halt`.  
* Kiểm tra pipeline dừng khi expectation fail.  
* Phối hợp với Member 2 để đảm bảo cleaning giúp expectation pass.

  ### **📦 Deliverables**

* `quality/expectations.py`  
* Minh chứng expectation pass/fail trong log.

  ### **💡 Ví dụ expectation**

* `doc_id` phải thuộc allowlist.  
* `effective_date` phải ở định dạng ISO.  
* Không tồn tại version policy xung đột.  
* `chunk_text` không được rỗng.  
  ---

  ## **👤 Member 4 — Embedding & Retrieval Evaluation Owner**

  ### **🎯 Vai trò**

Quản lý vector database và đánh giá hiệu quả retrieval trước và sau khi làm sạch dữ liệu.

### **🛠️ Nhiệm vụ**

* Quản lý embedding trong ChromaDB.  
* Đảm bảo **idempotent embedding** (upsert theo `chunk_id` và prune vector cũ).  
* Chạy và phân tích:

   python eval\_retrieval.py  
  python grading\_run.py

* Tạo **before/after evaluation** khi inject dữ liệu lỗi.  
* Đóng góp vào **quality report**.

  ### **📦 Deliverables**

* `artifacts/eval/before_after_eval.csv`  
* `artifacts/eval/grading_run.jsonl`

  ### **📊 Metrics đánh giá**

* `contains_expected`  
* `hits_forbidden`  
* `top1_doc_matches`  
  ---

  ## **👤 Member 5 — Monitoring, Documentation & Reporting Owner**

  ### **🎯 Vai trò**

Chịu trách nhiệm về **data observability**, tài liệu và báo cáo của nhóm.

### **🛠️ Nhiệm vụ**

* Thực hiện **freshness check**:

   python etl\_pipeline.py freshness \--manifest \<path\>

* Hoàn thiện các tài liệu:  
  * `docs/pipeline_architecture.md`  
  * `docs/data_contract.md`  
  * `docs/runbook.md`  
  * `docs/quality_report.md`  
* Tổng hợp `reports/group_report.md`.  
* Điều phối và kiểm tra `reports/individual/*.md`.  
* Đảm bảo tất cả deliverables được nộp đúng hạn.

  ### **📦 Deliverables**

* Tất cả tài liệu trong thư mục `docs/`  
* `reports/group_report.md`  
* `reports/individual/*.md`  
  ---

  ## **🔄 Sự phối hợp giữa các thành viên**

  Member 1 (ETL)  
         ↓  
  Member 2 (Cleaning) → Member 3 (Expectations)  
         ↓  
  Member 4 (Embedding & Evaluation)  
         ↓  
  Member 5 (Monitoring & Documentation)  
* **Member 2 & 3** cần phối hợp chặt chẽ để đảm bảo dữ liệu sạch và validation thành công.  
* **Member 4** sử dụng dữ liệu đã xử lý để đánh giá hiệu quả retrieval.  
* **Member 5** tổng hợp toàn bộ kết quả và hoàn thiện tài liệu.  
  ---

  ## **✅ Bảng tóm tắt Deliverables theo thành viên**

| Thành viên | File/Artifact chính |
| ----- | ----- |
| **M1** | `etl_pipeline.py`, logs, manifests |
| **M2** | `transform/cleaning_rules.py` |
| **M3** | `quality/expectations.py` |
| **M4** | `eval_retrieval.py`, `grading_run.jsonl` |
| **M5** | `docs/*.md`, `reports/*.md`, freshness |

1. 

