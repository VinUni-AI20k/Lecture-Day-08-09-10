"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Chiến lược tương thích Day 08:
    - Day 09 là project riêng, nhưng retrieval phải đọc đúng index đã build ở Day 08.
    - Vì vậy worker này KHÔNG import code retrieval của Day 08.
    - Worker chỉ tái sử dụng đúng "hợp đồng index" của Day 08:
      + Chroma DB path
      + collection name
      + embedding model
      + metadata schema (source, section, effective_date, ...)
    - Retrieval mode có thể chọn dense / sparse / hybrid ngay trong Day 09.

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", 3))
DAY09_LAB_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
DAY08_LAB_DIR = REPO_ROOT / "day08" / "lab"


class RetrievalUnavailableError(RuntimeError):
    """Raised when retrieval infra/config is unavailable."""


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_db_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (DAY09_LAB_DIR / candidate).resolve()


def _candidate_db_paths() -> list[Path]:
    configured = os.getenv("CHROMA_DB_PATH")
    candidates: list[Path] = []

    if configured:
        candidates.append(_resolve_db_path(configured))

    day09_default = DAY09_LAB_DIR / "chroma_db"
    day08_default = DAY08_LAB_DIR / "chroma_db"

    for path in [day09_default, day08_default]:
        if path not in candidates:
            candidates.append(path)

    return candidates


def _candidate_collection_names() -> list[str]:
    configured = os.getenv("CHROMA_COLLECTION")
    candidates = []
    if configured:
        candidates.append(configured)
    for name in ["rag_lab", "day09_docs"]:
        if name not in candidates:
            candidates.append(name)
    return candidates


def _format_chunks(chunks: list[dict]) -> list[dict]:
    formatted = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {}) or {}
        source = chunk.get("source") or metadata.get("source", "unknown")
        formatted.append({
            "text": chunk.get("text", ""),
            "source": source,
            "score": round(float(chunk.get("score", 0.0)), 4),
            "metadata": metadata,
        })
    return formatted


def _get_embedding_fn():
    """
    Trả về embedding function.
    Quan trọng: phải khớp với model đã dùng để build index ở Day 08.
    """
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

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")

        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()

        return embed
    except ImportError:
        pass

    import random

    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]

    print("⚠️  WARNING: Using random embeddings. Vui lòng kiểm tra API Key hoặc cài đặt thư viện.")
    return embed


def _get_collection_with_info():
    """
    Kết nối ChromaDB collection.

    Ưu tiên config hiện tại, nhưng nếu Day 09 chưa có collection tương thích
    thì tự fallback sang index của Day 08 để tận dụng artifact đã build.
    """
    import chromadb

    errors = []
    for db_path in _candidate_db_paths():
        if not db_path.exists():
            errors.append(f"missing db path: {db_path}")
            continue

        try:
            client = chromadb.PersistentClient(path=str(db_path))
        except Exception as exc:
            errors.append(f"cannot open {db_path}: {exc}")
            continue

        for collection_name in _candidate_collection_names():
            try:
                collection = client.get_collection(collection_name)
                return collection, str(db_path), collection_name
            except Exception as exc:
                errors.append(f"{db_path}::{collection_name} -> {exc}")

    joined = " | ".join(errors[-6:])
    raise RetrievalUnavailableError(
        "Không tìm thấy collection Chroma tương thích. "
        f"Đã thử: {joined}"
    )


def _get_collection():
    collection, _, _ = _get_collection_with_info()
    return collection


def _dedupe_chunks(chunks: list[dict], top_k: int) -> list[dict]:
    seen = set()
    deduped = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {}) or {}
        key = (metadata.get("source", "unknown"), chunk.get("text", "")[:160])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
        if len(deduped) >= top_k:
            break
    return deduped


def _score_query_source_match(query: str, source: str) -> float:
    lower_query = query.lower()
    lower_source = source.lower()

    mapping = [
        (["refund", "hoàn tiền", "flash sale", "vip"], ["refund"]),
        (["access", "cấp quyền", "approval", "level 3", "level 4", "contractor"], ["access", "control"]),
        (["p1", "sla", "ticket", "incident", "escalation"], ["sla", "helpdesk"]),
        (["err-", "password", "vpn", "helpdesk"], ["faq", "helpdesk"]),
        (["remote", "leave", "nghỉ"], ["leave", "hr"]),
    ]

    for query_terms, source_terms in mapping:
        if any(term in lower_query for term in query_terms) and any(term in lower_source for term in source_terms):
            return 0.08
    return 0.0


def _rerank_locally(query: str, chunks: list[dict], top_k: int) -> list[dict]:
    query_words = set(query.lower().split())

    def rank_score(chunk: dict) -> float:
        text = chunk.get("text", "").lower()
        metadata = chunk.get("metadata", {}) or {}
        source = metadata.get("source", chunk.get("source", ""))
        lexical_hits = sum(1 for word in query_words if word and word in text)
        lexical_bonus = min(0.12, lexical_hits * 0.02)
        source_bonus = _score_query_source_match(query, source)
        return float(chunk.get("score", 0.0)) + lexical_bonus + source_bonus

    ranked = sorted(chunks, key=rank_score, reverse=True)
    return _dedupe_chunks(ranked, top_k=top_k)


def _expand_query(query: str) -> list[str]:
    lower_query = query.lower()
    expansions = [query]
    alias_map = {
        "approval matrix": ["Access Control SOP", "Approval Matrix for System Access"],
        "approval matrix for system access": ["Access Control SOP"],
        "err-403-auth": ["authentication error", "helpdesk", "IT Helpdesk"],
        "vip": ["khách hàng VIP", "quy trình hoàn tiền chuẩn"],
    }

    for key, variants in alias_map.items():
        if key in lower_query:
            expansions.extend(variants)

    ordered = []
    for item in expansions:
        if item not in ordered:
            ordered.append(item)
    return ordered


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: embed query → query ChromaDB → trả về top_k chunks.
    """
    embed = _get_embedding_fn()
    query_embedding = embed(query)
    collection = _get_collection()

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"],
        )
    except Exception as exc:
        raise RetrievalUnavailableError(f"ChromaDB query failed: {exc}") from exc

    chunks = []
    for doc, dist, meta in zip(
        results.get("documents", [[]])[0],
        results.get("distances", [[]])[0],
        results.get("metadatas", [[]])[0],
    ):
        metadata = meta or {}
        chunks.append({
            "text": doc,
            "source": metadata.get("source", "unknown"),
            "score": round(1 - dist, 4),
            "metadata": metadata,
        })
    return chunks


def retrieve_sparse(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Sparse retrieval trên chính corpus đã index ở Day 08.
    Không cần re-index, chỉ đọc documents từ collection để build BM25 tạm thời.
    """
    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:
        raise RetrievalUnavailableError(
            "Thiếu thư viện rank_bm25 để chạy sparse retrieval."
        ) from exc

    collection = _get_collection()
    all_docs = collection.get(include=["documents", "metadatas"])
    corpus = all_docs.get("documents", []) or []
    metadatas = all_docs.get("metadatas", []) or []

    if not corpus:
        return []

    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    chunks = []
    for idx in top_indices:
        if scores[idx] <= 0:
            continue
        metadata = metadatas[idx] or {}
        chunks.append({
            "text": corpus[idx],
            "source": metadata.get("source", "unknown"),
            "score": float(scores[idx]),
            "metadata": metadata,
        })
    return chunks


def retrieve_hybrid(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Hybrid retrieval để hợp với corpus Day 08:
    - dense cho policy/paraphrase
    - sparse cho alias, code, exact term
    """
    dense_results = retrieve_dense(query, top_k=max(top_k, 6))
    sparse_results = retrieve_sparse(query, top_k=max(top_k, 6))

    combined_scores = {}
    all_results = {}

    def key_of(chunk: dict) -> str:
        metadata = chunk.get("metadata", {}) or {}
        return f"{metadata.get('source', 'unknown')}::{chunk.get('text', '')[:120]}"

    for rank, chunk in enumerate(dense_results, start=1):
        key = key_of(chunk)
        combined_scores[key] = combined_scores.get(key, 0.0) + (0.6 / (60 + rank))
        all_results[key] = chunk

    for rank, chunk in enumerate(sparse_results, start=1):
        key = key_of(chunk)
        combined_scores[key] = combined_scores.get(key, 0.0) + (0.4 / (60 + rank))
        all_results.setdefault(key, chunk)

    merged = []
    for key in sorted(combined_scores, key=combined_scores.get, reverse=True):
        chunk = all_results[key].copy()
        chunk["score"] = combined_scores[key]
        merged.append(chunk)

    return merged[: max(top_k, 6)]


def _choose_retrieval_mode(query: str) -> str:
    configured = os.getenv("RETRIEVAL_MODE", "auto").strip().lower()
    if configured in {"dense", "sparse", "hybrid"}:
        return configured

    lower_query = query.lower()
    if any(token in lower_query for token in ["approval matrix", "err-", "code", "mã lỗi"]):
        return "hybrid"
    return "dense"


def retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> tuple[list[dict], dict]:
    """
    Entry retrieval phù hợp index Day 08 nhưng chạy hoàn toàn trong Day 09.
    """
    mode = _choose_retrieval_mode(query)
    search_k = int(os.getenv("RETRIEVAL_SEARCH_TOP_K", max(top_k, 8)))
    use_rerank = _parse_bool(os.getenv("RETRIEVAL_USE_RERANK"), default=True)

    if mode == "dense":
        candidates = []
        for expanded_query in _expand_query(query):
            candidates.extend(retrieve_dense(expanded_query, top_k=search_k))
    elif mode == "sparse":
        candidates = []
        for expanded_query in _expand_query(query):
            candidates.extend(retrieve_sparse(expanded_query, top_k=search_k))
    elif mode == "hybrid":
        candidates = []
        for expanded_query in _expand_query(query):
            candidates.extend(retrieve_hybrid(expanded_query, top_k=search_k))
    else:
        raise RetrievalUnavailableError(f"Retrieval mode không hợp lệ: {mode}")

    if use_rerank:
        selected = _rerank_locally(query, candidates, top_k=top_k)
    else:
        selected = _dedupe_chunks(candidates, top_k=top_k)

    _, db_path, collection_name = _get_collection_with_info()
    retrieval_info = {
        "mode": mode,
        "search_top_k": search_k,
        "use_rerank": use_rerank,
        "db_path": db_path,
        "collection": collection_name,
    }
    return _format_chunks(selected), retrieval_info


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
        chunks, retrieval_info = retrieve(task, top_k=top_k)
        retrieval_backend = "local_day09_on_day08_index"

        sources = list({c["source"] for c in chunks})

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
            "retrieval_backend": retrieval_backend,
            "retrieval_mode": retrieval_info["mode"],
            "search_top_k": retrieval_info["search_top_k"],
            "db_path": retrieval_info["db_path"],
            "collection": retrieval_info["collection"],
        }
        state["history"].append(
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources} "
            f"via {retrieval_backend} mode={retrieval_info['mode']} "
            f"collection={retrieval_info['collection']}"
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
