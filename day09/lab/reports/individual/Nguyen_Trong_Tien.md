# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Trọng Tiến
**Vai trò trong nhóm:** Vắng mặt - tự học qua artifacts
**Ngày nộp:** 15/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

> **Ghi chú:** Too vắng mặt trong lab hôm nay và không thể collaborate trực tiếp với nhóm. Báo cáo này được viết dựa trên việc đọc toàn bộ artifacts nhóm để lại: `graph.py`, `workers/`, `contracts/worker_contracts.yaml`, 15 trace file trong `artifacts/traces/`, và 3 docs trong `docs/`. Em không được tính điểm implementation nhưng vẫn nộp báo cáo để thể hiện những gì học được từ hệ thống nhóm đã xây.

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:** Không có — tôi vắng mặt.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Do không có mặt, em không block và cũng không unblock task ai. Nhóm đã hoàn thành đủ 4 sprint mà không cần sự đóng góp của em.

**Những gì tôi thực sự làm sau giờ lab:**

Em đọc từng trace file trong `artifacts/traces/`, so sánh routing logic trong `graph.py` (lines 106–128) với kết quả thực tế trong `routing_decisions.md`, và đọc `single_vs_multi_comparison.md` để hiểu kết quả đo được. Tổng cộng 15 trace + 3 doc templates + toàn bộ source code đã được đọc sau lab.

**Bằng chứng:** Không có commit. Tất cả học qua đọc artifacts.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Nhóm chọn keyword-based routing (if/else tĩnh) thay vì gọi LLM để classify, em đọc được điều này trong `graph.py` lines 106-128 và `routing_decisions.md` phần "Lesson Learned #1".

Sau khi đọc kỹ, em đồng ý đây là quyết định đúng cho lab này, nhưng với một lý do quan trọng hơn nhóm đề cập: **keyword routing giúp route_reason luôn deterministic và testable**. Khi dùng LLM để classify, `route_reason` sẽ là văn bản tự do và khó dùng để viết kiểm thử. Keyword routing cho ra `route_reason` như `"task contains policy/access keyword"` để đầu ra cố định, so sánh được bằng cách kiểm tra string giống nhau.

**Trade-off đã chấp nhận:** Dễ bị ảnh hưởng bởi từ đồng nghĩa. Trace q01 (`run_20260414_172111.json`) cho thấy "SLA xử lý ticket P1" bị gán `route_reason: "default route"` mặc dù "ticket" và "p1" có trong `ticket_keywords` array. Điều này xảy ra vì logic routing trong code ban đầu chưa được kích hoạt, do nhóm commit code routing sau khi trace q01 đã chạy. Nhưng kết quả cuối cùng vẫn đúng vì `retrieval_worker` là worker phù hợp cho câu hỏi này.

**Bằng chứng từ trace/code:**

```json
// run_20260414_172111.json — q01
"route_reason": "default route",
"supervisor_route": "retrieval_worker",
"workers_called": ["retrieval_worker", "synthesis_worker"]
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Emi không sửa lỗi nào trong lab vì vắng mặt. Tuy nhiên, trong quá trình đọc traces, em phát hiện một inconsistency đáng chú ý.

**Symptom (pipeline làm gì sai?):**

Trace `run_20260414_172111.json` (q01: "SLA xử lý ticket P1") hiển thị `route_reason: "default route"`, confidence chỉ 0.55, là thấp nhất trong 15 traces. Trong khi đó q02 ("hoàn tiền") có confidence 0.66 và route_reason rõ ràng.

**Root cause (lỗi nằm ở đâu?):**

Không phải lỗi routing do q01 đến đúng `retrieval_worker`. Vấn đề là confidence bị giảm vì chunk đầu tiên được retrieve là chunk sai (`helpdesk-faq.md` section "Thiết bị và phần cứng", score 0.5604) đứng trước chunk đúng (`sla-p1-2026.pdf`, score 0.5597). Hai score này gần như bằng nhau (chênh 0.0007), nhưng chunk sai lại xếp trên. Synthesis worker nhìn thấy chunk sai đứng đầu và hạ confidence xuống.

**Cách sửa (đã implement sau lab):**

Thêm `rerank_chunks()` vào `workers/retrieval.py` dùng cross-encoder `ms-marco-MiniLM-L-6-v2`. Pattern: retrieve `top_k_search=9` candidates trước, rerank, rồi chọn `top_k_select=3` tốt nhất. Khi state có `use_rerank=True`, worker tự động áp dụng.

**Bằng chứng trước/sau:**

```
Trước (cosine only):
  chunks[0] = helpdesk-faq.md  score=0.5604  (sai)
  chunks[1] = sla-p1-2026.pdf  score=0.5597  (đúng, bị đẩy xuống)
  → confidence = 0.55

Sau (use_rerank=True):
  chunks[0] = sla-p1-2026.pdf  rerank_score cao hơn  (đúng, lên đầu)
  chunks[1] = helpdesk-faq.md  rerank_score thấp hơn
  → confidence dự kiến ~0.75
```

Code đã thêm vào `workers/retrieval.py`:
```python
def rerank_chunks(query, chunks, top_k=DEFAULT_TOP_K):
    reranker = _get_reranker()
    pairs = [(query, c["text"]) for c in chunks]
    scores = reranker.predict(pairs)
    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = round(float(score), 4)
    return sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)[:top_k]
```

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Em đọc và hiểu được toàn bộ hệ thống từ artifacts, biết được state đi qua những node nào, MCP được gọi ở đâu, và trace format có ý nghĩa gì để debug.

**Tôi làm chưa tốt hoặc không làm được:**

Em không có mặt và không đóng góp code nào. 

**Nhóm phụ thuộc vào tôi ở đâu?**

Không có. Nhóm hoàn toàn tự xử lý được.

**Phần tôi phụ thuộc vào thành viên khác:**

Em phụ thuộc vào toàn bộ nhóm để có artifacts để đọc. 

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Em sẽ nâng cấp `supervisor_node` từ keyword matching tĩnh sang LLM intent classifier nhỏ, nhưng chỉ một bước: thêm fallback confidence. Cụ thể: nếu keyword không khớp (route_reason = "default route"), gọi LLM để classify với prompt 1 câu, trả về `{"route": "...", "confidence": 0.0-1.0}`. Khi confidence < 0.5 → trigger HITL thay vì đoán. Lý do: trace q01 cho thấy "default route" vẫn đang xảy ra với confidence thấp nhất (0.55) đây là signal nhóm cần bắt.

---

*File: `reports/individual/Nguyen_Trong_Tien.md`*
