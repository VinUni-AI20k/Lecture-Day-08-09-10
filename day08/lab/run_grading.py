import json
from datetime import datetime
from rag_answer import rag_answer

with open("data/grading_questions.json") as f:
    questions = json.load(f)

log = []
for q in questions:
    result = rag_answer(q["question"], retrieval_mode="hybrid", verbose=False)
    log.append({
        "id": q["id"],
        "question": q["question"],
        "answer": result["answer"],
        "sources": result["sources"],
        "chunks_retrieved": len(result["chunks_used"]),
        "retrieval_mode": result["config"]["retrieval_mode"],
        "timestamp": datetime.now().isoformat(),
    })

with open("logs/grading_run.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
