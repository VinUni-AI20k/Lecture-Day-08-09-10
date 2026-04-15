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
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from rag_answer import rag_answer

load_dotenv()

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
    "use_rerank": False,           # Hoặc False nếu variant là hybrid không rerank
    "label": "variant_hybrid_rerank",
}

DEFAULT_SCORING_MODE = os.getenv("EVAL_SCORING_MODE", "llm").lower()

def _call_judge_llm(prompt: str) -> Optional[str]:
    """
    Gọi LLM để chấm điểm (judge). Hỗ trợ OpenAI và Gemini.
    Trả về text response hoặc None nếu không gọi được.

    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    try:
        if provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=300,
            )
            return response.choices[0].message.content

        elif provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
            response = model.generate_content(prompt)
            return response.text

        else:
            print(f"[Judge] Provider '{provider}' not supported. Set LLM_PROVIDER=openai or gemini.")
            return None

    except Exception as e:
        print(f"[Judge] LLM call failed: {e}")
        return None


def _parse_judge_response(response_text: Optional[str]) -> Dict[str, Any]:
    """
    Parse JSON response từ LLM judge.
    Xử lý các trường hợp: JSON thuần, JSON trong markdown code block, hoặc lỗi.
    """
    if not response_text:
        return {"score": None, "notes": "LLM judge not available"}

    # Thử parse trực tiếp
    try:
        result = json.loads(response_text)
        score = int(result.get("score", 0))
        score = max(1, min(5, score))  # Clamp 1-5
        notes = result.get("reason", result.get("notes", result.get("missing_points", "")))
        if isinstance(notes, list):
            notes = "; ".join(notes)
        return {"score": score, "notes": str(notes)}
    except (json.JSONDecodeError, ValueError):
        pass

    # Thử extract JSON từ markdown code block
    json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            score = int(result.get("score", 0))
            score = max(1, min(5, score))
            notes = result.get("reason", result.get("notes", ""))
            if isinstance(notes, list):
                notes = "; ".join(notes)
            return {"score": score, "notes": str(notes)}
        except (json.JSONDecodeError, ValueError):
            pass

    # Thử extract JSON từ bất kỳ đâu trong response
    json_match = re.search(r'({[^{}]*"score"[^{}]*})', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            score = int(result.get("score", 0))
            score = max(1, min(5, score))
            notes = result.get("reason", result.get("notes", ""))
            if isinstance(notes, list):
                notes = "; ".join(notes)
            return {"score": score, "notes": str(notes)}
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: thử tìm số điểm trong text
    score_match = re.search(r'(\d)[/\s]*5', response_text)
    if score_match:
        return {"score": int(score_match.group(1)), "notes": response_text[:100]}

    return {"score": None, "notes": f"Could not parse: {response_text[:100]}"}


# =============================================================================
# LLM-AS-JUDGE SCORING
# =============================================================================

def score_faithfulness_llm(
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

    Implemented by: nghlong3004 (Eval Owner) — LLM-as-Judge
    """
    # Edge case: pipeline chưa chạy hoặc không có answer
    if not answer or answer.startswith("PIPELINE_"):
        return {"score": None, "notes": "No answer to evaluate"}

    # Ghép context từ chunks
    context_text = "\n\n".join([
        f"[Chunk {i+1}] {c.get('metadata', {}).get('source', '?')}: {c.get('text', '')[:300]}"
        for i, c in enumerate(chunks_used[:5])  # Max 5 chunks để tiết kiệm token
    ])

    if not context_text.strip():
        return {"score": 1, "notes": "No context chunks — answer is ungrounded"}

    prompt = f"""You are a strict evaluator. Rate the FAITHFULNESS of the answer.
Faithfulness = Is every claim in the answer supported by the retrieved context?

Scoring:
  5 = Every fact in the answer is directly found in the context.
  4 = Almost fully grounded, 1 minor detail uncertain.
  3 = Mostly grounded, some info may come from model knowledge.
  2 = Many claims not supported by context.
  1 = Answer is mostly fabricated / not grounded.

Retrieved Context:
{context_text}

Answer to evaluate:
{answer}

Output ONLY a JSON object: {{"score": <int 1-5>, "reason": "<brief explanation>"}}"""

    response = _call_judge_llm(prompt)
    return _parse_judge_response(response)


def score_answer_relevance_llm(
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

    Implemented by: nghlong3004 (Eval Owner) — LLM-as-Judge
    """
    if not answer or answer.startswith("PIPELINE_"):
        return {"score": None, "notes": "No answer to evaluate"}

    prompt = f"""You are a strict evaluator. Rate the ANSWER RELEVANCE.
Answer Relevance = Does the answer directly address the user's question?

Scoring:
  5 = Answer directly and fully addresses the question.
  4 = Addresses the question but misses minor details.
  3 = Related but doesn't hit the core point.
  2 = Partially off-topic.
  1 = Does not answer the question at all.

Note: If the question asks about something NOT in the documents, and the answer correctly says
"I don't have enough information" or similar abstain response, give score 5 (correct behavior).

Question:
{query}

Answer:
{answer}

Output ONLY a JSON object: {{"score": <int 1-5>, "reason": "<brief explanation>"}}"""

    response = _call_judge_llm(prompt)
    return _parse_judge_response(response)


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


def score_completeness_llm(
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

    Implemented by: nghlong3004 (Eval Owner) — LLM-as-Judge
    """
    if not answer or answer.startswith("PIPELINE_"):
        return {"score": None, "notes": "No answer to evaluate"}

    if not expected_answer:
        return {"score": None, "notes": "No expected answer to compare"}

    prompt = f"""You are a strict evaluator. Rate the COMPLETENESS of the model answer
by comparing it against the expected answer.

Completeness = Does the model answer cover all key points from the expected answer?

Scoring:
  5 = All key points from expected answer are covered.
  4 = Missing 1 minor detail.
  3 = Missing some important information.
  2 = Missing many important points.
  1 = Missing most of the core content.

Question:
{query}

Expected Answer (ground truth):
{expected_answer}

Model Answer (to evaluate):
{answer}

Output ONLY a JSON object: {{"score": <int 1-5>, "reason": "<brief explanation>", "missing_points": ["<point1>", ...]}}"""

    response = _call_judge_llm(prompt)
    result = _parse_judge_response(response)

    # Extract missing_points nếu có
    if response:
        try:
            parsed = json.loads(response)
            if "missing_points" in parsed:
                missing = parsed["missing_points"]
                if isinstance(missing, list) and missing:
                    result["notes"] += f" | Missing: {'; '.join(missing)}"
        except (json.JSONDecodeError, ValueError):
            pass

    return result


# =============================================================================
# RULE-BASED SCORING
# Section rieng de de track code heuristic / non-LLM
# =============================================================================

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "cho", "co", "cua",
    "da", "de", "den", "duoc", "from", "hay", "if", "in", "is", "khi", "khong",
    "la", "neu", "nhung", "of", "or", "tai", "that", "the", "thi", "this", "to",
    "trong", "tu", "va", "voi",
}


def _normalize_text(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_alnum(text: str) -> str:
    text = _normalize_text(text)
    return re.sub(r"[^0-9a-zA-Z\s]", " ", text)


def _tokenize(text: str) -> List[str]:
    clean = _normalize_alnum(text)
    return [t for t in clean.split() if t and t not in STOPWORDS]


def _extract_numbers(text: str) -> List[str]:
    return re.findall(r"\d+(?:[.,]\d+)?", text or "")


def _extract_citations(answer: str) -> List[int]:
    return [int(x) for x in re.findall(r"\[(\d+)\]", answer or "")]


def _chunks_to_text(chunks_used: List[Dict[str, Any]]) -> str:
    return "\n".join(chunk.get("text", "") for chunk in chunks_used)


def _coverage_ratio(reference: str, candidate: str):
    ref_tokens = set(_tokenize(reference))
    cand_tokens = set(_tokenize(candidate))
    if not ref_tokens:
        return 0.0, [], []

    overlap = sorted(ref_tokens & cand_tokens)
    missing = sorted(ref_tokens - cand_tokens)
    ratio = len(overlap) / len(ref_tokens)
    return ratio, overlap, missing


def _score_from_ratio(ratio: float) -> int:
    if ratio >= 0.9:
        return 5
    if ratio >= 0.7:
        return 4
    if ratio >= 0.45:
        return 3
    if ratio >= 0.2:
        return 2
    return 1


def _is_abstain_answer(answer: str) -> bool:
    text = _normalize_text(answer)
    abstain_markers = [
        "khong du du lieu",
        "khong tim thay thong tin",
        "khong co thong tin",
        "toi khong biet",
        "i do not know",
        "insufficient",
        "not enough information",
    ]
    return any(marker in text for marker in abstain_markers)


def score_faithfulness_rule(
    answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Any]:
    answer_text = _normalize_text(answer)
    if not answer_text:
        return {"score": 1, "notes": "Empty answer"}

    if answer.startswith("ERROR:") or answer == "PIPELINE_NOT_IMPLEMENTED":
        return {"score": 1, "notes": "Pipeline error or not implemented"}

    if not chunks_used:
        if _is_abstain_answer(answer):
            return {"score": 5, "notes": "Abstained without context"}
        return {"score": 1, "notes": "No retrieved chunks but answer contains claims"}

    context_text = _chunks_to_text(chunks_used)
    ratio, overlap, missing = _coverage_ratio(answer, context_text)

    citation_ids = _extract_citations(answer)
    invalid_citations = [cid for cid in citation_ids if cid < 1 or cid > len(chunks_used)]

    score = _score_from_ratio(ratio)
    if citation_ids:
        score = min(5, score + 1)
    if invalid_citations:
        score = max(1, score - 1)

    notes = [f"rule ratio={ratio:.2f}"]
    if citation_ids:
        notes.append(f"citations={citation_ids}")
    if invalid_citations:
        notes.append(f"invalid citations={invalid_citations}")
    if missing:
        notes.append(f"missing from context: {', '.join(missing[:6])}")
    elif overlap:
        notes.append(f"covered terms: {', '.join(overlap[:6])}")

    return {"score": score, "notes": ". ".join(notes)}


def score_answer_relevance_rule(
    query: str,
    answer: str,
) -> Dict[str, Any]:
    answer_text = _normalize_text(answer)
    if not answer_text:
        return {"score": 1, "notes": "Empty answer"}

    if answer.startswith("ERROR:") or answer == "PIPELINE_NOT_IMPLEMENTED":
        return {"score": 1, "notes": "Pipeline error or not implemented"}

    ratio, overlap, missing = _coverage_ratio(query, answer)
    score = _score_from_ratio(ratio)

    if _is_abstain_answer(answer):
        score = max(score, 3)

    notes = [f"rule overlap={ratio:.2f}"]
    if overlap:
        notes.append(f"matched terms: {', '.join(overlap[:6])}")
    if missing:
        notes.append(f"unanswered terms: {', '.join(missing[:6])}")

    return {"score": score, "notes": ". ".join(notes)}


def score_completeness_rule(
    query: str,
    answer: str,
    expected_answer: str,
) -> Dict[str, Any]:
    if not answer.strip():
        return {"score": 1, "notes": "Empty answer"}

    if answer.startswith("ERROR:") or answer == "PIPELINE_NOT_IMPLEMENTED":
        return {"score": 1, "notes": "Pipeline error or not implemented"}

    if not expected_answer.strip():
        return {"score": 3, "notes": "No expected_answer provided"}

    ratio, overlap, missing = _coverage_ratio(expected_answer, answer)
    score = _score_from_ratio(ratio)

    expected_numbers = set(_extract_numbers(expected_answer))
    answer_numbers = set(_extract_numbers(answer))
    missing_numbers = sorted(expected_numbers - answer_numbers)

    if expected_numbers:
        if missing_numbers:
            score = max(1, score - 1)
        elif expected_numbers == answer_numbers:
            score = min(5, score + 1)

    if _is_abstain_answer(answer):
        query_tokens = set(_tokenize(query))
        expected_tokens = set(_tokenize(expected_answer))
        if query_tokens & expected_tokens:
            score = 1

    notes = [f"rule coverage={ratio:.2f}"]
    if overlap:
        notes.append(f"covered terms: {', '.join(overlap[:6])}")
    if missing:
        notes.append(f"missing terms: {', '.join(missing[:6])}")
    if missing_numbers:
        notes.append(f"missing numbers: {', '.join(missing_numbers)}")

    return {"score": score, "notes": ". ".join(notes)}


# =============================================================================
# SCORING DISPATCH
# =============================================================================

def score_faithfulness(
    answer: str,
    chunks_used: List[Dict[str, Any]],
    scoring_mode: str = DEFAULT_SCORING_MODE,
) -> Dict[str, Any]:
    if scoring_mode == "rule":
        return score_faithfulness_rule(answer, chunks_used)
    return score_faithfulness_llm(answer, chunks_used)


def score_answer_relevance(
    query: str,
    answer: str,
    scoring_mode: str = DEFAULT_SCORING_MODE,
) -> Dict[str, Any]:
    if scoring_mode == "rule":
        return score_answer_relevance_rule(query, answer)
    return score_answer_relevance_llm(query, answer)


def score_completeness(
    query: str,
    answer: str,
    expected_answer: str,
    scoring_mode: str = DEFAULT_SCORING_MODE,
) -> Dict[str, Any]:
    if scoring_mode == "rule":
        return score_completeness_rule(query, answer, expected_answer)
    return score_completeness_llm(query, answer, expected_answer)


# =============================================================================
# SCORECARD RUNNER
# =============================================================================

def run_scorecard(
    config: Dict[str, Any],
    test_questions: Optional[List[Dict]] = None,
    verbose: bool = True,
    scoring_mode: str = DEFAULT_SCORING_MODE,
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
    print(f"Scoring mode: {scoring_mode}")
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
        faith = score_faithfulness(answer, chunks_used, scoring_mode=scoring_mode)
        relevance = score_answer_relevance(query, answer, scoring_mode=scoring_mode)
        recall = score_context_recall(chunks_used, expected_sources)
        complete = score_completeness(
            query,
            answer,
            expected_answer,
            scoring_mode=scoring_mode,
        )

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
            "scoring_mode": scoring_mode,
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
    parser = argparse.ArgumentParser(description="Run evaluation scorecard")
    parser.add_argument(
        "--scoring-mode",
        choices=["llm", "rule"],
        default=DEFAULT_SCORING_MODE,
        help="Scoring backend to use",
    )
    args = parser.parse_args()

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
            scoring_mode=args.scoring_mode,
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
    print("\n--- Chạy Variant ---")
    variant_results = run_scorecard(
        config=VARIANT_CONFIG,
        test_questions=test_questions,
        verbose=True,
    )
    variant_md = generate_scorecard_summary(variant_results, VARIANT_CONFIG["label"])
    (RESULTS_DIR / "scorecard_variant.md").write_text(variant_md, encoding="utf-8")

    # --- A/B Comparison ---
    if baseline_results and variant_results:
        compare_ab(
            baseline_results,
            variant_results,
            output_csv="ab_comparison.csv"
        )

    print("\n\nViệc cần làm Sprint 4:")
    print("  1. Hoàn thành Sprint 2 + 3 trước")
    print("  2. Chấm điểm thủ công hoặc implement LLM-as-Judge trong score_* functions")
    print("  3. Chạy run_scorecard(BASELINE_CONFIG)")
    print("  4. Chạy run_scorecard(VARIANT_CONFIG)")
    print("  5. Gọi compare_ab() để thấy delta")
    print("  6. Cập nhật docs/tuning-log.md với kết quả và nhận xét")
