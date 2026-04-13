"""
run_grading.py — Script tạo logs/grading_run.json
===================================================
Chạy khi grading_questions.json được public (17:00).
Usage: python run_grading.py
"""

import json
from datetime import datetime
from pathlib import Path
from rag_answer import rag_answer

# Cấu hình — dùng cấu hình tốt nhất của nhóm
RETRIEVAL_MODE = "dense"  # Đổi thành "hybrid" nếu hybrid hoạt động tốt hơn
USE_RERANK = False

def main():
    # Thử load grading_questions.json trước
    grading_path = Path(__file__).parent / "data" / "grading_questions.json"
    
    if not grading_path.exists():
        print(f"❌ Chưa có file: {grading_path}")
        print("   File này sẽ được public lúc 17:00.")
        print("   Khi có file, copy vào data/ và chạy lại script này.")
        return
    
    with open(grading_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    
    print(f"📋 Loaded {len(questions)} grading questions")
    print(f"⚙️  Config: retrieval_mode={RETRIEVAL_MODE}, use_rerank={USE_RERANK}")
    print("=" * 60)
    
    log = []
    for i, q in enumerate(questions, 1):
        qid = q.get("id", f"gq{i:02d}")
        question = q["question"]
        print(f"\n[{qid}] {question}")
        
        try:
            result = rag_answer(
                question, 
                retrieval_mode=RETRIEVAL_MODE,
                use_rerank=USE_RERANK,
                verbose=False
            )
            entry = {
                "id": qid,
                "question": question,
                "answer": result["answer"],
                "sources": result["sources"],
                "chunks_retrieved": len(result["chunks_used"]),
                "retrieval_mode": result["config"]["retrieval_mode"],
                "timestamp": datetime.now().isoformat(),
            }
            print(f"   ✅ Answer: {result['answer'][:100]}...")
            print(f"   Sources: {result['sources']}")
        except Exception as e:
            entry = {
                "id": qid,
                "question": question,
                "answer": f"PIPELINE_ERROR: {str(e)}",
                "sources": [],
                "chunks_retrieved": 0,
                "retrieval_mode": RETRIEVAL_MODE,
                "timestamp": datetime.now().isoformat(),
            }
            print(f"   ❌ Error: {e}")
        
        log.append(entry)
    
    # Lưu log
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    output_path = logs_dir / "grading_run.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"✅ Log saved to: {output_path}")
    print(f"   Total questions: {len(log)}")
    print(f"   Errors: {sum(1 for e in log if 'PIPELINE_ERROR' in e['answer'])}")

if __name__ == "__main__":
    main()
