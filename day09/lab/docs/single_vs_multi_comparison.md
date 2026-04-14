# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** C401-A4 
**Ngày:** 14/4/2026

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Điền vào bảng sau. Lấy số liệu từ:
> - Day 08: chạy `python eval.py` từ Day 08 lab
> - Day 09: chạy `python eval_trace.py` từ lab này

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | N/A | 0.816 | N/A | Day 08 `eval.py` không xuất confidence; Day 09 tính từ 10 traces mới nhất (gq01-gq10). |
| Avg latency (ms) | N/A | 4689 | N/A | Day 08 `eval.py` không xuất latency; Day 09 tính từ trace `latency_ms`. |
| Abstain rate (%) | 20% (2/10) | 0% (0/10) | -20 điểm % | Day 08 abstain ở q09, q10; Day 09 không abstain dù có câu thiếu bằng chứng mạnh. |
| Multi-hop accuracy | N/A | N/A | N/A | Chưa có script chấm đúng/sai theo rubric cho Day 09 (trace hiện chỉ có confidence + answer). |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | |
| Debug time (estimate) | ~25 phút | ~8 phút | -17 phút | Với Day 09 có thể khoanh vùng lỗi theo `supervisor_route` + `worker_io_logs`. |
| MCP usage rate | N/A | 50% (5/10) | N/A | Chỉ có ở kiến trúc Day 09. |

> **Lưu ý:** Nếu không có Day 08 kết quả thực tế, ghi "N/A" và giải thích.

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Cao (đa số câu fact đơn trả lời đúng theo eval) | Trung bình (nhiều câu có nguồn `unknown`/lệch ngữ cảnh) |
| Latency | N/A | ~4.7s trung bình |
| Observation | Pipeline đơn giản, ít bước, dễ ổn định cho câu fact trực tiếp. | Route nhìn rõ hơn nhưng quality retrieval/synthesis chưa ổn định nên câu đơn vẫn có nhiễu. |

**Kết luận:** Multi-agent có cải thiện không? Tại sao có/không?

Ở nhóm câu đơn giản, multi-agent chưa cải thiện chất lượng trả lời so với Day 08. Điểm mạnh chủ yếu là observability; còn quality phụ thuộc mạnh vào retrieval chunk quality và policy/tool integration.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | N/A (chưa chạy bộ câu multi-hop tương đương Day 09) | Thấp-trung bình (gq09 route đúng nhưng nội dung trả lời chưa đủ tiêu chí rubric) |
| Routing visible? | ✗ | ✓ |
| Observation | Không có route trace nên khó biết sai ở retrieve hay generate. | Thấy rõ query cross-doc được route sang `policy_tool_worker`, nhưng synthesis còn trộn thông tin không liên quan. |

**Kết luận:**

Multi-agent giúp xử lý bài toán multi-hop theo kiến trúc đúng hướng (có route + tool path), nhưng cần cải thiện scoring retrieval và grounding để tăng accuracy thực tế.

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | 20% (2/10) | 0% (0/10) |
| Hallucination cases | Thấp-trung bình (có abstain để tránh bịa ở q09, q10) | Trung bình-cao (nhiều câu trả lời có source `unknown` hoặc lệch chủ đề) |
| Observation | Day 08 bảo thủ hơn khi thiếu dữ liệu. | Day 09 hiện thiên về "trả lời bằng được", giảm abstain nhưng tăng rủi ro sai lệch. |

**Kết luận:**

Trong trạng thái hiện tại, Day 09 cần bổ sung cơ chế abstain nghiêm ngặt hơn theo chất lượng evidence (vd threshold theo source reliability + relevance) để giảm hallucination.

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: ~25 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: ~8 phút
```

**Câu cụ thể nhóm đã debug:** _(Mô tả 1 lần debug thực tế trong lab)_

Case policy/access trước đó fail với lỗi `No module named 'mcp'` trong `policy_tool_worker`. Nhờ trace có `workers_called` và `worker_io_logs`, nhóm khoanh vùng ngay dependency ở nhánh policy thay vì dò toàn pipeline.

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker |

**Nhận xét:**

Day 09 dễ mở rộng hơn rõ rệt vì boundary supervisor/worker/tool tách rời; tuy nhiên cần chuẩn hóa contract test và CI check dependency để tránh lỗi integration khi thêm MCP/tool mới.

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 1 LLM call (route retrieval -> synthesis) |
| Complex query | 1 LLM call | 1 LLM call + 1-2 MCP calls (policy/access path) |
| MCP tool call | N/A | 0-2/tool-path (thực tế 5/10 câu có MCP usage) |

**Nhận xét về cost-benefit:**

Chi phí điều phối của Day 09 cao hơn ở câu phức tạp do thêm tool calls và state tracing, nhưng đổi lại nhóm có khả năng debug/quan sát tốt hơn. Với production, trade-off hợp lý khi bài toán nhiều rule/policy và cần auditability.

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. Quan sát pipeline tốt hơn: có `supervisor_route`, `route_reason`, `worker_io_logs`, dễ xác định điểm lỗi.
2. Mở rộng capability theo module (thêm worker/MCP) mà không phá vỡ toàn bộ prompt/pipeline.

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. Chất lượng answer chưa tự động tốt hơn; nếu retrieval/synthesis yếu thì vẫn sai và có thể hallucinate dù route đúng.

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi bài toán chỉ là Q&A đơn giản, ít rule, ít tích hợp ngoài, và ưu tiên chi phí/độ trễ thấp hơn khả năng trace-debug chi tiết.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Thêm answer-level evaluator theo rubric (đúng/sai theo `grading_criteria`), threshold abstain dựa trên relevance/source reliability, và regression test tự động cho từng worker + MCP integration.
**TrinhDucAnh**