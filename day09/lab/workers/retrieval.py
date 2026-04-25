"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Input (từ AgentState):
    - task: câu hỏi cần retrieve
    - (optional) retrieved_chunks nếu đã có từ trước

Output (vào AgentState):
    - retrieved_chunks: list of {"text", "source", "score", "metadata"}
    - retrieved_sources: list of source filenames
    - worker_io_log: log input/output của worker này

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os
import sys
import re
import time
import math
from collections import Counter
from functools import lru_cache
from typing import Callable, Optional
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3
DEFAULT_SCORE_THRESHOLD = 0.15

_EMBEDDING_FN: Optional[Callable[[str], list]] = None
_EMBEDDING_BACKEND = "uninitialized"


def _normalize_query(query: str) -> str:
    q = (query or "").strip().lower()
    q = re.sub(r"\s+", " ", q)
    replacements = {
        "p1": "ticket p1 escalation",
        "hoàn tiền": "refund policy",
        "cấp quyền": "access permission",
        "khẩn cấp": "emergency",
    }
    for src, dst in replacements.items():
        if src in q and dst not in q:
            q = f"{q} {dst}"
    return q


def _suggest_top_k(task: str, default_top_k: int = DEFAULT_TOP_K) -> int:
    t = (task or "").lower()
    hard_signals = ["đồng thời", "quy trình", "escalation", "contractor", "multi", "và"]
    if any(sig in t for sig in hard_signals):
        return max(default_top_k, 5)
    return default_top_k


def _tokenize(text: str) -> list:
    return re.findall(r"\w+", (text or "").lower())


def _lexical_score(query: str, text: str) -> float:
    q_tokens = _tokenize(query)
    d_tokens = _tokenize(text)
    if not q_tokens or not d_tokens:
        return 0.0

    q_count = Counter(q_tokens)
    d_count = Counter(d_tokens)
    overlap = 0.0
    for token, qf in q_count.items():
        if token in d_count:
            overlap += min(qf, d_count[token]) * (1.0 + 1.0 / (1 + len(token)))

    norm = math.sqrt(sum(v * v for v in q_count.values())) * math.sqrt(sum(v * v for v in d_count.values()))
    if norm == 0:
        return 0.0
    return round(min(1.0, overlap / norm), 4)


def _rerank_overlap(query: str, chunks: list, top_k: int) -> list:
    scored = []
    for c in chunks:
        dense = float(c.get("score", 0.0))
        lex = _lexical_score(query, c.get("text", ""))
        item = dict(c)
        item["lexical_score"] = lex
        item["rerank_score"] = round(0.75 * dense + 0.25 * lex, 4)
        scored.append(item)

    scored.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
    return scored[:top_k]


@lru_cache(maxsize=1)
def _load_docs_for_lexical() -> list:
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "docs")
    docs = []
    if not os.path.isdir(docs_dir):
        return docs
    for fname in sorted(os.listdir(docs_dir)):
        path = os.path.join(docs_dir, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()
            if text:
                docs.append({"source": fname, "text": text})
        except Exception:
            continue
    return docs


def _retrieve_lexical(query: str, top_k: int) -> list:
    docs = _load_docs_for_lexical()
    scored = []
    for d in docs:
        lex = _lexical_score(query, d["text"])
        if lex <= 0:
            continue
        scored.append({
            "text": d["text"],
            "source": d["source"],
            "score": round(0.4 + 0.6 * lex, 4),
            "metadata": {"retrieval": "lexical"},
            "retrieval_method": "lexical",
            "lexical_score": lex,
        })
    scored.sort(key=lambda x: x.get("lexical_score", 0.0), reverse=True)
    return scored[:max(top_k, 5)]


def _ensure_collection_seeded(collection) -> None:
    try:
        count = collection.count()
    except Exception:
        count = 0
    if count > 0:
        return

    docs = _load_docs_for_lexical()
    if not docs:
        return

    ids = []
    documents = []
    metadatas = []
    for i, d in enumerate(docs):
        ids.append(f"seed-{i}")
        documents.append(d["text"])
        metadatas.append({"source": d["source"], "seeded": True})

    try:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
    except Exception:
        pass


def _get_embedding_fn():
    """
    Trả về embedding function.
    TODO Sprint 1: Implement dùng OpenAI hoặc Sentence Transformers.
    """
    global _EMBEDDING_FN, _EMBEDDING_BACKEND
    if _EMBEDDING_FN is not None:
        return _EMBEDDING_FN

    # Option A (default): OpenAI embeddings
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        client = OpenAI(api_key=api_key)
        model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

        def embed(text: str) -> list:
            resp = client.embeddings.create(input=text, model=model_name)
            return resp.data[0].embedding

        _EMBEDDING_FN = embed
        _EMBEDDING_BACKEND = f"openai/{model_name}"
        return _EMBEDDING_FN
    except Exception:
        pass

    # Option B: local fallback only when explicitly allowed.
    if os.getenv("ALLOW_LOCAL_EMBED_FALLBACK", "0") == "1":
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")

            def embed(text: str) -> list:
                return model.encode([text])[0].tolist()

            _EMBEDDING_FN = embed
            _EMBEDDING_BACKEND = "sentence-transformers/all-MiniLM-L6-v2"
            return _EMBEDDING_FN
        except Exception:
            pass

    # Fallback debug-only nếu bật cờ môi trường.
    if os.getenv("ALLOW_RANDOM_EMBEDDING_DEBUG", "0") == "1":
        import random

        def embed(text: str) -> list:
            return [random.random() for _ in range(384)]

        _EMBEDDING_FN = embed
        _EMBEDDING_BACKEND = "debug/random"
        return _EMBEDDING_FN

    raise RuntimeError(
        "OpenAI embedding is required. Set OPENAI_API_KEY (and optional OPENAI_EMBEDDING_MODEL). "
        "For local fallback, set ALLOW_LOCAL_EMBED_FALLBACK=1 and install sentence-transformers."
    )


def _get_collection():
    """
    Kết nối ChromaDB collection.
    TODO Sprint 2: Đảm bảo collection đã được build từ Step 3 trong README.
    """
    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    try:
        collection = client.get_collection("day09_docs")
    except Exception:
        # Auto-create nếu chưa có
        collection = client.get_or_create_collection(
            "day09_docs",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"⚠️  Collection 'day09_docs' chưa có data. Chạy index script trong README trước.")
    return collection


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: embed query → query ChromaDB → trả về top_k chunks.

    TODO Sprint 2: Implement phần này.
    - Dùng _get_embedding_fn() để embed query
    - Query collection với n_results=top_k
    - Format result thành list of dict

    Returns:
        list of {"text": str, "source": str, "score": float, "metadata": dict}
    """
    # TODO: Implement dense retrieval
    embed = _get_embedding_fn()
    normalized_query = _normalize_query(query)
    query_embedding = embed(normalized_query)
    score_threshold = float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", str(DEFAULT_SCORE_THRESHOLD)))

    try:
        collection = _get_collection()
        _ensure_collection_seeded(collection)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(top_k, 8),
            include=["documents", "distances", "metadatas"]
        )

        docs = (results.get("documents") or [[]])[0]
        dists = (results.get("distances") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]

        chunks = []
        for doc, dist, meta in zip(docs, dists, metas):
            score = round(max(0.0, 1 - float(dist)), 4)
            if score < score_threshold:
                continue
            chunks.append({
                "text": doc,
                "source": (meta or {}).get("source", "unknown"),
                "score": score,
                "metadata": meta or {},
                "retrieval_method": "dense",
            })
        return chunks

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        # Fallback: return empty (abstain)
        return []


def retrieve_hybrid(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    normalized_query = _normalize_query(query)
    dense = retrieve_dense(normalized_query, top_k=max(top_k, 8))
    lexical = _retrieve_lexical(normalized_query, top_k=max(top_k, 8))

    by_key = {}
    for item in dense + lexical:
        key = (item.get("source", "unknown"), item.get("text", ""))
        if key not in by_key:
            by_key[key] = dict(item)
            continue

        prev = by_key[key]
        if float(item.get("score", 0.0)) > float(prev.get("score", 0.0)):
            prev["score"] = item.get("score", 0.0)
        if item.get("retrieval_method") != prev.get("retrieval_method"):
            prev["retrieval_method"] = "hybrid"

    merged = list(by_key.values())
    reranked = _rerank_overlap(normalized_query, merged, top_k=max(top_k, 5))
    return reranked[:top_k]


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    top_k = state.get("retrieval_top_k") or _suggest_top_k(task, DEFAULT_TOP_K)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])

    state["workers_called"].append(WORKER_NAME)

    # Log worker IO (theo contract)
    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        start = time.time()
        chunks = retrieve_hybrid(task, top_k=top_k)
        retrieval_latency_ms = int((time.time() - start) * 1000)

        sources = []
        seen = set()
        for c in chunks:
            src = c.get("source", "unknown")
            if src not in seen:
                sources.append(src)
                seen.add(src)

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources
        state["retrieval_diagnostics"] = {
            "embedding_backend": _EMBEDDING_BACKEND,
            "query_original": task,
            "query_normalized": _normalize_query(task),
            "top_k": top_k,
            "score_threshold": float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", str(DEFAULT_SCORE_THRESHOLD))),
            "chunks_count": len(chunks),
            "score_max": max((float(c.get("score", 0.0)) for c in chunks), default=0.0),
            "score_min": min((float(c.get("score", 0.0)) for c in chunks), default=0.0),
            "retrieval_methods": sorted(list({c.get("retrieval_method", "unknown") for c in chunks})),
            "retrieval_latency_ms": retrieval_latency_ms,
            "insufficient_evidence": len(chunks) == 0,
        }

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
            "embedding_backend": _EMBEDDING_BACKEND,
        }
        if chunks:
            state["history"].append(
                f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
            )
        else:
            state["history"].append(
                f"[{WORKER_NAME}] insufficient evidence (0 chunks above threshold)"
            )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["retrieval_diagnostics"] = {
            "embedding_backend": _EMBEDDING_BACKEND,
            "query_original": task,
            "query_normalized": _normalize_query(task),
            "top_k": top_k,
            "error": str(e),
            "insufficient_evidence": True,
        }
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    # Ghi worker IO vào state để trace
    state.setdefault("worker_io_logs", []).append(worker_io)

    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Retrieval Worker — Standalone Test")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for c in chunks[:2]:
            print(f"    [{c['score']:.3f}] {c['source']}: {c['text'][:80]}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\n✅ retrieval_worker test done.")
