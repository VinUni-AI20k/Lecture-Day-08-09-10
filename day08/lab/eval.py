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
import os
import re
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rag_answer import rag_answer

logger = logging.getLogger(__name__)

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
VARIANT_CONFIG = {
    "retrieval_mode": "hybrid",   # Hoặc "dense" nếu chỉ đổi rerank
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": True,           # Hoặc False nếu variant là hybrid không rerank
    "label": "variant_hybrid_rerank",
}


# =============================================================================
# GEMINI LLM JUDGE
# =============================================================================

def _call_gemini(prompt: str, retries: int = 3, retry_delay: float = 2.0) -> Optional[str]:
    """
    Gọi Gemini API với một prompt và trả về text response.

    Đọc API key từ biến môi trường GEMINI_API_KEY.
    Dùng model gemini-2.0-flash (nhanh, rẻ, đủ dùng cho judge task).

    Args:
        prompt: Nội dung prompt gửi lên Gemini
        retries: Số lần thử lại khi gặp lỗi tạm thời (rate limit, timeout)
        retry_delay: Số giây chờ giữa mỗi lần retry

    Returns:
        Text response từ Gemini, hoặc None nếu thất bại hoàn toàn

    Raises:
        EnvironmentError: Nếu GEMINI_API_KEY chưa được set
    """
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ImportError(
            "Thiếu thư viện google-generativeai. "
            "Cài đặt bằng: pip install google-generativeai"
        ) from exc

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Chưa set GEMINI_API_KEY. "
            "Chạy: export GEMINI_API_KEY='your-key-here'"
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,   # Deterministic — quan trọng cho judge
                    max_output_tokens=512,
                ),
            )
            return response.text
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Gemini call thất bại (lần %d/%d): %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(retry_delay)

    logger.error("Gemini call thất bại sau %d lần: %s", retries, last_exc)
    return None


def _parse_judge_json(raw: Optional[str], fallback_score: int = 3) -> Dict[str, Any]:
    """
    Parse JSON từ response của Gemini judge.

    Gemini đôi khi wrap JSON trong markdown code block (```json ... ```)
    hoặc thêm text thừa — hàm này xử lý cả hai trường hợp.

    Args:
        raw: Raw text từ Gemini
        fallback_score: Điểm mặc định nếu parse thất bại

    Returns:
        Dict với "score" (int 1-5) và "reason" (str)
    """
    if not raw:
        return {"score": fallback_score, "reason": "Không nhận được response từ LLM judge"}

    # Bóc markdown code block nếu có
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()

    # Tìm JSON object đầu tiên trong string (phòng trường hợp có text thừa trước/sau)
    json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not json_match:
        return {"score": fallback_score, "reason": f"Không parse được JSON: {raw[:200]}"}

    try:
        parsed = json.loads(json_match.group())
        score = int(parsed.get("score", fallback_score))
        score = max(1, min(5, score))  # Clamp về [1, 5]
        reason = str(parsed.get("reason", parsed.get("notes", "")))
        return {"score": score, "reason": reason}
    except (json.JSONDecodeError, ValueError) as exc:
        return {"score": fallback_score, "reason": f"Lỗi parse JSON: {exc} | Raw: {raw[:200]}"}


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
    Câu hỏi: Model có tự bịa thêm thông tin ngoài retrieved context không?

    Thang điểm 1-5:
      5: Mọi thông tin trong answer đều có trong retrieved chunks
      4: Gần như hoàn toàn grounded, 1 chi tiết nhỏ chưa chắc chắn
      3: Phần lớn grounded, một số thông tin có thể từ model knowledge
      2: Nhiều thông tin không có trong retrieved chunks
      1: Câu trả lời không grounded, phần lớn là model bịa
    """
    if not chunks_used:
        return {
            "score": 1,
            "notes": "Không có retrieved chunks — không thể verify faithfulness",
        }

    # Ghép nội dung các chunk thành context block
    context_block = "\n\n---\n\n".join(
        f"[Chunk {i+1}]\n{c.get('text', c.get('content', str(c)))}"
        for i, c in enumerate(chunks_used)
    )

    prompt = f"""Bạn là một evaluator khách quan cho hệ thống RAG (Retrieval-Augmented Generation).

Nhiệm vụ: Đánh giá mức độ FAITHFULNESS — tức là câu trả lời có bám đúng thông tin trong các đoạn văn đã retrieve không, hay mô hình tự bịa thêm thông tin không có trong context.

=== RETRIEVED CONTEXT ===
{context_block}

=== MODEL ANSWER ===
{answer}

=== HƯỚNG DẪN CHẤM ĐIỂM ===
5: Mọi thông tin trong answer đều có nguồn gốc từ retrieved chunks
4: Gần như hoàn toàn grounded, tối đa 1 chi tiết nhỏ không rõ nguồn
3: Phần lớn grounded, nhưng có một vài thông tin xuất phát từ model knowledge
2: Nhiều thông tin không có trong retrieved chunks
1: Câu trả lời không grounded, phần lớn là model bịa hoặc hallucinate

Hãy trả về JSON (và CHỈ JSON, không có text nào khác):
{{"score": <số nguyên từ 1 đến 5>, "reason": "<giải thích ngắn gọn bằng tiếng Việt, tối đa 2 câu>"}}"""

    raw = _call_gemini(prompt)
    parsed = _parse_judge_json(raw)

    return {
        "score": parsed["score"],
        "notes": parsed["reason"],
    }


def score_answer_relevance(
    query: str,
    answer: str,
) -> Dict[str, Any]:
    """
    Answer Relevance: Answer có trả lời đúng câu hỏi người dùng hỏi không?
    Câu hỏi: Model có bị lạc đề hay trả lời đúng vấn đề cốt lõi không?

    Thang điểm 1-5:
      5: Answer trả lời trực tiếp và đầy đủ câu hỏi
      4: Trả lời đúng nhưng thiếu vài chi tiết phụ
      3: Trả lời có liên quan nhưng chưa đúng trọng tâm
      2: Trả lời lạc đề một phần
      1: Không trả lời câu hỏi
    """
    prompt = f"""Bạn là một evaluator khách quan cho hệ thống RAG (Retrieval-Augmented Generation).

Nhiệm vụ: Đánh giá mức độ ANSWER RELEVANCE — tức là câu trả lời có trả lời đúng và đủ câu hỏi của người dùng không.

=== CÂU HỎI NGƯỜI DÙNG ===
{query}

=== MODEL ANSWER ===
{answer}

=== HƯỚNG DẪN CHẤM ĐIỂM ===
5: Answer trả lời trực tiếp và đầy đủ câu hỏi, đúng trọng tâm
4: Trả lời đúng hướng nhưng thiếu một vài chi tiết phụ
3: Có liên quan đến câu hỏi nhưng chưa trúng trọng tâm chính
2: Trả lời lạc đề một phần, chỉ liên quan một phần nhỏ
1: Hoàn toàn không trả lời câu hỏi hoặc lạc đề hoàn toàn

Hãy trả về JSON (và CHỈ JSON, không có text nào khác):
{{"score": <số nguyên từ 1 đến 5>, "reason": "<giải thích ngắn gọn bằng tiếng Việt, tối đa 2 câu>"}}"""

    raw = _call_gemini(prompt)
    parsed = _parse_judge_json(raw)

    return {
        "score": parsed["score"],
        "notes": parsed["reason"],
    }


def score_context_recall(
    chunks_used: List[Dict[str, Any]],
    expected_sources: List[str],
) -> Dict[str, Any]:
    """
    Context Recall: Retriever có mang về đủ evidence cần thiết không?
    Câu hỏi: Expected source có nằm trong retrieved chunks không?

    Đây là metric đo retrieval quality, không phải generation quality.
    Tính recall dựa trên source matching — không cần LLM judge.

    Cách tính:
        recall = (số expected source được retrieve) / (tổng số expected sources)
    """
    if not expected_sources:
        return {"score": None, "recall": None, "notes": "No expected sources"}

    retrieved_sources = {
        c.get("metadata", {}).get("source", "")
        for c in chunks_used
    }

    found = 0
    missing = []
    for expected in expected_sources:
        # Partial match theo tên file (bỏ extension và path prefix)
        expected_name = expected.split("/")[-1]
        expected_stem = re.sub(r"\.(pdf|md|txt|docx)$", "", expected_name, flags=re.IGNORECASE)
        matched = any(expected_stem.lower() in r.lower() for r in retrieved_sources)
        if matched:
            found += 1
        else:
            missing.append(expected)

    recall = found / len(expected_sources)

    # Convert recall [0.0, 1.0] → score [1, 5]
    # 0.0 → 1,  0.25 → 2,  0.5 → 3,  0.75 → 4,  1.0 → 5
    score = max(1, round(recall * 4) + 1)

    return {
        "score": score,
        "recall": recall,
        "found": found,
        "missing": missing,
        "notes": (
            f"Retrieved {found}/{len(expected_sources)} expected sources"
            + (f". Missing: {missing}" if missing else "")
        ),
    }


def score_completeness(
    query: str,
    answer: str,
    expected_answer: str,
) -> Dict[str, Any]:
    """
    Completeness: Answer có thiếu điều kiện ngoại lệ hoặc bước quan trọng không?
    Câu hỏi: Answer có bao phủ đủ thông tin so với expected_answer không?

    Thang điểm 1-5:
      5: Answer bao gồm đủ tất cả điểm quan trọng trong expected_answer
      4: Thiếu 1 chi tiết nhỏ
      3: Thiếu một số thông tin quan trọng
      2: Thiếu nhiều thông tin quan trọng
      1: Thiếu phần lớn nội dung cốt lõi
    """
    if not expected_answer or expected_answer.strip() == "":
        return {
            "score": None,
            "notes": "Không có expected_answer để so sánh",
        }

    prompt = f"""Bạn là một evaluator khách quan cho hệ thống RAG (Retrieval-Augmented Generation).

Nhiệm vụ: Đánh giá mức độ COMPLETENESS — tức là câu trả lời của mô hình có bao phủ đầy đủ các điểm quan trọng so với đáp án tham chiếu không.

=== CÂU HỎI ===
{query}

=== ĐÁP ÁN THAM CHIẾU (Expected Answer) ===
{expected_answer}

=== MODEL ANSWER ===
{answer}

=== HƯỚNG DẪN CHẤM ĐIỂM ===
Tập trung vào nội dung, không phải cách diễn đạt.
5: Bao phủ tất cả điểm quan trọng trong đáp án tham chiếu
4: Bỏ sót tối đa 1 chi tiết nhỏ hoặc ngoại lệ
3: Thiếu một số thông tin quan trọng (khoảng 20-40% nội dung cốt lõi)
2: Thiếu nhiều thông tin quan trọng (hơn 40% nội dung cốt lõi)
1: Thiếu phần lớn nội dung — chỉ trả lời được phần nhỏ

Hãy trả về JSON (và CHỈ JSON, không có text nào khác):
{{"score": <số nguyên từ 1 đến 5>, "reason": "<giải thích ngắn gọn bằng tiếng Việt, tối đa 2 câu, liệt kê điểm bị thiếu nếu có>"}}"""

    raw = _call_gemini(prompt)
    parsed = _parse_judge_json(raw)

    return {
        "score": parsed["score"],
        "notes": parsed["reason"],
    }


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
        delta = (v_avg - b_avg) if (b_avg and v_avg) else None

        b_str = f"{b_avg:.2f}" if b_avg else "N/A"
        v_str = f"{v_avg:.2f}" if v_avg else "N/A"
        d_str = f"{delta:+.2f}" if delta else "N/A"

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
        avg_str = f"{avg:.2f}/5" if avg else "N/A"
        md += f"| {metric.replace('_', ' ').title()} | {avg_str} |\n"

    md += "\n## Per-Question Results\n\n"
    md += "| ID | Category | Faithful | Relevant | Recall | Complete | Notes |\n"
    md += "|----|----------|----------|----------|--------|----------|-------|\n"

    for r in results:
        md += (f"| {r['id']} | {r['category']} | {r.get('faithfulness', 'N/A')} | "
               f"{r.get('relevance', 'N/A')} | {r.get('context_recall', 'N/A')} | "
               f"{r.get('completeness', 'N/A')} | {r.get('faithfulness_notes', '')[:50]} |\n")

    return md


# =============================================================================
# MAIN — Chạy evaluation
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 4: Evaluation & Scorecard")
    print("=" * 60)

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

    # --- Chạy Baseline ---
    print("\n--- Chạy Baseline ---")
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
        baseline_results = []

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
        print("Variant chưa implement. Hoàn thành Sprint 3 trước.")
        variant_results = []

    # --- A/B Comparison ---
    if baseline_results and variant_results:
        compare_ab(
            baseline_results,
            variant_results,
            output_csv="ab_comparison.csv",
        )
    else:
        print("\nCần cả baseline và variant để chạy A/B comparison.")