# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** C401-A2
**Ngày:** 2026-04-14

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.85 | 0.188 | -0.662 | Heuristic đánh giá khắt khe hơn |
| Avg latency (ms) | ~2500ms | 21189ms | +18689ms | Multi-agent orchestrate nhiều bước |
| Abstain rate (%) | 10% | 15% | +5% | Kiểm soát evidence chặt chẽ hơn |
| Multi-hop accuracy | 40% | 80% | +40% | Cải thiện vượt trội nhờ Worker chuyên trách |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | |
| Debug time (estimate) | 60 phút | 10 phút | -50 phút | Trace giúp khoanh vùng lỗi nhanh |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Cao | Rất cao |
| Latency | Thấp | Cao |
| Observation | Nhanh nhưng khó debug | Mất 15-20s nhưng thấy rõ luồng xử lý |

**Kết luận:** Multi-agent không mang lại lợi ích về tốc độ cho câu hỏi đơn giản, nhưng tăng tính minh bạch.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Trung bình | Cao |
| Routing visible? | ✗ | ✓ |
| Observation | Hay bị bỏ sót ý từ docs thứ hai | Phân tách được context từ nhiều worker |

**Kết luận:** Đây là thế mạnh của Multi-agent, hiệu quả vượt trội so với kiến trúc monolith.

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | Thấp | Cao |
| Hallucination cases | Thỉnh thoảng | Rất hiếm |
| Observation | LLM có xu hướng trả lời bừa | Synthesis worker kiểm soát evidence rất tốt |

**Kết luận:** Multi-agent giúp hệ thống an toàn hơn và ít bị ảo giác (hallucination) hơn.

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 60 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: 15 phút
```

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 2 LLM calls (Supervisor + Synthesis) |
| Complex query | 1 LLM call | 2-3 LLM calls |
| MCP tool call | N/A | 0-1 LLM calls trong logic tool |

**Nhận xét về cost-benefit:** Đổi chi phí và độ trễ để lấy sự chính xác và khả năng quản lý.

---

## 6. Kết luận

**Multi-agent tốt hơn single agent ở điểm nào?**
1. Độ tin cậy cho câu hỏi phức tạp (Multi-hop).
2. Khả năng bảo trì và gỡ lỗi (Observability).

**Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**
1. Độ trễ (Latency) cho các câu hỏi cực kỳ đơn giản.

**Khi nào KHÔNG nên dùng multi-agent?**
Khi hệ thống yêu cầu phản hồi tức thì (real-time) và các dữ liệu đầu vào cực kỳ đơn giản, không biến động.

**Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**
Thêm LLM-based routing để thay thế bộ keyword-based hiện tại nhằm tăng độ chính xác định tuyến.
