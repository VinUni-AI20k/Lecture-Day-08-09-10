"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
Sprint 2 (60 phút): Baseline RAG
  - Dense retrieval từ ChromaDB
  - Grounded answer function với prompt ép citation
  - Trả lời được ít nhất 3 câu hỏi mẫu, output có source

Sprint 3 (60 phút): Tuning tối thiểu
  - Thêm hybrid retrieval (dense + sparse/BM25)
  - Hoặc thêm rerank (cross-encoder)
  - Hoặc thử query transformation (expansion, decomposition, HyDE)
  - Tạo bảng so sánh baseline vs variant

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int, lo: int = 1, hi: int = 64) -> int:
    try:
        v = int(os.getenv(name, str(default)).strip())
        return max(lo, min(hi, v))
    except ValueError:
        return default


# =============================================================================
# CẤU HÌNH
# =============================================================================

# Có thể ghi đè bằng .env: TOP_K_SEARCH, TOP_K_SELECT, RRF_K
TOP_K_SEARCH = _env_int("TOP_K_SEARCH", 10, 1, 48)  # pool trước rerank / cắt top list
TOP_K_SELECT = _env_int("TOP_K_SELECT", 3, 1, 12)     # số chunk vào prompt

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
CROSS_ENCODER_MODEL = os.getenv(
    "CROSS_ENCODER_MODEL",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
)

CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"
CHROMA_COLLECTION = "rag_lab"
RRF_K = _env_int("RRF_K", 60, 10, 120)
ABSTAIN_ANSWER = "Không đủ dữ liệu trong tài liệu để trả lời."

# Cache BM25 corpus (reload sau khi build_index)
_bm25_bundle: Optional[Tuple[Any, List[str], List[str], List[Dict[str, Any]]]] = None


def _bm25_tokenize(text: str) -> List[str]:
    """Tách từ cho BM25: bỏ dấu câu dính token (vd. SLA?), ổn định hơn .split()."""
    return re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE)


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Dense retrieval: tìm kiếm theo embedding similarity trong ChromaDB.
    Score = 1 - distance (cosine distance trong Chroma).
    """
    import chromadb
    from index import get_embedding

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection(CHROMA_COLLECTION)
    n_docs = collection.count()
    if n_docs == 0:
        return []
    q_emb = get_embedding(query)
    res = collection.query(
        query_embeddings=[q_emb],
        n_results=min(top_k, n_docs),
        include=["documents", "metadatas", "distances"],
    )
    out: List[Dict[str, Any]] = []
    ids = res["ids"][0] if res["ids"] else []
    for i, cid in enumerate(ids):
        dist = res["distances"][0][i]
        score = float(1.0 - dist)
        meta = res["metadatas"][0][i] if res["metadatas"] and res["metadatas"][0] else {}
        doc = res["documents"][0][i] if res["documents"] else ""
        out.append({
            "id": cid,
            "text": doc,
            "metadata": dict(meta) if meta else {},
            "score": score,
        })
    return out


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def _bm25_load() -> Tuple[Any, List[str], List[str], List[Dict[str, Any]]]:
    """Load BM25 index từ Chroma (cache module-level)."""
    global _bm25_bundle
    if _bm25_bundle is not None:
        return _bm25_bundle

    import chromadb
    from rank_bm25 import BM25Okapi

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection(CHROMA_COLLECTION)
    data = collection.get(include=["documents", "metadatas"])
    ids = data["ids"]
    docs = list(data["documents"] or [])
    metas = list(data["metadatas"] or [])
    tokenized = [_bm25_tokenize(d) for d in docs]
    bm25 = BM25Okapi(tokenized)
    _bm25_bundle = (bm25, ids, docs, metas)
    return _bm25_bundle


def clear_bm25_cache() -> None:
    """Gọi sau khi build_index() để reload corpus."""
    global _bm25_bundle
    _bm25_bundle = None


def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: BM25 trên toàn bộ chunk trong Chroma.
    """
    bm25, ids, docs, metas = _bm25_load()
    if not ids:
        return []

    tokenized_query = _bm25_tokenize(query)
    if not tokenized_query:
        return []

    scores = bm25.get_scores(tokenized_query)
    n = min(top_k, len(ids))
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]

    out: List[Dict[str, Any]] = []
    for idx in top_indices:
        idx = int(idx)
        out.append({
            "id": ids[idx],
            "text": docs[idx],
            "metadata": dict(metas[idx]) if metas[idx] else {},
            "score": float(scores[idx]),
        })
    return out


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF).

    Mạnh ở: giữ được cả nghĩa (dense) lẫn keyword chính xác (sparse)
    Phù hợp khi: corpus lẫn lộn ngôn ngữ tự nhiên và tên riêng/mã lỗi/điều khoản

    Args:
        dense_weight: Trọng số cho dense score (0-1)
        sparse_weight: Trọng số cho sparse score (0-1)

    TODO Sprint 3 (nếu chọn hybrid):
    1. Chạy retrieve_dense() → dense_results
    2. Chạy retrieve_sparse() → sparse_results
    3. Merge bằng RRF:
       RRF_score(doc) = dense_weight * (1 / (60 + dense_rank)) +
                        sparse_weight * (1 / (60 + sparse_rank))
       60 là hằng số RRF tiêu chuẩn
    4. Sort theo RRF score giảm dần, trả về top_k

    Khi nào dùng hybrid (từ slide):
    - Corpus có cả câu tự nhiên VÀ tên riêng, mã lỗi, điều khoản
    - Query như "Approval Matrix" khi doc đổi tên thành "Access Control SOP"
    """
    n_dense = max(top_k * 2, 20)
    n_sparse = max(top_k * 2, 20)
    dense_results = retrieve_dense(query, top_k=n_dense)
    sparse_results = retrieve_sparse(query, top_k=n_sparse)

    by_id: Dict[str, Dict[str, Any]] = {}
    rrf: Dict[str, float] = {}

    for rank, ch in enumerate(dense_results):
        cid = ch["id"]
        by_id[cid] = ch
        rrf[cid] = rrf.get(cid, 0.0) + dense_weight / (RRF_K + rank + 1)

    for rank, ch in enumerate(sparse_results):
        cid = ch["id"]
        if cid not in by_id:
            by_id[cid] = ch
        rrf[cid] = rrf.get(cid, 0.0) + sparse_weight / (RRF_K + rank + 1)

    sorted_ids = sorted(rrf.keys(), key=lambda x: rrf[x], reverse=True)[:top_k]
    out: List[Dict[str, Any]] = []
    for cid in sorted_ids:
        ch = dict(by_id[cid])
        ch["score"] = float(rrf[cid])
        ch["rrf_score"] = float(rrf[cid])
        out.append(ch)
    return out


# =============================================================================
# RERANK (Sprint 3 alternative)
# Cross-encoder để chấm lại relevance sau search rộng
# =============================================================================

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Rerank các candidate chunks bằng cross-encoder.

    Cross-encoder: chấm lại "chunk nào thực sự trả lời câu hỏi này?"
    MMR (Maximal Marginal Relevance): giữ relevance nhưng giảm trùng lặp

    Funnel logic (từ slide):
      Search rộng (top-20) → Rerank (top-6) → Select (top-3)

    TODO Sprint 3 (nếu chọn rerank):
    Option A — Cross-encoder:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        pairs = [[query, chunk["text"]] for chunk in candidates]
        scores = model.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in ranked[:top_k]]

    Option B — Rerank bằng LLM (đơn giản hơn nhưng tốn token):
        Gửi list chunks cho LLM, yêu cầu chọn top_k relevant nhất

    Khi nào dùng rerank:
    - Dense/hybrid trả về nhiều chunk nhưng có noise
    - Muốn chắc chắn chỉ 3-5 chunk tốt nhất vào prompt
    """
    if not candidates:
        return []
    from sentence_transformers import CrossEncoder

    if not hasattr(rerank, "_model"):
        setattr(rerank, "_model", CrossEncoder(CROSS_ENCODER_MODEL))
    model = getattr(rerank, "_model")

    pairs = [[query, c["text"]] for c in candidates]
    bs = min(32, max(8, len(pairs)))
    scores = model.predict(pairs, batch_size=bs, show_progress_bar=False)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    out: List[Dict[str, Any]] = []
    for chunk, s in ranked[:top_k]:
        c = dict(chunk)
        c["score"] = float(s)
        c["rerank_score"] = float(s)
        out.append(c)
    return out


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion": Thêm từ đồng nghĩa, alias, tên cũ
      - "decomposition": Tách query phức tạp thành 2-3 sub-queries
      - "hyde": Sinh câu trả lời giả (hypothetical document) để embed thay query

    TODO Sprint 3 (nếu chọn query transformation):
    Gọi LLM với prompt phù hợp với từng strategy.

    Ví dụ expansion prompt:
        "Given the query: '{query}'
         Generate 2-3 alternative phrasings or related terms in Vietnamese.
         Output as JSON array of strings."

    Ví dụ decomposition:
        "Break down this complex query into 2-3 simpler sub-queries: '{query}'
         Output as JSON array."

    Khi nào dùng:
    - Expansion: query dùng alias/tên cũ (ví dụ: "Approval Matrix" → "Access Control SOP")
    - Decomposition: query hỏi nhiều thứ một lúc
    - HyDE: query mơ hồ, search theo nghĩa không hiệu quả
    """
    # TODO Sprint 3: Implement query transformation
    # Tạm thời trả về query gốc
    return [query]


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.

    Format: structured snippets với source, section, score (từ slide).
    Mỗi chunk có số thứ tự [1], [2], ... để model dễ trích dẫn.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")

        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if score is not None:
            header += f" | score={float(score):.4f}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Grounded prompt: evidence-only, abstain, citation [n], cùng ngôn ngữ với câu hỏi.
    """
    prompt = f"""You are an internal CS/IT policy assistant. Follow strictly:

1) Use ONLY information from the numbered context snippets below. Do not use outside knowledge.
2) **Same-or-different / comparison questions (e.g. leave types, access levels):** If the context defines two or more separate categories (e.g. distinct headings like "Annual Leave" vs "Sick Leave", or separate numbered items), you MUST answer by contrasting them using that text. State clearly whether the question's wording treats them as one thing or not, per policy. Cite [n]. **Do not abstain** when those definitions appear in any snippet.
3) **Abstain** only when no snippet contains facts needed to address the question at all. Then reply exactly:
    "{ABSTAIN_ANSWER}"
   (English questions may use: "Insufficient information in the documents to answer.")
4) When you cite evidence, include bracket references like [1], [2] matching snippet numbers.
5) Be concise and factual. Same language as the user's question (Vietnamese or English).

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM: OpenAI (mặc định) hoặc Gemini (LLM_PROVIDER=gemini).
    """
    if LLM_PROVIDER == "gemini":
        import google.generativeai as genai

        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY required when LLM_PROVIDER=gemini")
        genai.configure(api_key=key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0, "max_output_tokens": 512},
        )
        from run_telemetry import get_telemetry

        t = get_telemetry()
        if t is not None:
            um = getattr(response, "usage_metadata", None)
            if um is not None:
                from types import SimpleNamespace

                t.add_chat_usage(
                    SimpleNamespace(
                        prompt_tokens=int(getattr(um, "prompt_token_count", 0) or 0),
                        completion_tokens=int(
                            getattr(um, "candidates_token_count", 0) or 0
                        ),
                    )
                )
        return (response.text or "").strip()

    from openai import OpenAI

    from run_telemetry import get_telemetry

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY required when LLM_PROVIDER=openai")
    if not hasattr(call_llm, "_client"):
        setattr(call_llm, "_client", OpenAI(api_key=key))
    client = getattr(call_llm, "_client")
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512,
    )
    tel = get_telemetry()
    if tel is not None:
        tel.add_chat_usage(response.usage)
    return (response.choices[0].message.content or "").strip()


def call_llm_stream(prompt: str):
    """
    Generator variant of call_llm. Yields str tokens one at a time.
    Falls back to single-chunk yield for Gemini (no SSE SDK support in basic genai).
    """
    if LLM_PROVIDER == "gemini":
        import google.generativeai as genai
        from types import SimpleNamespace

        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY required when LLM_PROVIDER=gemini")
        genai.configure(api_key=key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        full_text = ""
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0, "max_output_tokens": 512},
            stream=True,
        )
        for chunk in response:
            delta = getattr(chunk, "text", "") or ""
            if delta:
                full_text += delta
                yield delta
        # Record usage after stream ends
        from run_telemetry import get_telemetry
        t = get_telemetry()
        if t is not None:
            # Gemini streaming doesn't reliably expose usage per-chunk; estimate
            t.add_chat_usage(SimpleNamespace(prompt_tokens=0, completion_tokens=len(full_text) // 4))
        return

    from openai import OpenAI
    from run_telemetry import get_telemetry

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY required when LLM_PROVIDER=openai")
    if not hasattr(call_llm, "_client"):
        setattr(call_llm, "_client", OpenAI(api_key=key))
    client = getattr(call_llm, "_client")
    stream = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512,
        stream=True,
    )
    prompt_tokens = 0
    completion_tokens = 0
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            completion_tokens += 1
            yield delta
        # Capture usage from final chunk (OpenAI sends it on the last chunk)
        if hasattr(chunk, "usage") and chunk.usage is not None:
            prompt_tokens = getattr(chunk.usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(chunk.usage, "completion_tokens", completion_tokens)
    tel = get_telemetry()
    if tel is not None:
        from types import SimpleNamespace
        tel.add_chat_usage(SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens))


def _trace_chunk_rows(chunks: List[Dict[str, Any]], text_snippet: int = 200) -> List[Dict[str, Any]]:
    """Bảng gọn cho UI (Streamlit): rank, nguồn, score, preview."""
    rows: List[Dict[str, Any]] = []
    for i, c in enumerate(chunks, 1):
        meta = c.get("metadata") or {}
        raw = c.get("text") or ""
        prev = raw.replace("\n", " ").strip()[:text_snippet]
        if len(raw) > text_snippet:
            prev += "…"
        rows.append({
            "#": i,
            "chunk_id": str(c.get("id", ""))[:36],
            "source": meta.get("source", ""),
            "section": (meta.get("section", "") or "")[:50],
            "score": round(float(c.get("score", 0.0)), 5),
            "preview": prev,
        })
    return rows


def _trace_score_stats(chunks: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    vals: List[float] = []
    for c in chunks:
        try:
            vals.append(float(c.get("score", 0.0)))
        except (TypeError, ValueError):
            continue
    if not vals:
        return None
    return {
        "min": min(vals),
        "max": max(vals),
        "avg": sum(vals) / len(vals),
    }


def _trace_sources_preview(chunks: List[Dict[str, Any]], limit: int = 4) -> str:
    sources: List[str] = []
    for c in chunks:
        src = str((c.get("metadata") or {}).get("source", "")).strip()
        if src and src not in sources:
            sources.append(src)
    if not sources:
        return "none"
    head = sources[:limit]
    tail = ""
    if len(sources) > limit:
        tail = f" (+{len(sources) - limit} more)"
    return ", ".join(head) + tail


def _retrieval_mode_note(retrieval_mode: str) -> str:
    notes = {
        "dense": "**Dense:** embed query (cùng model lúc index) → cosine search trong Chroma.",
        "sparse": "**Sparse (BM25):** tokenize query, chấm điểm keyword trên toàn corpus trong Chroma.",
        "hybrid": "**Hybrid:** dense + BM25, hợp nhất thứ hạng bằng **RRF** (Reciprocal Rank Fusion).",
    }
    return notes.get(
        retrieval_mode,
        "**Unknown mode:** kiểm tra lại retrieval_mode để trace đúng pipeline.",
    )


def _get_retriever(retrieval_mode: str):
    retrievers = {
        "dense": retrieve_dense,
        "sparse": retrieve_sparse,
        "hybrid": retrieve_hybrid,
    }
    if retrieval_mode not in retrievers:
        raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")
    return retrievers[retrieval_mode]


def rag_answer_impl(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    verbose: bool = False,
    trace: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        verbose: In thêm thông tin debug
        trace: Nếu True, thêm `pipeline_steps` — các bước trung gian cho UI (Streamlit).

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng
          - "pipeline_steps" (optional): list các bước khi trace=True

    TODO Sprint 2 — Implement pipeline cơ bản:
    1. Chọn retrieval function dựa theo retrieval_mode
    2. Gọi rerank() nếu use_rerank=True
    3. Truncate về top_k_select chunks
    4. Build context block và grounded prompt
    5. Gọi call_llm() để sinh câu trả lời
    6. Trả về kết quả kèm metadata

    TODO Sprint 3 — Thử các variant:
    - Variant A: đổi retrieval_mode="hybrid"
    - Variant B: bật use_rerank=True
    - Variant C: thêm query transformation trước khi retrieve
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
    }

    steps: List[Dict[str, Any]] = []
    if trace:
        steps.append({
            "step": 1,
            "name": "Câu hỏi",
            "emoji": "1️⃣",
            "detail": _retrieval_mode_note(retrieval_mode),
            "query": query,
        })

    # --- Bước 1: Retrieve ---
    retriever = _get_retriever(retrieval_mode)
    candidates = retriever(query, top_k=top_k_search)

    if not candidates:
        out: Dict[str, Any] = {
            "query": query,
            "answer": ABSTAIN_ANSWER,
            "sources": [],
            "chunks_used": [],
            "config": config,
        }
        if trace:
            steps.append({
                "step": 2,
                "name": "Retrieve",
                "emoji": "2️⃣",
                "detail": f"**{retrieval_mode}** · `top_k_search={top_k_search}` → **0** chunk. Kiểm tra đã `python index.py build` và `EMBEDDING_PROVIDER` khớp lúc index.",
                "table": [],
            })
            out["pipeline_steps"] = steps
        return out

    if trace:
        retrieve_stats = _trace_score_stats(candidates)
        retrieve_score_txt = "N/A"
        if retrieve_stats is not None:
            retrieve_score_txt = (
                f"{retrieve_stats['min']:.4f}..{retrieve_stats['max']:.4f} "
                f"(avg {retrieve_stats['avg']:.4f})"
            )
        retrieve_sources = _trace_sources_preview(candidates)
        retrieve_non_empty = sum(1 for c in candidates if (c.get("text") or "").strip())
        steps.append({
            "step": 2,
            "name": "Retrieve",
            "emoji": "2️⃣",
            "detail": (
                f"**{retrieval_mode}** · lấy **{len(candidates)}** ứng viên (`top_k_search={top_k_search}`). "
                f"Score range: **{retrieve_score_txt}**. "
                f"Chunk có nội dung: **{retrieve_non_empty}/{len(candidates)}**. "
                f"Nguồn: {retrieve_sources}."
            ),
            "stats": {
                "score": retrieve_stats,
                "non_empty_chunks": retrieve_non_empty,
                "sources_preview": retrieve_sources,
            },
            "table": _trace_chunk_rows(candidates),
        })

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    after_retrieve = list(candidates)

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
        select_detail = (
            f"**Cross-encoder** đánh giá cặp (query, chunk), giữ **{len(candidates)}** chunk tốt nhất "
            f"(target `top_k_select={top_k_select}`)."
        )
        select_title = "Rerank"
        select_emoji = "3️⃣"
    else:
        candidates = candidates[:top_k_select]
        select_detail = (
            f"Không rerank — lấy **{len(candidates)}** chunk đầu theo thứ tự điểm retrieve."
        )
        select_title = "Chọn top-k"
        select_emoji = "3️⃣"

    if trace:
        selected_stats = _trace_score_stats(candidates)
        selected_score_txt = "N/A"
        if selected_stats is not None:
            selected_score_txt = (
                f"{selected_stats['min']:.4f}..{selected_stats['max']:.4f} "
                f"(avg {selected_stats['avg']:.4f})"
            )
        selected_sources = _trace_sources_preview(candidates)
        selected_non_empty = sum(1 for c in candidates if (c.get("text") or "").strip())
        dropped = max(0, len(after_retrieve) - len(candidates))
        steps.append({
            "step": 3,
            "name": select_title,
            "emoji": select_emoji,
            "detail": (
                select_detail
                + f" (từ **{len(after_retrieve)}** ứng viên, bỏ **{dropped}**). "
                + f"Score sau chọn: **{selected_score_txt}**. "
                + f"Chunk có nội dung: **{selected_non_empty}/{len(candidates)}**. "
                + f"Nguồn giữ lại: {selected_sources}."
            ),
            "stats": {
                "score": selected_stats,
                "dropped_candidates": dropped,
                "non_empty_chunks": selected_non_empty,
                "sources_preview": selected_sources,
            },
            "table": _trace_chunk_rows(candidates),
        })

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # Chỉ giữ các chunk có text thực sự để tránh gửi context rỗng lên LLM.
    candidates = [c for c in candidates if (c.get("text") or "").strip()]
    if not candidates:
        out: Dict[str, Any] = {
            "query": query,
            "answer": ABSTAIN_ANSWER,
            "sources": [],
            "chunks_used": [],
            "config": config,
        }
        if trace:
            steps.append({
                "step": 4,
                "name": "Context check",
                "emoji": "4️⃣",
                "detail": "Retrieve có kết quả nhưng tất cả chunk sau select đều rỗng. Trả về abstain.",
                "table": [],
            })
            out["pipeline_steps"] = steps
        return out

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    if not context_block.strip():
        out: Dict[str, Any] = {
            "query": query,
            "answer": ABSTAIN_ANSWER,
            "sources": [],
            "chunks_used": [],
            "config": config,
        }
        if trace:
            steps.append({
                "step": 4,
                "name": "Context check",
                "emoji": "4️⃣",
                "detail": "Context block rỗng sau khi đóng gói chunk. Trả về abstain.",
                "table": [],
            })
            out["pipeline_steps"] = steps
        return out

    prompt = build_grounded_prompt(query, context_block)

    if trace:
        prompt_sources = _trace_sources_preview(candidates)
        steps.append({
            "step": 4,
            "name": "Context + prompt",
            "emoji": "4️⃣",
            "detail": (
                f"Đánh số **[1],[2],…**, kèm source/section/score → **{len(context_block)}** ký tự context. "
                f"Prompt grounded tổng **{len(prompt)}** ký tự. "
                f"Nguồn vào prompt: {prompt_sources}."
            ),
            "stats": {
                "prompt_sources_preview": prompt_sources,
            },
            "context_preview": context_block[:1800] + ("…" if len(context_block) > 1800 else ""),
            "prompt_preview": prompt[:1400] + ("…" if len(prompt) > 1400 else ""),
        })

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = (call_llm(prompt) or "").strip()
    if not answer:
        answer = ABSTAIN_ANSWER

    if trace:
        steps.append({
            "step": 5,
            "name": "LLM",
            "emoji": "5️⃣",
            "detail": f"**{LLM_MODEL}** · temperature=0 · trả lời bám context, trích dẫn `[n]` nếu có.",
            "answer_chars": len(answer),
        })

    # --- Bước 5: Extract sources ---
    sources = list({
        c["metadata"].get("source", "unknown")
        for c in candidates
    })

    out = {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }
    if trace:
        out["pipeline_steps"] = steps
    return out


def rag_answer_stream(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    request_id: Optional[str] = None,
    abort_event=None,
):
    """
    Generator variant of rag_answer_impl for Server-Sent Events streaming.

    Yields dicts:
      {"event": "step",  "data": <pipeline_step_dict>}   -- after each pre-LLM step
      {"event": "token", "data": "<text_delta>"}          -- per LLM token
      {"event": "done",  "data": {answer, sources, chunks_used, config, telemetry, request_id}}
      {"event": "error", "data": "<message>"}             -- on failure

    abort_event: optional threading.Event; generator stops between yields when set.
    """
    import threading
    from run_telemetry import RunTelemetry, telemetry_ctx
    import uuid as _uuid
    import time as _time

    if abort_event is None:
        abort_event = threading.Event()

    rid = request_id or str(_uuid.uuid4())
    tel = RunTelemetry("rag_stream", label=retrieval_mode)
    tok = telemetry_ctx.set(tel)

    def _aborted():
        return abort_event.is_set()

    try:
        config = {
            "retrieval_mode": retrieval_mode,
            "top_k_search": top_k_search,
            "top_k_select": top_k_select,
            "use_rerank": use_rerank,
        }

        # ── Step 1: Query ────────────────────────────────────────────
        if retrieval_mode == "sparse":
            retrieve_note = "**Sparse (BM25):** tokenize query, chấm điểm keyword trên toàn corpus trong Chroma."
        elif retrieval_mode == "dense":
            retrieve_note = "**Dense:** embed query → cosine search trong Chroma."
        else:
            retrieve_note = "**Hybrid:** dense + BM25, hợp nhất thứ hạng bằng **RRF**."
        step1 = {"step": 1, "name": "Câu hỏi", "emoji": "1️⃣", "detail": retrieve_note, "query": query}
        yield {"event": "step", "data": step1}
        if _aborted():
            return

        # ── Step 2: Retrieve ─────────────────────────────────────────
        if retrieval_mode == "dense":
            candidates = retrieve_dense(query, top_k=top_k_search)
        elif retrieval_mode == "sparse":
            candidates = retrieve_sparse(query, top_k=top_k_search)
        else:
            candidates = retrieve_hybrid(query, top_k=top_k_search)

        if not candidates:
            step2 = {
                "step": 2, "name": "Retrieve", "emoji": "2️⃣",
                "detail": f"**{retrieval_mode}** → **0** chunk. Kiểm tra đã index và EMBEDDING_PROVIDER khớp.",
                "table": [],
            }
            yield {"event": "step", "data": step2}
            done_data = {
                "answer": "Không đủ dữ liệu trong tài liệu để trả lời.",
                "sources": [], "chunks_used": [], "query": query, "config": config,
                "pipeline_steps": [step1, step2],
                "telemetry": _finish_tel(tel, tok, rid, config, query, ok=True),
                "request_id": rid,
            }
            yield {"event": "done", "data": done_data}
            return

        step2 = {
            "step": 2, "name": "Retrieve", "emoji": "2️⃣",
            "detail": f"**{retrieval_mode}** · lấy **{len(candidates)}** ứng viên (`top_k_search={top_k_search}`).",
            "table": _trace_chunk_rows(candidates),
        }
        yield {"event": "step", "data": step2}
        if _aborted():
            return

        # ── Step 3: Rerank / top-k select ────────────────────────────
        after_retrieve = list(candidates)
        if use_rerank:
            candidates = rerank(query, candidates, top_k=top_k_select)
            select_detail = (
                f"**Cross-encoder** đánh giá cặp (query, chunk), giữ **{len(candidates)}** chunk tốt nhất "
                f"(target `top_k_select={top_k_select}`)."
            )
            select_title, select_emoji = "Rerank", "3️⃣"
        else:
            candidates = candidates[:top_k_select]
            select_detail = f"Không rerank — lấy **{len(candidates)}** chunk đầu theo thứ tự điểm retrieve."
            select_title, select_emoji = "Chọn top-k", "3️⃣"

        step3 = {
            "step": 3, "name": select_title, "emoji": select_emoji,
            "detail": select_detail + f" (từ **{len(after_retrieve)}** ứng viên).",
            "table": _trace_chunk_rows(candidates),
        }
        yield {"event": "step", "data": step3}
        if _aborted():
            return

        # ── Step 4: Context + prompt ──────────────────────────────────
        context_block = build_context_block(candidates)
        prompt = build_grounded_prompt(query, context_block)
        step4 = {
            "step": 4, "name": "Context + prompt", "emoji": "4️⃣",
            "detail": (
                f"Đánh số **[1],[2],…** → **{len(context_block)}** ký tự context. "
                f"Prompt tổng **{len(prompt)}** ký tự."
            ),
            "context_preview": context_block[:1800] + ("…" if len(context_block) > 1800 else ""),
            "prompt_preview": prompt[:1400] + ("…" if len(prompt) > 1400 else ""),
        }
        yield {"event": "step", "data": step4}
        if _aborted():
            return

        # ── Step 5: Stream LLM tokens ─────────────────────────────────
        answer_parts: List[str] = []
        for delta in call_llm_stream(prompt):
            if _aborted():
                break
            answer_parts.append(delta)
            yield {"event": "token", "data": delta}

        answer = "".join(answer_parts).strip()

        step5 = {
            "step": 5, "name": "LLM", "emoji": "5️⃣",
            "detail": f"**{LLM_MODEL}** · temperature=0 · trả lời bám context.",
            "answer_chars": len(answer),
        }

        sources = list({c["metadata"].get("source", "unknown") for c in candidates})
        pipeline_steps = [step1, step2, step3, step4, step5]

        done_data = {
            "answer": answer,
            "sources": sources,
            "chunks_used": candidates,
            "query": query,
            "config": config,
            "pipeline_steps": pipeline_steps,
            "telemetry": _finish_tel(tel, tok, rid, config, query, ok=True),
            "request_id": rid,
        }
        yield {"event": "done", "data": done_data}

    except Exception as exc:
        try:
            _finish_tel(tel, tok, rid, {}, query, ok=False, error=str(exc))
        except Exception:
            pass
        yield {"event": "error", "data": str(exc)}


def _finish_tel(tel, tok, rid: str, config: Dict[str, Any], query: str, ok: bool, error: str = "") -> Dict[str, Any]:
    """Helper: finish telemetry and reset context var; return telemetry dict."""
    from run_telemetry import telemetry_ctx
    entry = tel.finish({
        "request_id": rid,
        "client": "fastapi_stream",
        "query_preview": (query[:200] + "…") if len(query) > 200 else query,
        "retrieval_mode": config.get("retrieval_mode", ""),
        "ok": ok,
        "error": error or None,
    })
    telemetry_ctx.reset(tok)
    return {
        "run_id": entry["run_id"],
        "duration_ms": entry["duration_ms"],
        "cost_usd": entry["cost_usd"],
        "usage": entry["usage"],
    }


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    verbose: bool = False,
    trace: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh. Mỗi lần gọi độc lập được ghi `logs/runs.jsonl`
    (thời gian, token, chi phí ước lượng). Khi đã nằm trong telemetry cha (vd. scorecard),
    chỉ cộng dồn token — một dòng log khi cha `finish`.
    """
    from run_telemetry import RunTelemetry, get_telemetry, telemetry_ctx

    parent = get_telemetry()
    tel: Optional[RunTelemetry] = None
    tok = None
    own = parent is None
    if own:
        tel = RunTelemetry("rag_answer", label=retrieval_mode)
        tok = telemetry_ctx.set(tel)
    out: Optional[Dict[str, Any]] = None
    try:
        out = rag_answer_impl(
            query,
            retrieval_mode,
            top_k_search,
            top_k_select,
            use_rerank,
            verbose,
            trace,
        )
        return out
    finally:
        if own and tel is not None and tok is not None:
            entry = tel.finish(
                {
                    "query_preview": (query[:200] + "…") if len(query) > 200 else query,
                    "retrieval_mode": retrieval_mode,
                    "top_k_search": top_k_search,
                    "top_k_select": top_k_select,
                    "use_rerank": use_rerank,
                }
            )
            if out is not None:
                out["telemetry"] = {
                    "run_id": entry["run_id"],
                    "duration_ms": entry["duration_ms"],
                    "cost_usd": entry["cost_usd"],
                    "usage": entry["usage"],
                }
            telemetry_ctx.reset(tok)


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.

    TODO Sprint 3:
    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "hybrid"]  # Thêm "sparse" sau khi implement

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError as e:
            print(f"Chưa implement: {e}")
        except Exception as e:
            print(f"Lỗi: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Test queries từ data/test_questions.json
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",  # Query không có trong docs → kiểm tra abstain
    ]

    print("\n--- Sprint 2: Test Baseline (Dense) ---")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = rag_answer(query, retrieval_mode="dense", verbose=True)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError:
            print("Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước.")
        except Exception as e:
            print(f"Lỗi: {e}")

    print("\n--- Sprint 3: So sánh strategies (cần OPENAI_API_KEY) ---")
    try:
        compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    except Exception as ex:
        print(f"(Bỏ qua demo compare: {ex})")

    print("\n\nViệc cần làm Sprint 2:")
    print("  1. Implement retrieve_dense() — query ChromaDB")
    print("  2. Implement call_llm() — gọi OpenAI hoặc Gemini")
    print("  3. Chạy rag_answer() với 3+ test queries")
    print("  4. Verify: output có citation không? Câu không có docs → abstain không?")

    print("\nViệc cần làm Sprint 3:")
    print("  1. Chọn 1 trong 3 variants: hybrid, rerank, hoặc query transformation")
    print("  2. Implement variant đó")
    print("  3. Chạy compare_retrieval_strategies() để thấy sự khác biệt")
    print("  4. Ghi lý do chọn biến đó vào docs/tuning-log.md")
