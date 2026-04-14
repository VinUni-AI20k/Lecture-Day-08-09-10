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
from pathlib import Path

from dotenv import load_dotenv
# Đọc .env từ thư mục cha (day09/lab/) dù chạy từ đâu
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")



# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3
_EMBED_FN = None


def _get_embedding_fn():
    """Trả về embedding function (Sentence Transformers → OpenAI → random fallback)."""
    global _EMBED_FN
    if _EMBED_FN is not None:
        return _EMBED_FN

    # Option A: Sentence Transformers (offline, không cần API key)
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")

        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()

        _EMBED_FN = embed
        return _EMBED_FN
    except ImportError:
        pass

    # Option B: OpenAI (cần API key)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        def embed(text: str) -> list:
            resp = client.embeddings.create(input=text, model="text-embedding-3-small")
            return resp.data[0].embedding

        _EMBED_FN = embed
        return _EMBED_FN
    except ImportError:
        pass

    # Fallback: random embeddings cho test (KHÔNG dùng production)
    import random

    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]

    print(
        "⚠️  WARNING: Using random embeddings (test only). Install sentence-transformers."
    )
    _EMBED_FN = embed
    return _EMBED_FN


def _resolve_chroma_path() -> str:
    """Resolve ChromaDB path dựa vào env hoặc fallback trong day09/lab/."""
    chroma_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    if not os.path.isabs(chroma_path):
        rel = chroma_path.lstrip("./")
        chroma_path = str(Path(__file__).resolve().parent.parent / rel)
    return chroma_path


def _get_collection():
    """Kết nối ChromaDB collection (auto-create nếu chưa có)."""
    import chromadb

    chroma_path = _resolve_chroma_path()
    collection_name = os.getenv("CHROMA_COLLECTION", "day09_docs")

    client = chromadb.PersistentClient(path=chroma_path)
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        # Auto-create nếu chưa có
        collection = client.get_or_create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"⚠️  Collection '{collection_name}' chưa có data. Chạy index script trong README trước.")
    return collection


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """Dense retrieval: embed query → query ChromaDB → trả về top_k chunks."""
    if not query or not query.strip():
        return []

    embed = _get_embedding_fn()
    query_embedding = embed(query)

    try:
        collection = _get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"],
        )

        documents = (results.get("documents") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]

        chunks = []
        for doc, dist, meta in zip(documents, distances, metadatas):
            similarity = max(0.0, min(1.0, 1 - float(dist)))
            chunks.append(
                {
                    "text": doc,
                    "source": (meta or {}).get("source", "unknown"),
                    "score": round(similarity, 4),
                    "metadata": meta or {},
                }
            )
        return chunks

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        return []


def run(state: dict) -> dict:
    """Worker entry point — gọi từ graph.py."""
    task = state.get("task", "")
    top_k = state.get("retrieval_top_k", DEFAULT_TOP_K)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])

    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_dense(task, top_k=top_k)
        sources = list({c["source"] for c in chunks})

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
