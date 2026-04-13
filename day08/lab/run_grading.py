"""
run_grading.py — Chạy pipeline với grading_questions.json và xuất log.

Sử dụng sau khi `grading_questions.json` được public lúc 17:00.
Dùng VARIANT_CONFIG (cấu hình tốt nhất) để trả lời 10 câu hỏi ẩn.

Output: logs/grading_run.json — format yêu cầu của SCORING.md mục 3.
"""

import json
from datetime import datetime
from pathlib import Path

from rag_answer import rag_answer
from eval import VARIANT_CONFIG

LAB_DIR = Path(__file__).parent
GRADING_PATH = LAB_DIR / "data" / "grading_questions.json"
LOG_DIR = LAB_DIR / "logs"
LOG_PATH = LOG_DIR / "grading_run.json"


def main() -> None:
    if not GRADING_PATH.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {GRADING_PATH}. File này được giảng viên public lúc 17:00."
        )

    with GRADING_PATH.open("r", encoding="utf-8") as f:
        questions = json.load(f)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = []

    print(f"Chạy {len(questions)} grading questions với config: {VARIANT_CONFIG['label']}")

    for q in questions:
        qid = q["id"]
        query = q["question"]
        print(f"  [{qid}] {query[:80]}...")
        try:
            result = rag_answer(
                query=query,
                retrieval_mode=VARIANT_CONFIG["retrieval_mode"],
                top_k_search=VARIANT_CONFIG["top_k_search"],
                top_k_select=VARIANT_CONFIG["top_k_select"],
                use_rerank=VARIANT_CONFIG["use_rerank"],
                verbose=False,
            )
            entry = {
                "id": qid,
                "question": query,
                "answer": result["answer"],
                "sources": result["sources"],
                "chunks_retrieved": len(result["chunks_used"]),
                "retrieval_mode": result["config"]["retrieval_mode"],
                "use_rerank": result["config"]["use_rerank"],
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        except Exception as e:
            entry = {
                "id": qid,
                "question": query,
                "answer": f"PIPELINE_ERROR: {e}",
                "sources": [],
                "chunks_retrieved": 0,
                "retrieval_mode": VARIANT_CONFIG["retrieval_mode"],
                "use_rerank": VARIANT_CONFIG["use_rerank"],
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        log.append(entry)

    with LOG_PATH.open("w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"\nĐã ghi log: {LOG_PATH} ({len(log)} câu)")


if __name__ == "__main__":
    main()
