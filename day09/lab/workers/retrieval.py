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
LAB_DIR = os.path.dirname(os.path.dirname(__file__))
DOCS_DIR = os.path.join(LAB_DIR, "data", "docs")
CHROMA_DIR = os.path.join(LAB_DIR, "chroma_db")
_EMBEDDING_FN = None
STOPWORDS = {
    "ai", "anh", "chi", "cho", "co", "cua", "da", "de", "duoc", "hay", "he", "khi",
    "khong", "la", "lam", "luc", "mot", "nay", "nao", "ngay", "nguoi", "nhan", "sau",
    "so", "tai", "the", "theo", "thi", "thoi", "toi", "tra", "trong", "tu", "va",
    "vi", "vien", "voi", "yeu", "cau", "dung", "gì", "gi", "bao", "nhieu", "qua",
    "kenh", "dau", "tien", "may", "gio",
}


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.lower()


def _tokenize(text: str) -> list:
    return re.findall(r"[a-z0-9_]+", _normalize(text))


def _keyword_tokens(text: str) -> set:
    return {
        token for token in _tokenize(text)
        if token not in STOPWORDS and (len(token) > 2 or token.isdigit())
    }


def _query_profile(query: str) -> dict:
    normalized_query = _normalize(query)
    profile = {
        "normalized": normalized_query,
        "tokens": _keyword_tokens(query),
        "numbers": {token for token in _tokenize(query) if token.isdigit()},
        "preferred_sources": set(),
        "required_phrases": [],
        "asks_for_channels": any(term in normalized_query for term in ["thong bao", "kenh", "pagerduty", "slack", "email"]),
        "asks_for_timing": any(term in normalized_query for term in ["bao", "deadline", "may gio", "muc", "sau bao nhieu", "khi nao"]),
    }

    if any(term in normalized_query for term in ["p1", "sla", "incident", "pagerduty", "senior engineer", "escalation"]):
        profile["preferred_sources"].add("sla_p1_2026.txt")
    if any(term in normalized_query for term in ["mat khau", "password", "helpdesk", "canh bao truoc"]):
        profile["preferred_sources"].add("it_helpdesk_faq.txt")
    if any(term in normalized_query for term in ["probation", "remote", "team lead"]):
        profile["preferred_sources"].add("hr_leave_policy.txt")
    if any(term in normalized_query for term in ["level 2", "level 3", "access", "it security", "contractor"]):
        profile["preferred_sources"].add("access_control_sop.txt")
    if any(term in normalized_query for term in ["refund", "hoan tien", "flash sale", "store credit"]):
        profile["preferred_sources"].add("policy_refund_v4.txt")

    if any(term in normalized_query for term in ["muc phat", "tai chinh"]):
        profile["required_phrases"] = ["muc phat", "tai chinh"]

    return profile


def _get_embedding_fn():
    """
    Trả về embedding function.
    TODO Sprint 1: Implement dùng OpenAI hoặc Sentence Transformers.
    """
    global _EMBEDDING_FN
    if _EMBEDDING_FN is not None:
        return _EMBEDDING_FN

    # Option A: Sentence Transformers (offline, không cần API key)
    try:
        from sentence_transformers import SentenceTransformer
        try:
            model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        except Exception:
            model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=False)

        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()

        _EMBEDDING_FN = embed
        return _EMBEDDING_FN
    except Exception:
        pass

    # Option B: OpenAI (cần API key)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        def embed(text: str) -> list:
            resp = client.embeddings.create(input=text, model="text-embedding-3-small")
            return resp.data[0].embedding

        _EMBEDDING_FN = embed
        return _EMBEDDING_FN
    except Exception:
        pass

    # Fallback: random embeddings cho test (KHÔNG dùng production)
    import random

    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]

    print("WARNING: Using random embeddings (test only). Install sentence-transformers.")
    _EMBEDDING_FN = embed
    return _EMBEDDING_FN


def _get_collection():
    """
    Kết nối ChromaDB collection.
    TODO Sprint 2: Đảm bảo collection đã được build từ Step 3 trong README.
    """
    import chromadb

    # Keep the worker self-contained: it opens the local persistent DB directly.
    client = chromadb.PersistentClient(path=CHROMA_DIR)
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
    query_profile = _query_profile(query)
    dense_chunks = []

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
                dense_chunks = chunks
    except Exception as e:
        print(f"WARNING: ChromaDB query failed: {e}", file=sys.stderr)

    # Always run a lexical pass on the small local corpus as a safety net.
    # This keeps retrieval grounded even when Chroma metadata is stale or sources are missing.
    if not os.path.isdir(DOCS_DIR):
        return []

    query_tokens = query_profile["tokens"]
    fallback_chunks = []

    for fname in sorted(os.listdir(DOCS_DIR)):
        file_path = os.path.join(DOCS_DIR, fname)
        if not os.path.isfile(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        sections = [section.strip() for section in re.split(r"\n(?=== )", content.replace("\r\n", "\n")) if section.strip()]
        for section_index, section_text in enumerate(sections, start=1):
            section_tokens = _keyword_tokens(section_text)
            if not section_tokens:
                continue

            overlap = len(query_tokens & section_tokens)
            if overlap == 0:
                continue

            # Small boosts help simple keyword routing questions surface the right section faster.
            score = overlap / max(len(query_tokens), 1)
            normalized_query = query_profile["normalized"]
            normalized_section = _normalize(section_text)
            normalized_source = _normalize(fname)

            if fname in query_profile["preferred_sources"]:
                score += 0.35

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
            if "mat khau" in normalized_query and "mat khau" in normalized_section:
                score += 0.3
            if "probation" in normalized_query and "probation" in normalized_section:
                score += 0.3
            if "remote" in normalized_query and "remote" in normalized_section:
                score += 0.25
            if "senior engineer" in normalized_query and "senior engineer" in normalized_section:
                score += 0.25
            if query_profile["asks_for_channels"] and any(
                term in normalized_section for term in ["slack", "email", "pagerduty", "alert", "on-call"]
            ):
                score += 0.25
            if query_profile["asks_for_timing"] and re.search(r"\b\d+\s*(phut|gio|ngay|tuan)\b", normalized_section):
                score += 0.2
            if query_profile["numbers"] and query_profile["numbers"] & set(re.findall(r"\b\d+\b", normalized_section)):
                score += 0.25
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

    candidates = fallback_chunks
    if dense_chunks and all(chunk.get("source") != "unknown" for chunk in dense_chunks):
        candidates = dense_chunks + fallback_chunks

    if query_profile["required_phrases"]:
        candidates = [
            chunk for chunk in candidates
            if any(phrase in _normalize(chunk.get("text", "")) for phrase in query_profile["required_phrases"])
        ]

    deduped = {}
    for chunk in candidates:
        source = chunk.get("source", "unknown")
        text = re.sub(r"\s+", " ", chunk.get("text", "")).strip()
        if not text:
            continue
        key = (source, text)
        existing = deduped.get(key)
        source_bonus = 0.05 if source in query_profile["preferred_sources"] else 0.0
        candidate_score = round(min(1.0, float(chunk.get("score", 0) or 0) + source_bonus), 4)
        if existing is None or candidate_score > existing["score"]:
            deduped[key] = {
                **chunk,
                "score": candidate_score,
            }

    merged_chunks = sorted(deduped.values(), key=lambda chunk: chunk["score"], reverse=True)
    return merged_chunks[: max(top_k * 2, 6)]


def _extract_relevant_sentences(query: str, chunks: list, max_sentences: int = 3) -> list:
    # Compress long retrieved sections into the most answer-worthy evidence sentences.
    profile = _query_profile(query)
    query_tokens = profile["tokens"]
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
            normalized_sentence = _normalize(sentence)
            sentence_tokens = _keyword_tokens(sentence)
            overlap = len(query_tokens & sentence_tokens)
            if profile["asks_for_timing"] and re.search(r"\b\d+\s*(phut|gio|ngay|tuan)\b", normalized_sentence):
                overlap += 2
            if profile["asks_for_channels"] and any(
                term in normalized_sentence for term in ["slack", "email", "pagerduty", "alert", "on-call"]
            ):
                overlap += 2
            if profile["asks_for_channels"] and "slack" in normalized_sentence and "email" in normalized_sentence:
                overlap += 3
            if profile["asks_for_channels"] and "pagerduty" in normalized_sentence:
                overlap += 3
            if "probation" in profile["normalized"] and "probation" in normalized_sentence:
                overlap += 2
            if "team lead" in profile["normalized"] and "team lead" in normalized_sentence:
                overlap += 2
            if profile["numbers"] and profile["numbers"] & set(re.findall(r"\b\d+\b", normalized_sentence)):
                overlap += 2
            if source in profile["preferred_sources"]:
                overlap += 1
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
        sentence_score = round(min(1.0, max(0.1, chunk_score + 0.05)), 4)
        selected.append({"text": sentence, "source": source, "score": sentence_score})
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
        focused_chunks = _extract_relevant_sentences(task, chunks, max_sentences=max(top_k, 4))
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
