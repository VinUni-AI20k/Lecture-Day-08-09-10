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

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rag_answer import rag_answer, call_llm

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
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": True,           # Hoặc False nếu variant là hybrid không rerank
    "label": "variant_hybrid_rerank",
}


def _call_judge_llm(prompt: str) -> str:
    """Thin wrapper around call_llm() — single mock point for tests."""
    return call_llm(prompt)


def _parse_judge_response(raw: str) -> dict:
    """
    Parse LLM judge response JSON with graceful fallback.
    - Strips markdown code fences if present
    - Validates score is int in [1, 5]
    - Returns fallback dict on any parse failure
    """
    import re
    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return {"score": None, "notes": f"Parse error: {raw}"}

    if not isinstance(parsed, dict) or "score" not in parsed:
        return {"score": None, "notes": f"Parse error: {raw}"}

    score = parsed["score"]
    if not isinstance(score, int) or score < 1 or score > 5:
        return {"score": None, "notes": f"Parse error: {raw}"}

    return parsed


# =============================================================================
# SCORING FUNCTIONS
# 4 metrics từ slide: Faithfulness, Answer Relevance, Context Recall, Completeness
# =============================================================================

def score_faithfulness(
    answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Faithfulness: Câu trả lời có bám đúng chứng cứ đã retrieve không?
    Score 1-5 via LLM-as-Judge.
    """
    if not chunks_used:
        return {"score": 1, "notes": "No context retrieved — answer cannot be grounded"}

    # Build context block with source headers
    context_parts = []
    for chunk in chunks_used:
        source = chunk.get("metadata", {}).get("source", "unknown")
        text = chunk.get("text", "")
        context_parts.append(f"[{source}]\n{text}")
    context_block = "\n\n".join(context_parts)

    prompt = f"""You are an evaluation judge. Rate the faithfulness of the answer below.

Retrieved context:
{context_block}

Answer to evaluate:
{answer}

Faithfulness rubric:
  5 — Every claim in the answer is directly supported by the retrieved context.
  4 — Nearly all claims are grounded; one minor detail is uncertain.
  3 — Most claims are grounded; some information may come from model knowledge.
  2 — Several claims are not present in the retrieved context.
  1 — The answer contains information not found in any retrieved chunk.

Respond ONLY with valid JSON: {{"score": <int 1-5>, "notes": "<explanation>"}}"""

    raw = _call_judge_llm(prompt)
    result = _parse_judge_response(raw)
    if "notes" not in result or not result["notes"]:
        result["notes"] = raw
    return result


def score_answer_relevance(
    query: str,
    answer: str,
) -> Dict[str, Any]:
    """
    Answer Relevance: Answer có trả lời đúng câu hỏi người dùng hỏi không?
    Score 1-5 via LLM-as-Judge.
    """
    prompt = f"""You are an evaluation judge. Rate how well the answer addresses the question.

Question: {query}

Answer: {answer}

Relevance rubric:
  5 — The answer directly and completely addresses the question.
  4 — The answer addresses the question but omits minor details.
  3 — The answer is related but does not fully address the core question.
  2 — The answer is partially off-topic.
  1 — The answer does not address the question at all.

Respond ONLY with valid JSON: {{"score": <int 1-5>, "notes": "<explanation>"}}"""

    raw = _call_judge_llm(prompt)
    result = _parse_judge_response(raw)
    if "notes" not in result or not result["notes"]:
        result["notes"] = raw
    return result


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
    Completeness: Answer có bao phủ đủ thông tin so với expected_answer không?
    Score 1-5 via LLM-as-Judge.
    """
    if not expected_answer:
        return {"score": None, "missing_points": [], "notes": "No expected answer provided"}

    prompt = f"""You are an evaluation judge. Compare the model answer against the expected answer.

Question: {query}

Model answer: {answer}

Expected answer: {expected_answer}

Completeness rubric:
  5 — The model answer covers all key points in the expected answer.
  4 — The model answer is missing one minor point.
  3 — The model answer is missing some important points.
  2 — The model answer is missing many important points.
  1 — The model answer is missing most of the key content.

Respond ONLY with valid JSON: {{"score": <int 1-5>, "missing_points": ["<point>", ...], "notes": "<explanation>"}}"""

    raw = _call_judge_llm(prompt)
    result = _parse_judge_response(raw)
    if result.get("score") is None:
        result.setdefault("missing_points", [])
        return result
    result.setdefault("missing_points", [])
    if "notes" not in result or not result["notes"]:
        result["notes"] = raw
    return result


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
        print(f"\nAverage {metric}: {avg:.2f}" if avg else f"\nAverage {metric}: N/A (chưa chấm)")

    return results


# =============================================================================
# A/B COMPARISON
# =============================================================================

def compare_ab(
    baseline_results: List[Dict],
    variant_results: List[Dict],
    output_csv: Optional[str] = None,
) -> None:
    """So sánh baseline vs variant theo từng câu hỏi và tổng thể."""
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

        b_scores_str = "/".join([str(b_row.get(m, "?")) for m in metrics])
        v_scores_str = "/".join([str(v_row.get(m, "?")) for m in metrics])

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
    """Tạo báo cáo tóm tắt scorecard dạng markdown."""
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]
    averages = {}
    for metric in metrics:
        scores = [r[metric] for r in results if r[metric] is not None]
        averages[metric] = sum(scores) / len(scores) if scores else None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"# Scorecard: {label}\nGenerated: {timestamp}\n\n## Summary\n\n"
    md += "| Metric | Average Score |\n|--------|---------------|\n"
    for metric, avg in averages.items():
        avg_str = f"{avg:.2f}/5" if avg is not None else "N/A"
        md += f"| {metric.replace('_', ' ').title()} | {avg_str} |\n"

    md += "\n## Per-Question Results\n\n"
    md += "| ID | Category | Faithful | Relevant | Recall | Complete | Notes |\n"
    md += "|----|----------|----------|----------|--------|----------|-------|\n"
    for r in results:
        notes = str(r.get("faithfulness_notes", ""))[:50].replace("|", "/")
        md += (
            f"| {r['id']} | {r['category']} "
            f"| {r.get('faithfulness', 'N/A')} "
            f"| {r.get('relevance', 'N/A')} "
            f"| {r.get('context_recall', 'N/A')} "
            f"| {r.get('completeness', 'N/A')} "
            f"| {notes} |\n"
        )
    return md


# =============================================================================
# GRADING LOG
# =============================================================================

def run_grading_log(
    questions_path: Path,
    config: Dict[str, Any],
    output_path: Path,
) -> None:
    """
    Sinh grading log JSON để nộp bài.
    Mỗi entry ghi: id, question, answer, sources, chunks_retrieved, retrieval_mode, timestamp.
    """
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    log_entries = []
    for q in questions:
        try:
            result = rag_answer(
                query=q["question"],
                retrieval_mode=config.get("retrieval_mode", "dense"),
                top_k_search=config.get("top_k_search", 10),
                top_k_select=config.get("top_k_select", 3),
                use_rerank=config.get("use_rerank", False),
                verbose=False,
            )
            answer = result["answer"]
            sources = result.get("sources", [])
            chunks_retrieved = len(result.get("chunks_used", []))
        except Exception as e:
            answer = f"PIPELINE_ERROR: {str(e)}"
            sources = []
            chunks_retrieved = 0

        log_entries.append({
            "id": q["id"],
            "question": q["question"],
            "answer": answer,
            "sources": sources,
            "chunks_retrieved": chunks_retrieved,
            "retrieval_mode": config.get("retrieval_mode", "dense"),
            "timestamp": datetime.now().isoformat(),
        })

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(log_entries, f, ensure_ascii=False, indent=2)
    print(f"\nGrading log saved: {output_path} ({len(log_entries)} entries)")


# =============================================================================
# MAIN — Chạy evaluation
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 4: Evaluation & Scorecard")
    print("=" * 60)

    # Load test questions
    print(f"\nLoading test questions từ: {TEST_QUESTIONS_PATH}")
    try:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)
        print(f"Tìm thấy {len(test_questions)} câu hỏi")
        for q in test_questions[:3]:
            print(f"  [{q['id']}] {q['question']} ({q['category']})")
        print("  ...")
    except FileNotFoundError:
        print("Không tìm thấy file test_questions.json!")
        test_questions = []

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    baseline_results = []
    variant_results = []

    # --- Chạy Baseline ---
    print("\n--- Chạy Baseline ---")
    try:
        baseline_results = run_scorecard(
            config=BASELINE_CONFIG,
            test_questions=test_questions,
            verbose=True,
        )
        baseline_md = generate_scorecard_summary(baseline_results, "baseline_dense")
        scorecard_path = RESULTS_DIR / "scorecard_baseline.md"
        scorecard_path.write_text(baseline_md, encoding="utf-8")
        print(f"\nScorecard lưu tại: {scorecard_path}")
    except NotImplementedError:
        print("Pipeline chưa implement. Hoàn thành Sprint 2 trước.")

    # --- Chạy Variant ---
    print("\n--- Chạy Variant ---")
    try:
        variant_results = run_scorecard(
            config=VARIANT_CONFIG,
            test_questions=test_questions,
            verbose=True,
        )
        variant_md = generate_scorecard_summary(variant_results, VARIANT_CONFIG["label"])
        (RESULTS_DIR / "scorecard_variant.md").write_text(variant_md, encoding="utf-8")
        print(f"\nScorecard lưu tại: {RESULTS_DIR / 'scorecard_variant.md'}")
    except NotImplementedError:
        print("Variant pipeline chưa implement.")

    # --- A/B Comparison ---
    if baseline_results and variant_results:
        compare_ab(
            baseline_results,
            variant_results,
            output_csv="ab_comparison.csv",
        )

    # --- Grading Log ---
    print("\n--- Sinh Grading Log ---")
    try:
        run_grading_log(
            questions_path=TEST_QUESTIONS_PATH,
            config=VARIANT_CONFIG,
            output_path=Path(__file__).parent / "logs" / "grading_run.json",
        )
    except NotImplementedError:
        print("Pipeline chưa implement — grading log bỏ qua.")
