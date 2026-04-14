# System Architecture — Lab Day 09

**Nhóm:** E402_Nhom11  
**Ngày:** 2026-04-14  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):** Multi-agent cho phép modularization, dễ debug và extend qua MCP tools.

---

## 2. Sơ đồ Pipeline

```
User Request
     │
     ▼
┌──────────────┐
│  Supervisor  │  ← route_reason, risk_high, needs_tool
└──────┬───────┘
       │
   [route_decision]
       │
  ┌────┴────────────────────┐
  │                         │
  ▼                         ▼
Retrieval Worker     Policy Tool Worker
  (evidence)           (policy check + MCP)
  │                         │
  └─────────┬───────────────┘
            │
            ▼
      Synthesis Worker
        (answer + cite)
            │
            ▼
         Output
```

## 3. Metrics từ Evaluation

- **Total Traces:** 12
- **Avg Confidence:** 0.584
- **Avg Latency:** 20587 ms
- **MCP Usage Rate:** 4/12 (33%)
- **HITL Rate:** 0/12 (0%)
