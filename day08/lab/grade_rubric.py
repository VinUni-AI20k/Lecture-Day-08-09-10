"""
grade_rubric.py — Chấm điểm grading questions theo thang Full/Partial/Zero/Penalty
====================================================================================
Thang điểm:
  Full    — đáp ứng tất cả grading_criteria                → 100% điểm câu
  Partial — đáp ứng ≥50% criteria, không hallucinate       → 50% điểm câu
  Zero    — đáp ứng <50% criteria, không hallucinate        → 0
  Penalty — bịa thông tin không có trong tài liệu           → −50% điểm câu

Đặc biệt (gq07 — abstain):
  Abstain rõ ràng                                          → 10/10
  Abstain mơ hồ                                            → 5/10
  Trả lời từ model knowledge, không cite nguồn             → 0/10
  Bịa con số / quy định cụ thể                             → −5 điểm

Chạy:
  python grade_rubric.py
  python grade_rubric.py --mode hybrid --rerank
  python grade_rubric.py --out results/grading_run_v2.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
LAB_DIR = Path(__file__).resolve().parent
GRADING_Q_PATH = LAB_DIR / "data" / "grading_questions.json"
LOGS_DIR = LAB_DIR / "logs"
RESULTS_DIR = LAB_DIR / "results"
DEFAULT_OUT = LOGS_DIR / "grading_rubric_run.jsonl"

TOTAL_RAW = 98  # tổng điểm raw tối đa theo đề bài
GROUP_MAX = 30  # quy đổi sang 30 điểm nhóm

USE_LLM_JUDGE = os.getenv("USE_LLM_JUDGE", "1").strip().lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Rubric scoring via LLM-as-Judge
# ---------------------------------------------------------------------------

_RUBRIC_SYSTEM = """Bạn là giám khảo chấm RAG pipeline. Nhiệm vụ: đánh giá câu trả lời của hệ thống
theo thang Full / Partial / Zero / Penalty dựa trên grading_criteria.

Định nghĩa:
- Full    : đáp ứng TẤT CẢ criteria (không cần hoàn hảo từng chữ, nhưng đủ ý)
- Partial : đáp ứng ≥50% criteria VÀ KHÔNG bịa thông tin
- Zero    : đáp ứng <50% criteria VÀ KHÔNG bịa thông tin
- Penalty : bịa ra con số, tên, quy trình hoặc kết luận KHÔNG có trong context

Hallucination = bịa thông tin. Đây là lỗi nghiêm trọng nhất → luôn trả về Penalty.
Nếu câu là abstain-type (expected_sources rỗng):
  - Trả lời rõ "không có thông tin trong tài liệu" → Full
  - Abstain mơ hồ, không nêu lý do                → Partial
  - Trả lời từ general knowledge, không cite       → Zero
  - Bịa số cụ thể / quy định                       → Penalty

Trả về JSON duy nhất:
{
  "grade": "Full" | "Partial" | "Zero" | "Penalty",
  "criteria_met": ["..."],
  "criteria_missed": ["..."],
  "hallucination_detected": true | false,
  "reason": "<giải thích ngắn ≤200 ký tự>"
}"""


def _call_llm(prompt: str) -> str:
    from rag_answer import call_llm
    return call_llm(prompt)


def _parse_json(text: str) -> Dict[str, Any]:
    import re
    text = (text or "").strip()
    if "```" in text:
        for block in re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE):
            block = block.strip()
            if block.startswith("{"):
                text = block
                break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start == -1:
        return {}
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    pass
                break
    return {}


def judge_rubric(
    question: Dict[str, Any],
    answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Chấm một câu theo rubric Full/Partial/Zero/Penalty bằng LLM-as-Judge."""
    if not USE_LLM_JUDGE:
        return {
            "grade": None,
            "criteria_met": [],
            "criteria_missed": [],
            "hallucination_detected": None,
            "reason": "USE_LLM_JUDGE=0 — chấm thủ công",
        }

    criteria = question.get("grading_criteria", [])
    is_abstain = not question.get("expected_sources")

    # Format retrieved context (tối đa 6000 ký tự)
    ctx_parts = []
    for i, c in enumerate(chunks_used[:12], 1):
        meta = c.get("metadata") or {}
        src = meta.get("source", "")
        t = (c.get("text") or "")[:1000]
        ctx_parts.append(f"[{i}] source={src}\n{t}")
    ctx = "\n\n---\n\n".join(ctx_parts)[:6000] or "(không có context)"

    prompt = f"""{_RUBRIC_SYSTEM}

---
Câu hỏi: {question['question']}

Grading criteria:
{json.dumps(criteria, ensure_ascii=False, indent=2)}

Abstain-type (không có expected sources): {is_abstain}

Retrieved context:
{ctx}

Câu trả lời của RAG pipeline:
{answer}
---"""

    try:
        raw = _call_llm(prompt)
        out = _parse_json(raw)
        grade = out.get("grade", "Zero")
        if grade not in ("Full", "Partial", "Zero", "Penalty"):
            grade = "Zero"
        return {
            "grade": grade,
            "criteria_met": out.get("criteria_met", []),
            "criteria_missed": out.get("criteria_missed", []),
            "hallucination_detected": bool(out.get("hallucination_detected", False)),
            "reason": (out.get("reason") or "")[:300],
        }
    except Exception as e:
        return {
            "grade": None,
            "criteria_met": [],
            "criteria_missed": [],
            "hallucination_detected": None,
            "reason": f"judge_error: {e}",
        }


# ---------------------------------------------------------------------------
# Points calculation
# ---------------------------------------------------------------------------

GRADE_MULTIPLIER = {
    "Full": 1.0,
    "Partial": 0.5,
    "Zero": 0.0,
    "Penalty": -0.5,
}

# gq07 là câu abstain với thang điểm đặc biệt
ABSTAIN_GRADE_POINTS: Dict[str, float] = {
    "Full": 10.0,     # abstain rõ ràng
    "Partial": 5.0,   # abstain mơ hồ
    "Zero": 0.0,      # trả lời từ model knowledge
    "Penalty": -5.0,  # bịa con số cụ thể
}


def calc_points(question: Dict[str, Any], grade: Optional[str]) -> float:
    """Tính điểm raw cho một câu theo rubric."""
    if grade is None:
        return 0.0
    raw_max = float(question.get("points", 0))
    qid = question.get("id", "")

    # gq07 dùng thang điểm tuyệt đối đặc biệt (không theo % của max)
    if qid == "gq07":
        return ABSTAIN_GRADE_POINTS.get(grade, 0.0)

    return raw_max * GRADE_MULTIPLIER.get(grade, 0.0)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_grading(
    retrieval_mode: str = "dense",
    top_k_search: int = 10,
    top_k_select: int = 3,
    use_rerank: bool = False,
    out_path: Optional[Path] = None,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """
    Chạy 10 grading questions qua RAG pipeline, chấm rubric, log kết quả.

    Returns:
        List log rows, mỗi row là một câu hỏi với answer + grade + points.
    """
    from rag_answer import rag_answer
    from run_telemetry import RunTelemetry, telemetry_ctx

    if not GRADING_Q_PATH.exists():
        print(f"[ERROR] Không tìm thấy {GRADING_Q_PATH}")
        return []

    with open(GRADING_Q_PATH, "r", encoding="utf-8") as f:
        questions: List[Dict[str, Any]] = json.load(f)

    config_label = f"{retrieval_mode}{'_rerank' if use_rerank else ''}"
    out_file = out_path or DEFAULT_OUT
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    _tel = RunTelemetry("grading_rubric", label=config_label)
    _tok = telemetry_ctx.set(_tel)

    log_rows: List[Dict[str, Any]] = []
    total_raw_earned = 0.0
    penalty_count = 0

    print(f"\n{'='*70}")
    print(f"Grading Run — {config_label}")
    print(f"Câu hỏi: {len(questions)} | LLM Judge: {'ON' if USE_LLM_JUDGE else 'OFF'}")
    print('='*70)

    try:
        for q in questions:
            qid = q["id"]
            query = q["question"]

            if verbose:
                print(f"\n[{qid}] {query}")

            # --- Gọi RAG pipeline ---
            try:
                result = rag_answer(
                    query=query,
                    retrieval_mode=retrieval_mode,
                    top_k_search=top_k_search,
                    top_k_select=top_k_select,
                    use_rerank=use_rerank,
                    verbose=False,
                )
                answer = result.get("answer", "")
                chunks_used = result.get("chunks_used", [])
                sources_retrieved = [
                    c.get("metadata", {}).get("source", "") for c in chunks_used
                ]
            except NotImplementedError:
                answer = "PIPELINE_NOT_IMPLEMENTED"
                chunks_used = []
                sources_retrieved = []
            except Exception as e:
                answer = f"ERROR: {e}"
                chunks_used = []
                sources_retrieved = []

            # --- Chấm rubric ---
            rubric = judge_rubric(q, answer, chunks_used)
            grade = rubric["grade"]
            points = calc_points(q, grade)
            total_raw_earned += points
            if grade == "Penalty":
                penalty_count += 1

            row: Dict[str, Any] = {
                "id": qid,
                "question": query,
                "category": q.get("category", ""),
                "rag_skill_tested": q.get("rag_skill_tested", ""),
                "points_max": q.get("points", 0),
                "answer": answer,
                "sources_retrieved": sources_retrieved,
                "expected_sources": q.get("expected_sources", []),
                "grade": grade,
                "points_earned": points,
                "criteria_met": rubric["criteria_met"],
                "criteria_missed": rubric["criteria_missed"],
                "hallucination_detected": rubric["hallucination_detected"],
                "judge_reason": rubric["reason"],
                "config": {
                    "retrieval_mode": retrieval_mode,
                    "top_k_search": top_k_search,
                    "top_k_select": top_k_select,
                    "use_rerank": use_rerank,
                },
                "logged_at": datetime.now(timezone.utc).isoformat(),
            }
            log_rows.append(row)

            if verbose:
                grade_display = grade or "?"
                print(f"  Grade : {grade_display:<8} | Points: {points:+.1f}/{q.get('points',0)}")
                print(f"  Answer: {answer[:120]}{'...' if len(answer) > 120 else ''}")
                if rubric["reason"]:
                    print(f"  Reason: {rubric['reason']}")

        # --- Tổng kết ---
        group_score = (total_raw_earned / TOTAL_RAW) * GROUP_MAX
        print(f"\n{'='*70}")
        print(f"Tổng điểm raw    : {total_raw_earned:.1f} / {TOTAL_RAW}")
        print(f"Điểm nhóm (×30)  : {group_score:.1f} / {GROUP_MAX}")
        print(f"Số câu Penalty   : {penalty_count}")
        print(f"LLM Judge        : {'ON' if USE_LLM_JUDGE else 'OFF (chấm thủ công)'}")
        print('='*70)

        # Grade breakdown
        from collections import Counter
        grade_counts = Counter(r["grade"] for r in log_rows if r["grade"])
        print("\nPhân bố grade:")
        for g in ("Full", "Partial", "Zero", "Penalty"):
            print(f"  {g:<8}: {grade_counts.get(g, 0)}")

    finally:
        _entry = _tel.finish({
            "config_label": config_label,
            "num_questions": len(log_rows),
            "total_raw_earned": total_raw_earned,
            "total_raw_max": TOTAL_RAW,
            "group_score_30": round((total_raw_earned / TOTAL_RAW) * GROUP_MAX, 2),
            "penalty_count": penalty_count,
        })
        telemetry_ctx.reset(_tok)
        print(
            f"\n[telemetry] grading_rubric `{config_label}`: "
            f"{_entry['duration_ms']:.0f} ms, "
            f"cost ~ ${_entry['cost_usd']['total_usd']:.4f} → logs/runs.jsonl"
        )

    # --- Ghi log ---
    with open(out_file, "w", encoding="utf-8") as f:
        for row in log_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\nLog đã ghi: {out_file}")

    # Ghi summary CSV vào results/
    _write_summary_csv(log_rows, config_label, total_raw_earned, group_score)

    return log_rows


def _write_summary_csv(
    rows: List[Dict[str, Any]],
    label: str,
    total_raw: float,
    group_score: float,
) -> None:
    import csv

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = RESULTS_DIR / f"grading_rubric_{label}.csv"
    fieldnames = [
        "id", "category", "rag_skill_tested",
        "points_max", "grade", "points_earned",
        "hallucination_detected", "judge_reason",
        "answer_preview",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "id": r["id"],
                "category": r["category"],
                "rag_skill_tested": r["rag_skill_tested"],
                "points_max": r["points_max"],
                "grade": r["grade"] or "",
                "points_earned": r["points_earned"],
                "hallucination_detected": r["hallucination_detected"],
                "judge_reason": r["judge_reason"],
                "answer_preview": (r["answer"] or "")[:200],
            })
        # Tổng kết dòng cuối
        writer.writerow({
            "id": "TOTAL",
            "category": "",
            "rag_skill_tested": "",
            "points_max": TOTAL_RAW,
            "grade": "",
            "points_earned": total_raw,
            "hallucination_detected": "",
            "judge_reason": f"group_score={group_score:.1f}/30",
            "answer_preview": "",
        })
    print(f"CSV summary  : {csv_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chấm điểm grading questions theo rubric Full/Partial/Zero/Penalty")
    parser.add_argument("--mode", default="dense", choices=["dense", "sparse", "hybrid"],
                        help="Retrieval mode (mặc định: dense)")
    parser.add_argument("--rerank", action="store_true", help="Bật rerank")
    parser.add_argument("--top-k-search", type=int, default=10)
    parser.add_argument("--top-k-select", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None,
                        help="Đường dẫn file log JSONL (mặc định: logs/grading_rubric_run.jsonl)")
    parser.add_argument("--no-judge", action="store_true",
                        help="Tắt LLM-as-Judge (chỉ chạy pipeline, không chấm)")
    args = parser.parse_args()

    if args.no_judge:
        os.environ["USE_LLM_JUDGE"] = "0"
        USE_LLM_JUDGE = False  # type: ignore[assignment]

    run_grading(
        retrieval_mode=args.mode,
        top_k_search=args.top_k_search,
        top_k_select=args.top_k_select,
        use_rerank=args.rerank,
        out_path=args.out,
        verbose=True,
    )
