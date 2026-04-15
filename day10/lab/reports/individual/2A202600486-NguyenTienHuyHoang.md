# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Tiến Huy Hoàng  
**Vai trò:** Embed & Idempotency Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài:** ~510 từ

---

## 1. Tôi phụ trách phần nào?

Trong Day10 tôi phụ trách tầng publish sang vector store: embed cleaned data vào ChromaDB, đảm bảo idempotency khi rerun, và xác nhận không còn vector stale sau mỗi lần cập nhật snapshot.

Phần việc chính của tôi nằm trong `etl_pipeline.py` ở bước tạo embedding, upsert theo `chunk_id`, và prune những ID không còn tồn tại trong cleaned snapshot hiện tại. Tôi cũng phụ trách phối hợp với người làm quality để xác định run nào được phép publish bình thường và run nào chỉ dùng để inject test.

Công việc của tôi nối trực tiếp với phần eval: nếu publish sai hoặc không prune đúng, các câu retrieval có thể vẫn chứa context cũ dù cleaning đã fix. Vì vậy tôi phải theo dõi metric `embed_prune_removed` và đối chiếu với kết quả `hits_forbidden` trong file eval.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật trọng tâm của tôi là dùng chiến lược **upsert + prune** thay vì chỉ upsert.

Nếu chỉ upsert, các chunk không còn hợp lệ sau clean (ví dụ chunk chứa "14 ngày làm việc") có thể vẫn nằm trong collection và tiếp tục bị retrieve ở top-k. Điều đó làm hệ thống trả lời không ổn định dù dữ liệu mới đã đúng. Khi thêm bước prune theo tập `chunk_id` hiện tại, collection luôn phản ánh đúng snapshot cleaned mới nhất.

Tôi xem đây là quyết định quan trọng nhất cho Day10 vì nó bảo đảm ranh giới publish: cleaned đúng phải kéo theo index đúng. Kết quả thực tế chứng minh quyết định này hiệu quả, vì mỗi lần chuyển trạng thái clean <-> inject đều có `embed_prune_removed=1`, đúng với kỳ vọng thay thế 1 chunk stale/canonical.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly rõ nhất là ở run inject (`run_id=inject-bad`): pipeline cố ý bỏ fix refund (`--no-refund-fix`) và bỏ halt validate (`--skip-validate`) để publish snapshot lỗi. Lúc đó câu `q_refund_window` bị `hits_forbidden=yes`, nghĩa là top-k đang chứa cả context đúng và context stale.

Tôi dùng log publish để xác nhận hiện tượng này không phải lỗi retrieval random mà do snapshot index đã bị thay đổi: `embed_prune_removed=1` cho thấy chunk sạch trước đó đã bị thay bởi chunk stale.

Sau đó khi chạy lại clean run (`run_id=2026-04-15T10-30Z`), hệ thống prune ngược lại chunk stale (`embed_prune_removed=1`) và eval trở về `hits_forbidden=no`. Như vậy nguyên nhân và cách fix đều truy được theo pipeline data boundary, không cần sửa prompt hay thay model.

---

## 4. Bằng chứng trước / sau

**Trước (inject-bad):**
- `artifacts/eval/after_inject_bad.csv`
- `q_refund_window`: `contains_expected=yes`, `hits_forbidden=yes`
- publish log có `embed_prune_removed=1`

**Sau (clean run 2026-04-15T10-30Z):**
- `artifacts/eval/before_after_eval.csv`
- `q_refund_window`: `contains_expected=yes`, `hits_forbidden=no`
- `artifacts/manifests/manifest_2026-04-15T10-30Z.json` xác nhận snapshot clean mới

Bộ bằng chứng này cho thấy phần embed/idempotency đã làm đúng: thay snapshot sạch vào index và loại hoàn toàn context stale khỏi top-k.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi muốn thêm bước xác minh post-publish tự động: sau khi embed xong sẽ chạy một bộ query smoke test (refund/leave/version) và fail run nếu còn `hits_forbidden=yes`. Cách này giúp chặn sớm snapshot lỗi trước khi đưa vào tầng serving.
