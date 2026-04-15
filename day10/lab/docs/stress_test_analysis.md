# Kế hoạch Stress Test Nâng cao - Lab Day 10 (Adversarial Level)

**Người phụ trách:** Quang (Transformation Engineer)
**Chiến lược:** Kiểm tra khả năng xử lý xung đột logic, bảo mật thông tin nhạy cảm và tính nhất quán của Vector DB.

---

## 1. Danh sách các kịch bản đối kháng (Adversarial Scenarios)

| ID | Kịch bản | Thách thức kỹ thuật | Kỳ vọng xử lý |
|:---|:---|:---|:---|
| **st_adv_01** | **Xung đột Version (Lỗi logic)** | Ghi 14 ngày (v4 chuẩn 7 ngày). | Rule `fix_stale_refund` phải ép về 7 ngày. |
| **st_adv_02** | **Xung đột Version (Thời gian)** | Dòng đúng nhưng `exported_at` cũ hơn. | Hệ thống phải giữ dòng đúng dựa trên logic "Correctness over Recency". |
| **st_adv_03** | **Rò rỉ PII (Bảo mật)** | Chứa SĐT và Email thật. | Rule `mask_pii` phải thay thế bằng `[REDACTED]`. |
| **st_adv_04** | **Phá vỡ Tokenizer** | Tab, Newline, Zero-width space. | Rule `clean_whitespace` đưa về khoảng trắng đơn. |
| **st_adv_05** | **Sai Case-sensitivity** | `policy_refund_V4` (viết hoa V). | Chuẩn hóa `lower()` hoặc đẩy vào Quarantine. |
| **st_adv_06** | **Nhiễu Emoji** | Quá nhiều emoji gây nhiễu vector. | Rule `remove_emoji` dọn dẹp sạch văn bản. |
| **st_adv_07** | **Dữ liệu chuẩn (Base)** | Dòng dữ liệu đúng để test duplicate. | Nạp vào bình thường. |
| **st_adv_08** | **Duplicate Tuyệt đối** | Trùng 100% với dòng `st_adv_07`. | Cơ chế Idempotency loại bỏ dòng này. |
| **st_adv_09** | **Giá trị Logic âm** | SLA ghi nhận `-1` giờ. | Đẩy vào Quarantine (lỗi `invalid_range`). |
| **st_adv_10** | **Doc_ID lạ** | `unknown_doc` không có trong contract. | Đẩy vào Quarantine (lỗi `unknown_doc_id`). |

---

## 2. Quy trình thực thi & Kiểm chứng (Execution & Assertions)

### Giai đoạn 1: Kiểm soát biên (Boundary Guard)
**Lệnh chạy:**
```bash
python etl_pipeline.py run --raw data/raw/policy_stress_test.csv --run-id adv-stress
```
**Tiêu chí đạt (Assertions):**
*   **PII Check:** Mở `cleaned_adv-stress.csv`, tìm chuỗi `090-123`. Kỳ vọng: **Không tìm thấy** (đã bị redacted).
*   **Whitespace Check:** Mở `cleaned_adv-stress.csv`, kiểm tra dòng `st_adv_04`. Kỳ vọng: Không còn Tab/Newline thừa.
*   **Range Check:** Mở `quarantine_adv-stress.csv`. Kỳ vọng: Dòng `st_adv_09` nằm ở đây với lý do `invalid_logical_range`.

### Giai đoạn 2: Kiểm tra tính bất biến (Idempotency Assertions)
**Lệnh chạy lại:** Chạy lại đúng lệnh trên 2 lần.
**Tiêu chí đạt:**
*   `embed_prune_removed` trong Log phải khớp với số lượng dòng bị loại bỏ.
*   `chroma_db` collection count không được tăng thêm dù chỉ 1 bản ghi.

### Giai đoạn 3: Đánh giá chất lượng Retrieval (Eval Assertions)
**Lệnh chạy:**
```bash
python eval_retrieval.py --out artifacts/eval/eval_adv_stress.csv
```
**Tiêu chí đạt:**
*   Câu hỏi `q_refund_window`: `hits_forbidden` phải là **NO**.
*   Câu hỏi `q_lockout`: Kết quả tìm kiếm không bị nhiễu bởi Emojis (kiểm tra `top1_preview`).

---

## 3. Giá trị đối với Báo cáo Nhóm
Việc vượt qua bản test này chứng minh nhóm không chỉ làm sạch dữ liệu mà còn xây dựng được một **"Data Firewall"** (Tường lửa dữ liệu) thực thụ cho AI Agent. Kết quả này sẽ chiếm trọng số lớn trong mục **"Distinction Evidence"** của báo cáo.
