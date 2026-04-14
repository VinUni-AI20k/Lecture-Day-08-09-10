"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Dense retrieval từ ChromaDB, trả về chunks + sources.

Input (từ AgentState):
    - task: câu hỏi cần retrieve
    - (optional) retrieval_top_k: số chunks cần lấy (default 3)

Output (vào AgentState):
    - retrieved_chunks: list of {"text", "source", "score", "metadata"}
    - retrieved_sources: list of source filenames
    - worker_io_logs: log input/output của worker này

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os
import sys
from pathlib import Path


def _load_env():
    """Load .env on demand (CLI / explicit init), not at import time."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass



WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 5


DOCS_DIR = Path(__file__).parent.parent / "data" / "docs"
CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"


def _get_embedding_fn():
    """Trả về embedding function. Ưu tiên Sentence Transformers, fallback OpenAI."""
    # Option A: Sentence Transformers (offline, không cần API key)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()
        return embed
    except ImportError:
        pass

    # Option B: OpenAI (cần OPENAI_API_KEY trong .env)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        def embed(text: str) -> list:
            resp = client.embeddings.create(input=text, model="text-embedding-3-small")
            return resp.data[0].embedding
        return embed
    except ImportError:
        pass

    # Fallback: random embeddings (KHÔNG dùng production)
    import random
    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]
    print("WARNING: Using random embeddings. Install sentence-transformers.")
    return embed


def _get_collection():
    """Kết nối ChromaDB collection 'day09_docs'."""
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        "day09_docs",
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def _chunk_text(text: str, source: str, chunk_size: int = 300, overlap: int = 50) -> list:
    """
    Chia văn bản thành các chunks nhỏ theo sliding window.
    Trả về list of {"text": str, "source": str, "chunk_id": str}.
    """
    chunks = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    words = " ".join(lines).split()

    i = 0
    chunk_idx = 0
    while i < len(words):
        chunk_words = words[i : i + chunk_size]
        chunk_text = " ".join(chunk_words).strip()
        if len(chunk_text) > 30:  # bỏ qua chunk quá ngắn
            chunks.append({
                "text": chunk_text,
                "source": source,
                "chunk_id": f"{source}__chunk{chunk_idx}",
            })
            chunk_idx += 1
        i += chunk_size - overlap

    return chunks


def build_index(docs_dir: str = None, force_rebuild: bool = False):
    """
    Đọc toàn bộ file .txt trong data/docs/, chia chunks, embed, nạp vào ChromaDB.
    Gọi một lần trước khi chạy pipeline:
        python workers/retrieval.py --build
    """
    docs_path = Path(docs_dir) if docs_dir else DOCS_DIR
    collection = _get_collection()

    # Kiểm tra xem đã có data chưa
    existing = collection.count()
    if existing > 0 and not force_rebuild:
        print(f"Collection đã có {existing} chunks. Bỏ qua build (dùng --force để rebuild).")
        return

    if force_rebuild and existing > 0:
        # Xóa hết để rebuild
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        client.delete_collection("day09_docs")
        print(f"Đã xóa collection cũ ({existing} chunks). Rebuilding...")
        collection = _get_collection()

    embed = _get_embedding_fn()

    all_chunks = []
    txt_files = list(docs_path.glob("*.txt"))
    if not txt_files:
        print(f"Không tìm thấy file .txt trong {docs_path}")
        return

    print(f"Indexing {len(txt_files)} files từ {docs_path} ...")
    for txt_file in txt_files:
        source = txt_file.name
        text = txt_file.read_text(encoding="utf-8")
        chunks = _chunk_text(text, source)
        all_chunks.extend(chunks)
        print(f"  {source}: {len(chunks)} chunks")

    # Nạp vào ChromaDB theo batch
    batch_size = 50
    for start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[start : start + batch_size]
        ids = [c["chunk_id"] for c in batch]
        documents = [c["text"] for c in batch]
        metadatas = [{"source": c["source"], "chunk_id": c["chunk_id"]} for c in batch]
        embeddings = [embed(c["text"]) for c in batch]

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    total = collection.count()
    print(f"Done. Tổng {total} chunks đã được index vào ChromaDB.")


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: embed query → query ChromaDB → trả về top_k chunks.

    Returns:
        list of {"text": str, "source": str, "score": float, "metadata": dict}
    """
    embed = _get_embedding_fn()
    query_embedding = embed(query)

    try:
        collection = _get_collection()

        if collection.count() == 0:
            print("WARNING: ChromaDB collection rỗng. Chạy 'python workers/retrieval.py --build' trước.")
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "distances", "metadatas"]
        )

        chunks = []
        for doc, dist, meta in zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0]
        ):
            chunks.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "score": round(1.0 - float(dist), 4),  # cosine similarity
                "metadata": meta,
            })
        return chunks

    except Exception as e:
        print(f"ChromaDB query failed: {e}")
        return []


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks, retrieved_sources, worker_io_logs
    """
    task = state.get("task", "")
    # Contract-compliant: top_k is the canonical key; retrieval_top_k kept as backward-compat alias
    top_k = state.get("top_k", state.get("retrieval_top_k", DEFAULT_TOP_K))

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
# CLI — chạy độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    _load_env()
    if "--build" in sys.argv or "--force" in sys.argv:
        build_index(force_rebuild="--force" in sys.argv)
        sys.exit(0)

    print("=" * 55)
    print("Retrieval Worker — Standalone Test")
    print("(Chạy '--build' lần đầu để index docs vào ChromaDB)")
    print("=" * 55)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\n Query: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for c in chunks[:2]:
            preview = c["text"][:80].replace("\n", " ")
            print(f"    [{c['score']:.3f}] {c['source']}: {preview}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\nretrieval_worker test done.")
