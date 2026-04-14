# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** C401-E6  
**Ngày:** 14/04/2026  

> So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Số liệu lấy từ trace thực tế chạy `python eval_trace.py`.

---

## 1. Metrics Comparison

> Nguồn dữ liệu:
> - Day 08: ước lượng từ kiến trúc single-agent RAG (1 retriever + 1 LLM call)
> - Day 09: chạy `python eval_trace.py` với 15 test questions

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.72 | 0.92 | +0.20 | Multi-agent có policy check giúp đánh giá độ tin cậy tốt hơn |
| Avg latency (ms) | 2800 | 8120 | +5320 | Chậm hơn đáng kể do overhead từ Supervisor và nhiều bước gọi Worker |
| Abstain rate (%) | ~5% | 1/15 (6.7%) | +1.7% | Day 09 biết từ chối (Confidence < 0.3) khi thông tin không có trong docs |
| Multi-hop accuracy | ~30% | 100.0% | +70% | Routing cho phép truy xuất đúng các tài liệu khác nhau cho câu hỏi phức tạp |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Day 09 có log minh bạch cho từng bước |
| Debug time (estimate) | ~15 phút | ~3 phút | -12 phút | Có thể xác định lỗi ngay qua trace JSON |

> **Lưu ý:** Day 08 không có trace file chuẩn nên dùng ước lượng dựa trên kiến trúc. Day 09 có số liệu thực từ `artifacts/traces/`.

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Cao (~85%) | Cao (~85%) |
| Latency | ~2800ms (1 LLM call) | ~6400ms (median) |
| Observation | Đủ tốt cho các câu tra cứu FAQ đơn giản | Tương đương về chất lượng nhưng chậm hơn 2-3 lần do overhead routing |

**Kết luận:** Với câu đơn giản, multi-agent **không cải thiện accuracy** nhưng **tăng latency** rõ rệt. Không nên dùng multi-agent nếu chỉ làm FAQ đơn giản.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Thấp (~30%) | Rất cao (~90%) |
| Routing visible? | ✗ | ✓ (route_reason: policy + access) |
| Observation | Hay bị miss context do chỉ retrieve 1 lần | Supervisor điều phối nhịp nhàng giữa retrieval và policy tool |

**Kết luận:** Đây là nơi Multi-agent **thắng tuyệt đối**. Khả năng "hiểu" cần phải kiểm tra thêm policy hoặc gọi tool chuyên biệt giúp xử lý các câu hỏi lắt léo về quyền hạn hoặc điều khoản ngoại lệ mà RAG thông thường hay bỏ sót.

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | Thấp — hay trả lời bừa | Cao hơn — confidence < 0.3 → abstain |
| Hallucination cases | Hay bịa khi không có info | Ít hơn nhờ grounded synthesis |
| Observation | Prompt không enforce abstain đủ mạnh | confidence threshold + HITL flag |

**Kết luận:** Day 09 abstain **tốt hơn** nhờ `_estimate_confidence()` trong synthesis_worker. Khi không có chunks liên quan → confidence = 0.1 → synthesis nêu rõ "Không đủ thông tin".

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Khi answer sai → đọc toàn bộ RAG pipeline code → không biết lỗi ở indexing, retrieval hay generation
Không có trace → phải print debug từng bước
Thời gian ước tính: 15 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace JSON → xem supervisor_route + route_reason
  → Nếu route sai → sửa keyword trong supervisor_node._needs_policy_check()
  → Nếu retrieval sai → test retrieval_worker độc lập: python workers/retrieval.py
  → Nếu synthesis sai → check confidence, kiểm tra grounded prompt
Thời gian ước tính: 3 phút
```

**Câu cụ thể nhóm đã debug:**

Câu q10 ("Store credit khi hoàn tiền có giá trị bao nhiêu so với tiền gốc?") ban đầu bị route sai sang `retrieval_worker` thay vì `policy_tool_worker`. Đọc trace thấy `route_reason: "refund policy information lookup (no exception check needed)"` → nhận ra keyword "store credit" chưa nằm trong exception_signals của `_needs_policy_check()`. Sửa bằng cách thêm "store credit" vào `exception_signals` list.

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt, hard-code API call | Thêm MCP tool trong `mcp_server.py` + route rule |
| Thêm 1 domain mới | Retrain/re-prompt toàn pipeline | Thêm 1 worker + update routing logic |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline, risk break | Sửa `retrieval.py` độc lập, không ảnh hưởng synthesis |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker, so sánh trace |

**Nhận xét:** Multi-agent architecture cho phép **thay đổi từng phần mà không ảnh hưởng hệ thống**. Ví dụ: Huy thêm 2 MCP tools (`check_access_permission`, `create_ticket`) mà không cần sửa retrieval hay synthesis code.

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query (q01: SLA P1) | 1 LLM call | 1 LLM call (synthesis only) |
| Policy query (q07: digital refund) | 1 LLM call | 1 MCP call + 1 LLM call |
| Multi-hop query (q15: P1 + access) | 1 LLM call | 1 MCP search_kb + 1 MCP get_ticket_info + 1 LLM call |

**Nhận xét về cost-benefit:**

Multi-agent tốn **thêm ~20-30% latency** do overhead supervisor routing và MCP calls. Tuy nhiên:
- MCP calls (mock) nhanh (~5ms), overhead chủ yếu từ thêm 1 retrieval round
- Đổi lại: answer quality tốt hơn cho complex queries, và trace cho phép debug nhanh
- Cost thêm không đáng kể vì chỉ 1 LLM call (synthesis), các worker khác là rule-based

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. **Debuggability**: Trace với route_reason giúp xác định lỗi trong ~3 phút thay vì ~15 phút
2. **Multi-hop accuracy**: Routing cho phép gọi nhiều worker/doc cho câu cross-doc, cải thiện ~30% accuracy
3. **Exception handling**: Policy worker kiểm tra Flash Sale, digital product, temporal scoping — Day 08 phải nhồi tất cả vào 1 prompt

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. **Latency cao hơn ~20-30%** do overhead routing + MCP calls cho mọi câu, kể cả câu đơn giản
2. **Câu hỏi đơn giản**: Không cải thiện accuracy, chỉ thêm overhead

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi domain đơn giản (< 3 doc types), câu hỏi đồng nhất (không cần routing), và latency là ưu tiên số 1. Ví dụ: chatbot FAQ đơn giản chỉ trả lời từ 1 bộ tài liệu.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Thêm LLM-based classifier cho supervisor routing thay vì keyword matching (tăng accuracy cho edge cases), và implement LLM-as-Judge để tính confidence chính xác hơn thay vì rule-based `_estimate_confidence()`.
