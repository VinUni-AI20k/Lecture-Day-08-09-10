# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** 04 
**Ngày:** 2026-04-14

## 0) Quy tắc điền số liệu

- Ưu tiên số liệu thật từ trace/report.
- Nếu chưa có Day 08 baseline thật, ghi `N/A (chưa có artifact)` và nêu kế hoạch bổ sung.
- Không điền số "đoán"; rubric chấm tính nhất quán giữa report và artifact.

## 1) Nguồn dữ liệu dùng để so sánh

- Day 09:
  - `python eval_trace.py --analyze`
  - `python eval_trace.py --compare`
  - `artifacts/traces/*.json`
- Day 08:
  - `eval.py` hoặc file baseline do nhóm lưu
  - Hiện tại: `N/A (chưa có artifact Day08 trong repo này)`

## 2) Metrics Comparison (bảng chính)

| Metric | Day 08 (Single) | Day 09 (Multi) | Delta | Trạng thái dữ liệu | Ghi chú |
|---|---:|---:|---:|---|---|
| Avg confidence | N/A | 0.739 | N/A | Day08: Placeholder / Day09: Real | từ `artifacts/eval_report.json` |
| Avg latency (ms) | N/A | 3494 | N/A | Day08: Placeholder / Day09: Real | |
| Abstain rate (%) | N/A | Thấp | N/A | Day08: Placeholder / Day09: Estimated | phần lớn câu đã có evidence |
| Multi-hop accuracy | N/A | Trung bình-khá (ước lượng) | N/A | Day08: Placeholder / Day09: Estimated | q15 có đủ 2 nguồn |
| Routing visibility | Không có | Có `route_reason` | N/A | Real | |
| MCP usage rate (%) | N/A | 33% (5/15) | N/A | Real | lấy từ `analyze_traces()` |
| HITL rate (%) | N/A | 6% (1/15) | N/A | Real | |
| Debug time cho 1 lỗi (phút) | N/A | 5-10 | N/A | Estimated | có route_reason + worker_io_logs |

> Ghi chú quan trọng: trong `eval_trace.py`, baseline Day 08 mặc định còn TODO nếu không truyền file baseline thật.

## 3) Phân tích theo nhóm câu hỏi

### 3.1 Simple retrieval

| Tiêu chí | Day 08 | Day 09 | Nhận xét |
|---|---|---|---|
| Accuracy | N/A | Khá | Retrieval đã có chunks + sources rõ |
| Latency | N/A | ~3.5s trung bình | Đã giảm sau khi đồng bộ embedding |
| Độ ổn định | N/A | Tốt | 15/15 câu chạy thành công |

### 3.2 Multi-hop / cross-policy (đặc biệt gq09)

| Tiêu chí | Day 08 | Day 09 | Nhận xét |
|---|---|---|---|
| Trả đủ 2 ý chính | N/A | Trung bình-khá | q15 đã trả được cả access + SLA từ 2 source |
| Có evidence trace route/worker | Không | Có | |
| Khả năng debug khi thiếu 1 ý | N/A | Tốt | Có `route_reason`, `workers_called`, `worker_io_logs` |

### 3.3 Câu cần abstain (đặc biệt gq07)

| Tiêu chí | Day 08 | Day 09 | Nhận xét |
|---|---|---|---|
| Tỉ lệ abstain đúng | N/A | Vừa phải | abstain xuất hiện khi evidence yếu |
| Hallucination cases | N/A | Thấp | câu trả lời có citation rõ hơn |
| Mức phạt dự kiến theo rubric | N/A | Giảm rủi ro so với lần chạy trước | |

## 4) Debuggability và khả năng vận hành

### Flow debug Day 08

```text
Answer sai -> đọc pipeline chung -> khó định vị retrieval/prompt/policy sai
```

### Flow debug Day 09

```text
Answer sai -> xem supervisor_route + route_reason + workers_called
-> route sai: sửa supervisor
-> route đúng nhưng output sai: test worker tương ứng độc lập
```

**Case debug thực tế của nhóm:**  
Trace `run_20260414_165615.json` cho thấy retrieval đã trả 3 chunks với source chuẩn, xác nhận fix đồng bộ embedding đã có hiệu lực.

## 5) Kết luận có thể chấm điểm

### Multi-agent tốt hơn ở

1. Quan sát pipeline theo từng worker rõ ràng, debug nhanh hơn.
2. Tích hợp MCP độc lập, không phải chỉnh prompt toàn hệ.

### Multi-agent chưa tốt hơn ở

1. Chưa có baseline Day08 thật nên chưa kết luận được delta tuyệt đối.

### Rủi ro cần ghi trung thực trong report

- Day08 baseline chưa có artifact thật trong repo nên chưa tính được delta.
- Một số metric comparison có thể còn placeholder nếu thiếu baseline Day 08.
- Chưa có `grading_run.jsonl` nên chưa chốt score raw/96.

### Kế hoạch cải thiện vòng sau

1. Chạy `eval_trace.py --grading` để có kết quả chấm thật.
2. Bổ sung artifact Day08 để tính delta latency/accuracy đầy đủ.
