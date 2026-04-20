"""
run_eval.py — Tạo grading_run.json cho nộp bài
===============================================
Script này tạo logs/grading_run.json từ grading_questions.json (hoặc test_questions.json nếu chưa có grading).

Chạy: python run_eval.py
"""

import json
from pathlib import Path
from datetime import datetime
from rag_answer import rag_answer  # Không dùng để tránh API call

# Cấu hình
GRADING_QUESTIONS_PATH = Path(__file__).parent / "data" / "grading_questions.json"
TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"
LOGS_DIR = Path(__file__).parent / "logs"

# Sử dụng test_questions.json nếu chưa có grading_questions.json
QUESTIONS_PATH = GRADING_QUESTIONS_PATH if GRADING_QUESTIONS_PATH.exists() else TEST_QUESTIONS_PATH

def main():
    print("Tạo grading_run.json...")

    # Load questions
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    log = []
    for q in questions:
        print(f"Chạy: {q['id']} - {q['question'][:50]}...")

        # Mock result để tránh gọi API (cho demo)
        # Trong thực tế, uncomment dòng dưới
        result = rag_answer(q["question"], retrieval_mode="hybrid", verbose=False)

        # Mock data
        mock_answer = "Mock answer for demo"  # Thay bằng result["answer"]
        mock_sources = ["mock_source.pdf"]  # Thay bằng result["sources"]
        mock_chunks = 3  # Thay bằng len(result["chunks_used"])

        log_entry = {
            "id": q["id"],
            "question": q["question"],
            "answer": mock_answer,
            "sources": mock_sources,
            "chunks_retrieved": mock_chunks,
            "retrieval_mode": "hybrid",
            "timestamp": datetime.now().isoformat(),
        }
        log.append(log_entry)

    # Save log
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "grading_run.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"Đã tạo: {log_path}")
    print(f"Tổng: {len(log)} câu hỏi")

if __name__ == "__main__":
    main()