# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** ___________
**Vai trò trong nhóm:** Trace & Docs Owner
**Ngày nộp:** 14/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi chịu trách nhiệm toàn bộ tầng **trace, evaluation và documentation** của hệ thống. Cụ thể gồm file `eval_trace.py` (pipeline chạy test/grading questions và phân tích metrics), thư mục `artifacts/` (traces, grading log, eval report), và các file trong `docs/`.

**Module/file tôi chịu trách nhiệm:**
- File chính: `eval_trace.py`, `docs/system_architecture.md`, `docs/routing_decisions.md`, `docs/single_vs_multi_comparison.md`
- Functions tôi implement:
  - `run_test_questions()` — chạy 15 câu test, lưu trace từng câu
  - `run_grading_questions()` — chạy 10 grading questions, xuất `grading_run.jsonl`
  - `analyze_traces()` — tính routing_distribution, avg_confidence, latency, mcp_usage_rate, hitl_rate
  - `compare_single_vs_multi()` — so sánh Day 08 vs Day 09
  - `save_eval_report()` — lưu báo cáo tổng kết JSON

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Worker Owner phải implement đúng interface `run(state) -> state` và điền đầy đủ `supervisor_route`, `workers_called`, `retrieved_sources`, `confidence` vào state. Nếu thiếu field nào, `analyze_traces()` của tôi tính metrics sẽ ra 0 hoặc bỏ sót.

**Bằng chứng:** File `artifacts/grading_run.jsonl` có 10 records. File `artifacts/traces/` có 25+ trace files. Cả hai được tạo bởi `eval_trace.py`.


---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Chuẩn hóa **trace format** thành schema cố định 12 field thay vì dump toàn bộ `AgentState`.

Ban đầu `save_trace()` trong `graph.py` dùng `json.dump(state, f)` — dump nguyên toàn bộ dict state gồm hơn 20 field (kể cả `retrieved_chunks` nội dung dài, `history`, `policy_result`...). Tôi đề xuất chỉ lưu 12 field chuẩn:

```json
{
  "run_id": "run_2026-04-14_1649",
  "task": "...",
  "supervisor_route": "retrieval_worker",
  "route_reason": "sla / ticket query",
  "workers_called": ["retrieval_worker", "synthesis_worker"],
  "mcp_tools_used": [],
  "retrieved_sources": ["sla_p1.txt"],
  "final_answer": "...",
  "confidence": 0.80,
  "hitl_triggered": false,
  "latency_ms": 0,
  "timestamp": "2026-04-14T16:49:00"
}
```

**Lý do:** Schema cố định giúp `analyze_traces()` đọc metrics ổn định không bị lỗi khi field đổi tên. Format cũ dump toàn state khiến mỗi trace file nặng ~3KB với nội dung chunk không cần thiết cho metrics.

**Các lựa chọn thay thế:**
- Giữ nguyên full state dump → dễ debug hơn nhưng file lớn và `analyze_traces()` phải biết cấu trúc sâu của state
- Dùng hai file riêng (full trace + slim metrics) → phức tạp hơn cần thiết

**Trade-off đã chấp nhận:** Mất `retrieved_chunks` và `history` trong trace file slim — không thể replay lại pipeline từ trace. Chấp nhận được vì `grading_run.jsonl` đã có đủ thông tin cho chấm điểm.

**Bằng chứng từ code:**
```python
# graph.py — save_trace() sau khi sửa
trace = {
    "run_id": state.get("run_id", ""),
    "task": state.get("task", ""),
    "supervisor_route": state.get("supervisor_route", ""),
    ...
    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
}
with open(filename, "w", encoding="utf-8") as f:
    json.dump(trace, f, ensure_ascii=False, indent=2)
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `analyze_traces()` bị `UnicodeDecodeError` khi đọc trace files — crash toàn bộ eval pipeline sau khi chạy xong 15 câu test.

**Symptom:**
```
File "eval_trace.py", line 189, in analyze_traces
    traces.append(json.load(f))
UnicodeDecodeError: 'charmap' codec can't decode byte 0x81 in position 31
```
Pipeline chạy 15/15 câu thành công nhưng bước phân tích trace phía sau crash, không ra được metrics và eval report.

**Root cause:** Trace files được lưu bằng `encoding="utf-8"` (có ký tự tiếng Việt như "phản hồi", "xử lý"), nhưng `analyze_traces()` mở file không chỉ định encoding — Python dùng encoding mặc định của hệ thống Windows là `cp1252`, không decode được UTF-8 multi-byte.

**Cách sửa:**
```python
# Trước — crash trên Windows
with open(os.path.join(traces_dir, fname)) as f:
    traces.append(json.load(f))

# Sau — hoạt động đúng
with open(os.path.join(traces_dir, fname), encoding="utf-8") as f:
    traces.append(json.load(f))
```

**Bằng chứng trước/sau:**

*Trước:*
```
Done. 15 / 15 succeeded.
UnicodeDecodeError: 'charmap' codec can't decode byte 0x81 ...
```

*Sau:*
```
Done. 15 / 15 succeeded.
Trace Analysis:
  total_traces: 25
  routing_distribution:
    policy_tool_worker: 14/25 (56%)
    retrieval_worker: 11/25 (44%)
  avg_confidence: 0.851
```

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi thiết kế `grading_run.jsonl` với đầy đủ field cần thiết cho chấm điểm: `id`, `question`, `answer`, `sources`, `supervisor_route`, `confidence`, `hitl_triggered`, `timestamp`. Format JSONL (mỗi dòng 1 JSON) giúp nộp file và parse phía grader dễ dàng hơn JSON array.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Phần `compare_single_vs_multi()` hiện vẫn dùng `day08_baseline` hardcode với `avg_confidence: 0.0` và `avg_latency_ms: 0` vì không có data thực từ Day 08. So sánh chưa có giá trị thực tế. Nếu có file kết quả Day 08, phần này mới đầy đủ.

**Nhóm phụ thuộc vào tôi ở đâu?**
`grading_run.jsonl` là file nộp chính để chấm điểm nhóm. Nếu tôi chưa chạy `eval_trace.py --grading` thì nhóm không có file để submit.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần Worker Owner implement đúng các field trong `AgentState` — đặc biệt `mcp_tools_used` phải là list string (tên tool), không phải list dict. Nếu sai format, `mcp_usage_rate` trong metrics tính nhầm.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ implement **auto-scoring** trong `eval_trace.py` để so khớp `answer` với `grading_criteria` từ `grading_questions.json`. Trace `gq07` (anti-hallucination) cho thấy answer hiện tại là `"[Evidence] - Không tìm thấy dữ liệu phù hợp"` — đúng tinh thần abstain nhưng chưa nói rõ "thông tin này không có trong tài liệu". Nếu có auto-scorer dùng LLM judge, tôi có thể biết trước nhóm được bao nhiêu điểm trước khi nộp và điều chỉnh pipeline.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*