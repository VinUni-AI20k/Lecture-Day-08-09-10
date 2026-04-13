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
  ✓ A/B comparison với giải thích
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rag_answer import rag_answer

# =============================================================================
# CẤU HÌNH
# =============================================================================

TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"
RESULTS_DIR = Path(__file__).parent / "results"

BASELINE_CONFIG = {
    "retrieval_mode": "dense",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,
    "label": "baseline_dense",
}

VARIANT_CONFIG = {
    "retrieval_mode": "hybrid",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,          # A/B Rule: chỉ thay retrieval_mode
    "label": "variant_hybrid",
}


VARIANT_HYDE_CONFIG = {
    "retrieval_mode": "hyde",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,
    "label": "variant_hyde",
}
# =============================================================================
# SCORING FUNCTIONS
# 4 metrics: Faithfulness, Answer Relevance, Context Recall, Completeness
# =============================================================================

def score_faithfulness(
    answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Faithfulness: Câu trả lời có bám đúng chứng cứ đã retrieve không?
    Thang điểm 1-5. Dùng LLM-as-Judge.
    """
    if not answer or not chunks_used:
        return {"score": None, "notes": "Không có answer hoặc chunks để chấm"}

    context_texts = "\n\n".join([
        f"[{i+1}] {c.get('text', '')[:300]}"
        for i, c in enumerate(chunks_used)
    ])

    prompt = f"""Bạn là evaluator của một RAG pipeline.
Đánh giá FAITHFULNESS (độ tin cậy dựa trên nguồn) của câu trả lời sau:
- 5: Toàn bộ thông tin trong answer đều có trong retrieved chunks
- 4: Gần như hoàn toàn grounded, 1 chi tiết nhỏ không chắc
- 3: Phần lớn grounded, một số thông tin có thể từ model knowledge
- 2: Nhiều thông tin không có trong retrieved chunks
- 1: Câu trả lời không grounded, phần lớn là bịa

Retrieved chunks:
{context_texts}

Answer cần đánh giá:
{answer}

Trả về JSON (chỉ JSON, không giải thích):
{{"score": <số 1-5>, "reason": "<lý do ngắn gọn trong 1 câu>"}}"""

    try:
        from rag_answer import call_llm
        response = call_llm(prompt)
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "score": int(result.get("score", 3)),
                "notes": result.get("reason", ""),
            }
    except Exception as e:
        pass

    return {"score": None, "notes": "LLM-as-Judge thất bại — cần chấm thủ công"}


def score_answer_relevance(
    query: str,
    answer: str,
) -> Dict[str, Any]:
    """
    Answer Relevance: Answer có trả lời đúng câu hỏi người dùng hỏi không?
    Thang điểm 1-5. Dùng LLM-as-Judge.
    """
    if not answer:
        return {"score": 1, "notes": "Không có answer"}

    prompt = f"""Bạn là evaluator của một RAG pipeline.
Đánh giá ANSWER RELEVANCE (câu trả lời có đúng trọng tâm không):
- 5: Answer trả lời trực tiếp và đầy đủ câu hỏi
- 4: Trả lời đúng nhưng thiếu vài chi tiết phụ
- 3: Trả lời có liên quan nhưng chưa đúng trọng tâm
- 2: Trả lời lạc đề một phần
- 1: Không trả lời câu hỏi

Câu hỏi: {query}
Answer: {answer}

Trả về JSON (chỉ JSON, không giải thích):
{{"score": <số 1-5>, "reason": "<lý do ngắn gọn>"}}"""

    try:
        from rag_answer import call_llm
        response = call_llm(prompt)
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "score": int(result.get("score", 3)),
                "notes": result.get("reason", ""),
            }
    except Exception:
        pass

    return {"score": None, "notes": "LLM-as-Judge thất bại — cần chấm thủ công"}


def score_context_recall(
    chunks_used: List[Dict[str, Any]],
    expected_sources: List[str],
) -> Dict[str, Any]:
    """
    Context Recall: Retriever có mang về đủ evidence cần thiết không?

    Tính recall = (số expected source được retrieve) / (tổng expected sources)
    Convert sang thang 1-5: 0.0→1, 0.25→2, 0.5→3, 0.75→4, 1.0→5
    """
    if not expected_sources:
        return {"score": None, "recall": None, "notes": "No expected sources (abstain case)"}

    retrieved_sources = {
        c.get("metadata", {}).get("source", "")
        for c in chunks_used
    }

    found = 0
    missing = []
    for expected in expected_sources:
        # Partial match: so sánh tên file (bỏ path prefix và extension)
        expected_name = expected.split("/")[-1]
        expected_stem = expected_name.rsplit(".", 1)[0]  # bỏ extension

        matched = any(
            expected_stem.lower().replace("-", "_").replace(".", "_") in
            r.lower().replace("-", "_").replace(".", "_")
            for r in retrieved_sources
        )
        if matched:
            found += 1
        else:
            missing.append(expected)

    recall = found / len(expected_sources)

    # Convert recall → thang 1-5
    if recall >= 1.0:
        score = 5
    elif recall >= 0.75:
        score = 4
    elif recall >= 0.5:
        score = 3
    elif recall >= 0.25:
        score = 2
    else:
        score = 1

    return {
        "score": score,
        "recall": recall,
        "found": found,
        "missing": missing,
        "notes": f"Retrieved {found}/{len(expected_sources)} expected sources" +
                 (f". Missing: {missing}" if missing else ""),
    }


def score_completeness(
    query: str,
    answer: str,
    expected_answer: str,
) -> Dict[str, Any]:
    """
    Completeness: Answer có thiếu điều kiện ngoại lệ hoặc bước quan trọng không?
    So sánh answer vs expected_answer bằng LLM-as-Judge.
    """
    if not answer or not expected_answer:
        return {"score": None, "notes": "Thiếu answer hoặc expected_answer"}

    prompt = f"""Bạn là evaluator của một RAG pipeline.
Đánh giá COMPLETENESS (độ đầy đủ) của model answer so với expected answer:
- 5: Model answer bao gồm đủ tất cả điểm quan trọng trong expected answer
- 4: Thiếu 1 chi tiết nhỏ, không quan trọng
- 3: Thiếu một số thông tin quan trọng
- 2: Thiếu nhiều thông tin quan trọng
- 1: Thiếu phần lớn nội dung cốt lõi

Câu hỏi: {query}
Expected answer: {expected_answer}
Model answer: {answer}

Trả về JSON (chỉ JSON, không giải thích):
{{"score": <số 1-5>, "missing_points": ["điểm còn thiếu 1", "..."], "reason": "<lý do ngắn>"}}"""

    try:
        from rag_answer import call_llm
        response = call_llm(prompt)
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "score": int(result.get("score", 3)),
                "missing_points": result.get("missing_points", []),
                "notes": result.get("reason", ""),
            }
    except Exception:
        pass

    return {"score": None, "notes": "LLM-as-Judge thất bại — cần chấm thủ công"}


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
        config: RAG config dict (retrieval_mode, top_k_search, top_k_select, use_rerank, label)
        test_questions: List câu hỏi. Nếu None, đọc từ TEST_QUESTIONS_PATH
        verbose: In kết quả từng câu

    Returns:
        List dict kết quả, mỗi dict có: id, question, category,
        faithfulness, relevance, context_recall, completeness, answer, ...
    """
    if test_questions is None:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)

    label = config.get("label", "unknown")
    rag_config = {k: v for k, v in config.items() if k != "label"}

    print(f"\n{'='*60}")
    print(f"Running Scorecard: {label}")
    print(f"Config: {rag_config}")
    print('='*60)

    results = []

    for q in test_questions:
        qid = q["id"]
        question = q["question"]
        expected_answer = q.get("expected_answer", "")
        expected_sources = q.get("expected_sources", [])
        category = q.get("category", "unknown")

        if verbose:
            print(f"\n[{qid}] {question}")

        try:
            # Chạy RAG pipeline
            rag_result = rag_answer(question, **rag_config)
            answer = rag_result["answer"]
            chunks_used = rag_result["chunks_used"]
            sources = rag_result["sources"]

            # Chấm điểm 4 metrics
            f_result = score_faithfulness(answer, chunks_used)
            r_result = score_answer_relevance(question, answer)
            rc_result = score_context_recall(chunks_used, expected_sources)
            c_result = score_completeness(question, answer, expected_answer)

            row = {
                "config": label,
                "id": qid,
                "category": category,
                "question": question,
                "answer": answer,
                "sources": str(sources),
                "faithfulness": f_result.get("score"),
                "faithfulness_notes": f_result.get("notes", ""),
                "relevance": r_result.get("score"),
                "relevance_notes": r_result.get("notes", ""),
                "context_recall": rc_result.get("score"),
                "context_recall_notes": rc_result.get("notes", ""),
                "completeness": c_result.get("score"),
                "completeness_notes": c_result.get("notes", ""),
            }

            if verbose:
                print(f"  Answer    : {answer[:120]}...")
                print(f"  Faithful  : {f_result['score']}/5 — {f_result.get('notes', '')[:60]}")
                print(f"  Relevance : {r_result['score']}/5 — {r_result.get('notes', '')[:60]}")
                print(f"  Ctx Recall: {rc_result['score']}/5 — {rc_result.get('notes', '')[:60]}")
                print(f"  Complete  : {c_result['score']}/5 — {c_result.get('notes', '')[:60]}")

        except Exception as e:
            print(f"  Lỗi: {e}")
            row = {
                "config": label,
                "id": qid,
                "category": category,
                "question": question,
                "answer": f"ERROR: {e}",
                "sources": "",
                "faithfulness": None,
                "faithfulness_notes": str(e),
                "relevance": None,
                "relevance_notes": "",
                "context_recall": None,
                "context_recall_notes": "",
                "completeness": None,
                "completeness_notes": "",
            }

        results.append(row)

    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]
    print(f"\n--- Tổng kết {label} ---")
    for metric in metrics:
        scores = [r[metric] for r in results if r[metric] is not None]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {metric:<20}: {avg:.2f}/5 (n={len(scores)}/{len(results)})")

    return results


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
    """
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]

    print(f"\n{'='*70}")
    print("A/B Comparison: Baseline vs Variant")
    print('='*70)
    print(f"{'Metric':<22} {'Baseline':>10} {'Variant':>10} {'Delta':>8}")
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

        print(f"{metric:<22} {b_str:>10} {v_str:>10} {d_str:>8}")

    # Per-question comparison
    print(f"\n{'ID':<6} {'B: F/R/Rc/C':<18} {'V: F/R/Rc/C':<18} {'Better?':<10}")
    print("-" * 58)

    b_by_id = {r["id"]: r for r in baseline_results}
    for v_row in variant_results:
        qid = v_row["id"]
        b_row = b_by_id.get(qid, {})

        b_scores_str = "/".join([str(b_row.get(m) or "?") for m in metrics])
        v_scores_str = "/".join([str(v_row.get(m) or "?") for m in metrics])

        b_total = sum((b_row.get(m) or 0) for m in metrics)
        v_total = sum((v_row.get(m) or 0) for m in metrics)
        better = "Variant ✓" if v_total > b_total else ("Baseline" if b_total > v_total else "Tie")

        print(f"{qid:<6} {b_scores_str:<18} {v_scores_str:<18} {better:<10}")

    # Export CSV
    if output_csv:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = RESULTS_DIR / output_csv
        combined = baseline_results + variant_results
        if combined:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=combined[0].keys())
                writer.writeheader()
                writer.writerows(combined)
            print(f"\nKết quả A/B đã lưu vào: {csv_path}")


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

    md = f"""# Scorecard: {label}
Generated: {timestamp}

## Summary

| Metric | Average Score |
|--------|--------------|
"""
    for metric, avg in averages.items():
        avg_str = f"{avg:.2f}/5" if avg is not None else "N/A"
        md += f"| {metric.replace('_', ' ').title()} | {avg_str} |\n"

    md += "\n## Per-Question Results\n\n"
    md += "| ID | Category | Faithful | Relevant | Recall | Complete | Notes |\n"
    md += "|----|----------|----------|----------|--------|----------|-------|\n"

    for r in results:
        notes = r.get("faithfulness_notes", "")[:60]
        md += (f"| {r['id']} | {r['category']} | {r.get('faithfulness', 'N/A')} | "
               f"{r.get('relevance', 'N/A')} | {r.get('context_recall', 'N/A')} | "
               f"{r.get('completeness', 'N/A')} | {notes} |\n")

    return md


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 4: Evaluation & Scorecard")
    print("=" * 60)

    # Load test questions
    print(f"\nLoading test questions từ: {TEST_QUESTIONS_PATH}")
    with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        test_questions = json.load(f)
    print(f"Tìm thấy {len(test_questions)} câu hỏi")

    # --- Chạy Baseline ---
    print("\n--- Chạy Baseline (Dense) ---")
    baseline_results = run_scorecard(
        config=BASELINE_CONFIG,
        test_questions=test_questions,
        verbose=True,
    )

    # Save baseline scorecard
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    baseline_md = generate_scorecard_summary(baseline_results, "baseline_dense")
    scorecard_path = RESULTS_DIR / "scorecard_baseline.md"
    scorecard_path.write_text(baseline_md, encoding="utf-8")
    print(f"\nBaseline scorecard lưu tại: {scorecard_path}")

    # --- Chạy Variant ---
    print("\n--- Chạy Variant (Hybrid) ---")
    variant_results = run_scorecard(
        config=VARIANT_CONFIG,
        test_questions=test_questions,
        verbose=True,
    )

    # Save variant scorecard
    variant_md = generate_scorecard_summary(variant_results, "variant_hybrid")
    variant_path = RESULTS_DIR / "scorecard_variant.md"
    variant_path.write_text(variant_md, encoding="utf-8")
    print(f"\nVariant scorecard lưu tại: {variant_path}")

    # --- A/B Comparison ---
    print("\n--- A/B Comparison ---")
    compare_ab(
        baseline_results=baseline_results,
        variant_results=variant_results,
        output_csv="ab_comparison.csv",
    )

    print("\nSprint 4 hoàn thành!")
    print("\n\nViệc cần làm Sprint 4:")
    print("  1. Hoàn thành Sprint 2 + 3 trước")
    print("  2. Chấm điểm thủ công hoặc implement LLM-as-Judge trong score_* functions")
    print("  3. Chạy run_scorecard(BASELINE_CONFIG)")
    print("  4. Chạy run_scorecard(VARIANT_CONFIG)")
    print("  5. Gọi compare_ab() để thấy delta")
    print("  6. Cập nhật docs/tuning-log.md với kết quả và nhận xét")
