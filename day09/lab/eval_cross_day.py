"""
eval_cross_day.py — Day08 (single-agent) vs Day09 (multi-agent) metric bridge

Mục tiêu:
1) Chuyển đổi metric Day08 (thang 1-5) sang không gian gần Day09 (0-1) để so sánh.
2) Tính thêm các metric còn thiếu bằng test heuristics cho CẢ hai hệ.
3) Xuất báo cáo JSON + Markdown phục vụ report sprint 4.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


LAB_DIR = Path(__file__).resolve().parent
DAY08_DIR = LAB_DIR.parent.parent / "day08" / "lab"
DEFAULT_DAY08_CSV = DAY08_DIR / "results" / "ab_comparison.csv"
DEFAULT_DAY08_TEST_FILE = DAY08_DIR / "data" / "test_questions.json"
DEFAULT_DAY08_CONFIG = "baseline_dense"
DEFAULT_DAY09_TEST_FILE = LAB_DIR / "data" / "test_questions.json"
DEFAULT_DAY09_RUNS_DIR = LAB_DIR / "artifacts" / "runs"
DEFAULT_OUTPUT_JSON = LAB_DIR / "artifacts" / "cross_day_metrics.json"
DEFAULT_OUTPUT_MD = LAB_DIR / "artifacts" / "cross_day_metrics.md"

ABSTAIN_MARKERS = (
    "không đủ thông tin",
    "không tìm thấy",
    "không có thông tin",
    "không thể tìm thấy",
    "tôi không biết",
    "i don't know",
    "not enough information",
    "insufficient context",
)


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _safe_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _parse_list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    text = str(value).strip()
    if not text:
        return []

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass

    # fallback: split by comma
    return [x.strip() for x in text.split(",") if x.strip()]


def _parse_retrieved_ratio_from_note(note: str) -> Optional[float]:
    if not note:
        return None
    m = re.search(r"retrieved\s*:\s*(\d+)\s*/\s*(\d+)", note, flags=re.IGNORECASE)
    if not m:
        return None
    hit = int(m.group(1))
    total = int(m.group(2))
    if total <= 0:
        return None
    return hit / total


def _contains_abstain(answer: str) -> bool:
    lower = (answer or "").lower()
    return any(marker in lower for marker in ABSTAIN_MARKERS)


def _has_citation(answer: str) -> bool:
    return bool(re.search(r"\[[^\]]+\]", answer or ""))


def _extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text or ""))


def _normalize_source(source: str) -> str:
    s = (source or "").strip().lower().replace("\\", "/")
    name = s.split("/")[-1]
    name = name.replace(".pdf", "").replace(".md", "").replace(".txt", "")
    return name


def _source_recall_ratio(expected_sources: list[str], retrieved_sources: list[str]) -> Optional[float]:
    if not expected_sources:
        return None

    expected_norm = [_normalize_source(src) for src in expected_sources]
    retrieved_norm = [_normalize_source(src) for src in retrieved_sources]

    hits = 0
    for expected in expected_norm:
        if any(expected in got or got in expected for got in retrieved_norm):
            hits += 1
    return hits / max(1, len(expected_norm))


def _numeric_consistency(expected_answer: str, answer: str) -> Optional[float]:
    expected_nums = _extract_numbers(expected_answer)
    if not expected_nums:
        return None
    answer_nums = _extract_numbers(answer)
    return len(expected_nums & answer_nums) / max(1, len(expected_nums))


def _convert_day08_confidence(row: dict[str, Any]) -> float:
    """
    Bridge Day08 (1-5 metrics) -> pseudo-confidence (0-1), calibrated to Day09 semantics.

    Conversion weights (sum=1.0):
      faithfulness 0.35
      relevance    0.25
      completeness 0.25
      recall       0.15
    """
    faith = (_safe_float(row.get("faithfulness")) or 0.0) / 5.0
    rel = (_safe_float(row.get("relevance")) or 0.0) / 5.0
    comp = (_safe_float(row.get("completeness")) or 0.0) / 5.0

    recall_raw = _safe_float(row.get("context_recall"))
    if recall_raw is None:
        # no expected source case -> reward safe abstain, penalize confident non-abstain
        recall = 1.0 if row.get("expected_abstain") and row.get("abstain") else 0.4
    else:
        recall = recall_raw / 5.0

    conf = 0.35 * faith + 0.25 * rel + 0.25 * comp + 0.15 * recall

    # small calibration bonuses
    if row.get("citation"):
        conf += 0.03
    if row.get("expected_abstain") and row.get("abstain"):
        conf += 0.05

    return round(max(0.1, min(0.95, conf)), 3)


def _load_day08_rows(csv_file: Path, config_label: str, day08_test_file: Path) -> list[dict[str, Any]]:
    with day08_test_file.open("r", encoding="utf-8") as f:
        test_questions = json.load(f)
    qmap = {q["id"]: q for q in test_questions}

    with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
        raw_rows = list(csv.DictReader(f))

    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        if raw.get("config_label") != config_label:
            continue

        qid = raw.get("id")
        q = qmap.get(qid, {})

        expected_sources = _parse_list_field(raw.get("expected_sources"))
        if not expected_sources:
            expected_sources = [str(s) for s in q.get("expected_sources", [])]

        retrieved_sources = _parse_list_field(raw.get("sources"))
        answer = str(raw.get("answer") or "")
        expected_answer = str(raw.get("expected_answer") or q.get("expected_answer") or "")
        category = str(raw.get("category") or q.get("category") or "")
        question = str(raw.get("query") or q.get("question") or "")

        context_recall_notes = str(raw.get("context_recall_notes") or "")
        inferred_ratio = _parse_retrieved_ratio_from_note(context_recall_notes)

        expected_abstain = (not expected_sources) or ("insufficient" in category.lower())
        abstain = _contains_abstain(answer)
        citation = _has_citation(answer)
        if expected_sources:
            if retrieved_sources:
                source_recall = _source_recall_ratio(expected_sources, retrieved_sources)
            elif inferred_ratio is not None:
                source_recall = inferred_ratio
            else:
                # fallback: use evaluator score (1-5)
                recall_score = _safe_float(raw.get("context_recall"))
                source_recall = (recall_score / 5.0) if recall_score is not None else None
        else:
            source_recall = None

        numeric_consistency = _numeric_consistency(expected_answer, answer)

        row = {
            "id": raw.get("id"),
            "question": question,
            "category": category,
            "answer": answer,
            "expected_answer": expected_answer,
            "expected_sources": expected_sources,
            "retrieved_sources": retrieved_sources,
            "faithfulness": _safe_float(raw.get("faithfulness")),
            "relevance": _safe_float(raw.get("relevance")),
            "context_recall": _safe_float(raw.get("context_recall")),
            "completeness": _safe_float(raw.get("completeness")),
            "latency_ms": _safe_float(raw.get("latency_ms")),
            "answered": _safe_bool(raw.get("answered")),
            "abstain": abstain,
            "expected_abstain": expected_abstain,
            "citation": citation,
            "source_recall": source_recall,
            "numeric_consistency": numeric_consistency,
            "mcp_used": False,
            "route_ok": None,
            "hitl_triggered": None,
            "multi_hop": "cross-document" in category.lower(),
        }
        row["confidence_est"] = _convert_day08_confidence(row)
        row["hitl_estimated"] = row["confidence_est"] < 0.4
        rows.append(row)

    return rows


def _find_latest_day09_jsonl(runs_dir: Path) -> Optional[Path]:
    candidates = [
        path for path in runs_dir.glob("*.jsonl")
        if not path.name.endswith("_summary.jsonl")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _load_day09_rows(jsonl_file: Path, test_questions_file: Path) -> list[dict[str, Any]]:
    with test_questions_file.open("r", encoding="utf-8") as f:
        questions = json.load(f)
    qmap = {q["id"]: q for q in questions}

    rows: list[dict[str, Any]] = []
    with jsonl_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            qid = rec.get("id")
            q = qmap.get(qid, {})

            trace_file = rec.get("trace_file")
            answer = ""
            if trace_file and Path(trace_file).exists():
                try:
                    trace = json.loads(Path(trace_file).read_text(encoding="utf-8"))
                    answer = str(trace.get("final_answer") or "")
                except Exception:
                    answer = str(rec.get("answer_preview") or "")
            else:
                answer = str(rec.get("answer_preview") or "")

            expected_sources = [str(s) for s in q.get("expected_sources", [])]
            retrieved_sources = [str(s) for s in rec.get("retrieved_sources", [])]
            expected_answer = str(q.get("expected_answer") or "")
            test_type = str(q.get("test_type") or "")
            category = str(q.get("category") or "")

            expected_abstain = (not expected_sources) or (test_type == "abstain") or ("insufficient" in category.lower())
            abstain = _contains_abstain(answer)
            citation = _has_citation(answer)
            source_recall = _source_recall_ratio(expected_sources, retrieved_sources)
            numeric_consistency = _numeric_consistency(expected_answer, answer)
            multi_hop = "multi" in test_type.lower() or "multi-hop" in category.lower()

            row = {
                "id": qid,
                "question": rec.get("question"),
                "category": category,
                "answer": answer,
                "expected_answer": expected_answer,
                "expected_sources": expected_sources,
                "retrieved_sources": retrieved_sources,
                "faithfulness": None,
                "relevance": None,
                "context_recall": None,
                "completeness": None,
                "latency_ms": _safe_float(rec.get("latency_ms")),
                "answered": not bool(rec.get("error")),
                "abstain": abstain,
                "expected_abstain": expected_abstain,
                "citation": citation,
                "source_recall": source_recall,
                "numeric_consistency": numeric_consistency,
                "mcp_used": bool(rec.get("mcp_tools_used")),
                "route_ok": rec.get("route_ok"),
                "hitl_triggered": bool(rec.get("hitl_triggered", False)),
                "multi_hop": multi_hop,
                "confidence": _safe_float(rec.get("confidence")) or 0.0,
                "supervisor_route": rec.get("supervisor_route"),
            }
            rows.append(row)

    return rows


def _avg(values: list[Optional[float]]) -> Optional[float]:
    numeric = [float(v) for v in values if isinstance(v, (int, float))]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _pct(part: int, total: int) -> Optional[float]:
    if total <= 0:
        return None
    return 100.0 * part / total


def _summarize_day08(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_recall_values = [r.get("source_recall") for r in rows]
    numeric_values = [r.get("numeric_consistency") for r in rows]

    abstain_count = sum(1 for r in rows if r.get("abstain"))
    citation_count = sum(1 for r in rows if r.get("citation"))
    answered_count = sum(1 for r in rows if r.get("answered"))
    hitl_estimated_count = sum(1 for r in rows if r.get("hitl_estimated"))

    return {
        "question_count": len(rows),
        "avg_confidence": round(_avg([r.get("confidence_est") for r in rows]) or 0.0, 3),
        "avg_latency_ms": round(_avg([r.get("latency_ms") for r in rows]) or 0.0, 3),
        "answered_rate_percent": round(_pct(answered_count, len(rows)) or 0.0, 2),
        "abstain_rate_percent": round(_pct(abstain_count, len(rows)) or 0.0, 2),
        "citation_rate_percent": round(_pct(citation_count, len(rows)) or 0.0, 2),
        "source_recall_rate_percent": round(100.0 * ((_avg(source_recall_values) or 0.0)), 2),
        "numeric_consistency_rate_percent": round(100.0 * ((_avg(numeric_values) or 0.0)), 2),
        "mcp_usage_rate_percent": 0.0,
        "hitl_rate_percent": round(_pct(hitl_estimated_count, len(rows)) or 0.0, 2),
        "route_accuracy_percent": None,
    }


def _summarize_day09(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_recall_values = [r.get("source_recall") for r in rows]
    numeric_values = [r.get("numeric_consistency") for r in rows]

    abstain_count = sum(1 for r in rows if r.get("abstain"))
    citation_count = sum(1 for r in rows if r.get("citation"))
    answered_count = sum(1 for r in rows if r.get("answered"))
    mcp_count = sum(1 for r in rows if r.get("mcp_used"))
    hitl_count = sum(1 for r in rows if r.get("hitl_triggered"))

    route_rows = [r for r in rows if isinstance(r.get("route_ok"), bool)]
    route_ok_count = sum(1 for r in route_rows if r.get("route_ok") is True)

    return {
        "question_count": len(rows),
        "avg_confidence": round(_avg([r.get("confidence") for r in rows]) or 0.0, 3),
        "avg_latency_ms": round(_avg([r.get("latency_ms") for r in rows]) or 0.0, 3),
        "answered_rate_percent": round(_pct(answered_count, len(rows)) or 0.0, 2),
        "abstain_rate_percent": round(_pct(abstain_count, len(rows)) or 0.0, 2),
        "citation_rate_percent": round(_pct(citation_count, len(rows)) or 0.0, 2),
        "source_recall_rate_percent": round(100.0 * ((_avg(source_recall_values) or 0.0)), 2),
        "numeric_consistency_rate_percent": round(100.0 * ((_avg(numeric_values) or 0.0)), 2),
        "mcp_usage_rate_percent": round(_pct(mcp_count, len(rows)) or 0.0, 2),
        "hitl_rate_percent": round(_pct(hitl_count, len(rows)) or 0.0, 2),
        "route_accuracy_percent": round(_pct(route_ok_count, len(route_rows)) or 0.0, 2) if route_rows else None,
    }


def _run_dataset_tests(rows: list[dict[str, Any]], has_routes: bool) -> dict[str, Any]:
    tests: dict[str, dict[str, Any]] = {}

    def _mk_result(name: str, candidates: list[dict[str, Any]], predicate) -> None:
        total = len(candidates)
        if total == 0:
            tests[name] = {
                "applicable": False,
                "passed": 0,
                "total": 0,
                "pass_rate_percent": None,
            }
            return
        passed = sum(1 for row in candidates if predicate(row))
        tests[name] = {
            "applicable": True,
            "passed": passed,
            "total": total,
            "pass_rate_percent": round(_pct(passed, total) or 0.0, 2),
        }

    abstain_rows = [r for r in rows if r.get("expected_abstain")]
    _mk_result("abstain_behavior", abstain_rows, lambda r: bool(r.get("abstain")))

    citation_rows = [r for r in rows if r.get("expected_sources") and not r.get("expected_abstain")]
    _mk_result("citation_presence", citation_rows, lambda r: bool(r.get("citation")))

    source_rows = [r for r in rows if r.get("expected_sources")]
    _mk_result("source_coverage_full", source_rows, lambda r: (r.get("source_recall") or 0.0) >= 1.0)

    numeric_rows = [r for r in rows if r.get("numeric_consistency") is not None]
    _mk_result("numeric_fidelity", numeric_rows, lambda r: (r.get("numeric_consistency") or 0.0) >= 1.0)

    multi_rows = [r for r in rows if r.get("multi_hop")]
    _mk_result(
        "multi_hop_support",
        multi_rows,
        lambda r: (not r.get("abstain")) and (len(set(r.get("retrieved_sources") or [])) >= 2),
    )

    if has_routes:
        route_rows = [r for r in rows if isinstance(r.get("route_ok"), bool)]
        _mk_result("route_correctness", route_rows, lambda r: r.get("route_ok") is True)
    else:
        tests["route_correctness"] = {
            "applicable": False,
            "passed": 0,
            "total": 0,
            "pass_rate_percent": None,
        }

    return tests


def _align_metrics(day08_summary: dict[str, Any], day09_summary: dict[str, Any]) -> list[dict[str, Any]]:
    metric_keys = [
        "avg_confidence",
        "avg_latency_ms",
        "answered_rate_percent",
        "abstain_rate_percent",
        "citation_rate_percent",
        "source_recall_rate_percent",
        "numeric_consistency_rate_percent",
        "mcp_usage_rate_percent",
        "hitl_rate_percent",
        "route_accuracy_percent",
    ]

    aligned: list[dict[str, Any]] = []
    for key in metric_keys:
        d08 = day08_summary.get(key)
        d09 = day09_summary.get(key)
        delta = None
        if isinstance(d08, (int, float)) and isinstance(d09, (int, float)):
            delta = round(float(d09) - float(d08), 3)
        aligned.append(
            {
                "metric": key,
                "day08_single_agent": d08,
                "day09_multi_agent": d09,
                "delta_day09_minus_day08": delta,
            }
        )
    return aligned


def _to_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Cross-Day Metrics Bridge (Day08 -> Day09)")
    lines.append("")
    lines.append(f"Generated: {payload['generated_at']}")
    lines.append("")

    lines.append("## Conversion notes")
    for note in payload.get("conversion_notes", []):
        lines.append(f"- {note}")
    lines.append("")

    lines.append("## Aligned metrics")
    lines.append("| Metric | Day08 (single) | Day09 (multi) | Delta (Day09-Day08) |")
    lines.append("|---|---:|---:|---:|")
    for row in payload["aligned_comparison"]:
        lines.append(
            f"| {row['metric']} | {row['day08_single_agent']} | {row['day09_multi_agent']} | {row['delta_day09_minus_day08']} |"
        )
    lines.append("")

    lines.append("## Additional tests")
    lines.append("### Day08")
    lines.append("| Test | Applicable | Passed/Total | Pass rate % |")
    lines.append("|---|---|---|---:|")
    for name, result in payload["day08"]["tests"].items():
        lines.append(
            f"| {name} | {result['applicable']} | {result['passed']}/{result['total']} | {result['pass_rate_percent']} |"
        )

    lines.append("")
    lines.append("### Day09")
    lines.append("| Test | Applicable | Passed/Total | Pass rate % |")
    lines.append("|---|---|---|---:|")
    for name, result in payload["day09"]["tests"].items():
        lines.append(
            f"| {name} | {result['applicable']} | {result['passed']}/{result['total']} | {result['pass_rate_percent']} |"
        )

    lines.append("")
    return "\n".join(lines)


def run(
    day08_csv: Path,
    day08_test_file: Path,
    day08_config: str,
    day09_jsonl: Optional[Path],
    day09_test_file: Path,
    output_json: Path,
    output_md: Path,
) -> dict[str, Any]:
    if not day08_csv.exists():
        raise FileNotFoundError(f"Day08 csv not found: {day08_csv}")
    if not day08_test_file.exists():
        raise FileNotFoundError(f"Day08 test questions not found: {day08_test_file}")
    if not day09_test_file.exists():
        raise FileNotFoundError(f"Day09 test questions not found: {day09_test_file}")

    if day09_jsonl is None:
        day09_jsonl = _find_latest_day09_jsonl(DEFAULT_DAY09_RUNS_DIR)
        if day09_jsonl is None:
            raise FileNotFoundError("No Day09 run jsonl found in artifacts/runs")

    day08_rows = _load_day08_rows(day08_csv, day08_config, day08_test_file)
    if not day08_rows:
        raise ValueError(f"No rows found for config_label='{day08_config}' in {day08_csv}")

    day09_rows = _load_day09_rows(day09_jsonl, day09_test_file)
    if not day09_rows:
        raise ValueError(f"No rows loaded from Day09 jsonl: {day09_jsonl}")

    day08_summary = _summarize_day08(day08_rows)
    day09_summary = _summarize_day09(day09_rows)

    day08_tests = _run_dataset_tests(day08_rows, has_routes=False)
    day09_tests = _run_dataset_tests(day09_rows, has_routes=True)

    aligned = _align_metrics(day08_summary, day09_summary)

    payload = {
        "generated_at": datetime.now().isoformat(),
        "inputs": {
            "day08_csv": str(day08_csv),
            "day08_test_questions": str(day08_test_file),
            "day08_config_label": day08_config,
            "day09_jsonl": str(day09_jsonl),
            "day09_test_questions": str(day09_test_file),
        },
        "conversion_notes": [
            "Day08 confidence is converted from 1-5 metrics using weighted normalization.",
            "When Day08 context_recall is missing (no expected source), recall bridge rewards safe abstain.",
            "Additional cross-day tests are heuristic and intended for comparative trend analysis.",
        ],
        "day08": {
            "summary": day08_summary,
            "tests": day08_tests,
            "row_count": len(day08_rows),
            "preview": day08_rows[:3],
        },
        "day09": {
            "summary": day09_summary,
            "tests": day09_tests,
            "row_count": len(day09_rows),
            "preview": day09_rows[:3],
        },
        "aligned_comparison": aligned,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_to_markdown(payload), encoding="utf-8")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-day metrics bridge Day08 -> Day09")
    parser.add_argument("--day08-csv", default=str(DEFAULT_DAY08_CSV), help="Path to day08 ab_comparison.csv")
    parser.add_argument("--day08-test-file", default=str(DEFAULT_DAY08_TEST_FILE), help="Path to day08 test questions")
    parser.add_argument("--day08-config", default=DEFAULT_DAY08_CONFIG, help="config_label in day08 csv")
    parser.add_argument("--day09-jsonl", default=None, help="Path to day09 run jsonl (default: latest)")
    parser.add_argument("--day09-test-file", default=str(DEFAULT_DAY09_TEST_FILE), help="Path to day09 test questions")
    parser.add_argument("--out-json", default=str(DEFAULT_OUTPUT_JSON), help="Output JSON report")
    parser.add_argument("--out-md", default=str(DEFAULT_OUTPUT_MD), help="Output markdown report")
    args = parser.parse_args()

    day09_jsonl = Path(args.day09_jsonl) if args.day09_jsonl else None
    payload = run(
        day08_csv=Path(args.day08_csv),
        day08_test_file=Path(args.day08_test_file),
        day08_config=args.day08_config,
        day09_jsonl=day09_jsonl,
        day09_test_file=Path(args.day09_test_file),
        output_json=Path(args.out_json),
        output_md=Path(args.out_md),
    )

    print("\n✅ Cross-day metrics report generated")
    print(f"- JSON: {args.out_json}")
    print(f"- MD  : {args.out_md}")
    print(f"- Day08 rows: {payload['day08']['row_count']}")
    print(f"- Day09 rows: {payload['day09']['row_count']}")


if __name__ == "__main__":
    main()
