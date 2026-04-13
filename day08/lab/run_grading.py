"""
run_grading.py — Chạy pipeline với grading_questions.json và ghi log
====================================================================
Cách dùng:
    python run_grading.py

Output:
    logs/grading_run.json  — format bắt buộc theo SCORING.md

Config mặc định: retrieval_mode="hybrid", use_rerank=True (variant tốt nhất)
Để đổi config, truyền argument:
    python run_grading.py --mode dense --no-rerank
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Thêm thư mục lab vào sys.path để import được rag_answer
sys.path.insert(0, str(Path(__file__).parent))

from rag_answer import rag_answer

# =============================================================================
# PATHS
# =============================================================================

GRADING_QUESTIONS_PATH = Path(__file__).parent / "data" / "grading_questions.json"
LOGS_DIR = Path(__file__).parent / "logs"
OUTPUT_PATH = LOGS_DIR / "grading_run.json"


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Chạy grading_questions qua RAG pipeline")
    parser.add_argument("--mode", default="hybrid",
                        choices=["dense", "sparse", "hybrid"],
                        help="Retrieval mode (mặc định: hybrid)")
    parser.add_argument("--no-rerank", action="store_true",
                        help="Tắt rerank (mặc định: bật)")
    parser.add_argument("--top-k-search", type=int, default=10,
                        help="Số chunk lấy từ vector store (mặc định: 10)")
    parser.add_argument("--top-k-select", type=int, default=3,
                        help="Số chunk đưa vào prompt (mặc định: 3)")
    args = parser.parse_args()

    retrieval_mode = args.mode
    use_rerank = not args.no_rerank
    top_k_search = args.top_k_search
    top_k_select = args.top_k_select

    # --- Load grading questions ---
    if not GRADING_QUESTIONS_PATH.exists():
        print(f"[ERROR] Không tìm thấy: {GRADING_QUESTIONS_PATH}")
        sys.exit(1)

    with open(GRADING_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print("=" * 65)
    print("Grading Run — RAG Pipeline")
    print("=" * 65)
    print(f"  Questions  : {len(questions)} câu")
    print(f"  Mode       : {retrieval_mode}")
    print(f"  Rerank     : {use_rerank}")
    print(f"  top_k      : search={top_k_search}, select={top_k_select}")
    print(f"  Output     : {OUTPUT_PATH}")
    print("=" * 65)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log = []
    for i, q in enumerate(questions, 1):
        qid = q["id"]
        question = q["question"]
        print(f"\n[{i}/{len(questions)}] {qid}: {question[:60]}...")

        try:
            result = rag_answer(
                query=question,
                retrieval_mode=retrieval_mode,
                top_k_search=top_k_search,
                top_k_select=top_k_select,
                use_rerank=use_rerank,
                verbose=False,
            )
            answer = result["answer"]
            sources = result["sources"]
            chunks_retrieved = len(result["chunks_used"])

            print(f"  Answer: {answer[:100]}{'...' if len(answer) > 100 else ''}")
            print(f"  Sources ({chunks_retrieved} chunks): {sources}")

        except Exception as e:
            print(f"  [ERROR] {e}")
            answer = f"PIPELINE_ERROR: {e}"
            sources = []
            chunks_retrieved = 0

        log.append({
            "id": qid,
            "question": question,
            "answer": answer,
            "sources": sources,
            "chunks_retrieved": chunks_retrieved,
            "retrieval_mode": retrieval_mode,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        })

    # --- Ghi log ---
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 65}")
    print(f"Hoàn thành: {len(log)} câu")
    print(f"Log đã lưu tại: {OUTPUT_PATH}")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
