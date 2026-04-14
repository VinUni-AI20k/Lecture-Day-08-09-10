# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** 2A202600292-TranDangQuangHuy  
**Ngày cập nhật:** 2026-04-14

**Nguồn dữ liệu dùng để điền:**
- Day08 baseline (test questions): `../../day08/lab/results/ab_comparison.csv` (`config_label=baseline_dense`)
- Day08 test schema: `../../day08/lab/data/test_questions.json`
- Day09 pre-pass run: `artifacts/runs/sprint4_test_20260414_115500_summary.json`
- Day09 confidence-pass run: `artifacts/runs/sprint4_test_confpass_20260414_1218_summary.json`
- Day09 route-pass run: `artifacts/runs/sprint4_test_routepass3_20260414_summary.json`
- Day09 latency-optimized run (latest): `artifacts/runs/sprint4_test_latencyopt_20260414_summary.json`
- Cross-day bridge report: `artifacts/cross_day_metrics.json`

---

## 1. Aligned Metrics (Day08 -> Day09 latest latency-optimized run)

> Ghi chú: Day08 không có confidence 0-1 gốc. Nhóm dùng bridge script (`eval_cross_day.py`) để quy đổi metric 1-5 sang confidence-like 0-1, đồng thời tính thêm metric còn thiếu.

| Metric | Day08 (Single Agent) | Day09 (Multi-Agent, latest) | Delta (Day09 - Day08) | Nhận xét |
|--------|----------------------|----------------------------------|------------------------|----------|
| Avg confidence | 0.754 (converted) | 0.851 | +0.097 | Day09 vẫn cao hơn Day08 sau các pass |
| Avg latency (ms) | 3977.624 | 1078.467 | -2899.157 | Latency giảm mạnh sau pass tối ưu policy-path |
| Answered rate (%) | 100.0 | 100.0 | 0.0 | Cả hai đều không fail pipeline |
| Abstain rate (%) | 30.0 | 6.67 | -23.33 | Day09 ít abstain hơn (cần theo dõi hallucination side-effect) |
| Citation rate (%) | 20.0 | 93.33 | +73.33 | Day09 enforce citation tốt hơn rõ rệt |
| Source recall rate (%) | 100.0 | 100.0 | 0.0 | Tương đương theo test set hiện có |
| Numeric consistency (%) | 64.58 | 63.78 | -0.80 | Gần tương đương, Day09 thấp nhẹ |
| MCP usage (%) | 0.0 | 40.0 | +40.0 | Route policy nhiều hơn nên MCP usage tăng |
| HITL rate (%) | 0.0 (estimated) | 6.67 | +6.67 | Chỉ còn 1 case low-confidence (`q09`) |
| Route accuracy (%) | N/A | 100.0 | N/A | Day08 không có route trace để đối chiếu |

---

## 2. Missing-Metric Tests (Implemented for both Day08/Day09)

### 2.1 Day08 (from `cross_day_metrics.json`)

| Test | Applicable | Passed / Total | Pass rate |
|------|------------|----------------|-----------|
| abstain_behavior | Yes | 0 / 1 | 0.0% |
| citation_presence | Yes | 2 / 9 | 22.22% |
| source_coverage_full | Yes | 9 / 9 | 100.0% |
| numeric_fidelity | Yes | 4 / 8 | 50.0% |
| multi_hop_support | No | 0 / 0 | N/A |
| route_correctness | No | 0 / 0 | N/A |

### 2.2 Day09 (latest route-pass)

| Test | Applicable | Passed / Total | Pass rate |
|------|------------|----------------|-----------|
| abstain_behavior | Yes | 1 / 1 | 100.0% |
| citation_presence | Yes | 14 / 14 | 100.0% |
| source_coverage_full | Yes | 14 / 14 | 100.0% |
| numeric_fidelity | Yes | 6 / 15 | 40.0% |
| multi_hop_support | Yes | 3 / 3 | 100.0% |
| route_correctness | Yes | 15 / 15 | 100.0% |

**Ý nghĩa:**
- Day09 vượt mạnh ở citation/source/multi-hop support observability.
- Numeric fidelity vẫn là vùng cần cải thiện thêm cho cả hai hệ (đặc biệt Day09 chỉ 40% theo test heuristic).

---

## 3. Iteration Timeline (Day09)

### 3.1 Thay đổi kỹ thuật đã áp dụng

1. `workers/retrieval.py`
   - Tokenization có stopword filtering để giảm overlap nhiễu.
   - Blend dense similarity + lexical score (`0.7 * dense + 0.3 * lexical`).
   - Lọc chunk điểm quá thấp (`score < 0.22`) để tránh kéo confidence xuống.
   - Local fallback có hint-doc selection theo intent (refund/SLA/access/HR/helpdesk).

2. `workers/synthesis.py`
   - Confidence estimator dùng top-evidence weighting (`top1/top2`) thay vì trung bình toàn chunk.
   - Thêm bonus cho citation/policy signals.
   - Hiệu chỉnh confidence riêng cho abstain answers.

### 3.2 Kết quả đo được theo từng run

| Metric | Pre-pass (11:55) | Confidence-pass (12:18) | Route-pass (12:32) | Latency-opt (12:41) |
|--------|-------------------|--------------------------|--------------------|---------------------|
| Avg confidence | 0.295 | 0.837 | 0.851 | 0.851 |
| HITL rate (%) | 86.67 | 6.67 | 6.67 | 6.67 |
| Avg latency (ms) | 2721.33 | 2705.67 | 4026.53 | 1078.47 |
| Route accuracy (%) | 73.33 | 73.33 | 100.0 | 100.0 |
| MCP usage (%) | 33.33 | 33.33 | 40.0 | 40.0 |

**Kết luận ngắn:**
- Confidence-pass giải quyết nút thắt confidence/HITL.
- Route-pass xử lý triệt để route accuracy (15/15).
- Latency-opt giữ nguyên quality và giảm latency mạnh (trung bình 1078.47 ms).

---

## 4. Phân tích theo loại câu hỏi

### 4.1 Câu hỏi single-worker
- Route accuracy proxy vẫn cao ở nhóm câu đơn giản.
- Confidence tăng rõ sau pass tuning do retrieval score ít bị dilution.

### 4.2 Câu hỏi multi-hop
- `multi_hop_support` đạt 100% theo test heuristic (3/3).
- `route_correctness` đã lên 100% sau route-pass (đặc biệt sửa đúng `q13`, `q15`).

### 4.3 Câu hỏi abstain
- Day09 giữ đúng hành vi abstain cho case thiếu context (`q09`), với confidence thấp tương ứng (0.10).

---

## 5. Kết luận

1. Việc bridge Day08 -> Day09 giúp so sánh trên cùng hệ metric có thể đo được thay vì để N/A.
2. Bộ missing-metric tests đã chạy cho cả Day08 và Day09, chỉ ra rõ vùng mạnh/yếu.
3. Sau route-pass + latency-opt, Day09 đạt route accuracy 100% và cải thiện mạnh latency.
4. Ưu tiên tiếp theo: nâng numeric fidelity.
