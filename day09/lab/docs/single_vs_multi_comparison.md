# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** E402_Nhom11  
**Ngày:** 2026-04-14

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.76 | 0.584 | +-0.176 | TODO: Điền delta accuracy thực tế từ grading |
| Avg latency (ms) | 7448 | 20587 | 20587 | Day 09 dùng mock workers |
| Abstain rate (%) | 0.0% | N/A | N/A | Day 09 có HITL thay vì abstain |
| Multi-hop accuracy | 0.4 | N/A | N/A | Multi-agent tốt hơn cho multi-hop |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Day 09 có route_reason cho từng câu → dễ debug hơn Day 08 |
| Debuggability | ✗ | ✓ | N/A | Multi-agent: có thể test từng worker độc lập. Single-agent: không thể. |
| MCP benefit | ✗ | ✓ | N/A | Day 09 có thể extend capability qua MCP không cần sửa core. Day 08 phải hard-code. |

---

## 2. Phân tích

Day 09 có route_reason cho từng câu → dễ debug hơn Day 08

Multi-agent: có thể test từng worker độc lập. Single-agent: không thể.

Day 09 có thể extend capability qua MCP không cần sửa core. Day 08 phải hard-code.
