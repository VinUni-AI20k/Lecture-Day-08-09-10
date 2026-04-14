"""
eval_trace.py — Trace Evaluation & Comparison
Sprint 4: Chạy pipeline với test questions, phân tích trace, so sánh single vs multi.

Chạy:
    python eval_trace.py                  # Chạy 15 test questions
    python eval_trace.py --grading        # Chạy grading questions (sau 17:00)
    python eval_trace.py --analyze        # Phân tích trace đã có
    python eval_trace.py --compare        # So sánh single vs multi

Outputs:
    artifacts/traces/          — trace của từng câu hỏi
    artifacts/grading_run.jsonl — log câu hỏi chấm điểm
    artifacts/eval_report.json  — báo cáo tổng kết
"""

import json
import os
import sys
import argparse
import statistics
from datetime import datetime
from typing import Optional

# Import graph
sys.path.insert(0, os.path.dirname(__file__))
from graph import run_graph, save_trace


# ─────────────────────────────────────────────
# 1. Run Pipeline on Test Questions
# ─────────────────────────────────────────────

def run_test_questions(questions_file: str = "data/test_questions.json") -> list:
    """
    Chạy pipeline với danh sách câu hỏi, lưu trace từng câu.

    Returns:
        list of (question, result) tuples
    """
    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)

    print(f"\n📋 Running {len(questions)} test questions from {questions_file}")
    print("=" * 60)

    results = []
    for i, q in enumerate(questions, 1):
        question_text = q["question"]
        q_id = q.get("id", f"q{i:02d}")

        print(f"[{i:02d}/{len(questions)}] {q_id}: {question_text[:65]}...")

        try:
            result = run_graph(question_text)
            result["question_id"] = q_id

            # Save individual trace
            trace_file = save_trace(result, f"artifacts/traces")
            print(f"  ✓ route={result.get('supervisor_route', '?')}, "
                  f"conf={result.get('confidence', 0):.2f}, "
                  f"{result.get('latency_ms', 0)}ms")

            results.append({
                "id": q_id,
                "question": question_text,
                "expected_answer": q.get("expected_answer", ""),
                "expected_sources": q.get("expected_sources", []),
                "difficulty": q.get("difficulty", "unknown"),
                "category": q.get("category", "unknown"),
                "result": result,
            })

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append({
                "id": q_id,
                "question": question_text,
                "error": str(e),
                "result": None,
            })

    print(f"\n✅ Done. {sum(1 for r in results if r.get('result'))} / {len(results)} succeeded.")
    return results


# ─────────────────────────────────────────────
# 2. Run Grading Questions (Sprint 4)
# ─────────────────────────────────────────────

def run_grading_questions(questions_file: str = "data/grading_questions.json") -> str:
    """
    Chạy pipeline với grading questions và lưu JSONL log.
    Dùng cho chấm điểm nhóm (chạy sau khi grading_questions.json được public lúc 17:00).

    Returns:
        path tới grading_run.jsonl
    """
    if not os.path.exists(questions_file):
        print(f"❌ {questions_file} chưa được public (sau 17:00 mới có).")
        return ""

    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)

    os.makedirs("artifacts", exist_ok=True)
    output_file = "artifacts/grading_run.jsonl"

    print(f"\n🎯 Running GRADING questions — {len(questions)} câu")
    print(f"   Output → {output_file}")
    print("=" * 60)

    with open(output_file, "w", encoding="utf-8") as out:
        for i, q in enumerate(questions, 1):
            q_id = q.get("id", f"gq{i:02d}")
            question_text = q["question"]
            print(f"[{i:02d}/{len(questions)}] {q_id}: {question_text[:65]}...")

            try:
                result = run_graph(question_text)
                record = {
                    "id": q_id,
                    "question": question_text,
                    "answer": result.get("final_answer", "PIPELINE_ERROR: no answer"),
                    "sources": result.get("retrieved_sources", []),
                    "supervisor_route": result.get("supervisor_route", ""),
                    "route_reason": result.get("route_reason", ""),
                    "workers_called": result.get("workers_called", []),
                    "mcp_tools_used": [t.get("tool") for t in result.get("mcp_tools_used", [])],
                    "confidence": result.get("confidence", 0.0),
                    "hitl_triggered": result.get("hitl_triggered", False),
                    "latency_ms": result.get("latency_ms"),
                    "timestamp": datetime.now().isoformat(),
                }
                print(f"  ✓ route={record['supervisor_route']}, conf={record['confidence']:.2f}")
            except Exception as e:
                record = {
                    "id": q_id,
                    "question": question_text,
                    "answer": f"PIPELINE_ERROR: {e}",
                    "sources": [],
                    "supervisor_route": "error",
                    "route_reason": str(e),
                    "workers_called": [],
                    "mcp_tools_used": [],
                    "confidence": 0.0,
                    "hitl_triggered": False,
                    "latency_ms": None,
                    "timestamp": datetime.now().isoformat(),
                }
                print(f"  ✗ ERROR: {e}")

            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n✅ Grading log saved → {output_file}")
    return output_file


# ─────────────────────────────────────────────
# 3. Analyze Traces
# ─────────────────────────────────────────────

def _percentile(data: list, p: float) -> float:
    """Tính percentile p (0-100) từ sorted data."""
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    d = k - f
    return round(sorted_data[f] + d * (sorted_data[c] - sorted_data[f]))


def check_routing_accuracy(traces_dir: str = "artifacts/traces",
                           questions_file: str = "data/test_questions.json") -> dict:
    """
    So sánh supervisor_route thực tế với expected_route từ test_questions.json.
    Trả về routing accuracy và danh sách mismatches.
    """
    if not os.path.exists(questions_file):
        return {"accuracy": "N/A", "note": "test_questions.json not found"}

    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)
    expected = {q["id"]: q.get("expected_route", "") for q in questions}

    if not os.path.exists(traces_dir):
        return {"accuracy": "N/A", "note": "traces dir not found"}

    trace_files = [f for f in os.listdir(traces_dir) if f.endswith(".json")]
    traces = []
    for fname in trace_files:
        with open(os.path.join(traces_dir, fname), encoding="utf-8") as f:
            traces.append(json.load(f))

    correct = 0
    total_checked = 0
    mismatches = []

    for t in traces:
        q_id = t.get("question_id", "")
        actual_route = t.get("supervisor_route", "")
        exp_route = expected.get(q_id, "")
        if not exp_route:
            continue
        total_checked += 1
        if actual_route == exp_route:
            correct += 1
        else:
            mismatches.append({
                "id": q_id,
                "task": t.get("task", "")[:60],
                "expected": exp_route,
                "actual": actual_route,
            })

    acc = round(correct / total_checked * 100, 1) if total_checked else 0
    return {
        "accuracy_pct": acc,
        "correct": correct,
        "total": total_checked,
        "mismatches": mismatches,
    }


def analyze_traces(traces_dir: str = "artifacts/traces") -> dict:
    """
    Đọc tất cả trace files và tính metrics tổng hợp.

    Metrics:
    - routing_distribution: % câu đi vào mỗi worker
    - avg_confidence: confidence trung bình
    - latency: mean, median (p50), p95, p99
    - mcp_usage_rate: % câu có MCP tool call
    - hitl_rate: % câu trigger HITL
    - routing_accuracy: so sánh với expected_route
    - source_coverage: các tài liệu nào được dùng nhiều nhất

    Returns:
        dict of metrics
    """
    if not os.path.exists(traces_dir):
        print(f"⚠️  {traces_dir} không tồn tại. Chạy run_test_questions() trước.")
        return {}

    trace_files = [f for f in os.listdir(traces_dir) if f.endswith(".json")]
    if not trace_files:
        print(f"⚠️  Không có trace files trong {traces_dir}.")
        return {}

    traces = []
    for fname in trace_files:
        with open(os.path.join(traces_dir, fname), encoding="utf-8") as f:
            traces.append(json.load(f))

    # Compute metrics
    routing_counts = {}
    confidences = []
    latencies = []
    mcp_calls = 0
    hitl_triggers = 0
    source_counts = {}

    for t in traces:
        route = t.get("supervisor_route", "unknown")
        routing_counts[route] = routing_counts.get(route, 0) + 1

        conf = t.get("confidence", 0)
        if conf:
            confidences.append(conf)

        lat = t.get("latency_ms")
        if lat:
            latencies.append(lat)

        if t.get("mcp_tools_used"):
            mcp_calls += 1

        if t.get("hitl_triggered"):
            hitl_triggers += 1

        for src in t.get("retrieved_sources", []):
            source_counts[src] = source_counts.get(src, 0) + 1

    total = len(traces)

    # Latency distribution
    latency_stats = {}
    if latencies:
        latency_stats = {
            "mean_ms": round(statistics.mean(latencies)),
            "median_ms": round(statistics.median(latencies)),
            "p95_ms": _percentile(latencies, 95),
            "p99_ms": _percentile(latencies, 99),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
        }

    # Routing accuracy
    routing_acc = check_routing_accuracy(traces_dir)

    metrics = {
        "total_traces": total,
        "routing_distribution": {k: f"{v}/{total} ({100*v//total}%)" for k, v in routing_counts.items()},
        "routing_accuracy": routing_acc,
        "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        "confidence_range": f"{min(confidences):.2f} – {max(confidences):.2f}" if confidences else "N/A",
        "latency": latency_stats,
        "mcp_usage_rate": f"{mcp_calls}/{total} ({100*mcp_calls//total}%)" if total else "0%",
        "hitl_rate": f"{hitl_triggers}/{total} ({100*hitl_triggers//total}%)" if total else "0%",
        "top_sources": sorted(source_counts.items(), key=lambda x: -x[1])[:5],
    }

    return metrics


# ─────────────────────────────────────────────
# 4. Compare Single vs Multi Agent
# ─────────────────────────────────────────────

def compare_single_vs_multi(
    multi_traces_dir: str = "artifacts/traces",
    day08_results_file: Optional[str] = None,
) -> dict:
    """
    So sánh Day 08 (single agent RAG) vs Day 09 (multi-agent).

    Returns:
        dict của comparison metrics
    """
    multi_metrics = analyze_traces(multi_traces_dir)

    # Day 08 baseline — single-agent RAG pipeline
    # Ước lượng dựa trên kiến trúc Day 08: 1 retriever + 1 LLM call, không routing
    day08_baseline = {
        "architecture": "Single-agent RAG (retrieve → generate)",
        "total_questions": 15,
        "avg_confidence": 0.72,
        "avg_latency_ms": 2800,
        "routing": "Không có — mọi câu đi qua 1 pipeline duy nhất",
        "exception_handling": "Không có — phải hard-code trong prompt",
        "abstain_capability": "Yếu — không có confidence threshold rõ ràng",
        "multi_hop_support": "Không — chỉ 1 lần retrieve, không cross-doc",
        "debuggability": "Thấp — không trace được lỗi ở retrieval hay generation",
    }

    if day08_results_file and os.path.exists(day08_results_file):
        with open(day08_results_file, encoding="utf-8") as f:
            day08_baseline = json.load(f)

    # Compute deltas
    multi_avg_lat = multi_metrics.get("latency", {}).get("mean_ms", 0)
    multi_avg_conf = multi_metrics.get("avg_confidence", 0)
    day08_lat = day08_baseline.get("avg_latency_ms", 2800)
    day08_conf = day08_baseline.get("avg_confidence", 0.72)

    lat_delta = multi_avg_lat - day08_lat if multi_avg_lat else "N/A"
    conf_delta = round(multi_avg_conf - day08_conf, 3) if multi_avg_conf else "N/A"

    comparison = {
        "generated_at": datetime.now().isoformat(),
        "day08_single_agent": day08_baseline,
        "day09_multi_agent": multi_metrics,
        "analysis": {
            "latency_delta_ms": lat_delta,
            "confidence_delta": conf_delta,
            "routing_visibility": (
                "Day 09: mỗi câu có route_reason + supervisor_route → dễ debug. "
                "Day 08: black box, không biết lỗi ở retrieval hay generation."
            ),
            "debuggability": (
                "Multi-agent: test từng worker độc lập, trace mỗi bước. "
                "Single-agent: phải debug toàn pipeline."
            ),
            "exception_handling": (
                "Day 09: policy_tool_worker kiểm tra Flash Sale, digital product, temporal scoping. "
                "Day 08: phải nhồi mọi rule vào 1 prompt."
            ),
            "extensibility": (
                "Day 09: thêm capability qua MCP tool mới, không sửa core. "
                "Day 08: phải sửa code pipeline."
            ),
            "multi_hop": (
                "Day 09: routing cho phép gọi nhiều worker cho câu cross-doc (q13, q15). "
                "Day 08: chỉ 1 lần retrieve → miss context."
            ),
        },
    }

    return comparison


# ─────────────────────────────────────────────
# 5. Save Eval Report
# ─────────────────────────────────────────────

def save_eval_report(comparison: dict) -> str:
    """Lưu báo cáo eval tổng kết ra file JSON."""
    os.makedirs("artifacts", exist_ok=True)
    output_file = "artifacts/eval_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    return output_file


# ─────────────────────────────────────────────
# 5b. Auto-update single_vs_multi_comparison.md
# ─────────────────────────────────────────────

def update_comparison_doc(metrics: dict):
    """
    Tự động cập nhật docs/single_vs_multi_comparison.md
    với số liệu thực từ trace — thay thế '(từ trace)'.
    """
    doc_path = "docs/single_vs_multi_comparison.md"
    if not os.path.exists(doc_path):
        print(f"⚠️  {doc_path} không tồn tại, bỏ qua auto-update.")
        return

    with open(doc_path, encoding="utf-8") as f:
        content = f.read()

    # Lấy metrics
    avg_conf = metrics.get("avg_confidence", "N/A")
    lat = metrics.get("latency", {})
    avg_lat = lat.get("mean_ms", "N/A")
    hitl_rate = metrics.get("hitl_rate", "N/A")
    mcp_rate = metrics.get("mcp_usage_rate", "N/A")
    routing_acc = metrics.get("routing_accuracy", {})
    acc_pct = routing_acc.get("accuracy_pct", "N/A")

    # Thay placeholder
    content = content.replace(
        "| Avg confidence | ~0.72 | (từ trace) |",
        f"| Avg confidence | ~0.72 | {avg_conf} |"
    )
    content = content.replace(
        "| Avg latency (ms) | ~2800 | (từ trace) |",
        f"| Avg latency (ms) | ~2800 | {avg_lat} |"
    )
    content = content.replace(
        "| Abstain rate (%) | ~5% | (từ trace) |",
        f"| Abstain rate (%) | ~5% | {hitl_rate} |"
    )
    content = content.replace(
        "| Multi-hop accuracy | ~30% | (từ trace) |",
        f"| Multi-hop accuracy | ~30% | routing {acc_pct}% |"
    )

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"📝 Auto-updated {doc_path} with real metrics.")


# ─────────────────────────────────────────────
# 6. CLI Entry Point
# ─────────────────────────────────────────────

def print_metrics(metrics: dict):
    """Print metrics đẹp."""
    if not metrics:
        return
    print("\n📊 Trace Analysis:")
    for k, v in metrics.items():
        if isinstance(v, list):
            print(f"  {k}:")
            for item in v:
                print(f"    • {item}")
        elif isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Day 09 Lab — Trace Evaluation")
    parser.add_argument("--grading", action="store_true", help="Run grading questions")
    parser.add_argument("--analyze", action="store_true", help="Analyze existing traces")
    parser.add_argument("--compare", action="store_true", help="Compare single vs multi")
    parser.add_argument("--test-file", default="data/test_questions.json", help="Test questions file")
    args = parser.parse_args()

    if args.grading:
        # Chạy grading questions
        log_file = run_grading_questions()
        if log_file:
            print(f"\n✅ Grading log: {log_file}")
            print("   Nộp file này trước 18:00!")

    elif args.analyze:
        # Phân tích traces
        metrics = analyze_traces()
        print_metrics(metrics)

    elif args.compare:
        # So sánh single vs multi
        comparison = compare_single_vs_multi()
        report_file = save_eval_report(comparison)
        print(f"\n📊 Comparison report saved → {report_file}")
        print("\n=== Day 08 vs Day 09 ===")
        for k, v in comparison.get("analysis", {}).items():
            print(f"  {k}: {v}")

    else:
        # Default: chạy test questions
        results = run_test_questions(args.test_file)

        # Phân tích trace
        metrics = analyze_traces()
        print_metrics(metrics)

        # Tự động cập nhật comparison doc với số liệu thực
        update_comparison_doc(metrics)

        # Lưu báo cáo
        comparison = compare_single_vs_multi()
        report_file = save_eval_report(comparison)
        print(f"\n📄 Eval report → {report_file}")
        print("\n✅ Sprint 4 complete! Tất cả output đã sẵn sàng để commit.")
