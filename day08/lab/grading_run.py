import json
from datetime import datetime

from rag_answer import rag_answer

# Load file grading mới add
with open("day08/lab/data/grading.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

log = []
for q in questions:
    # Sử dụng cấu hình Hybrid (Variant) vì cho kết quả ổn định hơn
    result = rag_answer(q["question"], retrieval_mode="hybrid", verbose=False)
    log.append(
        {
            "id": q["id"],
            "question": q["question"],
            "answer": result["answer"],
            "sources": result["sources"],
            "chunks_retrieved": len(result["chunks_used"]),
            "retrieval_mode": "hybrid",
            "timestamp": datetime.now().isoformat(),
        }
    )

# Lưu log đúng format yêu cầu
import os

os.makedirs("day08/lab/logs", exist_ok=True)
with open("day08/lab/logs/grading_run.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)

print("Đã tạo logs/grading_run.json thành công!")
