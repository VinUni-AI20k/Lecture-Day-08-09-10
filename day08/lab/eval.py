"""
eval.py — Sprint 4: Evaluation & Scorecard
==========================================
Mục tiêu Sprint 4 (60 phút):
  - Chạy 10 test questions qua pipeline
  - Chấm điểm theo 4 metrics: Faithfulness, Relevance, Context Recall, Completeness
  - So sánh baseline vs variant
  - Ghi kết quả ra scorecard

Definition of Done Sprint 4:
  ✓ Demo chạy end-to-end (index → retrieve → answer → score)
  ✓ Scorecard trước và sau tuning
  ✓ A/B comparison: baseline vs variant với giải thích vì sao variant tốt hơn

A/B Rule (từ slide):
  Chỉ đổi MỘT biến mỗi lần để biết điều gì thực sự tạo ra cải thiện.
  Đổi đồng thời chunking + hybrid + rerank + prompt = không biết biến nào có tác dụng.
"""

import os
import re
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rag_answer import rag_answer

USE_LLM_JUDGE = os.getenv("USE_LLM_JUDGE", "1").strip().lower() in ("1", "true", "yes")
GRADING_QUESTIONS_PATH = Path(__file__).parent / "data" / "grading_questions.json"
LOGS_DIR = Path(__file__).parent / "logs"

# =============================================================================
# CẤU HÌNH
# =============================================================================

TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"
RESULTS_DIR = Path(__file__).parent / "results"

# Cấu hình baseline (Sprint 2)
BASELINE_CONFIG = {
    "retrieval_mode": "dense",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,
    "label": "baseline_dense",
}

# Cấu hình variant (Sprint 3 — điều chỉnh theo lựa chọn của nhóm)
# TODO Sprint 4: Cập nhật VARIANT_CONFIG theo variant nhóm đã implement
VARIANT_CONFIG = {
    "retrieval_mode": "hybrid",   # Hoặc "dense" nếu chỉ đổi rerank
    # Pool rộng hơn → RRF + cross-encoder lọc nhiễu tốt hơn; thêm 1 chunk vào prompt cho câu nhiều ý.
    "top_k_search": 15,
    "top_k_select": 4,
    "use_rerank": True,           # Hoặc False nếu variant là hybrid không rerank
    "label": "variant_hybrid_rerank",
}


# =============================================================================
# SCORING FUNCTIONS
# 4 metrics từ slide: Faithfulness, Answer Relevance, Context Recall, Completeness
# =============================================================================

def _format_chunks_for_judge(chunks: List[Dict[str, Any]], limit: int = 14000) -> str:
    parts = []
    for i, c in enumerate(chunks[:24], 1):
        meta = c.get("metadata") or {}
        src = meta.get("source", "")
        t = (c.get("text") or "")[:7000]
        parts.append(f"[{i}] source={src}\n{t}")
    out = "\n\n---\n\n".join(parts)
    return out[:limit]


def _parse_json_from_llm(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    # Bỏ khối ```json ... ``` thường gặp từ GPT
    if "```" in text:
        for block in re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE):
            block = block.strip()
            if block.startswith("{"):
                text = block
                break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Lấy object JSON đầu tiên (cân bằng ngoặc)
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
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    pass
                break
    return {}


def _clamp_int_score(v: Any, lo: int = 1, hi: int = 5) -> Optional[int]:
    if v is None:
        return None
    try:
        x = int(round(float(v)))
        return max(lo, min(hi, x))
    except (TypeError, ValueError):
        return None


def score_faithfulness(
    answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Faithfulness: LLM-as-Judge (USE_LLM_JUDGE=0 để tắt).
    """
    if not USE_LLM_JUDGE:
        return {"score": None, "notes": "USE_LLM_JUDGE=0"}

    ctx = _format_chunks_for_judge(chunks_used)
    prompt = f"""You evaluate RAG answers. Rate FAITHFULNESS 1-5: does the answer stick to the context only?
5 = every claim supported by context; 1 = hallucinations or ignores context.

Context:
{ctx}

Answer:
{answer}

Return ONLY JSON: {{"score": <int 1-5>, "reason": "<short>"}}"""
    try:
        from rag_answer import call_llm

        raw = call_llm(prompt)
        out = _parse_json_from_llm(raw)
        sc = _clamp_int_score(out.get("score"))
        return {"score": sc, "notes": (out.get("reason") or "")[:800]}
    except Exception as e:
        return {"score": None, "notes": f"judge_error: {e}"}


def score_answer_relevance(
    query: str,
    answer: str,
) -> Dict[str, Any]:
    """
    Answer relevance vs question (LLM-as-Judge).
    """
    if not USE_LLM_JUDGE:
        return {"score": None, "notes": "USE_LLM_JUDGE=0"}

    prompt = f"""Rate how well the answer addresses the user question. Scale 1-5.
5 = directly and completely answers; 1 = off-topic or no answer.

Question: {query}

Answer: {answer}

Return ONLY JSON: {{"score": <int 1-5>, "reason": "<short>"}}"""
    try:
        from rag_answer import call_llm

        raw = call_llm(prompt)
        out = _parse_json_from_llm(raw)
        sc = _clamp_int_score(out.get("score"))
        return {"score": sc, "notes": (out.get("reason") or "")[:800]}
    except Exception as e:
        return {"score": None, "notes": f"judge_error: {e}"}


def score_context_recall(
    chunks_used: List[Dict[str, Any]],
    expected_sources: List[str],
) -> Dict[str, Any]:
    """
    Context Recall: Retriever có mang về đủ evidence cần thiết không?
    Câu hỏi: Expected source có nằm trong retrieved chunks không?

    Đây là metric đo retrieval quality, không phải generation quality.

    Cách tính đơn giản:
        recall = (số expected source được retrieve) / (tổng số expected sources)

    Ví dụ:
        expected_sources = ["policy/refund-v4.pdf", "sla-p1-2026.pdf"]
        retrieved_sources = ["policy/refund-v4.pdf", "helpdesk-faq.md"]
        recall = 1/2 = 0.5

    TODO Sprint 4:
    1. Lấy danh sách source từ chunks_used
    2. Kiểm tra xem expected_sources có trong retrieved sources không
    3. Tính recall score
    """
    if not expected_sources:
        # Câu hỏi không có expected source (ví dụ: "Không đủ dữ liệu" cases)
        return {"score": None, "recall": None, "notes": "No expected sources"}

    retrieved_sources = {
        c.get("metadata", {}).get("source", "")
        for c in chunks_used
    }

    # TODO: Kiểm tra matching theo partial path (vì source paths có thể khác format)
    found = 0
    missing = []
    for expected in expected_sources:
        # Kiểm tra partial match (tên file)
        expected_name = expected.split("/")[-1].replace(".pdf", "").replace(".md", "")
        matched = any(expected_name.lower() in r.lower() for r in retrieved_sources)
        if matched:
            found += 1
        else:
            missing.append(expected)

    recall = found / len(expected_sources) if expected_sources else 0

    return {
        "score": round(recall * 5),  # Convert to 1-5 scale
        "recall": recall,
        "found": found,
        "missing": missing,
        "notes": f"Retrieved: {found}/{len(expected_sources)} expected sources" +
                 (f". Missing: {missing}" if missing else ""),
    }


def score_completeness(
    query: str,
    answer: str,
    expected_answer: str,
) -> Dict[str, Any]:
    """
    Completeness vs reference answer (LLM-as-Judge).
    """
    if not USE_LLM_JUDGE:
        return {"score": None, "notes": "USE_LLM_JUDGE=0"}
    if not (expected_answer or "").strip():
        return {"score": None, "notes": "No expected_answer"}

    prompt = f"""Compare the model answer to the reference answer for the same question.
Rate COMPLETENESS 1-5: does the model cover the key points of the reference?
5 = covers all important points; 1 = misses most.

Question: {query}

Reference (gold): {expected_answer}

Model answer: {answer}

Return ONLY JSON: {{"score": <int 1-5>, "reason": "<short>"}}"""
    try:
        from rag_answer import call_llm

        raw = call_llm(prompt)
        out = _parse_json_from_llm(raw)
        sc = _clamp_int_score(out.get("score"))
        return {"score": sc, "notes": (out.get("reason") or "")[:800]}
    except Exception as e:
        return {"score": None, "notes": f"judge_error: {e}"}


# =============================================================================
# SCORECARD RUNNER
# =============================================================================

def run_scorecard(
    config: Dict[str, Any],
    test_questions: Optional[List[Dict]] = None,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """
    Chạy toàn bộ test questions qua pipeline và chấm điểm.

    Args:
        config: Pipeline config (retrieval_mode, top_k, use_rerank, ...)
        test_questions: List câu hỏi (load từ JSON nếu None)
        verbose: In kết quả từng câu

    Returns:
        List scorecard results, mỗi item là một row

    TODO Sprint 4:
    1. Load test_questions từ data/test_questions.json
    2. Với mỗi câu hỏi:
       a. Gọi rag_answer() với config tương ứng
       b. Chấm 4 metrics
       c. Lưu kết quả
    3. Tính average scores
    4. In bảng kết quả
    """
    if test_questions is None:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)

    results = []
    label = config.get("label", "unnamed")

    print(f"\n{'='*70}")
    print(f"Chạy scorecard: {label}")
    print(f"Config: {config}")
    print('='*70)

    from run_telemetry import (
        RunTelemetry,
        attach_cicd_faithfulness_fields,
        telemetry_ctx,
    )

    _tel = RunTelemetry("scorecard", label=label)
    _tok = telemetry_ctx.set(_tel)
    try:
        for q in test_questions:
            question_id = q["id"]
            query = q["question"]
            expected_answer = q.get("expected_answer", "")
            expected_sources = q.get("expected_sources", [])
            category = q.get("category", "")

            if verbose:
                print(f"\n[{question_id}] {query}")

            # --- Gọi pipeline ---
            try:
                result = rag_answer(
                    query=query,
                    retrieval_mode=config.get("retrieval_mode", "dense"),
                    top_k_search=config.get("top_k_search", 10),
                    top_k_select=config.get("top_k_select", 3),
                    use_rerank=config.get("use_rerank", False),
                    verbose=False,
                )
                answer = result["answer"]
                chunks_used = result["chunks_used"]

            except NotImplementedError:
                answer = "PIPELINE_NOT_IMPLEMENTED"
                chunks_used = []
            except Exception as e:
                answer = f"ERROR: {e}"
                chunks_used = []

            # --- Chấm điểm ---
            faith = score_faithfulness(answer, chunks_used)
            relevance = score_answer_relevance(query, answer)
            recall = score_context_recall(chunks_used, expected_sources)
            complete = score_completeness(query, answer, expected_answer)

            row = {
                "id": question_id,
                "category": category,
                "query": query,
                "answer": answer,
                "expected_answer": expected_answer,
                "faithfulness": faith["score"],
                "faithfulness_notes": faith["notes"],
                "relevance": relevance["score"],
                "relevance_notes": relevance["notes"],
                "context_recall": recall["score"],
                "context_recall_notes": recall["notes"],
                "completeness": complete["score"],
                "completeness_notes": complete["notes"],
                "config_label": label,
            }
            results.append(row)

            if verbose:
                print(f"  Answer: {answer[:100]}...")
                print(f"  Faithful: {faith['score']} | Relevant: {relevance['score']} | "
                      f"Recall: {recall['score']} | Complete: {complete['score']}")

        # Tính averages (bỏ qua None)
        for metric in ["faithfulness", "relevance", "context_recall", "completeness"]:
            scores = [r[metric] for r in results if r[metric] is not None]
            avg = sum(scores) / len(scores) if scores else None
            print(
                f"\nAverage {metric}: {avg:.2f}"
                if avg is not None
                else f"\nAverage {metric}: N/A (chưa chấm)"
            )

        return results
    finally:
        _extra: Dict[str, Any] = {
            "config_label": label,
            "num_questions": len(results),
            "slide_ci_cd_note": (
                "Slide Day 08 — CI/CD RAG: gắn RAGAS vào pipeline; ví dụ block deploy nếu faithfulness < 80%. "
                "Lab: faithfulness trung bình thang 1–5 → ratio = avg/5; gate 80% ⇔ avg ≥ 4.0."
            ),
        }
        if results:
            _av = average_metric_scores(results)
            _extra["metrics_avg"] = _av
            attach_cicd_faithfulness_fields(_extra, _av.get("faithfulness"))
        telemetry_ctx.reset(_tok)
        _entry = _tel.finish(_extra)
        print(
            f"\n[telemetry] scorecard `{label}`: {_entry['duration_ms']:.0f} ms, "
            f"cost ~ ${_entry['cost_usd']['total_usd']:.4f} → logs/runs.jsonl"
        )
        if _extra.get("cicd_faithfulness_gate_min_80pct") is not None:
            _pass = _extra["cicd_faithfulness_gate_min_80pct"]
            print(
                f"[telemetry] CI/CD faithfulness gate (≥80% as avg/5): "
                f"{'PASS' if _pass else 'FAIL'}"
            )


# =============================================================================
# SCORECARD HELPERS (UI / export)
# =============================================================================

METRIC_KEYS = ["faithfulness", "relevance", "context_recall", "completeness"]


def average_metric_scores(results: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """Trung bình từng metric (1–5 hoặc None nếu không có điểm)."""
    out: Dict[str, Optional[float]] = {}
    for m in METRIC_KEYS:
        scores = [r[m] for r in results if r.get(m) is not None]
        out[m] = sum(scores) / len(scores) if scores else None
    return out


def ab_comparison_rows(
    baseline_results: List[Dict[str, Any]],
    variant_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Một dòng / câu hỏi: điểm baseline vs variant và ai tốt hơn (tổng 4 metric)."""
    b_by_id = {r["id"]: r for r in baseline_results}
    rows: List[Dict[str, Any]] = []
    for v_row in variant_results:
        qid = v_row["id"]
        b_row = b_by_id.get(qid, {})
        b_total = sum(b_row.get(m, 0) or 0 for m in METRIC_KEYS)
        v_total = sum(v_row.get(m, 0) or 0 for m in METRIC_KEYS)
        if v_total > b_total:
            winner = "Variant"
        elif b_total > v_total:
            winner = "Baseline"
        else:
            winner = "Hòa"
        rows.append({
            "id": qid,
            "category": v_row.get("category", ""),
            "baseline_F": b_row.get("faithfulness"),
            "baseline_R": b_row.get("relevance"),
            "baseline_Rc": b_row.get("context_recall"),
            "baseline_C": b_row.get("completeness"),
            "variant_F": v_row.get("faithfulness"),
            "variant_R": v_row.get("relevance"),
            "variant_Rc": v_row.get("context_recall"),
            "variant_C": v_row.get("completeness"),
            "winner": winner,
        })
    return rows


# =============================================================================
# A/B COMPARISON
# =============================================================================

def compare_ab(
    baseline_results: List[Dict],
    variant_results: List[Dict],
    output_csv: Optional[str] = None,
) -> None:
    """
    So sánh baseline vs variant theo từng câu hỏi và tổng thể.

    TODO Sprint 4:
    Điền vào bảng sau để trình bày trong báo cáo:

    | Metric          | Baseline | Variant | Delta |
    |-----------------|----------|---------|-------|
    | Faithfulness    |   ?/5    |   ?/5   |  +/?  |
    | Answer Relevance|   ?/5    |   ?/5   |  +/?  |
    | Context Recall  |   ?/5    |   ?/5   |  +/?  |
    | Completeness    |   ?/5    |   ?/5   |  +/?  |

    Câu hỏi cần trả lời:
    - Variant tốt hơn baseline ở câu nào? Vì sao?
    - Biến nào (chunking / hybrid / rerank) đóng góp nhiều nhất?
    - Có câu nào variant lại kém hơn baseline không? Tại sao?
    """
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]

    print(f"\n{'='*70}")
    print("A/B Comparison: Baseline vs Variant")
    print('='*70)
    print(f"{'Metric':<20} {'Baseline':>10} {'Variant':>10} {'Delta':>8}")
    print("-" * 55)

    for metric in metrics:
        b_scores = [r[metric] for r in baseline_results if r[metric] is not None]
        v_scores = [r[metric] for r in variant_results if r[metric] is not None]

        b_avg = sum(b_scores) / len(b_scores) if b_scores else None
        v_avg = sum(v_scores) / len(v_scores) if v_scores else None
        delta = (v_avg - b_avg) if (b_avg is not None and v_avg is not None) else None

        b_str = f"{b_avg:.2f}" if b_avg is not None else "N/A"
        v_str = f"{v_avg:.2f}" if v_avg is not None else "N/A"
        d_str = f"{delta:+.2f}" if delta is not None else "N/A"

        print(f"{metric:<20} {b_str:>10} {v_str:>10} {d_str:>8}")

    # Per-question comparison
    print(f"\n{'Câu':<6} {'Baseline F/R/Rc/C':<22} {'Variant F/R/Rc/C':<22} {'Better?':<10}")
    print("-" * 65)

    b_by_id = {r["id"]: r for r in baseline_results}
    for v_row in variant_results:
        qid = v_row["id"]
        b_row = b_by_id.get(qid, {})

        b_scores_str = "/".join([
            str(b_row.get(m, "?")) for m in metrics
        ])
        v_scores_str = "/".join([
            str(v_row.get(m, "?")) for m in metrics
        ])

        # So sánh đơn giản
        b_total = sum(b_row.get(m, 0) or 0 for m in metrics)
        v_total = sum(v_row.get(m, 0) or 0 for m in metrics)
        better = "Variant" if v_total > b_total else ("Baseline" if b_total > v_total else "Tie")

        print(f"{qid:<6} {b_scores_str:<22} {v_scores_str:<22} {better:<10}")

    # Export to CSV
    if output_csv:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = RESULTS_DIR / output_csv
        combined = baseline_results + variant_results
        if combined:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=combined[0].keys())
                writer.writeheader()
                writer.writerows(combined)
            print(f"\nKết quả đã lưu vào: {csv_path}")


# =============================================================================
# REPORT GENERATOR
# =============================================================================

def generate_scorecard_summary(results: List[Dict], label: str) -> str:
    """
    Tạo báo cáo tóm tắt scorecard dạng markdown.

    TODO Sprint 4: Cập nhật template này theo kết quả thực tế của nhóm.
    """
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]
    metric_labels = {
        "faithfulness": "Faithfulness",
        "relevance": "Relevance",
        "context_recall": "Context Recall",
        "completeness": "Completeness",
    }

    def _fmt_score(value: Any) -> str:
        return "N/A" if value is None else str(value)

    def _md_cell(value: Any, max_len: int = 80) -> str:
        if value is None:
            return "N/A"
        text = str(value).replace("\n", " ").replace("|", "/")
        text = re.sub(r"\s{2,}", " ", text).strip()
        return text[:max_len]

    averages: Dict[str, Optional[float]] = {}
    for metric in metrics:
        scores = [r[metric] for r in results if r[metric] is not None]
        averages[metric] = sum(scores) / len(scores) if scores else None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: List[str] = [
        f"# Scorecard: {label}",
        f"Generated: {timestamp}",
        "",
        "## Summary",
        "",
        "|Metric|Average Score|",
        "|------|-------------|",
    ]

    for metric in metrics:
        avg = averages[metric]
        avg_str = f"{avg:.2f}/5" if avg is not None else "N/A"
        lines.append(f"|{metric_labels[metric]}|{avg_str}|")

    lines.extend([
        "",
        "## Per-Question Results",
        "",
        "|ID|Category|Faithful|Relevant|Recall|Complete|Notes|",
        "|--|--------|--------|--------|------|--------|-----|",
    ])

    for r in results:
        note = (
            r.get("faithfulness_notes")
            or r.get("relevance_notes")
            or r.get("context_recall_notes")
            or r.get("completeness_notes")
            or ""
        )
        lines.append(
            "|"
            + "|".join(
                [
                    _md_cell(r.get("id"), 20),
                    _md_cell(r.get("category"), 24),
                    _fmt_score(r.get("faithfulness")),
                    _fmt_score(r.get("relevance")),
                    _fmt_score(r.get("context_recall")),
                    _fmt_score(r.get("completeness")),
                    _md_cell(note, 80),
                ]
            )
            + "|"
        )

    return "\n".join(lines) + "\n"


# =============================================================================
# GRADING EXPORT (grading_questions.json -> logs/grading_run.json)
# =============================================================================


def export_grading_run(
    config: Optional[Dict[str, Any]] = None,
    out_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Chạy pipeline với `data/grading_questions.json`, ghi `logs/grading_run.json`.
    Dùng cấu hình tốt nhất của nhóm (mặc định VARIANT_CONFIG).
    """
    config = config or VARIANT_CONFIG
    out_path = out_path or (LOGS_DIR / "grading_run.json")
    if not GRADING_QUESTIONS_PATH.exists():
        print(f"[grading] Không tìm thấy {GRADING_QUESTIONS_PATH}")
        return []

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(GRADING_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    from run_telemetry import RunTelemetry, telemetry_ctx

    _gtel = RunTelemetry("grading_export", label=str(config.get("label", "")))
    _gtok = telemetry_ctx.set(_gtel)
    log: List[Dict[str, Any]] = []
    try:
        for q in questions:
            qq = q.get("question", "")
            qid = q.get("id", "")
            try:
                result = rag_answer(
                    query=qq,
                    retrieval_mode=config.get("retrieval_mode", "hybrid"),
                    top_k_search=config.get("top_k_search", 10),
                    top_k_select=config.get("top_k_select", 3),
                    use_rerank=config.get("use_rerank", True),
                    verbose=False,
                )
                log.append({
                    "id": qid,
                    "question": qq,
                    "answer": result["answer"],
                    "sources": result["sources"],
                    "chunks_retrieved": len(result.get("chunks_used") or []),
                    "retrieval_mode": result["config"]["retrieval_mode"],
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                log.append({
                    "id": qid,
                    "question": qq,
                    "answer": f"PIPELINE_ERROR: {e}",
                    "sources": [],
                    "chunks_retrieved": 0,
                    "retrieval_mode": str(config.get("retrieval_mode", "")),
                    "timestamp": datetime.now().isoformat(),
                })

        out_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[grading] Đã ghi {out_path} ({len(log)} câu)")
    finally:
        telemetry_ctx.reset(_gtok)
        _gent = _gtel.finish({"grading_rows": len(log), "output_path": str(out_path)})
        print(
            f"[telemetry] grading_export: {_gent['duration_ms']:.0f} ms, "
            f"cost ~ ${_gent['cost_usd']['total_usd']:.4f} → logs/runs.jsonl"
        )

    return log


# =============================================================================
# MAIN — Chạy evaluation
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "grading":
        print("Export grading_run.json …")
        export_grading_run()
        raise SystemExit(0)

    print("=" * 60)
    print("Sprint 4: Evaluation & Scorecard")
    print("=" * 60)

    if not os.getenv("OPENAI_API_KEY") and os.getenv("LLM_PROVIDER", "openai").lower() == "openai":
        print("\nCảnh báo: Thiếu OPENAI_API_KEY — rag_answer / LLM-as-Judge sẽ lỗi. Tạo file .env từ .env.example.\n")

    # Kiểm tra test questions
    print(f"\nLoading test questions từ: {TEST_QUESTIONS_PATH}")
    try:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)
        print(f"Tìm thấy {len(test_questions)} câu hỏi")

        # In preview
        for q in test_questions[:3]:
            print(f"  [{q['id']}] {q['question']} ({q['category']})")
        print("  ...")

    except FileNotFoundError:
        print("Không tìm thấy file test_questions.json!")
        test_questions = []

    # --- Chạy Baseline ---
    print("\n--- Chạy Baseline ---")
    baseline_results: List[Dict[str, Any]] = []
    try:
        baseline_results = run_scorecard(
            config=BASELINE_CONFIG,
            test_questions=test_questions,
            verbose=True,
        )

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        baseline_md = generate_scorecard_summary(baseline_results, "baseline_dense")
        scorecard_path = RESULTS_DIR / "scorecard_baseline.md"
        scorecard_path.write_text(baseline_md, encoding="utf-8")
        print(f"\nScorecard lưu tại: {scorecard_path}")

    except NotImplementedError:
        print("Pipeline chưa implement. Hoàn thành Sprint 2 trước.")
    except Exception as e:
        print(f"Baseline scorecard lỗi: {e}")

    variant_results: List[Dict[str, Any]] = []

    print("\n--- Chạy Variant (hybrid + rerank) ---")
    try:
        variant_results = run_scorecard(
            config=VARIANT_CONFIG,
            test_questions=test_questions,
            verbose=True,
        )
        variant_md = generate_scorecard_summary(variant_results, VARIANT_CONFIG["label"])
        (RESULTS_DIR / "scorecard_variant.md").write_text(variant_md, encoding="utf-8")
        print(f"\nScorecard variant lưu tại: {RESULTS_DIR / 'scorecard_variant.md'}")
    except Exception as e:
        print(f"Variant scorecard lỗi: {e}")

    if baseline_results and variant_results:
        compare_ab(
            baseline_results,
            variant_results,
            output_csv="ab_comparison.csv",
        )

    print("\nGợi ý: `python eval.py grading` sau khi có data/grading_questions.json")
