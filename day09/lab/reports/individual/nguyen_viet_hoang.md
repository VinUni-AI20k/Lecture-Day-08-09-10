# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Việt Hoàng  
**Vai trò trong nhóm:** Worker Owner (Retrieval/Search Worker)  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/retrieval.py`, cập nhật trạng thái trong `contracts/worker_contracts.yaml`
- Functions tôi implement: `_get_embedding_fn`, `_get_collection`, `retrieve_dense`, `_sanitize_input`, `_make_error`, `run`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi chịu trách nhiệm worker đầu tiên trong flow Supervisor-Worker: nhận task từ Supervisor, truy xuất evidence từ ChromaDB và trả lại `retrieved_chunks`, `retrieved_sources` cho downstream worker tổng hợp. Phần này là nền để Synthesis Worker có dữ liệu trích dẫn; nếu retrieval sai hoặc output không đúng contract thì worker phía sau sẽ hoặc hallucinate hoặc không trả lời được. Vì vậy tôi ưu tiên làm rõ input/output contract ngay từ đầu, gồm `task`, `top_k`, `worker_io_logs` và chuẩn lỗi `RETRIEVAL_FAILED`. Tôi cũng giữ tương thích ngược với state cũ (`retrieval_top_k`) để graph hiện tại chạy không bị gãy.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

Bằng chứng nằm trực tiếp trong `workers/retrieval.py`: phần validate input, clamp `top_k`, chuẩn hóa score `[0,1]`, và append `worker_io_logs`. Ngoài ra `contracts/worker_contracts.yaml` đã cập nhật `actual_implementation.status: "done"` cho `retrieval_worker`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tách rõ lớp “contract handling” khỏi “retrieval logic”, bằng cách thêm `_sanitize_input()` và `_make_error()` trước khi xử lý dense retrieval.

**Lý do:**

Lúc đầu tôi có thể viết nhanh `run(state)` theo kiểu đọc thẳng `task` rồi query DB. Tuy nhiên cách đó dễ phát sinh lỗi âm thầm khi input sai kiểu hoặc thiếu field, làm trace khó đọc và khó debug liên team. Tôi chọn tách thành 2 lớp: lớp chuẩn hóa/validate I/O và lớp retrieval thuần. Điều này giúp worker tuân thủ contract ổn định khi được gọi từ nhiều nơi (test độc lập, graph orchestrator, hoặc test script). Tôi cũng chủ động nhận cả `top_k` và `retrieval_top_k` để tránh mismatch giữa contract mới và graph cũ.

**Trade-off đã chấp nhận:**

Trade-off là code dài hơn một chút và có thêm nhánh xử lý lỗi, nhưng đổi lại interface rõ ràng hơn, trace dễ kiểm chứng hơn, và giảm rủi ro integration bug khi ghép nhóm.

**Bằng chứng từ trace/code:**

```python
def _sanitize_input(state: Dict[str, Any]) -> Tuple[str, int]:
    task_raw = state.get("task", "")
    if not isinstance(task_raw, str):
        raise ValueError("task must be a string")
    task = task_raw.strip()
    if not task:
        raise ValueError("task is required and cannot be empty")
    top_k_raw = state.get("top_k", state.get("retrieval_top_k", DEFAULT_TOP_K))
    top_k = int(top_k_raw)
    top_k = max(MIN_TOP_K, min(MAX_TOP_K, top_k))
    return task, top_k
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Standalone test của retrieval worker bị crash trên Windows console do lỗi encoding Unicode.

**Symptom (pipeline làm gì sai?):**

Khi chạy `python workers/retrieval.py`, worker chưa kịp test xong thì dừng với `UnicodeEncodeError` tại các dòng in ký tự Unicode như `▶`, `✅`, hoặc chuỗi test có dấu tiếng Việt. Kết quả là pipeline test độc lập của worker không hoàn tất, gây khó xác nhận Definition of Done.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Lỗi nằm ở lớp test/logging của worker, không phải retrieval logic hay contract. Terminal Windows dùng `cp1252` không encode được một số ký tự Unicode trong output.

**Cách sửa:**

Tôi thay các ký tự in log sang ASCII (`[WARN]`, `[OK]`, `> Query`) và đổi test query về bản không dấu để đảm bảo script chạy ổn định đa môi trường. Việc này không ảnh hưởng đến core retrieval contract nhưng giúp worker test độc lập đúng như README yêu cầu.

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.

Trước khi sửa: có `UnicodeEncodeError: 'charmap' codec can't encode character ...` và script dừng giữa chừng.  
Sau khi sửa: script chạy hết 3 query test và kết thúc với dòng `[OK] retrieval_worker test done.` (exit code 0).

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt ở việc “đóng gói worker theo contract” thay vì chỉ chạy được demo. Cụ thể là chuẩn hóa input, chuẩn format lỗi, trace IO rõ ràng và kiểm soát score range. Nhờ vậy phần retrieval có thể ghép vào Supervisor mà ít rủi ro sai giao diện.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Hiện tại tôi chưa xử lý sâu cho tình huống collection trống ngoài việc cảnh báo; tôi chưa bổ sung chiến lược fallback retrieval nâng cao (ví dụ sparse/hybrid cho Day09) trong worker này.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Nếu retrieval worker chưa ổn, Synthesis Worker sẽ thiếu evidence/citation và cả graph sẽ chỉ trả lời dạng placeholder hoặc abstain.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào bạn phụ trách Supervisor để route gọi worker thật thay vì wrapper placeholder, và phụ thuộc vào người phụ trách index/data để đảm bảo `day09_docs` có dữ liệu đúng schema metadata.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm một cải tiến: tích hợp fallback retrieval mode (dense -> sparse/BM25) ngay trong `workers/retrieval.py` khi dense trả về `0 chunks`. Lý do là trace test hiện cho thấy nhiều lần `retrieved_chunks=[]` khi collection hoặc embedding chưa đồng bộ, làm pipeline downstream thiếu evidence. Với fallback rõ ràng và log mode đã dùng trong `worker_io_logs`, nhóm sẽ debug nhanh hơn và tăng khả năng trả lời có nguồn trong điều kiện thực tế.

---
