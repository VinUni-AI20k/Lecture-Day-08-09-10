# Báo cáo cá nhân - Tuấn

**Họ và tên:** Tuấn  
**Vai trò:** Embed Owner  
**Ngày nộp:** 2026-04-15

## 1. Tôi phụ trách phần nào?

Tôi phụ trách lớp embed trong `etl_pipeline.py` (`cmd_embed_internal`) và phần đánh giá retrieval (`eval_retrieval.py`, `grading_run.py`) để chứng minh dữ liệu sạch thực sự cải thiện kết quả truy xuất.  
Trách nhiệm chính:
- Bảo đảm upsert theo `chunk_id`.
- Bảo đảm stale vector bị prune khi cleaned snapshot thay đổi.
- Sinh artifact eval và grading JSONL để nộp.

Tôi phối hợp với Cao để thống nhất quy tắc tạo `chunk_id` ổn định từ cleaned content. Tôi phối hợp với Ly để đưa chỉ số eval quan trọng vào quality report (`contains_expected`, `hits_forbidden`, `top1_doc_expected`).

## 2. Một quyết định kỹ thuật

Quyết định quan trọng của tôi là giữ mô hình idempotent theo snapshot publish:
1) lấy toàn bộ ids hiện có từ collection,  
2) tính tập id thừa so với cleaned hiện tại,  
3) delete id thừa trước khi upsert.

Cách này tránh hiện tượng "retrieval trả lời có vẻ đúng nhưng top-k vẫn chứa chunk stale". Đó là lỗi đặc trưng data observability mà lab yêu cầu bắt.  
Tôi cũng chỉnh `eval_retrieval.py` để xử lý an toàn trường hợp Chroma trả về `None` trong docs, tránh fail runtime khi join text.

## 3. Một lỗi/anomaly đã xử lý

Lỗi tôi xử lý là prune không luôn ổn định khi query ids cũ với tham số `include=[]` ở một số trạng thái collection. Hệ quả là stale vectors có thể không bị xóa triệt để trong một số lần rerun.  
Tôi đổi truy vấn sang `collection.get(include=["metadatas"], limit=100000)` để lấy ids chắc chắn hơn.  
Đồng thời ở evaluator, tôi thay join trực tiếp bằng `safe_docs = [d if isinstance(d, str) else ""]` để không vỡ nếu docs có phần tử `None`.

Nhờ đó:
- Pipeline không gãy ở bước eval.
- Artifact `before_after_eval.csv` và `grading_run.jsonl` được tạo ổn định.

## 4. Bằng chứng trước/sau

Bằng chứng inject (`sprint3-inject`):
- `after_inject_bad.csv`: `q_refund_window` có `hits_forbidden=yes`; `q_leave_version` thất bại (`contains_expected=no`).

Bằng chứng clean (`sprint4-final`):
- `before_after_eval.csv`: tất cả câu chính có `contains_expected=yes` và `hits_forbidden=no`; `q_leave_version` có `top1_doc_expected=yes`.
- `grading_run.jsonl`:  
  - `gq_d10_01`: pass (`contains_expected=true`, `hits_forbidden=false`)  
  - `gq_d10_02`: pass (`contains_expected=true`)  
  - `gq_d10_03`: pass đủ 3 điều kiện, gồm `top1_doc_matches=true`.

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ mở rộng evaluator thành 2 chế độ:
- `strict-topk` (hiện tại),
- `slice-eval` theo nhóm câu hỏi (refund/hr/security) với thống kê pass rate theo slice.

Việc này giúp theo dõi regression theo miền nghiệp vụ nhanh hơn khi pipeline thay đổi rule.
