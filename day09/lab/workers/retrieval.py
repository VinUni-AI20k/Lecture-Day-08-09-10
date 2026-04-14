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

import hashlib
import os
from pathlib import Path
from typing import Callable, List, Optional

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3
COLLECTION_NAME = "day09_docs"
CHROMA_DB_PATH = str(Path(__file__).resolve().parents[1] / "chroma_db")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai").strip().lower()
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

_EMBED_FN_CACHE: Optional[Callable[[str], List[float]]] = None


def _build_local_embed_fn() -> Optional[Callable[[str], List[float]]]:
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")

        def embed(text: str) -> List[float]:
            return model.encode(text, normalize_embeddings=True).tolist()

        return embed
    except Exception:
        return None


def _build_openai_embed_fn() -> Optional[Callable[[str], List[float]]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        def embed(text: str) -> List[float]:
            resp = client.embeddings.create(
                input=text,
                model=OPENAI_EMBEDDING_MODEL,
            )
            return list(resp.data[0].embedding)

        return embed
    except Exception:
        return None


def _build_fallback_embed_fn() -> Callable[[str], List[float]]:
    import random

    def embed(text: str) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16)
        rng = random.Random(seed)
        return [rng.random() for _ in range(384)]

    print(
        "⚠️  WARNING: Using pseudo-random embeddings (test only). "
        "Install sentence-transformers or set OPENAI_API_KEY."
    )
    return embed


def _get_embedding_fn() -> Callable[[str], List[float]]:
    """
    Trả về embedding function.
    TODO Sprint 1: Implement dùng OpenAI hoặc Sentence Transformers.
    """
    global _EMBED_FN_CACHE
    if _EMBED_FN_CACHE is not None:
        return _EMBED_FN_CACHE

    provider = EMBEDDING_PROVIDER
    if provider not in {"openai", "local", "auto"}:
        provider = "openai"

    openai_fn = _build_openai_embed_fn
    local_fn = _build_local_embed_fn

    if provider == "openai":
        embed_fn = openai_fn() or local_fn() or _build_fallback_embed_fn()
    elif provider == "local":
        embed_fn = local_fn() or openai_fn() or _build_fallback_embed_fn()
    else:
        # auto: ưu tiên local nếu có model, fallback OpenAI
        embed_fn = local_fn() or openai_fn() or _build_fallback_embed_fn()

    _EMBED_FN_CACHE = embed_fn
    return embed_fn


def _get_collection():
    """
    Kết nối ChromaDB collection.
    TODO Sprint 2: Đảm bảo collection đã được build từ Step 3 trong README.
    """
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        # Auto-create nếu chưa có
        collection = client.get_or_create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    try:
        if collection.count() == 0:
            print("⚠️  Collection 'day09_docs' đang rỗng. Chạy index script trong README trước.")
    except Exception:
        pass

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
    query = (query or "").strip()
    if not query:
        return []

    try:
        top_k = max(1, int(top_k))
    except (TypeError, ValueError):
        top_k = DEFAULT_TOP_K

    embed = _get_embedding_fn()

    try:
        query_embedding = embed(query)
    except Exception as e:
        print(f"⚠️  Embedding failed: {e}")
        return []

    try:
        collection = _get_collection()
        n_docs = collection.count()
        if n_docs == 0:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, n_docs),
            include=["documents", "distances", "metadatas"]
        )

        docs = results.get("documents", [[]])
        dists = results.get("distances", [[]])
        metas = results.get("metadatas", [[]])

        docs_row = docs[0] if docs else []
        dists_row = dists[0] if dists else []
        metas_row = metas[0] if metas else []

        chunks = []
        for doc, dist, meta in zip(docs_row, dists_row, metas_row):
            if not doc:
                continue

            metadata = meta if isinstance(meta, dict) else {}
            raw_score = 1.0 - float(dist) if dist is not None else 0.0
            score = round(max(0.0, min(1.0, raw_score)), 4)

            chunks.append({
                "text": doc,
                "source": metadata.get("source", "unknown"),
                "score": score,
                "metadata": metadata,
            })
        return chunks

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        # Fallback: return empty (abstain)
        return []


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    top_k = state.get("retrieval_top_k", state.get("top_k", DEFAULT_TOP_K))

    try:
        top_k = max(1, int(top_k))
    except (TypeError, ValueError):
        top_k = DEFAULT_TOP_K

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

    if not str(task).strip():
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        worker_io["output"] = {
            "chunks_count": 0,
            "sources": [],
        }
        state["history"].append(f"[{WORKER_NAME}] empty task → skip retrieval")
    else:
        try:
            chunks = retrieve_dense(task, top_k=top_k)

            sources = sorted({c.get("source", "unknown") for c in chunks})

            state["retrieved_chunks"] = chunks
            state["retrieved_sources"] = sources

            worker_io["output"] = {
                "chunks_count": len(chunks),
                "sources": sources,
            }
            state["history"].append(
                f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
            )

        except Exception as e:
            worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
            state["retrieved_chunks"] = []
            state["retrieved_sources"] = []
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
