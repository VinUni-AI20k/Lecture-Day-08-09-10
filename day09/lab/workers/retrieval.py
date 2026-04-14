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
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import vertexai
from vertexai.language_models import TextEmbeddingModel

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "day09_docs")

# BM25 singleton — built once from ChromaDB corpus, reused across calls
_bm25_cache = None


def _init_vertex():
    """Initialize Vertex AI once, resolving credentials path relative to lab root."""
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds:
        lab_root = Path(__file__).parent.parent
        creds_path = lab_root / creds
        if creds_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)
    vertexai.init(
        project=os.getenv("VERTEX_PROJECT", "vinai053"),
        location=os.getenv("VERTEX_LOCATION", "us-central1"),
    )


def _get_embedding_fn():
    """
    Returns Vertex AI text-multilingual-embedding-002 embed function.
    Falls back to OpenAI text-embedding-3-small if Vertex unavailable.
    """
    try:
        _init_vertex()
        model = TextEmbeddingModel.from_pretrained(
            os.getenv("VERTEX_EMBEDDING_MODEL", "text-multilingual-embedding-002")
        )
        def embed(text: str) -> list:
            return model.get_embeddings([text])[0].values
        return embed
    except Exception as e:
        print(f"⚠️  Vertex AI unavailable ({e}), falling back to OpenAI...")

    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    def embed(text: str) -> list:
        resp = client.embeddings.create(input=text, model="text-embedding-3-small")
        return resp.data[0].embedding
    return embed


def _get_collection():
    """Kết nối ChromaDB collection day09_docs."""
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception:
        collection = client.get_or_create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
        print(f"⚠️  Collection '{COLLECTION_NAME}' chưa có data. Chạy scripts/build_index.py trước.")
        return collection


def _get_bm25_index() -> dict:
    """
    Lazily build and cache BM25 index from all ChromaDB documents.
    Returns dict: {bm25, docs, metas}
    """
    global _bm25_cache
    if _bm25_cache is not None:
        return _bm25_cache

    from rank_bm25 import BM25Okapi
    collection = _get_collection()
    all_data = collection.get(include=["documents", "metadatas"])
    docs = all_data["documents"]
    metas = all_data["metadatas"]
    tokenized = [doc.lower().split() for doc in docs]
    _bm25_cache = {"bm25": BM25Okapi(tokenized), "docs": docs, "metas": metas}
    return _bm25_cache


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
    query_embedding = embed(query)

    try:
        collection = _get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )

        chunks = []
        for i, (doc, dist, meta) in enumerate(zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0]
        )):
            chunks.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "score": round(1 - dist, 4),  # cosine similarity
                "metadata": meta,
            })
        return chunks

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        # Fallback: return empty (abstain)
        return []


def retrieve_sparse(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Sparse retrieval via BM25 keyword search.
    Strong on exact terms: P1, ERR-403, Level 3, Flash Sale.
    Weak on paraphrase / synonyms.
    """
    cache = _get_bm25_index()
    bm25, docs, metas = cache["bm25"], cache["docs"], cache["metas"]
    scores = bm25.get_scores(query.lower().split())
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [
        {
            "text": docs[i],
            "source": metas[i].get("source", "unknown"),
            "score": float(scores[i]),
            "metadata": metas[i],
        }
        for i in top_indices
    ]


def retrieve_hybrid(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> list:
    """
    Hybrid retrieval: Dense + BM25 fused via Reciprocal Rank Fusion (RRF, k=60).

    RRF score(doc) = dense_weight * 1/(60 + dense_rank)
                   + sparse_weight * 1/(60 + sparse_rank)

    Best of both: semantic meaning (dense) + exact keywords (sparse).
    Default in Day 09 — matches Day 08's winning variant config.
    """
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    def rrf(results, weight):
        return {r["text"]: weight / (60 + rank) for rank, r in enumerate(results, 1)}

    dense_rrf = rrf(dense_results, dense_weight)
    sparse_rrf = rrf(sparse_results, sparse_weight)

    dense_by_text = {r["text"]: r for r in dense_results}
    sparse_by_text = {r["text"]: r for r in sparse_results}

    ranked = []
    for text in {r["text"] for r in dense_results + sparse_results}:
        base = dict(dense_by_text.get(text) or sparse_by_text.get(text))
        base["dense_rrf_score"] = dense_rrf.get(text, 0.0)
        base["sparse_rrf_score"] = sparse_rrf.get(text, 0.0)
        base["score"] = base["dense_rrf_score"] + base["sparse_rrf_score"]
        ranked.append(base)

    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:top_k]


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

    state["workers_called"].append(WORKER_NAME)

    # Log worker IO (theo contract)
    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_hybrid(task, top_k=top_k)  # hybrid is the default (Day 08 winning config)

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
