# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** C401 - C5  
**Ngày:** 14/04/2026

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.82 | 0.643 | −0.177 (−22%) | Multi-agent thận trọng hơn, ít over-confident hơn |
| Avg latency (ms) | 1,850 | 11,542 | +9,692 (+524%) | Tăng do supervisor routing + multi-worker pipeline |
| HITL / Abstain rate | 13% | 20% | +7% | Multi-agent kích hoạt HITL khi confidence < 0.5 |
| Multi-hop accuracy | ~20% | ~80%+ | +60% | Multi-agent cross-reference nhiều doc (gq09 Full) |
| Routing visibility | ✗ Không có | ✓ Có `route_reason` | N/A | Mỗi câu đều ghi lý do routing vào trace |
| Debug time (estimate) | 20–30 phút | 5–10 phút | −65% | Đọc `worker_io_logs` để xác định node lỗi |

> **Nguồn số liệu:** `artifacts/eval_report.json` (generated_at: 2026-04-14T17:58:09) và `artifacts/grading_run.jsonl` (10 grading questions + 15 test traces).

---

## 2. Phân tích định tính

### 2.1 Câu hỏi đơn giản

Multi-agent không mang lợi thế accuracy rõ rệt cho câu đơn giản, nhưng tăng tính minh bạch qua `route_reason`. Ví dụ thực tế từ trace:

- **gq08** ("Mật khẩu đổi sau bao nhiêu ngày?"): Supervisor route thẳng đến `retrieval_worker` với `route_reason = "task contains retrieval/SLA keyword"`. Confidence = 0.77, latency = 9,508ms. Câu trả lời đúng, nhưng latency cao hơn nhiều so với Day 08 (1,850ms trung bình) do phải đi qua chuỗi supervisor → retrieval_worker → synthesis_worker.

- **gq06** ("Nhân viên thử việc muốn làm remote?"): Route đến `retrieval_worker`, confidence = 0.79. Câu đơn giản nhưng vẫn trả lời chính xác điều kiện remote work từ `hr_leave_policy.txt`.

### 2.2 Câu hỏi multi-hop

Đây là điểm mạnh nhất của Multi-agent. Hệ thống bóc tách task phức tạp thành các bước cho từng worker chuyên biệt.

- **gq09** ("P1 lúc 2am + cấp Level 2 emergency access cho contractor"): Supervisor nhận diện `"multi-hop: access control + SLA context | risk_high flagged"`, gọi cả `retrieval_worker` + `policy_tool_worker` + `synthesis_worker`. MCP tool `get_ticket_info` được gọi thực tế. Câu trả lời nêu đủ cả 2 phần: SLA P1 notification procedure + điều kiện cấp Level 2 emergency access. Day 08 (single prompt) chỉ đạt ~20% multi-hop accuracy theo `eval_report.json`.

- **gq03** ("Level 3 access emergency — bao nhiêu người phê duyệt, ai cuối?"): `route_reason = "multi-hop: access control + SLA context | risk_high flagged"`, MCP tool `get_ticket_info` được gọi, confidence = 0.77, 3 workers được gọi theo thứ tự.

### 2.3 Khả năng từ chối (Abstain / HITL)

Multi-agent an toàn hơn cho môi trường doanh nghiệp nhờ cơ chế HITL trigger tự động khi confidence thấp.

- **gq07** ("Mức phạt tài chính vi phạm SLA P1?"): Đây là câu **không có thông tin trong tài liệu nội bộ**. Multi-agent trả lời đúng: `"Không đủ thông tin trong tài liệu nội bộ."`, confidence = **0.30**, `hitl_triggered = true`. Day 08 (single agent) không có cơ chế này — nguy cơ hallucinate con số không có thật dẫn đến penalty −50% điểm câu.

- HITL rate của Day 09: **3/15 traces (20%)** — tất cả đều là câu không đủ bằng chứng trong KB.

### 2.4 Phân phối routing thực tế

Từ 15 test traces, hệ thống phân phối routing như sau:

| Worker (Primary Route) | Số traces | Tỷ lệ |
|------------------------|-----------|-------|
| `retrieval_worker` | 8/15 | 53% |
| `policy_tool_worker` | 7/15 | 46% |

Supervisor phân biệt chính xác giữa "câu hỏi tra cứu thông tin" (retrieval) và "câu hỏi áp dụng quy tắc/exception" (policy) trong suốt 15 lần chạy — không bị nhầm lẫn routing lần nào. MCP tools được gọi trong **2/15 traces (13%)** — đều là câu hỏi multi-hop yêu cầu context ticket thực tế.

---

## 3. Phân tích khả năng Debug (Debuggability)

**Day 08:** Khi AI trả lời sai, phải đọc lại toàn bộ prompt dài và context để đoán model sai ở đâu. Không có vết (trace) chi tiết. Không biết context chunk nào được dùng, không biết bước nào thất bại.

**Day 09:** Chỉ cần đọc file trace JSON, kiểm tra `worker_io_logs` để xem từng node nhận input và trả ra output gì:

```json
// Ví dụ từ artifacts/traces/run_20260414_175516.json
"worker_io_logs": [
  {
    "worker": "retrieval_worker",
    "input": { "task": "SLA xử lý ticket P1 là bao lâu?", "top_k": 5 },
    "output": { "chunks_count": 5, "sources": ["sla_p1_2026.txt", ...] }
  },
  {
    "worker": "synthesis_worker",
    "output": { "answer_length": 124, "confidence": 0.72, "abstained": false }
  }
]
```

Nếu `synthesis_worker` trả kết quả sai, chỉ cần sửa `synthesis_worker` — không ảnh hưởng `retrieval_worker`. Ước tính giảm **65% thời gian debug** so với đọc toàn bộ single-agent prompt.

---

## 4. Khả năng mở rộng (Extensibility)

Kiến trúc Multi-agent có tính modular cực kỳ cao:
- **Thêm tính năng mới:** Thêm 1 Worker mới (ví dụ: `hr_worker` cho câu hỏi nhân sự) mà không sửa code hiện có.
- **Cập nhật luật nghiệp vụ:** Sửa `policy_tool_worker` độc lập, không đụng đến `retrieval_worker`.
- **Đổi model:** Chỉ cần thay đổi cấu hình của từng Worker riêng lẻ.
- **Tích hợp external tools:** Day 09 gọi external tools (`get_ticket_info`, `search_kb`) qua MCP protocol — Day 08 không có cơ chế này. MCP usage rate = **2/15 traces (13%)**.

---

## 5. Kết luận

| Tiêu chí | Single Agent (Day 08) | Multi-Agent (Day 09) | Winner |
|----------|-----------------------|----------------------|--------|
| Accuracy — câu đơn | avg_confidence 0.82 | avg_confidence 0.643 | Day 08 ✓ |
| Accuracy — multi-hop | ~20% | ~80%+ (gq09 Full) | **Day 09 ✓✓** |
| Latency | 1,850ms trung bình | 11,542ms trung bình | Day 08 ✓ |
| Anti-hallucination | Không có HITL | HITL khi confidence < 0.5 | **Day 09 ✓✓** |
| Debuggability | Không có trace chi tiết | `worker_io_logs` đầy đủ | **Day 09 ✓✓** |
| Extensibility | Sửa 1 prompt dài | Thêm/sửa từng Worker riêng lẻ | **Day 09 ✓✓** |
| Chi phí vận hành | Thấp (1 LLM call) | Cao (3+ LLM calls/query) | Day 08 ✓ |

**Ưu điểm Multi-Agent (Day 09):**
- Tăng tính minh bạch (Observability): mỗi trace ghi `route_reason`, `worker_io_logs`, `confidence` rõ ràng.
- Xử lý câu multi-hop tốt hơn đáng kể (+60% accuracy so với Day 08).
- Kiểm soát rủi ro hallucination qua HITL trigger tự động (gq07 abstain đúng, không bịa số liệu).
- Dễ debug và bảo trì — có thể test từng worker độc lập.

**Nhược điểm Multi-Agent (Day 09):**
- Tăng độ trễ rất lớn: +524% so với Day 08 (11,542ms vs 1,850ms).
- Average confidence thấp hơn (0.643 vs 0.82) — do cơ chế thận trọng hơn khi thiếu thông tin.
- Chi phí vận hành cao hơn: mỗi query gọi 2–3 LLM calls thay vì 1.

**Khuyến nghị:** Nên dùng Multi-agent cho hệ thống Enterprise yêu cầu sự chính xác, kiểm soát chặt và xử lý câu hỏi phức tạp cross-document (HR + SLA + Access Control). Dùng Single Agent cho ứng dụng nhỏ, câu hỏi đơn giản, hoặc khi latency là ưu tiên hàng đầu.
