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
import importlib
import os
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rag_answer import rag_answer

# =============================================================================
# CẤU HÌNH
# =============================================================================

TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"
GRADING_QUESTIONS_PATH = Path(__file__).parent / "data" / "grading_questions.json"
RESULTS_DIR = Path(__file__).parent / "results"
LOGS_DIR = Path(__file__).parent / "logs"

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
    "retrieval_mode": "dense",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": True,
    "label": "variant_dense_rerank",
}


# =============================================================================
# SCORING FUNCTIONS
# 4 metrics từ slide: Faithfulness, Answer Relevance, Context Recall, Completeness
# =============================================================================

def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize_text(text: str) -> List[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    stopwords = {
        "la", "là", "va", "và", "cho", "cua", "của", "the", "this", "that", "and",
        "or", "to", "trong", "voi", "với", "co", "có", "khong", "không", "mot", "một",
        "cac", "các", "ve", "về", "nhung", "nhưng", "de", "để", "voi", "when", "what",
    }
    tokens = [token for token in normalized.split() if len(token) > 2 and token not in stopwords]
    return tokens


def _safe_extract_json(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    candidates = [text.strip()]
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        candidates.insert(0, match.group(0))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue

    return {}


def _score_from_similarity(primary_text: str, reference_texts: List[str]) -> int:
    primary_tokens = set(_tokenize_text(primary_text))
    reference_tokens = set()
    for text in reference_texts:
        reference_tokens.update(_tokenize_text(text))

    if not primary_tokens:
        return 1
    if not reference_tokens:
        return 3

    overlap = len(primary_tokens & reference_tokens)
    coverage = overlap / max(len(primary_tokens), 1)

    if coverage >= 0.85:
        return 5
    if coverage >= 0.65:
        return 4
    if coverage >= 0.45:
        return 3
    if coverage >= 0.25:
        return 2
    return 1


def _judge_with_llm(metric_name: str, prompt: str) -> Optional[Dict[str, Any]]:
    raw_response = None

    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            from openai import OpenAI

            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a strict evaluation judge for a RAG pipeline. Return only JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=300,
            )
            raw_response = response.choices[0].message.content
        else:
            google_key = os.getenv("GOOGLE_API_KEY")
            if google_key:
                genai = importlib.import_module("google.generativeai")
                getattr(genai, "configure")(api_key=google_key)
                model_cls = getattr(genai, "GenerativeModel")
                model = model_cls(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
                response = model.generate_content(prompt)
                raw_response = getattr(response, "text", None)
    except Exception as exc:
        return {
            "score": None,
            "notes": f"LLM judge unavailable for {metric_name}: {exc}",
        }

    parsed = _safe_extract_json(raw_response or "")
    if not parsed:
        return None

    score_value = parsed.get("score", None)
    notes_value = parsed.get("notes", parsed.get("reason", ""))
    try:
        score_int = int(round(float(score_value))) if score_value is not None else None
    except Exception:
        score_int = None

    if score_int is not None:
        score_int = max(1, min(5, score_int))

    return {
        "score": score_int,
        "notes": str(notes_value).strip() if notes_value is not None else "",
    }


def _judge_or_fallback(metric_name: str, prompt: str, fallback_score: int, fallback_notes: str) -> Dict[str, Any]:
    judged = _judge_with_llm(metric_name, prompt)
    if judged is not None:
        score = judged.get("score")
        notes = judged.get("notes", "")
        if score is not None:
            return {"score": score, "notes": notes or fallback_notes}

    return {"score": fallback_score, "notes": fallback_notes}


def _source_basename(source: str) -> str:
    source = (source or "").replace("\\", "/")
    filename = source.rsplit("/", 1)[-1].lower()
    for extension in (".pdf", ".md", ".txt", ".docx"):
        if filename.endswith(extension):
            filename = filename[: -len(extension)]
    return filename


def _is_abstain_answer(answer: str) -> bool:
    normalized = _normalize_text(answer)
    return any(
        phrase in normalized
        for phrase in [
            "khong du du lieu",
            "khong tim thay thong tin",
            "khong co thong tin",
            "khong biet",
            "do not know",
            "insufficient context",
            "khong du thong tin",
        ]
    )

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

    TODO Sprint 4 — Có 2 cách chấm:

    Cách 1 — Chấm thủ công (Manual, đơn giản):
        Đọc answer và chunks_used, chấm điểm theo thang trên.
        Ghi lý do ngắn gọn vào "notes".

    Cách 2 — LLM-as-Judge (Tự động, nâng cao):
        Gửi prompt cho LLM:
            "Given these retrieved chunks: {chunks}
             And this answer: {answer}
             Rate the faithfulness on a scale of 1-5.
             5 = completely grounded in the provided context.
             1 = answer contains information not in the context.
             Output JSON: {'score': <int>, 'reason': '<string>'}"

    Trả về dict với: score (1-5) và notes (lý do)
    """
    context_texts = [chunk.get("text", "") for chunk in chunks_used]
    context_block = "\n\n".join(context_texts)

    prompt = f"""Rate the faithfulness of the answer to the provided context.
Return JSON with keys: score (integer 1-5) and notes (short explanation).

Rubric:
5 = every claim is supported by the context
4 = mostly supported, only one tiny detail is uncertain
3 = mixed support, some unsupported detail may appear
2 = many unsupported details
1 = largely hallucinated

Answer:
{answer}

Context:
{context_block}
"""

    if not answer or not chunks_used:
        fallback_score = 1 if answer and not _is_abstain_answer(answer) else 3
        return {
            "score": fallback_score,
            "notes": "No retrieved context available" if not chunks_used else "Answer is empty or cannot be judged confidently",
        }

    if _is_abstain_answer(answer):
        return {
            "score": 4,
            "notes": "Answer abstains instead of hallucinating",
        }

    fallback_score = _score_from_similarity(answer, context_texts)
    fallback_notes = f"Heuristic overlap with retrieved context suggests score {fallback_score}"
    return _judge_or_fallback("faithfulness", prompt, fallback_score, fallback_notes)


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

    TODO Sprint 4: Implement tương tự score_faithfulness
    """
    prompt = f"""Rate whether the answer addresses the user's question.
Return JSON with keys: score (integer 1-5) and notes (short explanation).

Rubric:
5 = directly answers the question clearly and completely
4 = answers the question correctly but misses a minor detail
3 = related but incomplete or partially on topic
2 = partially off topic
1 = does not answer the question

Question:
{query}

Answer:
{answer}
"""

    if not answer:
        return {
            "score": 1,
            "notes": "Empty answer",
        }

    if _is_abstain_answer(answer):
        fallback_score = 5 if any(marker in _normalize_text(query) for marker in ["err", "khong co", "không có"]) else 3
        return {
            "score": fallback_score,
            "notes": "Answer abstains; relevance depends on whether the query is out of scope",
        }

    fallback_score = _score_from_similarity(answer, [query])
    fallback_notes = f"Heuristic overlap with query suggests score {fallback_score}"
    return _judge_or_fallback("answer_relevance", prompt, fallback_score, fallback_notes)


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

    found = 0
    missing = []
    for expected in expected_sources:
        expected_name = _source_basename(expected)
        matched = any(expected_name and expected_name in _source_basename(retrieved) for retrieved in retrieved_sources)
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
    Completeness: Answer có thiếu điều kiện ngoại lệ hoặc bước quan trọng không?
    Câu hỏi: Answer có bao phủ đủ thông tin so với expected_answer không?

    Thang điểm 1-5:
      5: Answer bao gồm đủ tất cả điểm quan trọng trong expected_answer
      4: Thiếu 1 chi tiết nhỏ
      3: Thiếu một số thông tin quan trọng
      2: Thiếu nhiều thông tin quan trọng
      1: Thiếu phần lớn nội dung cốt lõi

    TODO Sprint 4:
    Option 1 — Chấm thủ công: So sánh answer vs expected_answer và chấm.
    Option 2 — LLM-as-Judge:
        "Compare the model answer with the expected answer.
         Rate completeness 1-5. Are all key points covered?
         Output: {'score': int, 'missing_points': [str]}"
    """
    prompt = f"""Compare the answer with the expected answer and rate completeness.
Return JSON with keys: score (integer 1-5) and notes (short explanation).

Rubric:
5 = answer covers all key points in the expected answer
4 = misses one small detail
3 = misses some important information
2 = misses much important information
1 = misses most of the core content

Question:
{query}

Expected answer:
{expected_answer}

Model answer:
{answer}
"""

    if not expected_answer:
        return {
            "score": None,
            "notes": "No expected answer available",
        }

    if not answer:
        return {
            "score": 1,
            "notes": "Empty answer",
        }

    if _is_abstain_answer(answer):
        fallback_score = 5 if not expected_answer else 2
        return {
            "score": fallback_score,
            "notes": "Answer abstains; completeness depends on whether abstention matches the expected answer",
        }

    fallback_score = _score_from_similarity(answer, [expected_answer])
    fallback_notes = f"Heuristic overlap with expected answer suggests score {fallback_score}"
    return _judge_or_fallback("completeness", prompt, fallback_score, fallback_notes)


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
    test_questions = test_questions or []

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
        md += (f"| {r['id']} | {r['category']} | {r.get('faithfulness', 'N/A')} | "
               f"{r.get('relevance', 'N/A')} | {r.get('context_recall', 'N/A')} | "
               f"{r.get('completeness', 'N/A')} | {r.get('faithfulness_notes', '')[:50]} |\n")

    return md


def generate_grading_run_log(
    output_filename: str = "grading_run.json",
    questions_path: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Tạo file logs/grading_run.json theo format yêu cầu trong SCORING.md.

    Quy tắc chọn input questions:
      1) Nếu questions_path được truyền vào -> dùng file đó.
      2) Nếu có data/grading_questions.json -> dùng file này.
      3) Fallback về data/test_questions.json.
    """
    cfg = config or BASELINE_CONFIG

    if questions_path is not None:
        selected_questions_path = questions_path
    elif GRADING_QUESTIONS_PATH.exists():
        selected_questions_path = GRADING_QUESTIONS_PATH
    else:
        selected_questions_path = TEST_QUESTIONS_PATH

    with open(selected_questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    log_rows = []
    for q in questions:
        qid = q.get("id", "unknown")
        query = q.get("question", "")

        try:
            result = rag_answer(
                query=query,
                retrieval_mode=cfg.get("retrieval_mode", "dense"),
                top_k_search=cfg.get("top_k_search", 10),
                top_k_select=cfg.get("top_k_select", 3),
                use_rerank=cfg.get("use_rerank", False),
                verbose=False,
            )
            answer = result.get("answer", "")
            sources = result.get("sources", [])
            chunks_retrieved = len(result.get("chunks_used", []))
            retrieval_mode = result.get("config", {}).get("retrieval_mode", cfg.get("retrieval_mode", "dense"))
        except Exception as e:
            answer = f"ERROR: {e}"
            sources = []
            chunks_retrieved = 0
            retrieval_mode = cfg.get("retrieval_mode", "dense")

        log_rows.append(
            {
                "id": qid,
                "question": query,
                "answer": answer,
                "sources": sources,
                "chunks_retrieved": chunks_retrieved,
                "retrieval_mode": retrieval_mode,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = LOGS_DIR / output_filename
    output_path.write_text(json.dumps(log_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nGrading log lưu tại: {output_path}")
    print(f"Số dòng log: {len(log_rows)}")
    print(f"Nguồn câu hỏi: {selected_questions_path}")
    return output_path


# =============================================================================
# MAIN — Chạy evaluation
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 4: Evaluation & Scorecard")
    print("=" * 60)

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
    print("Lưu ý: Cần hoàn thành Sprint 2 trước khi chạy scorecard!")
    try:
        baseline_results = run_scorecard(
            config=BASELINE_CONFIG,
            test_questions=test_questions,
            verbose=True,
        )

        # Save scorecard
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        baseline_md = generate_scorecard_summary(baseline_results, "baseline_dense")
        scorecard_path = RESULTS_DIR / "scorecard_baseline.md"
        scorecard_path.write_text(baseline_md, encoding="utf-8")
        print(f"\nScorecard lưu tại: {scorecard_path}")

    except NotImplementedError:
        print("Pipeline chưa implement. Hoàn thành Sprint 2 trước.")
        baseline_results = []

    # --- Chạy Variant (sau khi Sprint 3 hoàn thành) ---
    # TODO Sprint 4: Uncomment sau khi implement variant trong rag_answer.py
    print("\n--- Chạy Variant ---")
    variant_results = run_scorecard(
        config=VARIANT_CONFIG,
        test_questions=test_questions,
        verbose=True,
    )
    variant_md = generate_scorecard_summary(variant_results, VARIANT_CONFIG["label"])
    (RESULTS_DIR / "scorecard_variant.md").write_text(variant_md, encoding="utf-8")

    # --- A/B Comparison ---
    # TODO Sprint 4: Uncomment sau khi có cả baseline và variant
    if baseline_results and variant_results:
        compare_ab(
            baseline_results,
            variant_results,
            output_csv="ab_comparison.csv"
        )

    # --- Grading run log ---
    print("\n--- Tạo grading log ---")
    generate_grading_run_log(config=BASELINE_CONFIG)

    print("\n\nViệc cần làm Sprint 4:")
    print("  1. Hoàn thành Sprint 2 + 3 trước")
    print("  2. Chấm điểm thủ công hoặc implement LLM-as-Judge trong score_* functions")
    print("  3. Chạy run_scorecard(BASELINE_CONFIG)")
    print("  4. Chạy run_scorecard(VARIANT_CONFIG)")
    print("  5. Gọi compare_ab() để thấy delta")
    print("  6. Cập nhật docs/tuning-log.md với kết quả và nhận xét")