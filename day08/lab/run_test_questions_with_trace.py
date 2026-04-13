"""
Run data/test_questions.json through rag_answer() and write logs/query_trace.jsonl.

Usage:
  set RAG_TRACE=1
  python run_test_questions_with_trace.py
"""

import json
import os
from pathlib import Path

from rag_answer import rag_answer


LAB_DIR = Path(__file__).parent
TEST_QUESTIONS_PATH = LAB_DIR / "data" / "test_questions.json"


def main() -> None:
    os.environ["RAG_TRACE"] = os.getenv("RAG_TRACE", "1")

    questions = json.loads(TEST_QUESTIONS_PATH.read_text(encoding="utf-8"))
    for q in questions:
        _ = rag_answer(
            q["question"],
            retrieval_mode="hybrid",
            use_rerank=True,
            use_query_transform=True,
            transform_strategy="expansion",
            verbose=False,
        )
    print("Done. Trace written to lab/logs/query_trace.jsonl")


if __name__ == "__main__":
    main()

