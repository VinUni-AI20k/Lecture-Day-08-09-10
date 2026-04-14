"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Input (từ AgentState):
    - task: câu hỏi cần retrieve
    - (optional) top_k: số chunks cần retrieve (default: 3)

Output (vào AgentState):
    - retrieved_chunks: list of {"text", "source", "score", "metadata"}
    - retrieved_sources: list of source filenames
    - worker_io_logs: log input/output của worker này

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3


def _get_embedding_fn():
    """
    Trả về embedding function phù hợp với môi trường.
    Ưu tiên SentenceTransformers (offline), fallback sang OpenAI nếu có key.
    """
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        def st_embed(texts):
            return _model.encode(texts).tolist()
        # Wrap để chromadb gọi được
        from chromadb.utils.embedding_functions import EmbeddingFunction
        class STEmbeddingFunction(EmbeddingFunction):
            def __call__(self, input):
                return _model.encode(input).tolist()
        return STEmbeddingFunction()
    except ImportError:
        pass

    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_key,
            model_name="text-embedding-3-small"
        )

    raise RuntimeError("Không có embedding backend. Cài sentence-transformers hoặc set OPENAI_API_KEY.")


def _get_collection():
    """
    Kết nối ChromaDB collection.
    Dùng SentenceTransformers nếu không có OPENAI_API_KEY.
    """
    client = chromadb.PersistentClient(path="./chroma_db")
    ef = _get_embedding_fn()
    try:
        collection = client.get_collection(
            name="day09_docs",
            embedding_function=ef
        )
    except Exception:
        collection = client.get_or_create_collection(
            name="day09_docs",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"}
        )
        print("⚠️  Collection 'day09_docs' chưa có data. Chạy build_index.py trước.")
    return collection


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: query ChromaDB → trả về top_k chunks.

    Returns:
        list of {"text": str, "source": str, "score": float, "metadata": dict}
    """
    try:
        collection = _get_collection()
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )

        chunks = []
        if results["documents"] and results["documents"][0]:
            for doc, dist, meta in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0]
            ):
                chunks.append({
                    "text": doc,
                    "source": meta.get("source", "unknown") if meta else "unknown",
                    "score": round(1 - dist, 4),  # cosine similarity
                    "metadata": meta or {},
                })
        return chunks

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
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
    top_k = state.get("retrieval_top_k", DEFAULT_TOP_K)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("worker_io_logs", [])

    state["workers_called"].append(WORKER_NAME)

    # Log worker IO (theo contract)
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
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {len(sources)} sources"
        )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    # Ghi worker IO vào state để trace
    state["worker_io_logs"].append(worker_io)

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
