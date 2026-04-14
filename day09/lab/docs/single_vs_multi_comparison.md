# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** ___________  
**Ngày:** ___________

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
| Avg confidence | ___ | ___ | ___ | |
| Avg latency (ms) | ___ | ___ | ___ | |
| Abstain rate (%) | ___ | ___ | ___ | % câu trả về "không đủ info" |
| Multi-hop accuracy | ___ | ___ | ___ | % câu multi-hop trả lời đúng |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | |
| Debug time (estimate) | ___ phút | ___ phút | ___ | Thời gian tìm ra 1 bug |
| ___________________ | ___ | ___ | ___ | |

> **Lưu ý:** Nếu không có Day 08 kết quả thực tế, ghi "N/A" và giải thích.

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | ___ | ___ |
| Latency | ___ | ___ |
| Observation | ___________________ | ___________________ |

**Kết luận:** Multi-agent có cải thiện không? Tại sao có/không?

_________________

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | ___ | ___ |
| Routing visible? | ✗ | ✓ |
| Observation | ___________________ | ___________________ |

**Kết luận:**

_________________

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | ___ | ___ |
| Hallucination cases | ___ | ___ |
| Observation | ___________________ | ___________________ |

**Kết luận:**

_________________

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: ___ phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: ___ phút
```

**Câu cụ thể nhóm đã debug:** _(Mô tả 1 lần debug thực tế trong lab)_

_________________

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

_________________

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | ___ LLM calls |
| Complex query | 1 LLM call | ___ LLM calls |
| MCP tool call | N/A | ___ |

**Nhận xét về cost-benefit:**

_________________

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. ___________________
2. ___________________

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. ___________________

> **Khi nào KHÔNG nên dùng multi-agent?**

_________________

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

_________________
