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
import re
import sys
import unicodedata

# ————————————————————————————————————————————————
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ————————————————————————————————————————————————

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3


def _get_embedding_fn():
    """
    Trả về embedding function.
    TODO Sprint 1: Implement dùng OpenAI hoặc Sentence Transformers.
    """
    # Option A: Sentence Transformers (offline, không cần API key)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)

        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()

        return embed
    except Exception:
        pass

    # Option B: OpenAI (cần API key)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        def embed(text: str) -> list:
            resp = client.embeddings.create(input=text, model="text-embedding-3-small")
            return resp.data[0].embedding

        return embed
    except Exception:
        pass

    # Fallback: random embeddings cho test (KHÔNG dùng production)
    import random

    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]

    print("⚠️  WARNING: Using random embeddings (test only). Install sentence-transformers.")
    return embed


def _get_collection():
    """
    Kết nối ChromaDB collection.
    TODO Sprint 2: Đảm bảo collection đã được build từ Step 3 trong README.
    """
    import chromadb

    # Keep the worker self-contained: it opens the local persistent DB directly.
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
    try:
        collection = _get_collection()

        try:
            has_indexed_data = collection.count() > 0
        except Exception:
            has_indexed_data = False

        # Preferred path: dense retrieval from the indexed Chroma collection.
        if has_indexed_data:
            embed = _get_embedding_fn()
            query_embedding = embed(query)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "distances", "metadatas"]
            )

            documents = results.get("documents", [[]])
            distances = results.get("distances", [[]])
            metadatas = results.get("metadatas", [[]])

            if documents and documents[0]:
                chunks = []
                for doc, dist, meta in zip(documents[0], distances[0], metadatas[0]):
                    metadata = meta or {}
                    chunks.append({
                        "text": doc,
                        "source": metadata.get("source", "unknown"),
                        "score": round(max(0.0, min(1.0, 1 - float(dist))), 4),
                        "metadata": metadata,
                    })
                return chunks
    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}", file=sys.stderr)

    # Fallback lexical retrieval on local docs so worker can still run independently
    # when ChromaDB has not been indexed yet.
    def normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return normalized.lower()

    def tokenize(text: str) -> list:
        return re.findall(r"[a-z0-9_]+", normalize(text))

    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "docs")
    if not os.path.isdir(docs_dir):
        return []

    query_tokens = set(tokenize(query))
    fallback_chunks = []

    for fname in sorted(os.listdir(docs_dir)):
        file_path = os.path.join(docs_dir, fname)
        if not os.path.isfile(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        sections = [section.strip() for section in re.split(r"\n(?=== )", content.replace("\r\n", "\n")) if section.strip()]
        for section_index, section_text in enumerate(sections, start=1):
            section_tokens = set(tokenize(section_text))
            if not section_tokens:
                continue

            overlap = len(query_tokens & section_tokens)
            if overlap == 0:
                continue

            # Small boosts help simple keyword routing questions surface the right section faster.
            score = overlap / max(len(query_tokens), 1)
            normalized_query = normalize(query)
            normalized_section = normalize(section_text)
            normalized_source = normalize(fname)

            if "flash sale" in normalized_query and "flash sale" in normalized_section:
                score += 0.2
            if "license key" in normalized_query and "license key" in normalized_section:
                score += 0.2
            if "store credit" in normalized_query and "store credit" in normalized_section:
                score += 0.2
            if "p1" in normalized_query and "p1" in normalized_section:
                score += 0.15
            if "level 2" in normalized_query and "level 2" in normalized_section:
                score += 0.15
            if "level 3" in normalized_query and "level 3" in normalized_section:
                score += 0.15
            if "refund" in normalized_query and "refund" in normalized_source:
                score += 0.1
            if "access" in normalized_query and "access" in normalized_source:
                score += 0.1
            if "sla" in normalized_query and "sla" in normalized_source:
                score += 0.1

            fallback_chunks.append({
                "text": section_text,
                "source": fname,
                "score": round(min(1.0, score), 4),
                "metadata": {
                    "source": fname,
                    "fallback": "local_lexical_search",
                    "section_index": section_index,
                },
            })

    fallback_chunks.sort(key=lambda chunk: chunk["score"], reverse=True)
    return fallback_chunks[:top_k]


def _extract_relevant_sentences(query: str, chunks: list, max_sentences: int = 3) -> list:
    # Compress long retrieved sections into the most answer-worthy evidence sentences.
    def normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return normalized.lower()

    query_tokens = set(re.findall(r"[a-z0-9_]+", normalize(query)))
    asks_for_timing = any(token in query_tokens for token in ["bao", "lau", "khi", "nao", "deadline"])
    candidates = []

    for chunk in chunks:
        source = chunk.get("source", "unknown")
        chunk_score = float(chunk.get("score", 0) or 0)
        text = chunk.get("text", "")
        sentences = re.split(r"(?<=[\.\?!])\s+|\n+", text)
        for sentence in sentences:
            sentence = sentence.strip(" -\t")
            if len(sentence) < 20:
                continue
            sentence = re.sub(r"^\W+", "", sentence).strip()
            sentence = re.sub(r"\s+", " ", sentence)
            sentence_lower = sentence.lower()
            if sentence_lower.startswith(("source:", "department:", "effective date:", "access:")):
                continue
            if any(marker in sentence_lower for marker in [" source:", " department:", " effective date:", " access:"]):
                continue
            if re.fullmatch(r"[A-Z0-9\s\-]+", sentence):
                continue
            normalized_sentence = normalize(sentence)
            sentence_tokens = set(re.findall(r"[a-z0-9_]+", normalized_sentence))
            overlap = len(query_tokens & sentence_tokens)
            if asks_for_timing and re.search(r"\b\d+\s*(phut|gio|ngay|tuan)\b", normalized_sentence):
                overlap += 2
            if overlap == 0:
                continue
            if "===" in sentence or normalized_sentence.startswith(("phan ", "section ")):
                continue
            candidates.append((overlap, chunk_score, source, sentence))

    candidates.sort(key=lambda item: (item[0], item[1], len(item[3])), reverse=True)

    selected = []
    seen = set()
    for _, _, source, sentence in candidates:
        key = (source, sentence)
        if key in seen:
            continue
        seen.add(key)
        selected.append({"text": sentence, "source": source, "score": 1.0})
        if len(selected) >= max_sentences:
            break
    return selected


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    top_k = state.get("top_k", state.get("retrieval_top_k", DEFAULT_TOP_K))

    state.setdefault("workers_called", [])
    state.setdefault("history", [])

    state["workers_called"].append(WORKER_NAME)

    # Worker IO logs are stored in trace so we can debug retrieval separately from synthesis.
    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_dense(task, top_k=top_k)
        focused_chunks = _extract_relevant_sentences(task, chunks, max_sentences=top_k)
        if focused_chunks:
            chunks = focused_chunks

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

    # Persist per-worker IO to the shared state for later trace analysis.
    state.setdefault("worker_io_logs", []).append(worker_io)

    return state


# ————————————————————————————————————————————————
# Test độc lập
# ————————————————————————————————————————————————

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
            preview = c["text"][:80].encode("ascii", "replace").decode("ascii")
            print(f"    [{c['score']:.3f}] {c['source']}: {preview}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\n✅ retrieval_worker test done.")
