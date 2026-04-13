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
    "retrieval_mode": "hybrid",   # Hoặc "dense" nếu chỉ đổi rerank
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,          # Variant hiện tại của nhóm là hybrid không rerank
    "label": "variant_hybrid",
}


def load_questions(path: Path, label: str) -> List[Dict[str, Any]]:
    """
    Load một bộ câu hỏi từ file JSON và in preview ngắn.
    """
    print(f"\nLoading {label} từ: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except FileNotFoundError:
        print(f"Không tìm thấy file {path.name}!")
        return []

    print(f"Tìm thấy {len(questions)} câu hỏi")
    for q in questions[:3]:
        category = q.get("category")
        category_text = f" ({category})" if category else ""
        print(f"  [{q.get('id', '?')}] {q.get('question', '')}{category_text}")
    if len(questions) > 3:
        print("  ...")

    return questions


def parse_args() -> argparse.Namespace:
    """
    CLI cho eval.py:
      - Mặc định: chạy scorecard với test_questions.json
      - grading: chạy grading_questions.json và xuất logs/grading_run.json
    """
    parser = argparse.ArgumentParser(
        description="Run scorecard on test questions or generate grading logs."
    )
    parser.add_argument(
        "--dataset",
        choices=["test", "grading", "both"],
        default="test",
        help="Dataset to run: test, grading, or both. Default is test.",
    )
    parser.add_argument(
        "--config",
        choices=["baseline", "variant"],
        default="baseline",
        help="Pipeline config to use: baseline or variant.",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run both baseline and variant, then print A/B comparison.",
    )
    return parser.parse_args()


def get_config(config_name: str) -> Dict[str, Any]:
    """
    Resolve tên config CLI sang config dict.
    """
    if config_name == "variant":
        return VARIANT_CONFIG
    return BASELINE_CONFIG


def run_and_save_scorecard(
    questions: List[Dict[str, Any]],
    config: Dict[str, Any],
    prefix: str = "",
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """
    Chạy scorecard cho một config và lưu markdown summary.
    """
    results = run_scorecard(
        config=config,
        test_questions=questions,
        verbose=verbose,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    scorecard_name = f"scorecard_{prefix}{config['label']}.md"
    scorecard_md = generate_scorecard_summary(results, config["label"])
    scorecard_path = RESULTS_DIR / scorecard_name
    scorecard_path.write_text(scorecard_md, encoding="utf-8")
    print(f"\nScorecard lưu tại: {scorecard_path}")

    return results


# =============================================================================
# SCORING FUNCTIONS
# 4 metrics từ slide: Faithfulness, Answer Relevance, Context Recall, Completeness
# =============================================================================

def _call_judge_llm(prompt: str) -> str:
    """
    Gọi LLM để chấm điểm (LLM-as-Judge).
    Dùng chung OPENAI_API_KEY hoặc GOOGLE_API_KEY với pipeline.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")

    if openai_key:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=256,
        )
        return response.choices[0].message.content

    elif google_key:
        import google.generativeai as genai
        genai.configure(api_key=google_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text

    else:
        raise EnvironmentError(
            "Không tìm thấy API key. Cần OPENAI_API_KEY hoặc GOOGLE_API_KEY trong .env"
        )


def _parse_judge_response(raw: str) -> Dict[str, Any]:
    """
    Parse JSON từ response của LLM judge.
    Trả về {"score": int, "reason": str} hoặc fallback về score=None.
    """
    try:
        # Tìm JSON block trong response (đôi khi LLM wrap thêm text)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        pass
    return {"score": None, "reason": f"Parse lỗi: {raw[:100]}"}


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
    context_texts = "\n\n".join(
        f"[{i+1}] {c.get('text', '')[:400]}"
        for i, c in enumerate(chunks_used)
    )
    prompt = f"""You are an evaluation judge for a RAG system.

Given the retrieved context and the model answer below, rate the FAITHFULNESS of the answer on a scale of 1 to 5.

Scale:
5 = Every claim in the answer is directly supported by the retrieved context.
4 = Almost entirely grounded; at most 1 minor detail is uncertain.
3 = Mostly grounded, but some information may come from outside the context.
2 = Several claims are not supported by the retrieved context.
1 = The answer is mostly fabricated or contradicts the context.

Retrieved Context:
{context_texts}

Model Answer:
{answer}

Respond ONLY with a JSON object in this exact format:
{{"score": <integer 1-5>, "reason": "<one sentence explanation>"}}"""

    try:
        raw = _call_judge_llm(prompt)
        parsed = _parse_judge_response(raw)
        return {
            "score": parsed.get("score"),
            "notes": parsed.get("reason", ""),
        }
    except Exception as e:
        return {"score": None, "notes": f"Judge error: {e}"}




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
    prompt = f"""You are an evaluation judge for a RAG system.

Given the question and the model answer, rate the ANSWER RELEVANCE on a scale of 1 to 5.

Scale:
5 = The answer directly and completely addresses the question asked.
4 = The answer is correct but missing a few minor details.
3 = The answer is related but does not fully focus on the core question.
2 = The answer is partially off-topic.
1 = The answer does not address the question at all.

Question:
{query}

Model Answer:
{answer}

Respond ONLY with a JSON object in this exact format:
{{"score": <integer 1-5>, "reason": "<one sentence explanation>"}}"""

    try:
        raw = _call_judge_llm(prompt)
        parsed = _parse_judge_response(raw)
        return {
            "score": parsed.get("score"),
            "notes": parsed.get("reason", ""),
        }
    except Exception as e:
        return {"score": None, "notes": f"Judge error: {e}"}




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

    prompt = f"""You are an evaluation judge for a RAG system.

Compare the model answer with the reference (expected) answer and rate the COMPLETENESS on a scale of 1 to 5.

Scale:
5 = The model answer covers all key points in the expected answer.
4 = Missing only 1 minor detail.
3 = Missing some important information.
2 = Missing many important points.
1 = Missing most of the core content.

Question:
{query}

Expected Answer (reference):
{expected_answer}

Model Answer:
{answer}

Respond ONLY with a JSON object in this exact format:
{{"score": <integer 1-5>, "reason": "<one sentence explanation>"}}"""

    try:
        raw = _call_judge_llm(prompt)
        parsed = _parse_judge_response(raw)
        return {
            "score": parsed.get("score"),
            "notes": parsed.get("reason", ""),
        }
    except Exception as e:
        return {"score": None, "notes": f"Judge error: {e}"}


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
# GRADING RUN LOG GENERATOR
# Tạo logs/grading_run.json theo đúng format yêu cầu trong SCORING.md
# =============================================================================

def generate_grading_log(
    questions_path: Path = GRADING_QUESTIONS_PATH,
    retrieval_mode: str = "hybrid",
    use_rerank: bool = False,
    top_k_search: int = 10,
    top_k_select: int = 3,
) -> None:
    """
    Chạy pipeline với grading_questions.json và xuất log ra logs/grading_run.json.

    Format log theo chuẩn SCORING.md:
    [
      {
        "id": "gq01",
        "question": "...",
        "answer": "...",
        "sources": [...],
        "chunks_retrieved": 3,
        "retrieval_mode": "hybrid",
        "timestamp": "2026-04-12T17:23:45"
      },
      ...
    ]

    Gọi hàm này sau 17:00 khi grading_questions.json được public.
    Dùng cấu hình tốt nhất của nhóm (retrieval_mode + use_rerank).
    """
    if not questions_path.exists():
        print(f"[grading_log] Không tìm thấy {questions_path}")
        print("  → Chờ đến 17:00 khi grading_questions.json được public.")
        return

    with open(questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"\n[grading_log] Bắt đầu chạy {len(questions)} câu grading...")
    print(f"  Config: mode={retrieval_mode}, rerank={use_rerank}, top_k={top_k_search}→{top_k_select}")

    log = []
    for q in questions:
        qid = q.get("id", "?")
        question = q.get("question", "")
        print(f"  [{qid}] {question[:60]}...")

        try:
            result = rag_answer(
                query=question,
                retrieval_mode=retrieval_mode,
                top_k_search=top_k_search,
                top_k_select=top_k_select,
                use_rerank=use_rerank,
                verbose=False,
            )
            log.append({
                "id": qid,
                "question": question,
                "answer": result["answer"],
                "sources": result["sources"],
                "chunks_retrieved": len(result["chunks_used"]),
                "retrieval_mode": result["config"]["retrieval_mode"],
                "timestamp": datetime.now().isoformat(),
            })
        except NotImplementedError:
            log.append({
                "id": qid,
                "question": question,
                "answer": "PIPELINE_ERROR: Pipeline chưa được implement đầy đủ.",
                "sources": [],
                "chunks_retrieved": 0,
                "retrieval_mode": retrieval_mode,
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as e:
            log.append({
                "id": qid,
                "question": question,
                "answer": f"PIPELINE_ERROR: {e}",
                "sources": [],
                "chunks_retrieved": 0,
                "retrieval_mode": retrieval_mode,
                "timestamp": datetime.now().isoformat(),
            })

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "grading_run.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"\n[grading_log] ✓ Log lưu tại: {log_path}")
    print(f"[grading_log] Tổng số câu đã chạy: {len(log)}")




if __name__ == "__main__":
    args = parse_args()
    selected_config = get_config(args.config)

    print("=" * 60)
    print("Sprint 4: Evaluation & Scorecard")
    print("=" * 60)
    print(f"Dataset: {args.dataset}")
    print(f"Config: {args.config} -> {selected_config}")
    print(f"Compare mode: {args.compare}")

    if args.dataset in ("test", "both"):
        test_questions = load_questions(TEST_QUESTIONS_PATH, "test questions")

        print("\n--- Chạy Scorecard (test) ---")
        print("Lưu ý: Cần hoàn thành Sprint 2 trước khi chạy scorecard!")
        try:
            if args.compare:
                baseline_results = run_and_save_scorecard(
                    test_questions,
                    BASELINE_CONFIG,
                    verbose=True,
                )
                variant_results = run_and_save_scorecard(
                    test_questions,
                    VARIANT_CONFIG,
                    verbose=True,
                )
                compare_ab(
                    baseline_results,
                    variant_results,
                    output_csv="ab_comparison_test.csv",
                )
            else:
                run_and_save_scorecard(
                    test_questions,
                    selected_config,
                    verbose=True,
                )

        except NotImplementedError:
            print("Pipeline chưa implement. Hoàn thành Sprint 2 trước.")

    if args.dataset in ("grading", "both"):
        grading_questions = load_questions(GRADING_QUESTIONS_PATH, "grading questions")

        if args.compare:
            print("\n--- Chạy A/B Comparison (grading) ---")
            baseline_results = run_and_save_scorecard(
                grading_questions,
                BASELINE_CONFIG,
                prefix="grading_",
                verbose=True,
            )
            variant_results = run_and_save_scorecard(
                grading_questions,
                VARIANT_CONFIG,
                prefix="grading_",
                verbose=True,
            )
            compare_ab(
                baseline_results,
                variant_results,
                output_csv="ab_comparison_grading.csv",
            )
        else:
            print("\n--- Chạy Grading Log ---")
            generate_grading_log(
                questions_path=GRADING_QUESTIONS_PATH,
                retrieval_mode=selected_config["retrieval_mode"],
                use_rerank=selected_config["use_rerank"],
                top_k_search=selected_config["top_k_search"],
                top_k_select=selected_config["top_k_select"],
            )

    print("\n\nLệnh gợi ý:")
    print("  python eval.py")
    print("  python eval.py --config variant")
    print("  python eval.py --dataset grading --config variant")
    print("  python eval.py --dataset both --config variant")
    print("  python eval.py --dataset grading --compare")
    print("  python eval.py --dataset test --compare")
