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
import re
import argparse
import time
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from rag_answer import (
    rag_answer,
    retrieve_candidates,
    build_context_block,
)


def _configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


_configure_utf8_stdio()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"
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

# Cấu hình variant (Sprint 3 — hybrid rẻ token nhất vì không thêm rerank/query transform)
# Hybrid weights sẽ được tune bằng benchmark ở dưới.
VARIANT_CONFIG = {
    "retrieval_mode": "hybrid",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,
    "dense_weight": 0.7,
    "sparse_weight": 0.3,
    "label": "variant_hybrid_rrf",
}

# Các cấu hình hybrid sẽ được benchmark nhanh để chọn weight tốt nhất
HYBRID_WEIGHT_GRID = [
    (0.8, 0.2),
    (0.7, 0.3),
    (0.6, 0.4),
    (0.5, 0.5),
    (0.4, 0.6),
]

ABSTAIN_PHRASES = [
    "không đủ dữ liệu",
    "không tìm thấy",
    "không có trong tài liệu",
    "i don't know",
    "i do not know",
    "not enough information",
    "no sufficient context",
]

STOPWORDS = {
    "và", "hoặc", "cho", "của", "là", "the", "a", "an", "to", "is",
    "in", "on", "at", "of", "for", "with", "that", "this", "theo",
    "bao", "nhiêu", "mấy", "có", "không", "là", "được", "bị", "vì",
    "một", "những", "các", "trong", "tại", "từ", "với", "when", "what",
    "how", "why", "where", "who", "which",
}


def _content_tokens(text: str) -> List[str]:
    tokens = re.findall(r"[\w-]+", (text or "").lower())
    return [t for t in tokens if len(t) > 2 and t not in STOPWORDS]


def _token_overlap_ratio(a: str, b: str) -> float:
    a_tokens = set(_content_tokens(a))
    b_tokens = set(_content_tokens(b))
    if not a_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens)


def _extract_numbers(text: str) -> List[str]:
    return re.findall(r"\d+(?:\.\d+)?", text or "")


def _has_abstain_phrase(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in ABSTAIN_PHRASES)


def _score_from_ratio(ratio: float) -> int:
    if ratio >= 0.85:
        return 5
    if ratio >= 0.7:
        return 4
    if ratio >= 0.55:
        return 3
    if ratio >= 0.4:
        return 2
    return 1


def estimate_prompt_tokens(chunks_used: List[Dict[str, Any]]) -> int:
    """Ước lượng số token prompt từ context block (rẻ, không gọi LLM)."""
    context = build_context_block(chunks_used)
    return max(1, len(context) // 4)


def _normalize_question_item(item: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Chuẩn hóa một câu hỏi để chấp nhận file cùng schema nhưng linh hoạt hơn."""
    if not isinstance(item, dict):
        raise ValueError(f"Question at index {index} is not an object")

    normalized = dict(item)
    question = str(normalized.get("question", "")).strip()
    if not question:
        raise ValueError(f"Question at index {index} is missing 'question'")

    question_id = normalized.get("id") or f"q{index:02d}"
    expected_sources = normalized.get("expected_sources", [])
    if expected_sources is None:
        expected_sources = []
    elif isinstance(expected_sources, str):
        expected_sources = [expected_sources]
    elif not isinstance(expected_sources, list):
        expected_sources = [str(expected_sources)]

    normalized.update({
        "id": str(question_id),
        "question": question,
        "expected_answer": str(normalized.get("expected_answer", "") or ""),
        "expected_sources": [str(source).strip() for source in expected_sources if str(source).strip()],
        "difficulty": str(normalized.get("difficulty", "") or ""),
        "category": str(normalized.get("category", "") or ""),
    })
    return normalized


def load_questions_from_path(questions_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Load và chuẩn hóa câu hỏi từ bất kỳ file JSON nào cùng format test_questions.json."""
    path = Path(questions_path)
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError(f"Question file must contain a JSON list: {path}")

    return [_normalize_question_item(item, index + 1) for index, item in enumerate(payload)]


def _load_test_questions(
    test_questions: Optional[List[Dict[str, Any]]] = None,
    questions_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    if test_questions is not None:
        return [_normalize_question_item(item, index + 1) for index, item in enumerate(test_questions)]
    return load_questions_from_path(questions_path or TEST_QUESTIONS_PATH)


def _retrieve_candidates_for_mode(
    query: str,
    retrieval_mode: str,
    top_k_search: int,
    top_k_select: int,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
    use_rerank: bool = False,
    use_query_transform: bool = False,
    query_transform_strategy: str = "expansion",
) -> Dict[str, Any]:
    """Lấy candidates mà không chạy LLM để benchmark retrieval rẻ token."""
    return retrieve_candidates(
        query=query,
        retrieval_mode=retrieval_mode,
        top_k_search=top_k_search,
        top_k_select=top_k_select,
        use_rerank=use_rerank,
        use_query_transform=use_query_transform,
        query_transform_strategy=query_transform_strategy,
        dense_weight=dense_weight,
        sparse_weight=sparse_weight,
    )


def _source_matches_expected(source: str, expected_sources: List[str]) -> bool:
    source_lower = (source or "").lower()
    for expected in expected_sources:
        expected_name = expected.split("/")[-1].replace(".pdf", "").replace(".md", "").lower()
        if expected_name and expected_name in source_lower:
            return True
    return False


def _ranking_metrics(
    chunks_used: List[Dict[str, Any]],
    expected_sources: List[str],
) -> Dict[str, Optional[float]]:
    if not expected_sources:
        return {"top1_hit": None, "mrr": None}

    top1_hit = 0.0
    reciprocal_rank = 0.0

    if chunks_used:
        first_source = chunks_used[0].get("metadata", {}).get("source", "")
        top1_hit = 1.0 if _source_matches_expected(first_source, expected_sources) else 0.0

    for rank, chunk in enumerate(chunks_used, 1):
        source = chunk.get("metadata", {}).get("source", "")
        if _source_matches_expected(source, expected_sources):
            reciprocal_rank = 1.0 / rank
            break

    return {"top1_hit": top1_hit, "mrr": reciprocal_rank}


def evaluate_retrieval_mode(
    test_questions: List[Dict[str, Any]],
    retrieval_mode: str,
    top_k_search: int = 10,
    top_k_select: int = 3,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
    use_rerank: bool = False,
    use_query_transform: bool = False,
    query_transform_strategy: str = "expansion",
) -> Dict[str, Any]:
    """Chấm retrieval-only scorecard để so sánh dense / sparse / hybrid."""
    questions = [_normalize_question_item(item, index + 1) for index, item in enumerate(test_questions or [])]
    rows: List[Dict[str, Any]] = []
    recall_scores: List[float] = []
    recall_points: List[float] = []
    top1_hits: List[float] = []
    mrr_scores: List[float] = []
    token_costs: List[int] = []
    query_variant_counts: List[int] = []
    hit_count = 0
    judged_count = 0

    for q in questions:
        query = q["question"]
        expected_sources = q.get("expected_sources", [])

        bundle = _retrieve_candidates_for_mode(
            query=query,
            retrieval_mode=retrieval_mode,
            top_k_search=top_k_search,
            top_k_select=top_k_select,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
            use_rerank=use_rerank,
            use_query_transform=use_query_transform,
            query_transform_strategy=query_transform_strategy,
        )
        selected = bundle["selected_candidates"]
        recall = score_context_recall(selected, expected_sources)
        est_tokens = estimate_prompt_tokens(selected)
        ranking = _ranking_metrics(selected, expected_sources)

        if expected_sources:
            judged_count += 1
            recall_scores.append(float(recall.get("recall") or 0.0))
            recall_points.append(float(recall.get("score") or 0.0))
            top1_hits.append(float(ranking["top1_hit"] or 0.0))
            mrr_scores.append(float(ranking["mrr"] or 0.0))
            if float(recall.get("recall") or 0.0) > 0:
                hit_count += 1

        token_costs.append(est_tokens)
        query_variant_counts.append(len(bundle.get("query_variants", [])))
        rows.append({
            "id": q["id"],
            "query": query,
            "expected_sources": expected_sources,
            "retrieved_sources": [c.get("metadata", {}).get("source", "") for c in selected],
            "recall": recall.get("recall"),
            "recall_score": recall.get("score"),
            "top1_hit": ranking["top1_hit"],
            "mrr": ranking["mrr"],
            "estimated_prompt_tokens": est_tokens,
            "query_variants": bundle.get("query_variants", []),
        })

    avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else None
    avg_score = sum(recall_points) / len(recall_points) if recall_points else None
    avg_top1_hit = sum(top1_hits) / len(top1_hits) if top1_hits else None
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else None
    avg_tokens = sum(token_costs) / len(token_costs) if token_costs else None
    avg_query_variants = sum(query_variant_counts) / len(query_variant_counts) if query_variant_counts else None
    hit_rate = hit_count / judged_count if judged_count else None

    return {
        "retrieval_mode": retrieval_mode,
        "dense_weight": dense_weight,
        "sparse_weight": sparse_weight,
        "use_rerank": use_rerank,
        "use_query_transform": use_query_transform,
        "query_transform_strategy": query_transform_strategy,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "avg_recall": avg_recall,
        "avg_recall_score": avg_score,
        "avg_top1_hit": avg_top1_hit,
        "avg_mrr": avg_mrr,
        "avg_prompt_tokens": avg_tokens,
        "avg_query_variants": avg_query_variants,
        "hit_rate": hit_rate,
        "judged_count": judged_count,
        "rows": rows,
    }


def find_best_hybrid_weights(
    test_questions: List[Dict[str, Any]],
    top_k_search: int = 10,
    top_k_select: int = 3,
) -> Dict[str, Any]:
    """Grid search rất nhỏ để chọn hybrid weight tốt nhất với token cost thấp nhất."""
    best_summary: Optional[Dict[str, Any]] = None
    best_key = None

    for dense_weight, sparse_weight in HYBRID_WEIGHT_GRID:
        summary = evaluate_retrieval_mode(
            test_questions=test_questions,
            retrieval_mode="hybrid",
            top_k_search=top_k_search,
            top_k_select=top_k_select,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
        )

        score_key = (
            summary["avg_recall"] or 0.0,
            -float(summary["avg_prompt_tokens"] or 0.0),
        )
        if best_key is None or score_key > best_key:
            best_key = score_key
            best_summary = summary

    return best_summary or {
        "retrieval_mode": "hybrid",
        "dense_weight": 0.6,
        "sparse_weight": 0.4,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "avg_recall": None,
        "avg_recall_score": None,
        "avg_prompt_tokens": None,
        "hit_rate": None,
        "judged_count": 0,
        "rows": [],
    }


def build_error_tree_mapping() -> List[Dict[str, str]]:
    """Bảng mapping lỗi RAG → stage → root cause → fix."""
    return [
        {
            "failure_mode": "Câu trả lời sai sự thật",
            "pipeline_stage": "Generation",
            "root_cause": "Prompt chưa đủ grounding hoặc model tự suy diễn ngoài context",
            "recommended_fix": "Tăng citation constraint, thêm abstain rule và giảm temperature",
        },
        {
            "failure_mode": "Hallucination (trả lời không có trong context)",
            "pipeline_stage": "Generation / Retrieval",
            "root_cause": "Context thiếu evidence, top_k quá thấp hoặc prompt cho phép bịa",
            "recommended_fix": "Dùng hybrid + rerank, tăng top_k_search, ép answer-only-from-context",
        },
        {
            "failure_mode": "Câu trả lời thiếu chi tiết quan trọng",
            "pipeline_stage": "Retrieval / Chunking",
            "root_cause": "Chunk quá ngắn/quá dài, missing evidence hoặc select top-k chưa đủ",
            "recommended_fix": "Semantic chunking, hybrid search, tăng select/rerank, kiểm tra overlap",
        },
        {
            "failure_mode": "Context truy xuất không liên quan",
            "pipeline_stage": "Retrieval",
            "root_cause": "Dense search bỏ lỡ keyword/alias, sparse không được fuse tốt",
            "recommended_fix": "Hybrid RRF, query transform, kiểm tra alias và weight dense/sparse",
        },
        {
            "failure_mode": "Phản hồi chậm (> 5 giây)",
            "pipeline_stage": "Retrieval / Rerank / Generation",
            "root_cause": "Reranker nặng, query transform quá nhiều variants, model load lặp lại",
            "recommended_fix": "Cache reranker, giới hạn số variants, ưu tiên hybrid không rerank cho baseline",
        },
    ]


def compare_retrieval_scorecards(
    test_questions: Optional[List[Dict[str, Any]]] = None,
    top_k_search: int = 10,
    top_k_select: int = 3,
    verbose: bool = True,
    output_log_path: Optional[str] = "retrieval_comparison.json",
    output_md_path: Optional[str] = "retrieval_comparison.md",
) -> Dict[str, Any]:
    """So sánh 4 strategies: baseline, hybrid, rerank, query transform."""
    questions = _load_test_questions(test_questions)

    best_hybrid = find_best_hybrid_weights(
        test_questions=questions,
        top_k_search=top_k_search,
        top_k_select=top_k_select,
    )

    strategy_suite = [
        {
            "label": "baseline_dense",
            "retrieval_mode": "dense",
            "use_rerank": False,
            "use_query_transform": False,
            "dense_weight": 0.6,
            "sparse_weight": 0.4,
        },
        {
            "label": "hybrid_rrf",
            "retrieval_mode": "hybrid",
            "use_rerank": False,
            "use_query_transform": False,
            "dense_weight": best_hybrid.get("dense_weight", 0.8),
            "sparse_weight": best_hybrid.get("sparse_weight", 0.2),
        },
        {
            "label": "rerank_dense",
            "retrieval_mode": "rerank",
            "use_rerank": True,
            "use_query_transform": False,
            "dense_weight": 0.6,
            "sparse_weight": 0.4,
        },
        {
            "label": "query_transform_dense",
            "retrieval_mode": "query_transform",
            "use_rerank": False,
            "use_query_transform": True,
            "query_transform_strategy": "expansion",
            "dense_weight": 0.6,
            "sparse_weight": 0.4,
        },
    ]

    summaries: Dict[str, Dict[str, Any]] = {}
    for strategy in strategy_suite:
        label = strategy.pop("label")
        summary = evaluate_retrieval_mode(
            test_questions=questions,
            retrieval_mode=strategy.get("retrieval_mode", "dense"),
            top_k_search=top_k_search,
            top_k_select=top_k_select,
            dense_weight=strategy.get("dense_weight", 0.6),
            sparse_weight=strategy.get("sparse_weight", 0.4),
            use_rerank=strategy.get("use_rerank", False),
            use_query_transform=strategy.get("use_query_transform", False),
            query_transform_strategy=strategy.get("query_transform_strategy", "expansion"),
        )
        summary["label"] = label
        summaries[label] = summary

    ranking = sorted(
        summaries.values(),
        key=lambda s: (
            s.get("avg_recall") or 0.0,
            s.get("avg_top1_hit") or 0.0,
            s.get("avg_mrr") or 0.0,
            -(s.get("avg_prompt_tokens") or 0.0),
        ),
        reverse=True,
    )
    best = ranking[0] if ranking else None

    if verbose:
        print(f"\n{'='*80}")
        print("Retrieval score comparison: baseline vs hybrid / rerank / query transform")
        print(f"{'='*80}")
        print(
            f"{'Strategy':<22} {'Config':<14} {'Recall@3':>8} {'Top1':>8} "
            f"{'MRR':>8} {'Tok est.':>10} {'QVars':>7}"
        )
        print("-" * 80)

        for label, summary in summaries.items():
            config_bits = []
            if summary.get("retrieval_mode") == "hybrid" or label == "hybrid_rrf":
                config_bits.append(f"{summary.get('dense_weight', 0.0):.1f}/{summary.get('sparse_weight', 0.0):.1f}")
            elif summary.get("retrieval_mode") == "rerank" or summary.get("use_rerank"):
                config_bits.append("rerank")
            else:
                config_bits.append("base")

            if summary.get("use_query_transform"):
                config_bits.append("qt")

            config = "+".join(config_bits)
            recall_str = f"{100 * (summary.get('avg_recall') or 0):.1f}%"
            top1_str = f"{100 * (summary.get('avg_top1_hit') or 0):.1f}%"
            mrr_str = f"{(summary.get('avg_mrr') or 0):.2f}"
            tok_str = f"{(summary.get('avg_prompt_tokens') or 0):.0f}"
            qv_str = f"{(summary.get('avg_query_variants') or 0):.1f}"
            print(f"{label:<22} {config:<14} {recall_str:>8} {top1_str:>8} {mrr_str:>8} {tok_str:>10} {qv_str:>7}")

        print("-" * 80)
        if best:
            print(
                "Recommendation: "
                f"{best.get('label', 'unknown')} has the strongest retrieval quality/tokens trade-off."
            )
        print(
            f"Best hybrid weights: dense_weight={best_hybrid['dense_weight']:.1f}, "
            f"sparse_weight={best_hybrid['sparse_weight']:.1f}"
        )

    payload = {
        "timestamp": datetime.now().isoformat(),
        "test_questions_count": len(questions),
        "best_strategy": best.get("label") if best else None,
        "best_hybrid_weights": {
            "dense_weight": best_hybrid.get("dense_weight"),
            "sparse_weight": best_hybrid.get("sparse_weight"),
        },
        "strategies": summaries,
        "error_tree": build_error_tree_mapping(),
    }

    if output_log_path:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOGS_DIR / output_log_path
        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Comparison log đã lưu tại: {log_path}")

    if output_md_path:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        md_path = LOGS_DIR / output_md_path
        md_lines = [
            f"# Retrieval Comparison\n",
            f"Generated: {payload['timestamp']}\n",
            f"Test questions: {payload['test_questions_count']}\n",
            f"Best strategy: {payload['best_strategy']}\n",
            "\n## Strategy Summary\n",
            "| Strategy | Recall@3 | Top1 | MRR | Avg prompt tokens | Query variants |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for label, summary in summaries.items():
            md_lines.append(
                f"| {label} | {100 * (summary.get('avg_recall') or 0):.1f}% | "
                f"{100 * (summary.get('avg_top1_hit') or 0):.1f}% | {summary.get('avg_mrr') or 0:.2f} | "
                f"{summary.get('avg_prompt_tokens') or 0:.0f} | {summary.get('avg_query_variants') or 0:.1f} |"
            )
        md_lines += [
            "\n## Error Tree\n",
            "| Failure Mode | Pipeline Stage | Root Cause | Recommended Fix |",
            "|---|---|---|---|",
        ]
        for row in payload["error_tree"]:
            md_lines.append(
                f"| {row['failure_mode']} | {row['pipeline_stage']} | {row['root_cause']} | {row['recommended_fix']} |"
            )
        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        print(f"Markdown comparison log đã lưu tại: {md_path}")

    return summaries


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
    if not answer or answer.startswith("ERROR"):
        return {"score": 1, "notes": "Empty/error answer"}

    context_text = " ".join(chunk.get("text", "") for chunk in chunks_used)
    overlap_ratio = _token_overlap_ratio(answer, context_text)
    score = _score_from_ratio(overlap_ratio)

    if _has_abstain_phrase(answer):
        score = max(score, 4 if chunks_used else 5)

    answer_numbers = set(_extract_numbers(answer))
    context_numbers = set(_extract_numbers(context_text))
    unsupported_numbers = answer_numbers - context_numbers
    if unsupported_numbers:
        score = max(1, score - 1)

    if "[" in answer and "]" in answer:
        score = min(5, score + 1)

    return {
        "score": score,
        "notes": (
            f"token_overlap={overlap_ratio:.2f}, "
            f"unsupported_numbers={sorted(unsupported_numbers) if unsupported_numbers else []}"
        ),
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
    if not answer or answer.startswith("ERROR"):
        return {"score": 1, "notes": "Empty/error answer"}

    if _has_abstain_phrase(answer):
        return {"score": 4, "notes": "Safe abstain / uncertainty handling"}

    ratio = _token_overlap_ratio(query, answer)
    score = _score_from_ratio(ratio)
    if len(_content_tokens(answer)) >= len(_content_tokens(query)):
        score = min(5, score + 1)

    return {
        "score": score,
        "notes": f"query_answer_overlap={ratio:.2f}",
    }


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
    if not expected_answer:
        return {"score": None, "notes": "No expected answer provided"}

    if not answer or answer.startswith("ERROR"):
        return {"score": 1, "notes": "Empty/error answer"}

    ratio = _token_overlap_ratio(expected_answer, answer)
    score = _score_from_ratio(ratio)

    expected_numbers = set(_extract_numbers(expected_answer))
    answer_numbers = set(_extract_numbers(answer))
    missing_numbers = expected_numbers - answer_numbers
    if expected_numbers:
        number_ratio = len(expected_numbers & answer_numbers) / len(expected_numbers)
        score = max(score, _score_from_ratio(number_ratio))
        if missing_numbers:
            score = max(1, score - 1)

    return {
        "score": score,
        "notes": (
            f"expected_overlap={ratio:.2f}, "
            f"missing_numbers={sorted(missing_numbers) if missing_numbers else []}"
        ),
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
        test_questions = load_questions_from_path(TEST_QUESTIONS_PATH)

    questions = [_normalize_question_item(item, index + 1) for index, item in enumerate(test_questions or [])]

    results = []
    label = config.get("label", "unnamed")

    print(f"\n{'='*70}")
    print(f"Chạy scorecard: {label}")
    print(f"Config: {config}")
    print('='*70)

    for q in questions:
        question_id = q["id"]
        query = q["question"]
        expected_answer = q.get("expected_answer", "")
        expected_sources = q.get("expected_sources", [])
        category = q.get("category", "")

        if verbose:
            print(f"\n[{question_id}] {query}")

        # --- Gọi pipeline ---
        try:
            start_time = time.perf_counter()
            result = rag_answer(
                query=query,
                retrieval_mode=config.get("retrieval_mode", "dense"),
                top_k_search=config.get("top_k_search", 10),
                top_k_select=config.get("top_k_select", 3),
                use_rerank=config.get("use_rerank", False),
                use_query_transform=config.get("use_query_transform", False),
                query_transform_strategy=config.get("query_transform_strategy", "expansion"),
                dense_weight=config.get("dense_weight", 0.6),
                sparse_weight=config.get("sparse_weight", 0.4),
                verbose=False,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            answer = result["answer"]
            chunks_used = result["chunks_used"]

        except NotImplementedError:
            answer = "PIPELINE_NOT_IMPLEMENTED"
            chunks_used = []
            latency_ms = None
        except Exception as e:
            answer = f"ERROR: {e}"
            chunks_used = []
            latency_ms = None

        # --- Chấm điểm ---
        faith = score_faithfulness(answer, chunks_used)
        relevance = score_answer_relevance(query, answer)
        recall = score_context_recall(chunks_used, expected_sources)
        complete = score_completeness(query, answer, expected_answer)
        answered = bool((answer or "").strip()) and not answer.startswith("ERROR") and answer != "PIPELINE_NOT_IMPLEMENTED"

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
            "latency_ms": latency_ms,
            "answered": answered,
            "config_label": label,
            "retrieval_mode": result.get("config", {}).get("retrieval_mode", config.get("retrieval_mode", "dense")),
            "sources": result.get("sources", []),
            "chunks_retrieved": len(chunks_used),
        }
        results.append(row)

        if verbose:
            print(f"  Answer: {answer[:100]}...")
            print(f"  Faithful: {faith['score']} | Relevant: {relevance['score']} | "
                  f"Recall: {recall['score']} | Complete: {complete['score']} | "
                  f"Latency: {latency_ms:.0f} ms" if latency_ms is not None else "Latency: N/A")

    # Tính averages (bỏ qua None)
    for metric in ["faithfulness", "relevance", "context_recall", "completeness"]:
        scores = [r[metric] for r in results if r[metric] is not None]
        avg = sum(scores) / len(scores) if scores else None
        print(f"\nAverage {metric}: {avg:.2f}" if avg else f"\nAverage {metric}: N/A (chưa chấm)")

    latency_scores = [r["latency_ms"] for r in results if r["latency_ms"] is not None]
    avg_latency = sum(latency_scores) / len(latency_scores) if latency_scores else None
    answer_rate = (sum(1 for r in results if r["answered"]) / len(results)) if results else None
    print(f"\nAverage latency_ms: {avg_latency:.0f} ms" if avg_latency is not None else "\nAverage latency_ms: N/A")
    print(f"Average answered_rate: {100 * answer_rate:.1f}%" if answer_rate is not None else "Average answered_rate: N/A")

    return results


# =============================================================================
# A/B COMPARISON
# =============================================================================

def compare_ab(
    baseline_results: List[Dict],
    variant_results: List[Dict],
    output_csv: Optional[str] = None,
    output_log_path: Optional[str] = None,
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

    def _avg(values: List[Any]) -> Optional[float]:
        numeric = [float(v) for v in values if v is not None]
        return sum(numeric) / len(numeric) if numeric else None

    def _answer_rate(rows: List[Dict[str, Any]]) -> Optional[float]:
        return (sum(1 for r in rows if r.get("answered")) / len(rows)) if rows else None

    def _avg_latency(rows: List[Dict[str, Any]]) -> Optional[float]:
        return _avg([r.get("latency_ms") for r in rows])

    print(f"\n{'='*70}")
    print("A/B Comparison: Baseline vs Variant")
    print('='*70)
    print(f"{'Metric':<20} {'Baseline':>10} {'Variant':>10} {'Delta':>8}")
    print("-" * 55)

    for metric in metrics:
        b_avg = _avg([r.get(metric) for r in baseline_results])
        v_avg = _avg([r.get(metric) for r in variant_results])
        delta = (v_avg - b_avg) if (b_avg is not None and v_avg is not None) else None

        b_str = f"{b_avg:.2f}" if b_avg is not None else "N/A"
        v_str = f"{v_avg:.2f}" if v_avg is not None else "N/A"
        d_str = f"{delta:+.2f}" if delta is not None else "N/A"

        print(f"{metric:<20} {b_str:>10} {v_str:>10} {d_str:>8}")

    latency_b = _avg_latency(baseline_results)
    latency_v = _avg_latency(variant_results)
    latency_delta = (latency_v - latency_b) if (latency_b is not None and latency_v is not None) else None
    answer_rate_b = _answer_rate(baseline_results)
    answer_rate_v = _answer_rate(variant_results)
    answer_rate_delta = (answer_rate_v - answer_rate_b) if (answer_rate_b is not None and answer_rate_v is not None) else None

    print(f"{'latency_ms':<20} {f'{latency_b:.0f} ms' if latency_b is not None else 'N/A':>10} {f'{latency_v:.0f} ms' if latency_v is not None else 'N/A':>10} {f'{latency_delta:+.0f} ms' if latency_delta is not None else 'N/A':>8}")
    print(f"{'answer_rate':<20} {f'{100*answer_rate_b:.1f}%' if answer_rate_b is not None else 'N/A':>10} {f'{100*answer_rate_v:.1f}%' if answer_rate_v is not None else 'N/A':>10} {f'{100*answer_rate_delta:+.1f}%' if answer_rate_delta is not None else 'N/A':>8}")

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

    if output_log_path:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOGS_DIR / output_log_path
        payload = {
            "timestamp": datetime.now().isoformat(),
            "baseline": {
                "summary": {
                    "faithfulness": _avg([r.get("faithfulness") for r in baseline_results]),
                    "relevance": _avg([r.get("relevance") for r in baseline_results]),
                    "context_recall": _avg([r.get("context_recall") for r in baseline_results]),
                    "completeness": _avg([r.get("completeness") for r in baseline_results]),
                    "latency_ms": latency_b,
                    "answer_rate": answer_rate_b,
                },
                "rows": baseline_results,
            },
            "variant": {
                "summary": {
                    "faithfulness": _avg([r.get("faithfulness") for r in variant_results]),
                    "relevance": _avg([r.get("relevance") for r in variant_results]),
                    "context_recall": _avg([r.get("context_recall") for r in variant_results]),
                    "completeness": _avg([r.get("completeness") for r in variant_results]),
                    "latency_ms": latency_v,
                    "answer_rate": answer_rate_v,
                },
                "rows": variant_results,
            },
        }
        if baseline_results and variant_results:
            payload["delta"] = {
                "faithfulness": (_avg([r.get("faithfulness") for r in variant_results]) or 0) - (_avg([r.get("faithfulness") for r in baseline_results]) or 0),
                "relevance": (_avg([r.get("relevance") for r in variant_results]) or 0) - (_avg([r.get("relevance") for r in baseline_results]) or 0),
                "context_recall": (_avg([r.get("context_recall") for r in variant_results]) or 0) - (_avg([r.get("context_recall") for r in baseline_results]) or 0),
                "completeness": (_avg([r.get("completeness") for r in variant_results]) or 0) - (_avg([r.get("completeness") for r in baseline_results]) or 0),
                "latency_ms": (latency_v or 0) - (latency_b or 0),
                "answer_rate": (answer_rate_v or 0) - (answer_rate_b or 0),
            }

        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nComparison log đã lưu tại: {log_path}")


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

    latency_scores = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    avg_latency = sum(latency_scores) / len(latency_scores) if latency_scores else None
    answer_rate = (sum(1 for r in results if r.get("answered")) / len(results)) if results else None

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
    md += "| ID | Category | Faithful | Relevant | Recall | Complete | Latency ms | Answered | Notes |\n"
    md += "|----|----------|----------|----------|--------|----------|-----------|----------|-------|\n"

    for r in results:
        md += (f"| {r['id']} | {r['category']} | {r.get('faithfulness', 'N/A')} | "
               f"{r.get('relevance', 'N/A')} | {r.get('context_recall', 'N/A')} | "
               f"{r.get('completeness', 'N/A')} | {r.get('latency_ms', 'N/A')} | "
               f"{r.get('answered', 'N/A')} | {r.get('faithfulness_notes', '')[:50]} |\n")

    md += "\n## Speed & Coverage\n\n"
    md += f"- Average latency: {avg_latency:.0f} ms\n" if avg_latency is not None else "- Average latency: N/A\n"
    md += f"- Answered rate: {100 * answer_rate:.1f}%\n" if answer_rate is not None else "- Answered rate: N/A\n"

    return md


def write_grading_run_log(
    questions: List[Dict[str, Any]],
    config: Dict[str, Any],
    output_path: Path,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """Ghi log theo format grading_run.json cho bất kỳ file câu hỏi cùng schema."""
    normalized_questions = [_normalize_question_item(item, index + 1) for index, item in enumerate(questions)]
    output_rows: List[Dict[str, Any]] = []

    for q in normalized_questions:
        try:
            result = rag_answer(
                query=q["question"],
                retrieval_mode=config.get("retrieval_mode", "dense"),
                top_k_search=config.get("top_k_search", 10),
                top_k_select=config.get("top_k_select", 3),
                use_rerank=config.get("use_rerank", False),
                use_query_transform=config.get("use_query_transform", False),
                query_transform_strategy=config.get("query_transform_strategy", "expansion"),
                dense_weight=config.get("dense_weight", 0.6),
                sparse_weight=config.get("sparse_weight", 0.4),
                verbose=False,
            )
            output_rows.append({
                "id": q["id"],
                "question": q["question"],
                "answer": result["answer"],
                "sources": result.get("sources", []),
                "chunks_retrieved": len(result.get("chunks_used", [])),
                "retrieval_mode": result.get("config", {}).get("retrieval_mode", config.get("retrieval_mode", "dense")),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
        except Exception as exc:
            output_rows.append({
                "id": q["id"],
                "question": q["question"],
                "answer": f"PIPELINE_ERROR: {exc}",
                "sources": [],
                "chunks_retrieved": 0,
                "retrieval_mode": config.get("retrieval_mode", "dense"),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
        if verbose:
            print(f"[grading-log] {q['id']} done")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    if verbose:
        print(f"Grading log đã lưu tại: {output_path}")
    return output_rows


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sprint 4 evaluation runner")
    parser.add_argument(
        "--questions-file",
        type=str,
        default=str(TEST_QUESTIONS_PATH),
        help="Path to a JSON file with the same schema as data/test_questions.json",
    )
    parser.add_argument(
        "--write-grading-log",
        action="store_true",
        help="Also write logs/grading_run.json using the chosen scoring config",
    )
    parser.add_argument(
        "--grading-log-path",
        type=str,
        default=str(LOGS_DIR / "grading_run.json"),
        help="Output path for grading log JSON",
    )
    return parser


def _load_questions_for_cli(questions_file: str) -> List[Dict[str, Any]]:
    path = Path(questions_file)
    print(f"\nLoading test questions từ: {path}")
    questions = load_questions_from_path(path)
    print(f"Tìm thấy {len(questions)} câu hỏi")
    for q in questions[:3]:
        print(f"  [{q['id']}] {q['question']} ({q.get('category', '')})")
    if len(questions) > 3:
        print("  ...")
    return questions


# =============================================================================
# MAIN — Chạy evaluation
# =============================================================================

if __name__ == "__main__":
    parser = _build_arg_parser()
    args = parser.parse_args()

    print("=" * 60)
    print("Sprint 4: Evaluation & Scorecard")
    print("=" * 60)

    try:
        test_questions = _load_questions_for_cli(args.questions_file)
    except FileNotFoundError:
        print(f"Không tìm thấy file questions: {args.questions_file}!")
        test_questions = []
    except ValueError as exc:
        print(f"File questions không hợp lệ: {exc}")
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
    print("\n--- Chạy Variant ---")
    try:
        variant_results = run_scorecard(
            config=VARIANT_CONFIG,
            test_questions=test_questions,
            verbose=True,
        )

        variant_md = generate_scorecard_summary(variant_results, VARIANT_CONFIG["label"])
        variant_path = RESULTS_DIR / "scorecard_variant.md"
        variant_path.write_text(variant_md, encoding="utf-8")
        print(f"\nScorecard lưu tại: {variant_path}")

    except NotImplementedError:
        print("Variant pipeline chưa implement.")
        variant_results = []

    # --- Chạy Rerank variant ---
    print("\n--- Chạy Rerank Variant ---")
    rerank_config = {
        "retrieval_mode": "rerank",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": True,
        "use_query_transform": False,
        "label": "variant_rerank",
    }
    try:
        rerank_results = run_scorecard(
            config=rerank_config,
            test_questions=test_questions,
            verbose=True,
        )
        rerank_md = generate_scorecard_summary(rerank_results, rerank_config["label"])
        rerank_path = RESULTS_DIR / "scorecard_rerank.md"
        rerank_path.write_text(rerank_md, encoding="utf-8")
        print(f"\nScorecard lưu tại: {rerank_path}")
    except NotImplementedError:
        print("Rerank pipeline chưa implement.")
        rerank_results = []

    # --- Chạy Query Transform variant ---
    print("\n--- Chạy Query Transform Variant ---")
    qt_config = {
        "retrieval_mode": "query_transform",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": False,
        "use_query_transform": True,
        "query_transform_strategy": "expansion",
        "label": "variant_query_transform",
    }
    try:
        qt_results = run_scorecard(
            config=qt_config,
            test_questions=test_questions,
            verbose=True,
        )
        qt_md = generate_scorecard_summary(qt_results, qt_config["label"])
        qt_path = RESULTS_DIR / "scorecard_query_transform.md"
        qt_path.write_text(qt_md, encoding="utf-8")
        print(f"\nScorecard lưu tại: {qt_path}")
    except NotImplementedError:
        print("Query transform pipeline chưa implement.")
        qt_results = []

    # --- A/B Comparison ---
    if baseline_results and variant_results:
        compare_ab(
            baseline_results,
            variant_results,
            output_csv="ab_comparison_hybrid.csv",
            output_log_path="scorecard_ab_hybrid.json",
        )

    if baseline_results and rerank_results:
        compare_ab(
            baseline_results,
            rerank_results,
            output_csv="ab_comparison_rerank.csv",
            output_log_path="scorecard_ab_rerank.json",
        )

    if baseline_results and qt_results:
        compare_ab(
            baseline_results,
            qt_results,
            output_csv="ab_comparison_query_transform.csv",
            output_log_path="scorecard_ab_query_transform.json",
        )

    if args.write_grading_log:
        print("\n--- Writing grading_run.json ---")
        write_grading_run_log(
            questions=test_questions,
            config=VARIANT_CONFIG,
            output_path=Path(args.grading_log_path),
            verbose=True,
        )

    # --- Retrieval Strategy Comparison (4-way) ---
    print("\n--- Retrieval strategy comparison (4-way) ---")
    compare_retrieval_scorecards(
        test_questions=test_questions,
        top_k_search=BASELINE_CONFIG.get("top_k_search", 10),
        top_k_select=BASELINE_CONFIG.get("top_k_select", 3),
        verbose=True,
        output_log_path="retrieval_comparison.json",
        output_md_path="retrieval_comparison.md",
    )

    print("\n\nViệc cần làm Sprint 4:")
    print("  1. Đã chạy run_scorecard(BASELINE_CONFIG) và lưu results/scorecard_baseline.md")
    print("  2. Đã chạy run_scorecard(VARIANT_CONFIG) và lưu results/scorecard_variant.md")
    print("  3. Đã chạy run_scorecard(rerank_config) và lưu results/scorecard_rerank.md")
    print("  4. Đã chạy run_scorecard(qt_config) và lưu results/scorecard_query_transform.md")
    print("  5. Đã chạy compare_ab() cho baseline vs hybrid/rerank/query_transform")
    print("  6. Đã chạy compare_retrieval_scorecards() và lưu logs/retrieval_comparison.json")
    print("  7. Cập nhật docs/tuning-log.md và docs/architecture.md với kết quả mới")
