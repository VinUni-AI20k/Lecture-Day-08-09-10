"""
FastAPI bridge cho UI Next.js: POST /api/rag gọi rag_answer(trace=True).

Chạy từ thư mục lab:
  pip install -r requirements.txt
  uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

load_dotenv()

from rag_answer import rag_answer, rag_answer_stream  # noqa: E402
from run_telemetry import RunTelemetry, telemetry_ctx  # noqa: E402

LAB_DIR = Path(__file__).resolve().parent
LOGS_DIR = LAB_DIR / "logs"
ACCESS_LOG = LOGS_DIR / "api_access.log"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger("api.rag")
access_logger = logging.getLogger("api.access")

_file_handler: Optional[logging.Handler] = None


def _setup_access_file_logging() -> None:
    global _file_handler
    if _file_handler is not None:
        return
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(ACCESS_LOG, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s"))
    access_logger.addHandler(fh)
    access_logger.setLevel(logging.INFO)
    _file_handler = fh


_setup_access_file_logging()

_DEFAULT_CORS = (
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:3001,http://127.0.0.1:3001"
)
_origins = [
    o.strip()
    for o in os.getenv("RAG_CORS_ORIGINS", _DEFAULT_CORS).split(",")
    if o.strip()
]

app = FastAPI(title="Day08 RAG Lab API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_and_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        access_logger.info(
            "%s %s status=error duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            duration_ms,
            rid,
        )
        raise
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    access_logger.info(
        "%s %s status=%s duration_ms=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        rid,
    )
    response.headers["X-Request-ID"] = rid
    return response


class RagRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    retrieval_mode: Literal["dense", "sparse", "hybrid"] = "dense"
    top_k_search: Optional[int] = Field(default=None, ge=1, le=48)
    top_k_select: Optional[int] = Field(default=None, ge=1, le=12)
    use_rerank: bool = False


@app.get("/api/health")
def health() -> Dict[str, Any]:
    """Kiểm tra API và (nếu được) số document trong Chroma."""
    out: Dict[str, Any] = {"ok": True, "service": "day08-rag-api"}
    try:
        import chromadb
        from rag_answer import CHROMA_COLLECTION, CHROMA_DB_DIR

        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        col = client.get_collection(CHROMA_COLLECTION)
        out["chroma_collection"] = CHROMA_COLLECTION
        out["chroma_count"] = col.count()
    except Exception as e:
        out["chroma_error"] = type(e).__name__
    return out


@app.post("/api/rag")
def post_rag(
    request: Request,
    body: RagRequest,
    x_request_id: Optional[str] = Header(default=None, alias="X-Request-ID"),
) -> Dict[str, Any]:
    rid = x_request_id or getattr(request.state, "request_id", None) or str(uuid.uuid4())
    qprev = body.query[:200] + "…" if len(body.query) > 200 else body.query

    tel = RunTelemetry("api_rag", label=body.retrieval_mode)
    tok = telemetry_ctx.set(tel)
    out: Optional[Dict[str, Any]] = None
    err: Optional[BaseException] = None
    try:
        kw: Dict[str, Any] = {
            "query": body.query,
            "retrieval_mode": body.retrieval_mode,
            "use_rerank": body.use_rerank,
            "verbose": False,
            "trace": True,
        }
        if body.top_k_search is not None:
            kw["top_k_search"] = body.top_k_search
        if body.top_k_select is not None:
            kw["top_k_select"] = body.top_k_select
        out = rag_answer(**kw)
    except Exception as e:
        err = e
        log.exception("rag_answer failed request_id=%s", rid)
    finally:
        entry = tel.finish(
            {
                "request_id": rid,
                "client": "fastapi",
                "query_preview": qprev,
                "retrieval_mode": body.retrieval_mode,
                "ok": err is None,
                "error": type(err).__name__ if err else None,
            }
        )
        telemetry_ctx.reset(tok)

    if err is not None:
        raise HTTPException(status_code=500, detail="RAG pipeline lỗi — xem log server.")

    assert out is not None
    telemetry = {
        "run_id": entry["run_id"],
        "duration_ms": entry["duration_ms"],
        "cost_usd": entry["cost_usd"],
        "usage": entry["usage"],
    }
    return {
        "answer": out.get("answer", ""),
        "sources": out.get("sources", []),
        "chunks_used": out.get("chunks_used", []),
        "query": out.get("query", body.query),
        "config": out.get("config", {}),
        "pipeline_steps": out.get("pipeline_steps", []),
        "telemetry": telemetry,
        "request_id": rid,
    }


# ---------------------------------------------------------------------------
# SSE streaming abort registry
# ---------------------------------------------------------------------------
_abort_registry: Dict[str, threading.Event] = {}
_abort_lock = threading.Lock()


def _register_abort(rid: str) -> threading.Event:
    ev = threading.Event()
    with _abort_lock:
        _abort_registry[rid] = ev
    return ev


def _unregister_abort(rid: str) -> None:
    with _abort_lock:
        _abort_registry.pop(rid, None)


class AbortRequest(BaseModel):
    request_id: str


@app.post("/api/rag/abort")
def abort_rag(body: AbortRequest) -> Dict[str, Any]:
    """Signal an in-flight streaming request to stop."""
    with _abort_lock:
        ev = _abort_registry.get(body.request_id)
    if ev is not None:
        ev.set()
        return {"ok": True, "request_id": body.request_id}
    return {"ok": False, "detail": "request_id not found or already complete"}


@app.post("/api/rag/stream")
def post_rag_stream(
    request: Request,
    body: RagRequest,
    x_request_id: Optional[str] = Header(default=None, alias="X-Request-ID"),
):
    """Server-Sent Events streaming endpoint for RAG pipeline."""
    rid = x_request_id or getattr(request.state, "request_id", None) or str(uuid.uuid4())
    abort_ev = _register_abort(rid)

    def generate() -> Iterator[str]:
        try:
            kw: Dict[str, Any] = {
                "query": body.query,
                "retrieval_mode": body.retrieval_mode,
                "use_rerank": body.use_rerank,
                "request_id": rid,
                "abort_event": abort_ev,
            }
            if body.top_k_search is not None:
                kw["top_k_search"] = body.top_k_search
            if body.top_k_select is not None:
                kw["top_k_select"] = body.top_k_select

            for item in rag_answer_stream(**kw):
                event_type = item.get("event", "message")
                data_str = json.dumps(item.get("data", {}), ensure_ascii=False)
                yield f"event: {event_type}\ndata: {data_str}\n\n"
        except Exception as exc:
            log.exception("rag_answer_stream failed request_id=%s", rid)
            err_data = json.dumps({"message": str(exc)}, ensure_ascii=False)
            yield f"event: error\ndata: {err_data}\n\n"
        finally:
            _unregister_abort(rid)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "X-Request-ID": rid,
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
