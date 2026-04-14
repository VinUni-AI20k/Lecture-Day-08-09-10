import json
import os
from pathlib import Path

def generate_docs_from_eval_report(eval_report_path: str, docs_dir: str):
    """
    Tạo ra các file documentation từ eval_report.json
    """
    # Đọc eval_report.json
    with open(eval_report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    # Tạo system_architecture.md
    generate_system_architecture(docs_dir, report)

    # Tạo routing_decisions.md
    generate_routing_decisions(docs_dir, report)

    # Tạo single_vs_multi_comparison.md
    generate_comparison(docs_dir, report)

def generate_system_architecture(docs_dir: str, report: dict):
    content = f"""# System Architecture — Lab Day 09

**Nhóm:** E402_Nhom11  
**Ngày:** {report.get('generated_at', '').split('T')[0]}  
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

- **Total Traces:** {report['day09_multi_agent']['total_traces']}
- **Avg Confidence:** {report['day09_multi_agent']['avg_confidence']:.3f}
- **Avg Latency:** {report['day09_multi_agent']['avg_latency_ms']} ms
- **MCP Usage Rate:** {report['day09_multi_agent']['mcp_usage_rate']}
- **HITL Rate:** {report['day09_multi_agent']['hitl_rate']}
"""

    with open(os.path.join(docs_dir, 'system_architecture.md'), 'w', encoding='utf-8') as f:
        f.write(content)

def generate_routing_decisions(docs_dir: str, report: dict):
    routing = report['day09_multi_agent']['routing_distribution']
    content = f"""# Routing Decisions Log — Lab Day 09

**Nhóm:** E402_Nhom11  
**Ngày:** {report.get('generated_at', '').split('T')[0]}

---

## Routing Distribution

- **Policy Tool Worker:** {routing['policy_tool_worker']}
- **Retrieval Worker:** {routing['retrieval_worker']}

## Top Sources

"""
    for source, count in report['day09_multi_agent']['top_sources']:
        content += f"- {source}: {count} lần\n"

    with open(os.path.join(docs_dir, 'routing_decisions.md'), 'w', encoding='utf-8') as f:
        f.write(content)

def generate_comparison(docs_dir: str, report: dict):
    day08 = report['day08_single_agent']
    day09 = report['day09_multi_agent']
    analysis = report['analysis']

    content = f"""# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** E402_Nhom11  
**Ngày:** {report.get('generated_at', '').split('T')[0]}

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | {day08['avg_confidence']} | {day09['avg_confidence']:.3f} | +{day09['avg_confidence'] - day08['avg_confidence']:.3f} | {analysis.get('accuracy_delta', 'N/A')} |
| Avg latency (ms) | {day08['avg_latency_ms']} | {day09['avg_latency_ms']} | {analysis['latency_delta']} | Day 09 dùng mock workers |
| Abstain rate (%) | {day08['abstain_rate'] * 100}% | N/A | N/A | Day 09 có HITL thay vì abstain |
| Multi-hop accuracy | {day08['multi_hop_accuracy']} | N/A | N/A | Multi-agent tốt hơn cho multi-hop |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | {analysis['routing_visibility']} |
| Debuggability | ✗ | ✓ | N/A | {analysis['debuggability']} |
| MCP benefit | ✗ | ✓ | N/A | {analysis['mcp_benefit']} |

---

## 2. Phân tích

{analysis.get('routing_visibility', '')}

{analysis.get('debuggability', '')}

{analysis.get('mcp_benefit', '')}
"""

    with open(os.path.join(docs_dir, 'single_vs_multi_comparison.md'), 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    # Path đến eval_report.json
    eval_report_path = Path(__file__).parent.parent / "artifacts" / "eval_report.json"
    docs_dir = Path(__file__).parent

    generate_docs_from_eval_report(str(eval_report_path), str(docs_dir))
    print("Docs generated successfully!")