"""
eval_trace.py — Sprint 4 evaluator for Day 09

Chức năng:
- Chạy pipeline trên test questions
- Lưu trace theo từng run (thư mục riêng)
- Sinh JSONL log + summary metrics từ run thực tế
- (Tuỳ chọn) so sánh với baseline Day 08 nếu có file số liệu
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from graph import run_graph, save_trace


LAB_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = LAB_DIR / "artifacts"
TRACES_ROOT = ARTIFACTS_DIR / "traces"
RUNS_DIR = ARTIFACTS_DIR / "runs"
DEFAULT_TEST_FILE = LAB_DIR / "data" / "test_questions.json"
DEFAULT_DAY08_BASELINE = ARTIFACTS_DIR / "day08_baseline.json"


def _ensure_dirs() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    TRACES_ROOT.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _new_run_name(prefix: str = "test") -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _safe_short(text: str, n: int = 120) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= n else text[: n - 3].rstrip() + "..."


def run_test_questions(
    questions_file: str | Path = DEFAULT_TEST_FILE,
    run_name: Optional[str] = None,
) -> dict[str, Any]:
    """Run full pipeline on test questions and persist traces/logs for this run."""
    _ensure_dirs()

    q_path = Path(questions_file)
    if not q_path.is_absolute():
        q_path = LAB_DIR / q_path
    if not q_path.exists():
        raise FileNotFoundError(f"questions file not found: {q_path}")

    with q_path.open("r", encoding="utf-8") as f:
        questions = json.load(f)

    run_name = run_name or _new_run_name("sprint4_test")
    run_dir = TRACES_ROOT / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    jsonl_file = RUNS_DIR / f"{run_name}.jsonl"

    print(f"\n📋 Running {len(questions)} questions")
    print(f"   Questions: {q_path}")
    print(f"   Traces   : {run_dir}")
    print(f"   JSONL    : {jsonl_file}")
    print("=" * 72)

    records: list[dict[str, Any]] = []

    with jsonl_file.open("w", encoding="utf-8") as out:
        for idx, item in enumerate(questions, start=1):
            qid = item.get("id", f"q{idx:02d}")
            question = item["question"]
            expected_route = item.get("expected_route")

            print(f"[{idx:02d}/{len(questions)}] {qid}: {_safe_short(question, 72)}")

            try:
                result = run_graph(question)
                result["question_id"] = qid

                trace_file = save_trace(result, str(run_dir))
                route = result.get("supervisor_route", "")
                confidence = float(result.get("confidence", 0.0) or 0.0)
                latency_ms = result.get("latency_ms")
                route_ok = route == expected_route if expected_route else None

                record = {
                    "id": qid,
                    "question": question,
                    "expected_route": expected_route,
                    "route_ok": route_ok,
                    "supervisor_route": route,
                    "route_reason": result.get("route_reason", ""),
                    "workers_called": result.get("workers_called", []),
                    "mcp_tools_used": result.get("mcp_tools_used", []),
                    "retrieved_sources": result.get("retrieved_sources", []),
                    "confidence": confidence,
                    "hitl_triggered": bool(result.get("hitl_triggered", False)),
                    "latency_ms": latency_ms,
                    "trace_file": trace_file,
                    "answer_preview": _safe_short(result.get("final_answer", ""), 180),
                    "timestamp": datetime.now().isoformat(),
                    "error": None,
                }

                print(
                    f"  ✓ route={route}"
                    f", route_ok={route_ok}"
                    f", conf={confidence:.2f}"
                    f", latency={latency_ms}ms"
                )
            except Exception as exc:
                record = {
                    "id": qid,
                    "question": question,
                    "expected_route": expected_route,
                    "route_ok": False,
                    "supervisor_route": "error",
                    "route_reason": str(exc),
                    "workers_called": [],
                    "mcp_tools_used": [],
                    "retrieved_sources": [],
                    "confidence": 0.0,
                    "hitl_triggered": False,
                    "latency_ms": None,
                    "trace_file": None,
                    "answer_preview": f"PIPELINE_ERROR: {exc}",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(exc),
                }
                print(f"  ✗ ERROR: {exc}")

            records.append(record)
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = summarize_records(records)
    summary.update(
        {
            "run_name": run_name,
            "questions_file": str(q_path),
            "trace_dir": str(run_dir),
            "jsonl_file": str(jsonl_file),
            "generated_at": datetime.now().isoformat(),
        }
    )

    summary_file = RUNS_DIR / f"{run_name}_summary.json"
    with summary_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n✅ Sprint 4 run complete")
    print(f"   Summary : {summary_file}")
    return summary


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    success = [r for r in records if not r.get("error")]
    failed = [r for r in records if r.get("error")]

    route_counts: dict[str, int] = {}
    conf_values: list[float] = []
    lat_values: list[float] = []
    source_counts: dict[str, int] = {}
    hitl = 0
    mcp_used = 0
    route_eval = [r for r in records if r.get("expected_route") is not None and r.get("error") is None]
    route_correct = sum(1 for r in route_eval if r.get("route_ok") is True)

    for r in success:
        route = r.get("supervisor_route", "unknown")
        route_counts[route] = route_counts.get(route, 0) + 1

        conf = r.get("confidence")
        if isinstance(conf, (int, float)):
            conf_values.append(float(conf))

        lat = r.get("latency_ms")
        if isinstance(lat, (int, float)):
            lat_values.append(float(lat))

        if r.get("hitl_triggered"):
            hitl += 1

        if r.get("mcp_tools_used"):
            mcp_used += 1

        for src in r.get("retrieved_sources", []) or []:
            source_counts[src] = source_counts.get(src, 0) + 1

    def _pct(n: int, d: int) -> float:
        return round((100.0 * n / d), 2) if d else 0.0

    summary = {
        "total_questions": total,
        "successful_runs": len(success),
        "failed_runs": len(failed),
        "routing_distribution": route_counts,
        "avg_confidence": round(sum(conf_values) / len(conf_values), 3) if conf_values else 0.0,
        "avg_latency_ms": round(sum(lat_values) / len(lat_values), 2) if lat_values else 0.0,
        "mcp_usage": {
            "count": mcp_used,
            "rate_percent": _pct(mcp_used, len(success)),
        },
        "hitl_usage": {
            "count": hitl,
            "rate_percent": _pct(hitl, len(success)),
        },
        "route_accuracy": {
            "evaluated": len(route_eval),
            "correct": route_correct,
            "rate_percent": _pct(route_correct, len(route_eval)),
        },
        "top_sources": sorted(source_counts.items(), key=lambda x: (-x[1], x[0]))[:10],
        "failed_ids": [r.get("id") for r in failed],
    }
    return summary


def compare_single_vs_multi(
    multi_summary: dict[str, Any],
    day08_baseline_file: str | Path | None = None,
) -> dict[str, Any]:
    """Compare current Day 09 run against optional Day 08 baseline file."""
    baseline_path: Optional[Path] = None
    if day08_baseline_file:
        baseline_path = Path(day08_baseline_file)
        if not baseline_path.is_absolute():
            baseline_path = LAB_DIR / baseline_path
    else:
        baseline_path = DEFAULT_DAY08_BASELINE

    day08: dict[str, Any] | None = None
    if baseline_path and baseline_path.exists():
        with baseline_path.open("r", encoding="utf-8") as f:
            day08 = json.load(f)

    day09 = {
        "total_questions": multi_summary.get("total_questions"),
        "avg_confidence": multi_summary.get("avg_confidence"),
        "avg_latency_ms": multi_summary.get("avg_latency_ms"),
        "hitl_rate_percent": multi_summary.get("hitl_usage", {}).get("rate_percent"),
        "mcp_usage_rate_percent": multi_summary.get("mcp_usage", {}).get("rate_percent"),
        "route_accuracy_percent": multi_summary.get("route_accuracy", {}).get("rate_percent"),
        "routing_distribution": multi_summary.get("routing_distribution", {}),
    }

    analysis_notes: list[str] = [
        "Day 09 includes supervisor route_reason and worker-level traceability.",
        "MCP usage is measurable from mcp_tools_used in each trace.",
    ]

    delta: dict[str, Any] = {}
    if day08:
        d08_conf = day08.get("avg_confidence")
        d09_conf = day09.get("avg_confidence")
        if isinstance(d08_conf, (int, float)) and isinstance(d09_conf, (int, float)):
            delta["avg_confidence"] = round(float(d09_conf) - float(d08_conf), 3)

        d08_lat = day08.get("avg_latency_ms")
        d09_lat = day09.get("avg_latency_ms")
        if isinstance(d08_lat, (int, float)) and isinstance(d09_lat, (int, float)):
            delta["avg_latency_ms"] = round(float(d09_lat) - float(d08_lat), 2)
    else:
        analysis_notes.append("Day 08 baseline file not found; cross-day numeric deltas are N/A for this run.")

    return {
        "generated_at": datetime.now().isoformat(),
        "day08_single_agent": day08,
        "day09_multi_agent": day09,
        "delta": delta,
        "analysis_notes": analysis_notes,
    }


def save_eval_report(report: dict[str, Any], output_file: str | Path = ARTIFACTS_DIR / "eval_report.json") -> str:
    out = Path(output_file)
    if not out.is_absolute():
        out = LAB_DIR / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return str(out)


def print_summary(summary: dict[str, Any]) -> None:
    print("\n📊 Run Summary")
    print("-" * 72)
    print(f"total_questions   : {summary.get('total_questions')}")
    print(f"successful_runs   : {summary.get('successful_runs')}")
    print(f"failed_runs       : {summary.get('failed_runs')}")
    print(f"avg_confidence    : {summary.get('avg_confidence')}")
    print(f"avg_latency_ms    : {summary.get('avg_latency_ms')}")
    print(f"mcp_usage         : {summary.get('mcp_usage')}")
    print(f"hitl_usage        : {summary.get('hitl_usage')}")
    print(f"route_accuracy    : {summary.get('route_accuracy')}")
    print(f"routing_dist      : {summary.get('routing_distribution')}")
    print(f"top_sources       : {summary.get('top_sources')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Day 09 Sprint 4 evaluator")
    parser.add_argument("--run", action="store_true", help="Run test questions and save traces")
    parser.add_argument("--test-file", default=str(DEFAULT_TEST_FILE), help="Path to test questions JSON")
    parser.add_argument("--run-name", default=None, help="Optional run name")
    parser.add_argument("--compare", action="store_true", help="Generate Day08 vs Day09 comparison report")
    parser.add_argument("--day08-baseline", default=str(DEFAULT_DAY08_BASELINE), help="Path to Day08 baseline JSON")
    args = parser.parse_args()

    if args.run:
        summary = run_test_questions(args.test_file, args.run_name)
        print_summary(summary)

        report = {
            "run_summary": summary,
            "comparison": compare_single_vs_multi(summary, args.day08_baseline) if args.compare else None,
        }
        report_file = save_eval_report(report)
        print(f"\n📄 Eval report: {report_file}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
