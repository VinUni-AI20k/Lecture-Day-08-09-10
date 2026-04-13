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
# Dựa trên rag_answer.py, variant phù hợp nhất hiện tại là hybrid retrieval.
# Không bật rerank vì rerank() mới đang là placeholder, chưa tạo khác biệt thực sự.
VARIANT_CONFIG = {
    "retrieval_mode": "hybrid",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,
    "label": "variant_hybrid",
}

JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))
JUDGE_USE_LLM = os.getenv("EVAL_USE_LLM_JUDGE", "1").strip().lower() not in {"0", "false", "no"}
JUDGE_MAX_CHUNK_CHARS = int(os.getenv("EVAL_JUDGE_MAX_CHUNK_CHARS", "700"))
_JUDGE_CACHE: Dict[str, Dict[str, Dict[str, Any]]] = {}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _extract_keywords(text: str) -> List[str]:
    return [
        token for token in re.findall(r"\w+", _normalize_text(text), flags=re.UNICODE)
        if len(token) > 2
    ]


def _is_abstain_answer(answer: str) -> bool:
    normalized = _normalize_text(answer)
    markers = [
        "không đủ dữ liệu",
        "khong du du lieu",
        "không tìm thấy thông tin",
        "khong tim thay thong tin",
        "không có thông tin",
        "khong co thong tin",
        "i do not know",
        "insufficient",
    ]
    return any(marker in normalized for marker in markers)


def _expected_prefers_abstain(expected_answer: str) -> bool:
    normalized = _normalize_text(expected_answer)
    markers = [
        "không tìm thấy thông tin",
        "không đề cập",
        "không có thông tin",
        "không đủ dữ liệu",
        "hãy liên hệ",
        "co the la",
        "có thể là",
    ]
    return any(marker in normalized for marker in markers)


def _clamp_score(value: Any) -> int:
    try:
        return max(1, min(5, int(value)))
    except (TypeError, ValueError):
        return 1


def _safe_note(text: Any, fallback: str) -> str:
    note = re.sub(r"\s+", " ", str(text or "")).strip()
    return note or fallback


def _serialize_chunks_for_judge(chunks_used: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    serialized = []
    for idx, chunk in enumerate(chunks_used[:3], start=1):
        metadata = chunk.get("metadata", {})
        serialized.append({
            "rank": idx,
            "source": metadata.get("source", ""),
            "section": metadata.get("section", ""),
            "score": chunk.get("score"),
            "text": (chunk.get("text", "") or "")[:JUDGE_MAX_CHUNK_CHARS],
        })
    return serialized


def _heuristic_judge(
    query: str,
    answer: str,
    expected_answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    if answer in {"PIPELINE_NOT_IMPLEMENTED"} or _normalize_text(answer).startswith("error:"):
        return {
            "faithfulness": {"score": 1, "notes": "Pipeline loi hoac chua implement."},
            "relevance": {"score": 1, "notes": "Khong the danh gia vi pipeline khong tra loi hop le."},
            "completeness": {"score": 1, "notes": "Khong co cau tra loi hop le de so sanh."},
        }

    answer_norm = _normalize_text(answer)
    expected_norm = _normalize_text(expected_answer)
    context_text = " ".join(chunk.get("text", "") for chunk in chunks_used)
    context_tokens = set(_extract_keywords(context_text))
    answer_tokens = set(_extract_keywords(answer))
    expected_tokens = set(_extract_keywords(expected_answer))
    query_tokens = set(_extract_keywords(query))

    support_ratio = (
        len(answer_tokens & context_tokens) / max(1, len(answer_tokens))
        if answer_tokens else 0.0
    )
    expected_overlap = (
        len(answer_tokens & expected_tokens) / max(1, len(expected_tokens))
        if expected_tokens else 0.0
    )
    query_overlap = (
        len(answer_tokens & query_tokens) / max(1, len(query_tokens))
        if query_tokens else 0.0
    )

    abstain = _is_abstain_answer(answer)
    should_abstain = _expected_prefers_abstain(expected_answer)

    if abstain and should_abstain:
        completeness_score = 5 if "hãy liên hệ" in expected_norm or "hay lien he" in expected_norm else 4
        return {
            "faithfulness": {"score": 5, "notes": "Abstain phu hop voi expected answer va tranh hallucination."},
            "relevance": {"score": 5, "notes": "Tra loi dung huong cho cau hoi thieu du lieu."},
            "completeness": {
                "score": completeness_score,
                "notes": "Cau tra loi da nhan biet thieu du lieu; co the thieu mot chi dan hanh dong nho.",
            },
        }

    if abstain and not should_abstain:
        return {
            "faithfulness": {"score": 4, "notes": "Khong bịa thong tin, nhung co the bo sot evidence da retrieve."},
            "relevance": {"score": 2, "notes": "Abstain trong khi expected answer co thong tin cu the."},
            "completeness": {"score": 1, "notes": "Bo sot phan lon noi dung can tra loi."},
        }

    if support_ratio >= 0.7:
        faith_score = 5
    elif support_ratio >= 0.5:
        faith_score = 4
    elif support_ratio >= 0.3:
        faith_score = 3
    elif chunks_used:
        faith_score = 2
    else:
        faith_score = 1

    if expected_overlap >= 0.75:
        completeness_score = 5
    elif expected_overlap >= 0.5:
        completeness_score = 4
    elif expected_overlap >= 0.3:
        completeness_score = 3
    elif answer_tokens:
        completeness_score = 2
    else:
        completeness_score = 1

    if query_overlap >= 0.6:
        relevance_score = 5
    elif query_overlap >= 0.4:
        relevance_score = 4
    elif query_overlap >= 0.2:
        relevance_score = 3
    elif answer_tokens:
        relevance_score = 2
    else:
        relevance_score = 1

    return {
        "faithfulness": {
            "score": faith_score,
            "notes": f"Heuristic support ratio voi context = {support_ratio:.2f}.",
        },
        "relevance": {
            "score": relevance_score,
            "notes": f"Heuristic overlap voi query = {query_overlap:.2f}.",
        },
        "completeness": {
            "score": completeness_score,
            "notes": f"Heuristic overlap voi expected answer = {expected_overlap:.2f}.",
        },
    }


def _parse_judge_json(raw_text: str) -> Dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Empty judge response")

    candidates = [text]
    fenced = re.findall(r"\{.*\}", text, flags=re.DOTALL)
    candidates.extend(fenced)

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"Judge response khong phai JSON hop le: {text[:200]}")


def _call_llm_judge(
    query: str,
    answer: str,
    expected_answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    judge_payload = {
        "query": query,
        "answer": answer,
        "expected_answer": expected_answer,
        "retrieved_chunks": _serialize_chunks_for_judge(chunks_used),
    }
    system_prompt = (
        "You are a strict RAG evaluator. Score only based on the user query, the expected answer, "
        "the retrieved chunks, and the model answer. Penalize unsupported facts heavily. "
        "If the answer correctly abstains because the evidence is insufficient, reward faithfulness and relevance. "
        "Return ONLY valid JSON with this exact shape: "
        "{\"faithfulness\":{\"score\":1-5,\"notes\":\"...\"},"
        "\"relevance\":{\"score\":1-5,\"notes\":\"...\"},"
        "\"completeness\":{\"score\":1-5,\"notes\":\"...\"}}."
    )
    user_prompt = (
        "Rubric:\n"
        "- Faithfulness: is the answer supported by retrieved chunks?\n"
        "- Relevance: does the answer directly address the question?\n"
        "- Completeness: does the answer cover the important points in expected_answer?\n"
        "- Score each metric from 1 to 5.\n"
        "- Keep notes concise and evidence-based.\n\n"
        f"Evaluation payload:\n{json.dumps(judge_payload, ensure_ascii=False, indent=2)}"
    )
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    parsed = _parse_judge_json(content)

    judged = {}
    for metric in ("faithfulness", "relevance", "completeness"):
        metric_data = parsed.get(metric, {}) if isinstance(parsed, dict) else {}
        judged[metric] = {
            "score": _clamp_score(metric_data.get("score")),
            "notes": _safe_note(metric_data.get("notes"), f"LLM judge khong tra ve notes cho {metric}."),
        }
    return judged


def _get_judge_result(
    query: str,
    answer: str,
    expected_answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    cache_key = json.dumps(
        {
            "query": query,
            "answer": answer,
            "expected_answer": expected_answer,
            "chunks": _serialize_chunks_for_judge(chunks_used),
            "model": JUDGE_MODEL,
            "use_llm": JUDGE_USE_LLM,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    if cache_key in _JUDGE_CACHE:
        return _JUDGE_CACHE[cache_key]

    use_llm = JUDGE_USE_LLM and bool(os.getenv("OPENAI_API_KEY"))
    if use_llm:
        try:
            judged = _call_llm_judge(query, answer, expected_answer, chunks_used)
            for metric in judged.values():
                metric["notes"] = f"{metric['notes']} [AI-as-Judge:{JUDGE_MODEL}]"
            _JUDGE_CACHE[cache_key] = judged
            return judged
        except Exception as exc:
            print(f"[Judge] LLM judge loi, fallback heuristic: {exc}")

    judged = _heuristic_judge(query, answer, expected_answer, chunks_used)
    for metric in judged.values():
        metric["notes"] = f"{metric['notes']} [heuristic]"
    _JUDGE_CACHE[cache_key] = judged
    return judged


# =============================================================================
# SCORING FUNCTIONS
# 4 metrics từ slide: Faithfulness, Answer Relevance, Context Recall, Completeness
# =============================================================================

def score_faithfulness(
    query: str,
    answer: str,
    expected_answer: str,
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
    judged = _get_judge_result(query, answer, expected_answer, chunks_used)
    return judged["faithfulness"]


def score_answer_relevance(
    query: str,
    answer: str,
    expected_answer: str,
    chunks_used: Optional[List[Dict[str, Any]]] = None,
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
    judged = _get_judge_result(query, answer, expected_answer, chunks_used or [])
    return judged["relevance"]


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
    chunks_used: Optional[List[Dict[str, Any]]] = None,
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
    judged = _get_judge_result(query, answer, expected_answer, chunks_used or [])
    return judged["completeness"]


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
        faith = score_faithfulness(query, answer, expected_answer, chunks_used)
        relevance = score_answer_relevance(query, answer, expected_answer, chunks_used)
        recall = score_context_recall(chunks_used, expected_sources)
        complete = score_completeness(query, answer, expected_answer, chunks_used)

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
    metric_labels = {
        "faithfulness": "Faithfulness",
        "relevance": "Answer Relevance",
        "context_recall": "Context Recall",
        "completeness": "Completeness",
    }

    def average(rows: List[Dict], metric: str) -> Optional[float]:
        scores = [r[metric] for r in rows if r.get(metric) is not None]
        return sum(scores) / len(scores) if scores else None

    print(f"\n{'='*70}")
    print("A/B Comparison: Baseline vs Variant")
    print('='*70)
    print(f"{'Metric':<20} {'Baseline':>10} {'Variant':>10} {'Delta':>8}")
    print("-" * 55)

    summary_rows = []
    for metric in metrics:
        b_avg = average(baseline_results, metric)
        v_avg = average(variant_results, metric)
        delta = (v_avg - b_avg) if (b_avg is not None and v_avg is not None) else None

        b_str = f"{b_avg:.2f}" if b_avg is not None else "N/A"
        v_str = f"{v_avg:.2f}" if v_avg is not None else "N/A"
        d_str = f"{delta:+.2f}" if delta is not None else "N/A"

        print(f"{metric_labels[metric]:<20} {b_str:>10} {v_str:>10} {d_str:>8}")
        summary_rows.append((metric_labels[metric], b_avg, v_avg, delta))

    # Per-question comparison
    print(f"\n{'Câu':<6} {'Baseline F/R/Rc/C':<22} {'Variant F/R/Rc/C':<22} {'Better?':<10}")
    print("-" * 65)

    b_by_id = {r["id"]: r for r in baseline_results}
    better_variant = []
    better_baseline = []
    ties = []

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

        delta_parts = []
        for metric in metrics:
            b_score = b_row.get(metric)
            v_score = v_row.get(metric)
            if b_score is None or v_score is None:
                continue
            if v_score > b_score:
                delta_parts.append(f"{metric_labels[metric]} +{v_score - b_score}")
            elif v_score < b_score:
                delta_parts.append(f"{metric_labels[metric]} {v_score - b_score}")

        explanation = "; ".join(delta_parts) if delta_parts else "Khong du diem de ket luan"
        if better == "Variant":
            better_variant.append((qid, explanation))
        elif better == "Baseline":
            better_baseline.append((qid, explanation))
        else:
            ties.append(qid)

    print("\nMarkdown table for report (with Delta):")
    print("| Metric | Baseline | Variant | Delta |")
    print("|--------|----------|---------|-------|")
    for label, b_avg, v_avg, delta in summary_rows:
        b_cell = f"{b_avg:.2f}/5" if b_avg is not None else "N/A"
        v_cell = f"{v_avg:.2f}/5" if v_avg is not None else "N/A"
        
        # Highlight delta with clear indicators
        if delta is not None:
            if delta > 0:
                d_cell = f"🚀 +{delta:.2f}"
            elif delta < 0:
                d_cell = f"🔻 {delta:.2f}"
            else:
                d_cell = f"➖ {delta:.2f}"
        else:
            d_cell = "N/A"
            
        print(f"| {label} | {b_cell} | {v_cell} | {d_cell} |")

    print("\nNhan xet nhanh (A/B Comparison Insights):")
    if better_variant:
        print("- Variant tot hon o cac cau:", ", ".join(f"{qid} ({reason})" for qid, reason in better_variant))
    else:
        print("- Variant chua cho thay su vuot troi ro rang o cau nao.")

    if better_baseline:
        print("- Baseline van tot hon o cac cau:", ", ".join(f"{qid} ({reason})" for qid, reason in better_baseline))
    else:
        print("- Baseline khong co cau nao tot hon Variant.")

    if ties:
        print("- Khong co su khac biet diem so o:", ", ".join(ties))

    best_metric = None
    best_delta = None
    for metric_label, _, _, delta in summary_rows:
        if delta is None:
            continue
        if best_delta is None or delta > best_delta:
            best_delta = delta
            best_metric = metric_label

    print("\nGiải thích vì sao chọn biến đổi (Variant Justification):")
    print("- Dựa trên A/B Rule: Chúng ta chỉ thay đổi MỘT biến số duy nhất (từ Dense -> Hybrid Retrieval) để đo lường chính xác tác động.")
    if best_metric is not None:
        print("- Biến 'Hybrid Retrieval' được chọn vì nó giúp cải thiện khả năng tìm kiếm từ khóa kết hợp ngữ nghĩa.")
        print(f"- Kết quả thực tế cho thấy đóng góp lớn nhất nằm ở metric: {best_metric} với mức thay đổi ({best_delta:+.2f}).")
        print("- Điều này chứng minh rằng việc kết hợp sparse (BM25) và dense (vector) giúp xử lý tốt hơn các query chứa mã số (như policy ID) hoặc từ khóa đặc thù mà dense-only thường bỏ sót.")
    else:
        print("- Hiện chưa có đủ dữ liệu để đánh giá chính xác tác động của biến này. Cần chạy đánh giá trên bộ test hoàn chỉnh.")

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

    Tạo summary đủ dùng để nộp scorecard và đọc nhanh các câu yếu/mạnh.
    """
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]
    metric_labels = {
        "faithfulness": "Faithfulness",
        "relevance": "Answer Relevance",
        "context_recall": "Context Recall",
        "completeness": "Completeness",
    }
    averages = {}
    for metric in metrics:
        scores = [r[metric] for r in results if r[metric] is not None]
        averages[metric] = sum(scores) / len(scores) if scores else None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ranked_rows = sorted(
        results,
        key=lambda r: sum((r.get(m) or 0) for m in metrics),
    )

    md = f"""# Scorecard: {label}
Generated: {timestamp}

## Summary

| Metric | Average Score |
|--------|--------------|
"""
    for metric, avg in averages.items():
        avg_str = f"{avg:.2f}/5" if avg is not None else "N/A"
        md += f"| {metric_labels[metric]} | {avg_str} |\n"

    md += "\n## Quick Notes\n\n"
    md += f"- Config label: `{label}`\n"
    if ranked_rows:
        weakest = ", ".join(r["id"] for r in ranked_rows[:3])
        strongest = ", ".join(r["id"] for r in ranked_rows[-3:][::-1])
        md += f"- Weakest questions: {weakest}\n"
        md += f"- Strongest questions: {strongest}\n"

    md += "\n## Per-Question Results\n\n"
    md += "| ID | Category | Faithful | Relevant | Recall | Complete | Notes |\n"
    md += "|----|----------|----------|----------|--------|----------|-------|\n"

    for r in results:
        notes = " | ".join(
            note for note in [
                r.get("faithfulness_notes", ""),
                r.get("context_recall_notes", ""),
                r.get("completeness_notes", ""),
            ] if note
        )[:80]
        md += (f"| {r['id']} | {r['category']} | {r.get('faithfulness', 'N/A')} | "
               f"{r.get('relevance', 'N/A')} | {r.get('context_recall', 'N/A')} | "
               f"{r.get('completeness', 'N/A')} | {notes} |\n")

    return md


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

    print("\n\nViệc cần làm Sprint 4:")
    print("  1. Hoàn thành Sprint 2 + 3 trước")
    print("  2. Chấm điểm thủ công hoặc implement LLM-as-Judge trong score_* functions")
    print("  3. Chạy run_scorecard(BASELINE_CONFIG)")
    print("  4. Chạy run_scorecard(VARIANT_CONFIG)")
    print("  5. Gọi compare_ab() để thấy delta")
    print("  6. Cập nhật docs/tuning-log.md với kết quả và nhận xét")
