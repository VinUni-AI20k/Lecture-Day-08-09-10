# File: run_grading.py
import json
import os
from datetime import datetime
from pathlib import Path
from rag_answer import rag_answer

GRADING_FILE = Path("data/grading_questions.json")
LOG_FILE = Path("logs/grading_run.json")

def main():
    if not GRADING_FILE.exists():
        print("Chưa đến 17:00 hoặc bạn chưa tải file grading_questions.json vào thư mục data/ !")
        return

    # Tự động tạo thư mục logs nếu chưa có
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(GRADING_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    log = []
    print(f"Bắt đầu chạy {len(questions)} câu hỏi Grading...")
    
    for q in questions:
        print(f"Đang chạy câu: {q['id']}")
        try:
            # LƯU Ý KHI RUN THẬT: Đổi retrieval_mode thành "hybrid" hoặc cấu hình tốt nhất của nhóm bạn
            result = rag_answer(q["question"], retrieval_mode="dense", use_rerank=False, verbose=False)
            
            log.append({
                "id": q["id"],
                "question": q["question"],
                "answer": result["answer"],
                "sources": result["sources"],
                "chunks_retrieved": len(result["chunks_used"]),
                "retrieval_mode": result["config"]["retrieval_mode"],
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as e:
            print(f"Lỗi ở câu {q['id']}: {e}")
            log.append({
                "id": q["id"],
                "question": q["question"],
                "answer": f"PIPELINE_ERROR: {e}",
                "sources": [],
                "chunks_retrieved": 0,
                "retrieval_mode": "error",
                "timestamp": datetime.now().isoformat(),
            })

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    
    print(f"Đã chạy xong! File log được lưu tại: {LOG_FILE}")
    print("NỘP FILE NÀY TRƯỚC 18:00 NHÉ!")

if __name__ == "__main__":
    main()