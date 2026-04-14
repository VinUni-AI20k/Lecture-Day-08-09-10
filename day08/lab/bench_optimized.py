"""Benchmark with optimized config: dense + rerank, top_k_select=10."""
import json, sys, os, time
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
from rag_answer import rag_answer

with open("data/test/grading_questions.json", encoding="utf-8") as f:
    questions = json.load(f)

CONFIG = {
    "retrieval_mode": "dense",
    "top_k_search": 20,
    "top_k_select": 10,
    "use_rerank": True,
}

print(f"Config: {CONFIG}")
print(f"Running {len(questions)} questions...\n")

log = []
for q in questions:
    qid = q["id"]
    query = q["question"]
    t0 = time.time()
    result = rag_answer(query, **CONFIG, verbose=False)
    elapsed = time.time() - t0
    
    answer = result["answer"]
    sources = result["sources"]
    print(f"[{qid}] ({elapsed:.1f}s) {answer[:120]}...")
    print(f"  Sources: {sources}\n")
    
    log.append({
        "id": qid,
        "question": query,
        "answer": answer,
        "sources": sources,
        "chunks_retrieved": len(result.get("chunks_used", [])),
        "retrieval_mode": CONFIG["retrieval_mode"],
        "use_rerank": CONFIG["use_rerank"],
        "top_k_search": CONFIG["top_k_search"],
        "top_k_select": CONFIG["top_k_select"],
        "timestamp": datetime.now().isoformat(),
    })

with open("logs/grading_run_v3.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)

print(f"\nSaved to logs/grading_run_v3.json")
