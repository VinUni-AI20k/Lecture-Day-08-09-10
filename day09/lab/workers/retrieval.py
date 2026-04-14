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
from dotenv import load_dotenv
load_dotenv()

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", 3))


class RetrievalUnavailableError(RuntimeError):
    """Raised when retrieval infra/config is unavailable."""
    pass


def _get_embedding_fn():
    """
    Trả về embedding function.
    Quan trọng: Phải khớp với model đã dùng để build index ở Day 08 (OpenAI).
    """
    # Ưu tiên OpenAI (cần API key) vì Day 08 dùng model này
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            def embed(text: str) -> list:
                resp = client.embeddings.create(input=text, model="text-embedding-3-small")
                return resp.data[0].embedding
            return embed
        except ImportError:
            print("⚠️  Không tìm thấy thư viện 'openai'. Đang thử fallback...")

    # Option B: Sentence Transformers
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()
        return embed
    except ImportError:
        pass

    # Fallback: random embeddings cho test (KHÔNG dùng cho production)
    import random
    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]
    print("⚠️  WARNING: Using random embeddings. Vui lòng kiểm tra API Key hoặc cài đặt thư viện.")
    return embed


def _get_collection():
    """
    Kết nối ChromaDB collection.
    Lấy thông tin từ .env hoặc mặc định trỏ về Day 08 nếu cần.
    """
    import chromadb
    
    # Lấy path từ .env, nếu không có thì trỏ sang Day 08
    db_path = os.getenv("CHROMA_DB_PATH", "../../day08/lab/chroma_db")
    collection_name = os.getenv("CHROMA_COLLECTION", "rag_lab")
    
    client = chromadb.PersistentClient(path=db_path)
    try:
        collection = client.get_collection(collection_name)
    except Exception as e:
        raise RetrievalUnavailableError(
            f"Collection '{collection_name}' không tồn tại tại '{db_path}'. "
            f"Kiểm tra CHROMA_DB_PATH / CHROMA_COLLECTION. ({e})"
        ) from e
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
    query_embedding = embed(query)

    collection = _get_collection()

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )
    except Exception as e:
        raise RetrievalUnavailableError(f"ChromaDB query failed: {e}") from e

    chunks = []
    for doc, dist, meta in zip(
        results.get("documents", [[]])[0],
        results.get("distances", [[]])[0],
        results.get("metadatas", [[]])[0]
    ):
        chunks.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "score": round(1 - dist, 4),  # cosine similarity
            "metadata": meta,
        })
    return chunks


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    raw_top_k = state.get("top_k", state.get("retrieval_top_k", DEFAULT_TOP_K))
    try:
        top_k = int(raw_top_k)
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

    except RetrievalUnavailableError as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(
            f"[{WORKER_NAME}] retrieval unavailable: {e}"
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
