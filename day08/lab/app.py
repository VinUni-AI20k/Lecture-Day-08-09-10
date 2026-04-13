"""
app.py — FastAPI Backend cho RAG Pipeline (Day 08 Lab)
=======================================================
Bọc lõi (index.py, rag_answer.py, eval.py) thành REST API.
KHÔNG thay đổi bất kỳ logic nào của core.

Cài đặt thêm:
    pip install fastapi uvicorn

Chạy:
    uvicorn app:app --reload --port 8000

Endpoints:
    GET  /api/status              — Kiểm tra index đã được build chưa
    POST /api/index/build         — Build hoặc rebuild index
    POST /api/ask                 — Hỏi pipeline RAG
    POST /api/compare             — So sánh dense vs hybrid cho 1 query
    POST /api/eval/run            — Chạy scorecard cho N câu hỏi test
    GET  /api/questions           — Lấy danh sách test questions
"""

import json
import traceback
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =============================================================================
# KHỞI TẠO APP
# =============================================================================

app = FastAPI(
    title="RAG Lab API — Day 08",
    description="REST API bọc RAG Pipeline: index.py + rag_answer.py + eval.py",
    version="1.0.0",
)

# CORS cho phép React dev server (localhost:3000 hoặc 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"
TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"

# State cho background indexing
_index_status = {"state": "idle", "message": "", "started_at": None, "finished_at": None}


# =============================================================================
# SCHEMAS
# =============================================================================

class AskRequest(BaseModel):
    query: str
    retrieval_mode: str = "dense"       # "dense" | "hybrid" | "sparse"
    top_k_search: int = 10
    top_k_select: int = 3
    use_rerank: bool = False
    verbose: bool = False

class CompareRequest(BaseModel):
    query: str
    top_k_search: int = 10
    top_k_select: int = 3

class EvalRequest(BaseModel):
    config_label: str = "baseline_dense"  # "baseline_dense" | "variant_hybrid"
    max_questions: Optional[int] = None    # None = tất cả 10 câu


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/api/status")
def get_status():
    """
    Kiểm tra trạng thái hệ thống:
    - Index đã được build chưa?
    - Có bao nhiêu chunks?
    - Trạng thái indexing hiện tại
    """
    status = {
        "index_exists": False,
        "chunk_count": 0,
        "index_status": _index_status.copy(),
        "chroma_db_path": str(CHROMA_DB_DIR),
        "timestamp": datetime.now().isoformat(),
    }

    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")
        status["index_exists"] = True
        status["chunk_count"] = collection.count()
    except Exception:
        status["index_exists"] = False

    return status


@app.post("/api/index/build")
async def build_index_endpoint(background_tasks: BackgroundTasks):
    """
    Trigger build index (chạy background để không block).
    Gọi đúng build_index() từ index.py — không thay đổi logic.
    """
    global _index_status

    if _index_status["state"] == "running":
        return {"message": "Indexing đang chạy, vui lòng chờ", "status": _index_status}

    _index_status = {
        "state": "running",
        "message": "Đang build index...",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
    }

    def _run_index():
        global _index_status
        try:
            from index import build_index
            build_index()
            _index_status["state"] = "done"
            _index_status["message"] = "Index build thành công!"
            _index_status["finished_at"] = datetime.now().isoformat()
        except Exception as e:
            _index_status["state"] = "error"
            _index_status["message"] = str(e)
            _index_status["finished_at"] = datetime.now().isoformat()

    background_tasks.add_task(_run_index)
    return {"message": "Bắt đầu build index...", "status": _index_status}


@app.post("/api/ask")
def ask(req: AskRequest):
    """
    Hỏi RAG pipeline.
    Gọi đúng rag_answer() từ rag_answer.py — không thay đổi logic.

    Response:
        query, answer, sources, chunks_used, config, latency_ms
    """
    import time
    t0 = time.time()

    try:
        from rag_answer import rag_answer
        result = rag_answer(
            query=req.query,
            retrieval_mode=req.retrieval_mode,
            top_k_search=req.top_k_search,
            top_k_select=req.top_k_select,
            use_rerank=req.use_rerank,
            verbose=req.verbose,
        )
        latency_ms = int((time.time() - t0) * 1000)

        # Serialize chunks (bỏ embedding vector để nhẹ response)
        chunks_serialized = []
        for c in result.get("chunks_used", []):
            chunks_serialized.append({
                "text": c.get("text", "")[:500],  # Truncate dài
                "source": c.get("metadata", {}).get("source", ""),
                "section": c.get("metadata", {}).get("section", ""),
                "effective_date": c.get("metadata", {}).get("effective_date", ""),
                "department": c.get("metadata", {}).get("department", ""),
                "score": round(c.get("score", 0), 4),
            })

        return {
            "query": result["query"],
            "answer": result["answer"],
            "sources": result["sources"],
            "chunks": chunks_serialized,
            "config": result["config"],
            "latency_ms": latency_ms,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")


@app.post("/api/compare")
def compare(req: CompareRequest):
    """
    So sánh Dense vs Hybrid cho cùng 1 query.
    Trả về kết quả của cả hai strategies để hiển thị A/B.
    """
    import time
    from rag_answer import rag_answer

    results = {}
    for mode in ["dense", "hybrid"]:
        t0 = time.time()
        try:
            r = rag_answer(
                query=req.query,
                retrieval_mode=mode,
                top_k_search=req.top_k_search,
                top_k_select=req.top_k_select,
                use_rerank=False,
                verbose=False,
            )
            results[mode] = {
                "answer": r["answer"],
                "sources": r["sources"],
                "chunks": [
                    {
                        "text": c.get("text", "")[:400],
                        "source": c.get("metadata", {}).get("source", ""),
                        "section": c.get("metadata", {}).get("section", ""),
                        "score": round(c.get("score", 0), 4),
                    }
                    for c in r["chunks_used"]
                ],
                "latency_ms": int((time.time() - t0) * 1000),
            }
        except Exception as e:
            results[mode] = {"error": str(e), "latency_ms": 0}

    return {
        "query": req.query,
        "dense": results.get("dense", {}),
        "hybrid": results.get("hybrid", {}),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/eval/run")
def run_eval(req: EvalRequest):
    """
    Chạy scorecard evaluation.
    Gọi đúng run_scorecard() từ eval.py — không thay đổi logic.
    """
    from eval import run_scorecard, BASELINE_CONFIG, VARIANT_CONFIG

    config_map = {
        "baseline_dense": BASELINE_CONFIG,
        "variant_hybrid": VARIANT_CONFIG,
    }

    config = config_map.get(req.config_label)
    if not config:
        raise HTTPException(status_code=400, detail=f"config_label không hợp lệ: {req.config_label}")

    try:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)

        if req.max_questions:
            test_questions = test_questions[:req.max_questions]

        results = run_scorecard(
            config=config,
            test_questions=test_questions,
            verbose=False,
        )

        # Tính summary
        metrics = ["faithfulness", "relevance", "context_recall", "completeness"]
        summary = {}
        for m in metrics:
            scores = [r[m] for r in results if r.get(m) is not None]
            summary[m] = round(sum(scores) / len(scores), 2) if scores else None

        return {
            "config": req.config_label,
            "results": results,
            "summary": summary,
            "total_questions": len(results),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


@app.get("/api/questions")
def get_questions():
    """Lấy danh sách 10 test questions."""
    try:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            questions = json.load(f)
        return {"questions": questions, "total": len(questions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    return {
        "name": "RAG Lab API — Day 08",
        "docs": "/docs",
        "endpoints": ["/api/status", "/api/index/build", "/api/ask", "/api/compare", "/api/eval/run", "/api/questions"],
    }
