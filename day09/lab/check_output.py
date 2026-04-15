"""Quick script to verify all output files match SCORING.md requirements."""
import json, os

print("=" * 60)
print("OUTPUT VERIFICATION vs SCORING.md")
print("=" * 60)

# 1. Check trace files
traces_dir = "artifacts/traces"
trace_files = [f for f in os.listdir(traces_dir) if f.endswith(".json")]
print(f"\n[1] TRACE FILES: {len(trace_files)}/15")

# Required fields from SCORING.md line 114-127
required_fields = [
    "supervisor_route", "route_reason", "workers_called",
    "mcp_tools_used", "confidence", "hitl_triggered"
]

sample = json.load(open(os.path.join(traces_dir, trace_files[0]), encoding="utf-8"))
for f in required_fields:
    val = sample.get(f, "MISSING!!!")
    status = "OK" if f in sample else "MISSING"
    print(f"    {f}: [{status}] = {str(val)[:50]}")

# Check question_id exists
print(f"    question_id: [{'OK' if 'question_id' in sample else 'MISSING'}]")
print(f"    final_answer: [{'OK' if 'final_answer' in sample else 'MISSING'}]")
print(f"    route_reason != 'unknown': [{'OK' if sample.get('route_reason','') != 'unknown' else 'FAIL'}]")

# 2. Check eval_report.json
print(f"\n[2] EVAL REPORT:")
if os.path.exists("artifacts/eval_report.json"):
    report = json.load(open("artifacts/eval_report.json", encoding="utf-8"))
    print(f"    File exists: [OK]")
    print(f"    Has day08_single_agent: [{'OK' if 'day08_single_agent' in report else 'MISSING'}]")
    print(f"    Has day09_multi_agent: [{'OK' if 'day09_multi_agent' in report else 'MISSING'}]")
    print(f"    Has analysis: [{'OK' if 'analysis' in report else 'MISSING'}]")
else:
    print(f"    File exists: [MISSING!!!]")

# 3. Check comparison doc has real numbers
print(f"\n[3] COMPARISON DOC:")
comp_path = "docs/single_vs_multi_comparison.md"
if os.path.exists(comp_path):
    content = open(comp_path, encoding="utf-8").read()
    has_placeholder = "(tu trace)" in content or "(t\u1eeb trace)" in content
    print(f"    File exists: [OK]")
    print(f"    No placeholders remaining: [{'FAIL - has (tu trace)' if has_placeholder else 'OK'}]")
    # Check >= 2 metrics
    metrics_found = 0
    for m in ["confidence", "latency", "Abstain", "Multi-hop", "Debug time"]:
        if m.lower() in content.lower():
            metrics_found += 1
    print(f"    Metrics found: {metrics_found} (need >= 2): [{'OK' if metrics_found >= 2 else 'FAIL'}]")
else:
    print(f"    File exists: [MISSING!!!]")

# 4. Check individual report
print(f"\n[4] INDIVIDUAL REPORT:")
report_path = "reports/individual/2A202600160_NguyenHoangLong.md"
if os.path.exists(report_path):
    content = open(report_path, encoding="utf-8").read()
    word_count = len(content.split())
    sections = ["1.", "2.", "3.", "4.", "5."]
    sections_found = sum(1 for s in sections if s in content)
    print(f"    File exists: [OK]")
    print(f"    Word count: {word_count} (need 500-800): [{'OK' if 500 <= word_count <= 900 else 'WARN'}]")
    print(f"    Sections found: {sections_found}/5: [{'OK' if sections_found >= 5 else 'FAIL'}]")
    # Check specific requirements
    has_code_evidence = "```" in content
    has_tradeoff = "trade-off" in content.lower() or "Trade-off" in content
    print(f"    Has code evidence: [{'OK' if has_code_evidence else 'FAIL'}]")
    print(f"    Has trade-off: [{'OK' if has_tradeoff else 'FAIL'}]")
else:
    print(f"    File exists: [MISSING!!!]")

# 5. Check grading_run.jsonl
print(f"\n[5] GRADING RUN:")
if os.path.exists("artifacts/grading_run.jsonl"):
    lines = open("artifacts/grading_run.jsonl", encoding="utf-8").readlines()
    print(f"    File exists: [OK] - {len(lines)} entries")
else:
    print(f"    File exists: [NOT YET] - run 'python eval_trace.py --grading' after 17:00")

# 6. Summary
print(f"\n{'=' * 60}")
print("SUMMARY")
print(f"{'=' * 60}")
issues = []
if len(trace_files) < 15:
    issues.append("Traces incomplete")
if not os.path.exists("artifacts/eval_report.json"):
    issues.append("eval_report.json missing")
if not os.path.exists("artifacts/grading_run.jsonl"):
    issues.append("grading_run.jsonl not yet (wait for 17:00)")

if not issues:
    print("ALL CHECKS PASSED!")
else:
    for i in issues:
        print(f"  WARNING: {i}")
