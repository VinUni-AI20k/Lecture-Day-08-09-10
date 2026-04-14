# Single Agent vs Multi-Agent Comparison — Lab Day 09

> Số liệu Day 08 lấy từ `day08/lab/results/grading_auto.json` (nếu có trong repo).  
> Số liệu Day 09: chạy `python eval_trace.py` rồi xem `artifacts/eval_report.json` và `artifacts/traces/`.

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Grading raw (từ auto-grader) | 83 / 98 (snapshot) | Chạy `--grading` để cập nhật | — | Day 08: `grading_auto.json` |
| Projected 30 điểm nhóm | 25.41 (snapshot) | Tính sau khi có `grading_run.jsonl` | — | Cùng cách quy đổi SCORING |
| Avg confidence | — | Từ `analyze_traces()` | — | Day 09 log `confidence` mỗi câu |
| Avg latency (ms) | — | Từ `analyze_traces()` | — | Day 09 log `latency_ms` |
| Routing visibility | Không có `route_reason` | Có `supervisor_route` + `route_reason` | + | Tiêu chí Day 09 |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu đơn giản (single-document)

Multi-agent thường **tốn thêm bước** (supervisor + retrieval + synthesis) so với một lần gọi LLM trong Day 08, nhưng **tách được lỗi** (retrieval vs synthesis).

### 2.2 Multi-hop (cross-document)

Day 09 route `multi_hop` gọi retrieval rồi policy; trace cho thấy rõ **workers_called** — Day 08 khó biết lỗi nằm ở retrieve hay generate nếu không có log chi tiết.

### 2.3 Abstain / mã lỗi không có trong docs

Cả hai pipeline đều phụ thuộc prompt grounded. Day 09 thêm **route_reason** giúp giải thích vì sao chọn retrieval (không bắt buộc HITL cho ERR-xxx trong lab).

---

## 3. Debuggability

**Day 08:** Sửa trong `rag_answer.py` — một luồng.

**Day 09:** `artifacts/traces/*.json` + test từng worker (`python workers/retrieval.py`, …).

---

## 4. Extensibility

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm API | Sửa pipeline | Thêm tool trong `mcp_server.py` + gọi trong policy worker |
| Đổi retrieval | Sửa `rag_answer` | `workers/retrieval.py` hoặc `search_kb` |

---

## 5. Kết luận

**Multi-agent tốt hơn ở:** quan sát được routing, test từng worker, tích hợp MCP có ranh giới rõ.

**Multi-agent kém hơn / tốn hơn ở:** độ trễ (nhiều bước), phức tạp triển khai hơn monolith.

**Khi không nên dùng multi-agent:** workload nhỏ, không cần trace, latency cực thấp.
