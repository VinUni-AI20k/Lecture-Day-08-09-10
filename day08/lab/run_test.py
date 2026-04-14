"""
run_test.py — Sprint 2 (Eval Owner): Chạy tự động bộ câu hỏi qua pipeline
=============================================================================
Script này load test questions, chạy từng câu qua rag_answer(), và lưu kết quả
ra file JSON + in bảng tóm tắt.

Dùng để:
  - Sprint 2: Test baseline pipeline với bộ câu hỏi chính + extra
  - Sprint 3: So sánh nhanh khi thay đổi config
  - Sprint 4: Tạo log cho grading_questions.json

Usage:
  python run_test.py                         # Chạy test_questions.json (mặc định)
  python run_test.py --extra                 # Chạy test_questions_extra.json
  python run_test.py --all                   # Chạy cả 2 bộ (19 câu)
  python run_test.py --file data/grading_questions.json  # Chạy file tùy chọn
  python run_test.py --mode hybrid           # Đổi retrieval mode
  python run_test.py --rerank                # Bật rerank

Author: Long (Eval Owner)
"""

import json
import argparse
import sys
import io
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Fix encoding cho Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ==============================================================================
# CẤU HÌNH
# ==============================================================================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
RESULTS_DIR = BASE_DIR / "results"

TEST_QUESTIONS_PATH = DATA_DIR / "test_questions.json"
TEST_QUESTIONS_EXTRA_PATH = DATA_DIR / "test_questions_extra.json"


# ==============================================================================
# LOAD QUESTIONS
# ==============================================================================

def load_questions(filepath: Path) -> List[Dict[str, Any]]:
    """Load câu hỏi từ file JSON."""
    if not filepath.exists():
        print(f"[MISS] Khong tim thay file: {filepath}")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        questions = json.load(f)
    print(f"[OK] Loaded {len(questions)} cau hoi tu {filepath.name}")
    return questions


def load_all_questions(
    use_main: bool = True,
    use_extra: bool = False,
    custom_file: str = None,
) -> List[Dict[str, Any]]:
    """Load câu hỏi theo lựa chọn."""
    questions = []

    if custom_file:
        filepath = Path(custom_file)
        if not filepath.is_absolute():
            filepath = BASE_DIR / filepath
        return load_questions(filepath)

    if use_main:
        questions.extend(load_questions(TEST_QUESTIONS_PATH))
    if use_extra:
        questions.extend(load_questions(TEST_QUESTIONS_EXTRA_PATH))

    return questions


# ==============================================================================
# RUN PIPELINE
# ==============================================================================

def run_single_question(
    question: Dict[str, Any],
    retrieval_mode: str = "dense",
    top_k_search: int = 10,
    top_k_select: int = 3,
    use_rerank: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Chạy 1 câu hỏi qua pipeline, trả về kết quả có cấu trúc.
    Xử lý graceful khi pipeline chưa implement hoặc lỗi.
    """
    from rag_answer import rag_answer

    qid = question["id"]
    query = question["question"]
    expected = question.get("expected_answer", "")
    expected_sources = question.get("expected_sources", [])

    result_entry = {
        "id": qid,
        "question": query,
        "expected_answer": expected,
        "expected_sources": expected_sources,
        "category": question.get("category", ""),
        "difficulty": question.get("difficulty", ""),
        "answer": None,
        "sources": [],
        "chunks_retrieved": 0,
        "retrieval_mode": retrieval_mode,
        "use_rerank": use_rerank,
        "status": "pending",
        "error": None,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        result = rag_answer(
            query=query,
            retrieval_mode=retrieval_mode,
            top_k_search=top_k_search,
            top_k_select=top_k_select,
            use_rerank=use_rerank,
            verbose=verbose,
        )
        result_entry["answer"] = result["answer"]
        result_entry["sources"] = result["sources"]
        result_entry["chunks_retrieved"] = len(result.get("chunks_used", []))
        result_entry["status"] = "success"

    except NotImplementedError as e:
        result_entry["status"] = "not_implemented"
        result_entry["error"] = str(e).split("\n")[0]
        result_entry["answer"] = f"PIPELINE_NOT_IMPLEMENTED: {result_entry['error']}"

    except Exception as e:
        result_entry["status"] = "error"
        result_entry["error"] = str(e)
        result_entry["answer"] = f"PIPELINE_ERROR: {str(e)}"

    return result_entry


def run_all_questions(
    questions: List[Dict[str, Any]],
    retrieval_mode: str = "dense",
    top_k_search: int = 10,
    top_k_select: int = 3,
    use_rerank: bool = False,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """Chạy toàn bộ câu hỏi và trả về list kết quả."""
    results = []
    total = len(questions)

    print(f"\n{'='*70}")
    print(f"  Chay {total} cau hoi | mode={retrieval_mode} | rerank={use_rerank}")
    print(f"  top_k_search={top_k_search} | top_k_select={top_k_select}")
    print(f"{'='*70}\n")

    for i, q in enumerate(questions, 1):
        qid = q["id"]
        query = q["question"]
        difficulty = q.get("difficulty", "?")
        category = q.get("category", "?")

        print(f"[{i}/{total}] ({qid}) [{difficulty}] [{category}]")
        print(f"  Q: {query}")

        result = run_single_question(
            question=q,
            retrieval_mode=retrieval_mode,
            top_k_search=top_k_search,
            top_k_select=top_k_select,
            use_rerank=use_rerank,
            verbose=verbose,
        )
        results.append(result)

        # In kết quả ngắn gọn
        status = result["status"]
        if status == "success":
            answer_preview = result["answer"][:120] + "..." if len(result["answer"]) > 120 else result["answer"]
            print(f"  [OK] A: {answer_preview}")
            print(f"       Sources: {result['sources']} | Chunks: {result['chunks_retrieved']}")
        elif status == "not_implemented":
            print(f"  [TODO] Chua implement: {result['error']}")
        else:
            print(f"  [ERR] Loi: {result['error']}")
        print()

    return results


# ==============================================================================
# REPORT & SAVE
# ==============================================================================

def print_summary_table(results: List[Dict[str, Any]]) -> None:
    """In bảng tóm tắt kết quả."""
    print(f"\n{'='*70}")
    print("  BANG TOM TAT KET QUA")
    print(f"{'='*70}")
    print(f"{'ID':<6} {'Diff':<8} {'Category':<20} {'Status':<16} {'Chunks':<8} {'Sources'}")
    print("-" * 80)

    stats = {"success": 0, "not_implemented": 0, "error": 0}

    for r in results:
        status_icon = {
            "success": "[OK]",
            "not_implemented": "[TODO]",
            "error": "[ERR]",
        }.get(r["status"], r["status"])

        sources_str = ", ".join(r["sources"][:2]) if r["sources"] else "-"
        if len(r["sources"]) > 2:
            sources_str += f" (+{len(r['sources'])-2})"

        print(f"{r['id']:<6} {r.get('difficulty','?'):<8} {r.get('category',''):<20} "
              f"{status_icon:<16} {r['chunks_retrieved']:<8} {sources_str}")

        stats[r["status"]] = stats.get(r["status"], 0) + 1

    print("-" * 80)
    print(f"Tong: {len(results)} cau | "
          f"{stats['success']} thanh cong | "
          f"{stats['not_implemented']} chua implement | "
          f"{stats['error']} loi")

    # Quick check: source recall
    if stats["success"] > 0:
        recall_hits = 0
        recall_total = 0
        for r in results:
            if r["status"] == "success" and r["expected_sources"]:
                recall_total += 1
                retrieved_str = " ".join(r["sources"]).lower()
                for exp in r["expected_sources"]:
                    exp_name = exp.split("/")[-1].replace(".pdf", "").replace(".md", "").lower()
                    if exp_name in retrieved_str:
                        recall_hits += 1
                        break
        if recall_total > 0:
            print(f"\n[RECALL] Source Recall nhanh: {recall_hits}/{recall_total} cau retrieve dung expected source")


def save_results(
    results: List[Dict[str, Any]],
    output_path: Path,
) -> None:
    """Lưu kết quả ra file JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVE] Ket qua da luu: {output_path}")


def save_grading_log(
    results: List[Dict[str, Any]],
    output_path: Path,
) -> None:
    """
    Lưu kết quả theo format grading_run.json (yêu cầu trong SCORING.md).
    Dùng khi chạy grading_questions.json lúc 17:00-18:00.
    """
    log = []
    for r in results:
        log.append({
            "id": r["id"],
            "question": r["question"],
            "answer": r["answer"] or "PIPELINE_ERROR: No answer generated",
            "sources": r["sources"],
            "chunks_retrieved": r["chunks_retrieved"],
            "retrieval_mode": r["retrieval_mode"],
            "timestamp": r["timestamp"],
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"\n[LOG] Grading log da luu: {output_path}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sprint 2 — Chạy tự động bộ câu hỏi qua RAG pipeline"
    )
    parser.add_argument("--extra", action="store_true",
                        help="Chạy test_questions_extra.json thay vì main")
    parser.add_argument("--all", action="store_true",
                        help="Chạy cả test_questions.json + extra (19 câu)")
    parser.add_argument("--file", type=str, default=None,
                        help="Chạy file câu hỏi tùy chọn (vd: data/grading_questions.json)")
    parser.add_argument("--mode", type=str, default="dense",
                        choices=["dense", "sparse", "hybrid"],
                        help="Retrieval mode (default: dense)")
    parser.add_argument("--rerank", action="store_true",
                        help="Bật cross-encoder rerank")
    parser.add_argument("--top-k-search", type=int, default=10,
                        help="Số chunk search rộng (default: 10)")
    parser.add_argument("--top-k-select", type=int, default=3,
                        help="Số chunk đưa vào prompt (default: 3)")
    parser.add_argument("--verbose", action="store_true",
                        help="In chi tiết prompt và retrieval")
    parser.add_argument("--grading", action="store_true",
                        help="Lưu output theo format grading_run.json")
    parser.add_argument("--output", type=str, default=None,
                        help="Đường dẫn file output (mặc định: logs/test_run_<timestamp>.json)")

    args = parser.parse_args()

    # Load questions
    if args.file:
        questions = load_all_questions(custom_file=args.file)
    elif args.all:
        questions = load_all_questions(use_main=True, use_extra=True)
    elif args.extra:
        questions = load_all_questions(use_main=False, use_extra=True)
    else:
        questions = load_all_questions(use_main=True, use_extra=False)

    if not questions:
        print("[ERR] Khong co cau hoi nao de chay!")
        sys.exit(1)

    # Run pipeline
    results = run_all_questions(
        questions=questions,
        retrieval_mode=args.mode,
        top_k_search=args.top_k_search,
        top_k_select=args.top_k_select,
        use_rerank=args.rerank,
        verbose=args.verbose,
    )

    # Print summary
    print_summary_table(results)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.grading:
        grading_path = LOGS_DIR / "grading_run.json"
        save_grading_log(results, grading_path)
    
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = BASE_DIR / output_path
    else:
        output_path = LOGS_DIR / f"test_run_{timestamp}.json"

    save_results(results, output_path)

    # Status check
    success_count = sum(1 for r in results if r["status"] == "success")
    if success_count == 0:
        print("\n[WARN] Pipeline chua implement. Doi Tech Lead hoan thanh Sprint 2:")
        print("    1. get_embedding() trong index.py")
        print("    2. build_index() trong index.py")
        print("    3. retrieve_dense() trong rag_answer.py")
        print("    4. call_llm() trong rag_answer.py")
    elif success_count < len(results):
        print(f"\n[WARN] {len(results) - success_count} cau bi loi -- kiem tra pipeline.")
    else:
        print(f"\n[DONE] Tat ca {len(results)} cau chay thanh cong!")


if __name__ == "__main__":
    main()
