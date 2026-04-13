"""
Chấm tự động `logs/grading_run.json` theo rubric trong `data/grading_questions.json`.

Chạy (từ thư mục lab, cần OPENAI_API_KEY trong .env):
  python grade_grading_run.py

Output:
  - results/grading_auto.json
  - results/grading_auto_report.md

Lưu ý: Đây là LLM-as-judge — **ước lượng** để so sánh nội bộ giữa các nhóm, không thay thế
điểm giảng viên (SCORING.md). Tiêu chí khớp tinh thần Full/Partial/Zero/Penalty trong đề.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

LAB = Path(__file__).resolve().parent
DEFAULT_QUESTIONS = LAB / "data" / "grading_questions.json"
DEFAULT_LOG = LAB / "logs" / "grading_run.json"
RESULTS_DIR = LAB / "results"


def _parse_judge_json(text: str) -> Dict[str, Any]:
    from eval import _parse_json_from_llm

    return _parse_json_from_llm(text)


def judge_one(rubric: Dict[str, Any], log_row: Dict[str, Any]) -> Dict[str, Any]:
    criteria: List[str] = rubric.get("grading_criteria") or []
    crit_text = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(criteria))
    max_pts = float(rubric.get("max_points") or 10)
    abstain = bool(rubric.get("abstain_question"))

    extra = ""
    if abstain:
        extra = (
            "\n**Câu ABSTAIN:** Trong tài liệu không có mức phạt. "
            "Full nếu nói rõ không có thông tin trong tài liệu và không bịa số. "
            "Penalty nếu bịa mức phạt hoặc quy định không tồn tại trong doc."
        )

    prompt = f"""Bạn là giám khảo bài lab RAG. Chấm câu trả lời của pipeline.

**Câu hỏi:** {rubric.get("question", "")}

**Câu trả lời pipeline:** {log_row.get("answer", "")}

**Sources pipeline:** {json.dumps(log_row.get("sources", []), ensure_ascii=False)}

**Tiêu chí chấm (đánh giá đã đạt từng mục dựa trên nội dung policy chuẩn của đề bài):**
{crit_text}
{extra}

**Thang điểm theo rubric đề:**
- **Full:** đạt TẤT CẢ tiêu chí; không hallucinate.
- **Partial:** đạt ≥ 50% tiêu chí; không hallucinate.
- **Zero:** đạt < 50% tiêu chí, không hallucinate (hoặc sai lệch nghiêm trọng).
- **Penalty:** có hallucination (bịa số, tên, quy trình không có trong policy) → trừ 50% điểm tối đa của câu.

Trả về **CHỈ** một JSON hợp lệ:
{{"verdict": "Full"|"Partial"|"Zero"|"Penalty", "criteria_met": [true hoặc false cho từng tiêu chí theo đúng thứ tự], "hallucination": true/false, "reason": "tối đa 2 câu tiếng Việt"}}"""

    from rag_answer import call_llm

    raw = call_llm(prompt)
    parsed = _parse_judge_json(raw)
    verdict = str(parsed.get("verdict") or "Zero").strip()
    if verdict not in ("Full", "Partial", "Zero", "Penalty"):
        verdict = "Zero"

    if verdict == "Full":
        pts = max_pts
    elif verdict == "Partial":
        pts = max_pts * 0.5
    elif verdict == "Penalty":
        pts = -max_pts * 0.5
    else:
        pts = 0.0

    return {
        "id": rubric["id"],
        "verdict": verdict,
        "points": round(pts, 2),
        "max_points": max_pts,
        "reason": (parsed.get("reason") or "")[:500],
        "criteria_met": parsed.get("criteria_met"),
        "hallucination": parsed.get("hallucination"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Auto-grade grading_run.json")
    ap.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    from run_telemetry import RunTelemetry, telemetry_ctx

    _jtel = RunTelemetry("grading_auto_judge", label="grade_grading_run")
    _jtok = telemetry_ctx.set(_jtel)

    rubrics: List[Dict[str, Any]] = json.loads(
        args.questions.read_text(encoding="utf-8")
    )
    by_id = {r["id"]: r for r in rubrics}
    log_rows: List[Dict[str, Any]] = json.loads(args.log.read_text(encoding="utf-8"))

    per_q: List[Dict[str, Any]] = []
    total_raw = 0.0
    try:
        for row in log_rows:
            rid = row.get("id")
            rub = by_id.get(rid)
            if not rub:
                per_q.append({"id": rid, "error": "Không có rubric trong grading_questions.json", "points": 0.0})
                continue
            try:
                r = judge_one(rub, row)
                total_raw += r["points"]
                per_q.append(r)
            except Exception as e:
                per_q.append({"id": rid, "error": str(e), "points": 0.0, "verdict": "ERROR"})
    finally:
        telemetry_ctx.reset(_jtok)
        _jent = _jtel.finish({"graded": len(per_q)})
        print(
            f"[telemetry] grading_auto_judge: {_jent['duration_ms']:.0f} ms, "
            f"cost ~ ${_jent['cost_usd']['total_usd']:.4f} → logs/runs.jsonl"
        )

    max_raw = sum(float(r.get("max_points") or 0) for r in rubrics)
    projected_30 = (total_raw / max_raw) * 30.0 if max_raw else 0.0

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "total_raw_estimate": round(total_raw, 2),
        "max_raw": max_raw,
        "projected_grading_30pts": round(projected_30, 2),
        "formula": f"({total_raw:.2f} / {max_raw}) * 30",
        "per_question": per_q,
    }
    (RESULTS_DIR / "grading_auto.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Chấm tự động — grading questions",
        "",
        "> LLM-as-judge: **ước lượng** để benchmark nội bộ. Điểm chính thức do GV chấm theo [SCORING.md](SCORING.md).",
        "",
        f"- **Tổng raw (ước lượng):** {total_raw:.2f} / {max_raw:.0f}",
        f"- **Quy đổi kiểu 30 điểm phần grading nhóm:** **{projected_30:.2f} / 30**",
        "",
        "## Chi tiết",
        "",
        "| ID | Verdict | Điểm | Max | Lý do (rút gọn) |",
        "|----|---------|------|-----|-----------------|",
    ]
    for r in per_q:
        if "error" in r:
            lines.append(f"| {r.get('id')} | ERROR | 0 | — | {r.get('error', '')[:100]} |")
        else:
            reason = (r.get("reason") or "").replace("|", "/").replace("\n", " ")[:100]
            lines.append(
                f"| {r['id']} | {r.get('verdict')} | {r.get('points')} | {r.get('max_points')} | {reason} |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            "## So sánh với nhóm khác (gợi ý)",
            "",
            "1. Dùng **cùng script + cùng bản rubric** (`grading_questions.json`) và so sánh `projected_grading_30pts`.",
            "2. Theo [SCORING.md](SCORING.md): bonus +2 nếu **gq06** đạt Full; tránh **Penalty** ở **gq07** (bịa mức phạt).",
            "3. Cải thiện **gq08** (phân biệt loại phép) thường cần prompt + retrieval tốt hơn, không chỉ tăng top_k.",
            "",
            "## File 10 câu grading ở đâu?",
            "",
            "- Đề + rubric: [`data/grading_questions.json`](data/grading_questions.json)",
            "- Log pipeline: [`logs/grading_run.json`](logs/grading_run.json) (tạo bằng `python eval.py grading`)",
        ]
    )
    (RESULTS_DIR / "grading_auto_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {RESULTS_DIR / 'grading_auto.json'}")
    print(f"Wrote {RESULTS_DIR / 'grading_auto_report.md'}")
    print(f"Raw ~ {total_raw:.2f} / {max_raw:.0f}  =>  projected (×30/98): {projected_30:.2f} / 30")


if __name__ == "__main__":
    main()
