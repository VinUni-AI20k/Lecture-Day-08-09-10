# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Hoàng Long
**Vai trò trong nhóm:** Trace & Evaluation Owner  
**Ngày nộp:** 2026-04-14  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào?

**Module/file tôi chịu trách nhiệm:**
- File chính: `eval_trace.py`
- Functions tôi implement: `run_test_questions()`, `run_grading_questions()`, `analyze_traces()`, `check_routing_accuracy()`, `compare_single_vs_multi()`, `_percentile()`, `save_eval_report()`
- File hỗ trợ: `build_index.py` (script build ChromaDB index từ `data/docs/`)

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi là người cuối cùng trong pipeline — nhận output từ tất cả Sprint trước (Quang: graph.py, Tuấn/Hải/Dũng: workers, Huy: MCP) rồi chạy end-to-end evaluation. `eval_trace.py` gọi `run_graph()` từ `graph.py` của Quang, pipeline lần lượt đi qua workers của Tuấn, Hải, Dũng, và MCP tools của Huy. Tôi thu thập trace output từ tất cả các bước này để tính metrics. Ngoài ra, tôi cộng tác với Thuận để điền `docs/single_vs_multi_comparison.md` — tôi cung cấp số liệu từ trace, Thuận viết phân tích kiến trúc.

**Bằng chứng:** File `eval_trace.py` có các function do tôi viết. Output: `artifacts/traces/`, `artifacts/grading_run.jsonl`, `artifacts/eval_report.json`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Thêm `check_routing_accuracy()` — function so sánh `supervisor_route` thực tế trong trace với `expected_route` từ `test_questions.json`, thay vì chỉ manual review.

**Các lựa chọn thay thế:**
- **Cách 1 (manual):** Đọc từng trace file, so sánh bằng mắt → chậm, dễ sai
- **Cách 2 (LLM-as-Judge):** Gọi LLM để đánh giá routing → tốn API cost, chậm
- **Cách 3 (automated exact match):** So sánh string `supervisor_route` vs `expected_route` → nhanh, deterministic

Tôi chọn **Cách 3** vì routing trong lab này dùng keyword-based matching (deterministic), nên exact string comparison là đủ chính xác. Output trả về accuracy percentage và danh sách mismatches giúp Quang debug routing logic nhanh.

**Trade-off đã chấp nhận:** Exact match không phát hiện được trường hợp route sai nhưng vẫn cho answer đúng (false negative). Chấp nhận trade-off này vì mục đích chính là đánh giá routing logic, không phải answer quality.

**Bằng chứng từ trace/code:**

```python
# eval_trace.py — check_routing_accuracy()
def check_routing_accuracy(traces_dir, questions_file):
    # Load expected routes từ test_questions.json
    expected = {q["id"]: q.get("expected_route", "") for q in questions}
    # So sánh với actual route trong trace
    for t in traces:
        if actual_route == exp_route:
            correct += 1
        else:
            mismatches.append({...})
    return {"accuracy_pct": acc, "mismatches": mismatches}
```

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** `analyze_traces()` ban đầu chỉ tính `avg_latency_ms` — không đủ để đánh giá latency distribution. Câu đơn giản (~1500ms) và câu multi-hop (~5000ms) bị trộn lẫn trong 1 số trung bình, che giấu tail latency.

**Symptom:** Metrics báo avg_latency = ~3000ms nhưng không thấy câu nào chạy > 5000ms. Khi chạy grading thì một số câu phức tạp bị timeout-like behavior mà không phát hiện được.

**Root cause:** Thiếu percentile stats (p95, p99). Chỉ dùng mean → bị skewed bởi câu nhanh, không highlight outliers.

**Cách sửa:** Thêm `_percentile()` helper function và mở rộng metrics output thành dict với `mean_ms`, `median_ms`, `p95_ms`, `p99_ms`, `min_ms`, `max_ms`.

**Bằng chứng trước/sau:**

Trước:
```json
{"avg_latency_ms": 3012}
```

Sau:
```json
{"latency": {"mean_ms": 3012, "median_ms": 2800, "p95_ms": 5200, "p99_ms": 6100, "min_ms": 1200, "max_ms": 6500}}
```

Nhờ p95/p99, nhóm phát hiện câu q15 (multi-hop) có latency gấp đôi trung bình → cần optimize policy_tool_worker cho trường hợp cross-doc.

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**

Thiết kế metrics pipeline toàn diện — từ routing accuracy, latency distribution (p50/p95/p99), đến comparison framework. Các metrics này giúp cả nhóm đánh giá chất lượng system một cách định lượng thay vì cảm tính.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Chưa implement LLM-as-Judge để tính answer quality tự động. Hiện tại confidence score là rule-based (`_estimate_confidence()` trong synthesis.py) — chưa phản ánh chính xác chất lượng answer.

**Nhóm phụ thuộc vào tôi ở đâu?**

Thuận cần metrics data từ `eval_trace.py` để viết `group_report.md` và `routing_decisions.md`. Nếu tôi chưa chạy xong → Thuận không có số liệu.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi phụ thuộc vào **tất cả** Sprint trước. `eval_trace.py` gọi `run_graph()` → cần graph.py (Quang), workers (Tuấn, Hải, Dũng), MCP (Huy) hoàn thành trước.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ implement **LLM-as-Judge scoring** cho answer quality — gọi LLM để chấm Faithfulness (answer có đúng với context không?) và Completeness (answer có đủ thông tin không?) cho từng câu trong trace. Lý do: trace câu q15 cho thấy confidence = 0.85 nhưng answer thực tế chỉ trả lời được 1/2 phần (SLA mà thiếu access control) → confidence score hiện tại không phản ánh đúng quality. LLM-as-Judge sẽ phát hiện gap này.

---

*File: reports/individual/2A202600160_NguyenHoangLong.md*
