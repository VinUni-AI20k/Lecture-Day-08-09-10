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
from rag_answer import rag_answer
from langchain_openai import ChatOpenAI
import os

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall as ragas_context_recall

# =============================================================================
# CẤU HÌNH
# =============================================================================

TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"
GRADING_QUESTIONS_PATH = Path(__file__).parent / "data" / "grading_questions.json"
RESULTS_DIR = Path(__file__).parent / "results"

# Cấu hình baseline (Sprint 2)
BASELINE_CONFIG = {
    "retrieval_mode": "dense",
    "top_k_search": 10,
    "top_k_select": 3,
    "label": "baseline_dense",
}

# Cấu hình variant (Sprint 3 — điều chỉnh theo lựa chọn của nhóm)
VARIANT_CONFIG = {
    "retrieval_mode": "hybrid",
    "top_k_search": 10,
    "top_k_select": 3,
    "label": "variant_hybrid",
}
api_base = os.getenv("OPENAI_API_BASE")

def get_judge_llm():
    """Khởi tạo LLM làm giám khảo chấm điểm"""
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=api_base if api_base else None,
        temperature=0
    )

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
    # TODO Sprint 4: Implement scoring
    # Tạm thời trả về None (yêu cầu chấm thủ công)
    context = "\n".join([c.get("page_content", "") for c in chunks_used])
    if not context:
        return {
            "score": 1,  # Không có evidence nào, answer chắc chắn không faithful
            "notes": "No retrieved chunks, answer likely not faithful",
        }
    llm = get_judge_llm()
    prompt = f"""Given these retrieved chunks: {context}
             And this answer: {answer}
             Rate the faithfulness on a scale of 1-5.
             5 = completely grounded in the provided context.
             1 = answer contains information not in the context.
             Output JSON: {{"score": int, "reason": "string"}}"""
    try:
        response = llm.invoke(prompt)
        import re,json
        match = re.search(r"\{.*\}", response.content, re.DOTALL)
        result = json.loads(match.group())
        return {
                "score": result.get("score"),
                "notes": result.get("reason"),
            }
    except Exception as e:
        return {
        "score": 1,
        "notes": "No context provided",
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

    TODO Sprint 4: Implement tương tự score_faithfulness
    """
    llm = get_judge_llm()
    prompt = f"""Rate RELEVANCE (1-5): Does the answer directly address the question?
    QUERY: {query}
    ANSWER: {answer}
    Return JSON: {{"score": int, "reason": "string"}}"""
    try:
        llm_response = llm.invoke(prompt)
        import re,json
        match = re.search(r"\{.*\}", llm_response.content, re.DOTALL)
        result = json.loads(match.group())
        return {"score": result['score'], "notes": result['reason']}
    except Exception as e:
        return {"score": 3, "notes": "Error in LLM evaluation"}
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
        return {
            "score": 5 if not chunks_used else 3, # Thưởng điểm nếu không lấy chunk thừa cho câu ko có data
            "recall": 1.0 if not chunks_used else 0.0, 
            "notes": "Abstain case: No expected sources."
        }

    retrieved_sources = {
        c.get("metadata", {}).get("source", "")
        for c in chunks_used
    }

    # TODO: Kiểm tra matching theo partial path (vì source paths có thể khác format)
    retrieved_sources = set()
    for c in chunks_used:
        source_path = c.get("metadata", {}).get("source", "")
        # Lấy tên file cuối cùng (ví dụ: hr/policy.pdf -> policy.pdf)
        clean_name = source_path.split("/")[-1].split("\\")[-1].lower()
        if clean_name:
            retrieved_sources.add(clean_name)

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
    score_5 = round(recall * 5)
    score_5 = max(1, min(5, score_5)) if found > 0 else 0

    return {
        "score": score_5,  # Convert to 1-5 scale
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
    grading_criteria: List[str] = None
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
        # Không có expected answer để so sánh
        return {"score": None, "notes": "No expected answer for comparison"}
    llm = get_judge_llm()
    criteria_text = "\n".join([f"- {c}" for c in grading_criteria]) if grading_criteria else "None"
    
    prompt =f"""Rate COMPLETENESS (1-5): Compare answer to expected answer. Are all key points covered?
    EXPECTED ANSWER: {expected_answer}
    GRADING CRITERIA:
    {criteria_text}

    ACTUAL ANSWER: {answer}
    Return JSON: {{"score": int, "reason": "string"}}"""
    try: 
        response = llm.invoke(prompt)
        import re,json
        match = re.search(r"\{.*\}", response.content, re.DOTALL)
        result = json.loads(match.group())
        return {"score": result['score'], "notes": result['reason']}
    except Exception as e:
        return {"score": 3, "notes": "Error in LLM evaluation"}


#thanh
def compute_ragas_scores(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tính RAGAS metrics từ kết quả run_scorecard."""
    if not results:
        return {
            "faithfulness": None,
            "answer_relevancy": None,
            "context_precision": None,
            "context_recall": None,
            "notes": "No results to evaluate",
        }

    dataset = Dataset.from_dict(
        {
            "question": [r.get("query", "") for r in results],
            "answer": [r.get("answer", "") for r in results],
            "contexts": [r.get("contexts", []) for r in results],
            "ground_truth": [r.get("expected_answer", "") for r in results],
        }
    )

    try:
        scores = evaluate(
            dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                ragas_context_recall,
            ],
        )
        return {
            "faithfulness": round(float(scores["faithfulness"]), 4),
            "answer_relevancy": round(float(scores["answer_relevancy"]), 4),
            "context_precision": round(float(scores["context_precision"]), 4),
            "context_recall": round(float(scores["context_recall"]), 4),
        }
    except Exception as e:
        return {
            "faithfulness": None,
            "answer_relevancy": None,
            "context_precision": None,
            "context_recall": None,
            "notes": f"RAGAS evaluation failed: {e}",
        }


#thanh
def compute_abstain_accuracy(results: List[Dict[str, Any]]) -> float:
    """Tỷ lệ abstain đúng trên các câu expected_sources rỗng."""
    abstain_cases = [r for r in results if r.get("expected_sources") == []]
    if not abstain_cases:
        return 1.0

    def is_abstain(answer: str) -> bool:
        normalized = (answer or "").strip().lower()
        return (
            "không đủ dữ liệu" in normalized
            or "không tìm thấy thông tin" in normalized
            or "không có thông tin" in normalized
            or "i do not know" in normalized
            or "do not know" in normalized
        )

    correct = 0
    for row in abstain_cases:
        answer = row.get("answer", "")
        chunks_used = row.get("chunks_used", [])
        sources = row.get("sources", [])
        if is_abstain(answer) or (not chunks_used and not sources):
            correct += 1

    return round(correct / len(abstain_cases), 4)

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
        grading_criteria = q.get("grading_criteria", [])

        if verbose:
            print(f"\n[{question_id}] {query}")

        # --- Gọi pipeline ---
        result = {}
        try:
            result = rag_answer(
                query=query,
                retrieval_mode=config.get("retrieval_mode", "dense"),
                top_k_search=config.get("top_k_search", 10),
                top_k_select=config.get("top_k_select", 3),
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
        complete = score_completeness(query, answer, expected_answer, grading_criteria)

        row = {
            "id": question_id,
            "category": category,
            "query": query,
            "answer": answer,
            "expected_answer": expected_answer,
            "expected_sources": expected_sources, #thanh
            "sources": result.get("sources", []) if "result" in locals() and isinstance(result, dict) else [], #thanh
            "chunks_used": chunks_used, #thanh
            "contexts": [
                c.get("text") or c.get("page_content", "")
                for c in chunks_used
                if isinstance(c, dict)
            ], #thanh
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
    """
    # 1. Tính toán điểm trung bình
    metrics = {
        "faithfulness": {"target": 0.90, "score": 0.0},
        "relevance": {"target": 0.85, "score": 0.0},
        "context_recall": {"target": 0.80, "score": 0.0},
        "completeness": {"target": 0.80, "score": 0.0}
    }
    
    for m in metrics:
        scores = [r[m] for r in results if r[m] is not None]
        # Chuyển thang điểm 1-5 sang 0.0-1.0 (ví dụ 4/5 = 0.8)
        avg = (sum(scores) / len(scores) / 5) if scores else 0.0
        metrics[m]["score"] = avg

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 2. Xây dựng nội dung Markdown
    md = f"# Scorecard — {label.replace('_', ' ').title()}\n"
    md += f"**Thời gian chạy:** {timestamp} \n\n"
    
    md += "## RAGAS Metrics\n"
    md += "| Metric | Score | Target | Status |\n"
    md += "|---|---|---|---|---|\n"
    
    for name, data in metrics.items():
        status = "✅" if data["score"] >= data["target"] else "❌"
        md += f"| {name.replace('_', ' ').title()} | {data['score']:.2f} | > {data['target']:.2f} | {status} |\n"
    
    # Thêm Abstain Accuracy (tính riêng dựa trên category 'Insufficient Context')
    abstain_results = [r for r in results if r['category'] == 'Insufficient Context']
    if abstain_results:
        # Pass nếu answer có chứa "không tìm thấy" hoặc completeness/faithfulness đạt cao cho abstain question
        correct_abstains = sum(1 for r in abstain_results if "không tìm thấy" in r['answer'].lower() or r['completeness'] >= 4)
        abstain_score = correct_abstains / len(abstain_results)
    else:
        abstain_score = 0.0

    md += f"| Abstain Accuracy | {abstain_score:.2f} | = 1.00 | {'✅' if abstain_score == 1.0 else '❌'} |\n\n"

    md += "## Per-question Results\n"
    md += "| ID | Category | Expected | Got | Pass? |\n"
    md += "|---|---|---|---|---|\n"

    for r in results:
        # Check pass/fail dựa trên tổng điểm (ví dụ > 3 là pass)
        is_pass = "✅" if (r.get('faithfulness', 0) or 0) >= 4 else "❌"
        # Rút ngắn câu trả lời để bảng đẹp
        got_short = r['answer'][:50].replace('\n', ' ') + "..."
        exp_short = r['expected_answer'][:50].replace('\n', ' ') + "..."
        
        md += f"| {r['id']} | {r['category']} | {exp_short} | {got_short} | {is_pass} |\n"

    return md

# =============================================================================
# MAIN — Chạy evaluation
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 4: Evaluation & Scorecard")
    print("=" * 60)

    # Kiểm tra test questions
    data_source = TEST_QUESTIONS_PATH.stem
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
        scorecard_path = RESULTS_DIR / f"scorecard_baseline_{data_source}.md"
        scorecard_path.write_text(baseline_md, encoding="utf-8")
        print(f"\nScorecard lưu tại: {scorecard_path}")

        #thanh
        ragas_scores = compute_ragas_scores(baseline_results)
        abstain_accuracy = compute_abstain_accuracy(baseline_results)
        print("\nRAGAS Metrics:")
        for metric_name, metric_value in ragas_scores.items():
            print(f"  {metric_name}: {metric_value}")
        print(f"Abstain Accuracy: {abstain_accuracy}")

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
    (RESULTS_DIR / f"scorecard_variant_{data_source}.md").write_text(variant_md, encoding="utf-8")

    # --- A/B Comparison ---
    # TODO Sprint 4: Uncomment sau khi có cả baseline và variant
    if baseline_results and variant_results:
        compare_ab(
            baseline_results,
            variant_results,
            output_csv=f"ab_comparison_{data_source}.csv"
        )

    print("\n\nViệc cần làm Sprint 4:")
    print("  1. Hoàn thành Sprint 2 + 3 trước")
    print("  2. Chấm điểm thủ công hoặc implement LLM-as-Judge trong score_* functions")
    print("  3. Chạy run_scorecard(BASELINE_CONFIG)")
    print("  4. Chạy run_scorecard(VARIANT_CONFIG)")
    print("  5. Gọi compare_ab() để thấy delta")
    print("  6. Cập nhật docs/tuning-log.md với kết quả và nhận xét")
