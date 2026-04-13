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
import json
import logging
import re
import sys
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


def _configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


_configure_utf8_stdio()

logger = logging.getLogger(__name__)

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant").strip()
FALLBACK_LLM_PROVIDER = os.getenv("FALLBACK_LLM_PROVIDER", "openai").strip().lower()
FALLBACK_LLM_MODEL = os.getenv("FALLBACK_LLM_MODEL", "gpt-4o-mini").strip()

# Query transform mặc định là local heuristic để giữ token cost thấp.
# Nếu muốn thử LLM rewrite, set QUERY_TRANSFORM_USE_LLM=1 trong .env.
QUERY_TRANSFORM_USE_LLM = os.getenv("QUERY_TRANSFORM_USE_LLM", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
QUERY_TRANSFORM_MAX_VARIANTS = int(os.getenv("QUERY_TRANSFORM_MAX_VARIANTS", "3"))
QUERY_VARIANT_WEIGHT_DECAY = float(os.getenv("QUERY_VARIANT_WEIGHT_DECAY", "0.85"))

# Alias / synonym hints cho query expansion query transform.
QUERY_ALIAS_RULES = [
    (r"\bapproval matrix\b", ["access control sop", "system access approval", "level 3 approval"]),
    (r"\baccess control sop\b", ["approval matrix", "system access approval", "elevated access"]),
    (r"\bsla\b", ["service level agreement", "ticket escalation", "priority 1"]),
    (r"\bp1\b", ["priority 1", "urgent incident", "escalation"]),
    (r"\brefund\b", ["hoàn tiền", "return policy", "policy refund v4"]),
    (r"hoàn tiền", ["refund", "return policy", "policy refund v4"]),
    (r"\bremote\b", ["work from home", "remote work", "team lead approval"]),
    (r"\bcontractor\b", ["third-party vendor", "vendor access", "admin access"]),
    (r"\bpassword\b", ["password reset", "login issue", "helpdesk faq"]),
    (r"\berr-403(-auth)?\b", ["authentication error", "login issue", "helpdesk faq"]),
    (r"\blevel 3\b", ["elevated access", "admin access", "it security"]),
    (r"\bcấp quyền\b", ["access approval", "system access", "access control sop"]),
]

_CROSS_ENCODER_MODEL = None


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Dense retrieval: tìm kiếm theo embedding similarity trong ChromaDB.

    Args:
        query: Câu hỏi của người dùng
        top_k: Số chunk tối đa trả về

    Returns:
        List các dict, mỗi dict là một chunk với:
          - "text": nội dung chunk
          - "metadata": metadata (source, section, effective_date, ...)
          - "score": cosine similarity score
    """
    import chromadb
    from index import get_embedding, CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    for text, meta, dist in zip(documents, metadatas, distances):
        chunks.append({
            "text": text,
            "metadata": meta or {},
            # ChromaDB cosine distance = 1 - similarity → convert back
            "score": float(1.0 - dist),
        })

    return chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).

    Mạnh ở: exact term, mã lỗi, tên riêng (ví dụ: "ERR-403", "P1", "refund")
    Hay hụt: câu hỏi paraphrase, đồng nghĩa

    Yêu cầu: pip install rank-bm25
    """
    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:
        raise ImportError(
            "Thiếu thư viện rank-bm25. Cài đặt: pip install rank-bm25"
        ) from exc

    import chromadb
    from index import CHROMA_DB_DIR

    # Load toàn bộ chunks từ ChromaDB để build BM25 index
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    all_results = collection.get(include=["documents", "metadatas"])
    all_docs = all_results.get("documents") or []
    all_metas = all_results.get("metadatas") or []

    if not all_docs:
        logger.warning("[retrieve_sparse] Không có documents trong ChromaDB")
        return []

    # Tokenize đơn giản (split theo whitespace, lowercase)
    tokenized_corpus = [doc.lower().split() for doc in all_docs]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # Lấy top_k index theo score giảm dần
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    chunks = []
    max_score = scores[top_indices[0]] if top_indices else 1.0
    for idx in top_indices:
        raw_score = float(scores[idx])
        if raw_score <= 0:
            continue  # BM25 = 0 nghĩa là không liên quan
        chunks.append({
            "text": all_docs[idx],
            "metadata": all_metas[idx] if all_metas[idx] is not None else {},
            # Normalize về [0, 1] để dễ so sánh với dense score
            "score": raw_score / max_score if max_score > 0 else 0.0,
        })

    return chunks


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

    RRF score(doc) = dense_weight * 1/(60 + dense_rank)
                   + sparse_weight * 1/(60 + sparse_rank)
    """
    dense_results = retrieve_dense(query, top_k=top_k)
    try:
        sparse_results = retrieve_sparse(query, top_k=top_k)
    except Exception as exc:
        logger.warning("[retrieve_hybrid] BM25 thất bại, fallback về dense only: %s", exc)
        return dense_results

    # Build lookup: text → RRF score (dùng text làm key vì không có chunk id)
    rrf_scores: Dict[str, float] = {}
    chunk_by_text: Dict[str, Dict[str, Any]] = {}

    for rank, chunk in enumerate(dense_results):
        key = chunk["text"]
        rrf_scores[key] = rrf_scores.get(key, 0.0) + dense_weight * (1.0 / (60 + rank))
        chunk_by_text[key] = chunk

    for rank, chunk in enumerate(sparse_results):
        key = chunk["text"]
        rrf_scores[key] = rrf_scores.get(key, 0.0) + sparse_weight * (1.0 / (60 + rank))
        chunk_by_text[key] = chunk

    # Sort theo RRF score giảm dần
    sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)[:top_k]

    merged = []
    for key in sorted_keys:
        chunk = dict(chunk_by_text[key])   # shallow copy
        chunk["score"] = rrf_scores[key]   # override score bằng RRF score
        merged.append(chunk)

    return merged


# =============================================================================
# RERANK (Sprint 3 alternative)
# =============================================================================

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Rerank các candidate chunks bằng cross-encoder ms-marco-MiniLM-L-6-v2.

    Funnel: Search rộng (top-20) → Rerank → Select (top_k)

    Yêu cầu: pip install sentence-transformers
    """
    if not candidates:
        return []

    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise ImportError(
            "Thiếu thư viện sentence-transformers. "
            "Cài đặt: pip install sentence-transformers"
        ) from exc

    global _CROSS_ENCODER_MODEL
    if _CROSS_ENCODER_MODEL is None:
        _CROSS_ENCODER_MODEL = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    model = _CROSS_ENCODER_MODEL
    pairs = [[query, chunk["text"]] for chunk in candidates]
    scores = model.predict(pairs)

    ranked = sorted(
        zip(candidates, scores),
        key=lambda x: float(x[1]),
        reverse=True,
    )

    result = []
    for chunk, score in ranked[:top_k]:
        chunk = dict(chunk)
        chunk["rerank_score"] = float(score)
        result.append(chunk)

    return result


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion":      Thêm từ đồng nghĩa, alias, tên cũ → 2-3 alternative phrasings
      - "decomposition":  Tách query phức tạp thành 2-3 sub-queries
      - "hyde":           Sinh câu trả lời giả (hypothetical document) để embed thay query

    Returns:
        List[str] — gồm query gốc + các query đã biến đổi.
        Luôn giữ query gốc ở index 0 để fallback an toàn.
    """
    def _dedupe_preserve_order(items: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            value = item.strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    def _replace_pattern(text: str, pattern: str, replacement: str) -> str:
        return re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    def _build_local_variants() -> List[str]:
        base_query = query.strip()
        if not base_query:
            return [query]

        lowered = base_query.lower()
        variants = [base_query]

        if strategy == "expansion":
            alias_terms: List[str] = []
            replacements: List[str] = []
            for pattern, synonyms in QUERY_ALIAS_RULES:
                if re.search(pattern, lowered, flags=re.IGNORECASE):
                    alias_terms.extend(synonyms)
                    replacements.append(_replace_pattern(base_query, pattern, synonyms[0]))

            alias_terms = _dedupe_preserve_order(alias_terms)
            replacements = _dedupe_preserve_order(replacements)

            if alias_terms:
                variants.append(f"{base_query} {' '.join(alias_terms[:6])}".strip())
            variants.extend(replacements)

            if not alias_terms and not replacements:
                generic_hints = []
                if any(term in lowered for term in ["phê duyệt", "approval", "access", "quyền"]):
                    generic_hints.append("access control approval")
                if any(term in lowered for term in ["refund", "hoàn tiền", "hoan tien"]):
                    generic_hints.append("refund return policy")
                if any(term in lowered for term in ["sla", "p1", "ticket"]):
                    generic_hints.append("service level agreement priority 1")
                if generic_hints:
                    variants.append(f"{base_query} {' '.join(generic_hints)}")

        elif strategy == "decomposition":
            parts = re.split(r"\b(?:and|or|và|hoặc)\b|[,;/+]", base_query, flags=re.IGNORECASE)
            subqueries = [part.strip() for part in parts if len(part.strip()) >= 4]
            if len(subqueries) >= 2:
                variants.extend(subqueries[: max(1, QUERY_TRANSFORM_MAX_VARIANTS - 1)])
            else:
                variants.append(f"{base_query} key policy exception details")

        elif strategy == "hyde":
            hints: List[str] = []
            for pattern, synonyms in QUERY_ALIAS_RULES:
                if re.search(pattern, lowered, flags=re.IGNORECASE):
                    hints.extend(synonyms[:2])
            hints = _dedupe_preserve_order(hints)
            summary = " ".join(hints[:5]) if hints else "policy details, approval steps, exceptions"
            variants.append(
                f"This question is about {summary}. The relevant document should explain the rule, "
                f"approval steps, exceptions, and time limits for: {base_query}"
            )

        else:
            logger.warning("[transform_query] Strategy '%s' không hỗ trợ, dùng query gốc", strategy)
            return [base_query]

        return _dedupe_preserve_order(variants)[:QUERY_TRANSFORM_MAX_VARIANTS]

    if not QUERY_TRANSFORM_USE_LLM:
        return _build_local_variants()

    strategy_prompts = {
        "expansion": (
            f"Given the search query: '{query}'\n"
            "Generate 2 alternative phrasings or related terms that could help retrieve "
            "relevant documents (e.g. synonyms, abbreviations, related concepts).\n"
            "Respond in the SAME language as the query.\n"
            'Output ONLY a JSON array of strings, e.g. ["alt1", "alt2"]'
        ),
        "decomposition": (
            f"Break down this complex query into 2-3 simpler sub-queries: '{query}'\n"
            "Each sub-query should be self-contained and answerable independently.\n"
            "Respond in the SAME language as the query.\n"
            'Output ONLY a JSON array of strings, e.g. ["sub1", "sub2"]'
        ),
        "hyde": (
            f"Write a short hypothetical document passage (2-3 sentences) that would "
            f"directly answer this query: '{query}'\n"
            "This passage will be used as a search query to find similar real documents.\n"
            "Respond in the SAME language as the query.\n"
            'Output ONLY a JSON array with one string, e.g. ["hypothetical passage here"]'
        ),
    }

    if strategy not in strategy_prompts:
        return _build_local_variants()

    try:
        raw = call_llm(strategy_prompts[strategy])
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        alternatives = json.loads(cleaned)
        if not isinstance(alternatives, list):
            raise ValueError("LLM không trả về list")
        seen = {query}
        result = [query]
        for alt in alternatives:
            if isinstance(alt, str) and alt.strip() and alt not in seen:
                result.append(alt.strip())
                seen.add(alt)
        return result[:QUERY_TRANSFORM_MAX_VARIANTS]
    except Exception as exc:
        logger.warning("[transform_query] Thất bại (%s), dùng local fallback: %s", strategy, exc)
        return _build_local_variants()


def _normalize_retrieval_mode(
    retrieval_mode: str,
    use_rerank: bool,
    use_query_transform: bool,
) -> tuple[str, bool, bool]:
    """Chuẩn hóa retrieval mode để hỗ trợ alias rerank/query_transform."""
    mode = (retrieval_mode or "dense").strip().lower()

    if mode in {"rerank", "rerank_dense"}:
        return "dense", True, use_query_transform
    if mode in {"query_transform", "transform", "qt"}:
        return "dense", use_rerank, True
    if mode in {"dense", "sparse", "hybrid"}:
        return mode, use_rerank, use_query_transform

    raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")


def _retrieve_single_query(
    query: str,
    retrieval_mode: str,
    top_k: int,
    dense_weight: float,
    sparse_weight: float,
) -> List[Dict[str, Any]]:
    if retrieval_mode == "dense":
        return retrieve_dense(query, top_k=top_k)
    if retrieval_mode == "sparse":
        return retrieve_sparse(query, top_k=top_k)
    if retrieval_mode == "hybrid":
        return retrieve_hybrid(
            query,
            top_k=top_k,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
        )
    raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")


def _fuse_query_variant_results(
    query_groups: List[Dict[str, Any]],
    top_k: int,
) -> List[Dict[str, Any]]:
    """Fuse kết quả từ nhiều query variants bằng Reciprocal Rank Fusion."""
    rrf_scores: Dict[str, float] = {}
    chunk_by_text: Dict[str, Dict[str, Any]] = {}

    for group in query_groups:
        query_weight = float(group.get("weight", 1.0))
        query_text = group.get("query", "")
        results = group.get("results", []) or []

        for rank, chunk in enumerate(results):
            key = chunk["text"]
            contribution = query_weight * (1.0 / (60 + rank))
            rrf_scores[key] = rrf_scores.get(key, 0.0) + contribution

            stored = chunk_by_text.get(key)
            if stored is None or contribution > stored.get("_fuse_contribution", -1.0):
                clone = dict(chunk)
                clone["_fuse_contribution"] = contribution
                clone["_query_variant"] = query_text
                chunk_by_text[key] = clone

    sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)[:top_k]

    merged: List[Dict[str, Any]] = []
    for key in sorted_keys:
        chunk = dict(chunk_by_text[key])
        chunk["score"] = rrf_scores[key]
        merged.append(chunk)

    return merged


def retrieve_candidates(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    use_query_transform: bool = False,
    query_transform_strategy: str = "expansion",
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> Dict[str, Any]:
    """Retrieve candidates cho một query, hỗ trợ hybrid/rerank/query-transform kết hợp."""
    base_mode, effective_rerank, effective_transform = _normalize_retrieval_mode(
        retrieval_mode=retrieval_mode,
        use_rerank=use_rerank,
        use_query_transform=use_query_transform,
    )

    query_variants = transform_query(query, strategy=query_transform_strategy) if effective_transform else [query.strip()]
    query_variants = [variant.strip() for variant in query_variants if variant and variant.strip()]
    query_variants = list(dict.fromkeys(query_variants)) or [query.strip()]

    query_groups = []
    for idx, query_variant in enumerate(query_variants):
        query_weight = max(0.5, QUERY_VARIANT_WEIGHT_DECAY ** idx)
        results = _retrieve_single_query(
            query=query_variant,
            retrieval_mode=base_mode,
            top_k=top_k_search,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
        )
        query_groups.append({
            "query": query_variant,
            "weight": query_weight,
            "results": results,
        })

    candidate_pool = _fuse_query_variant_results(query_groups, top_k=top_k_search)

    if effective_rerank:
        selected_candidates = rerank(query, candidate_pool, top_k=top_k_select)
    else:
        selected_candidates = candidate_pool[:top_k_select]

    return {
        "query": query,
        "query_variants": query_variants,
        "base_mode": base_mode,
        "retrieval_mode": retrieval_mode,
        "use_rerank": effective_rerank,
        "use_query_transform": effective_transform,
        "query_transform_strategy": query_transform_strategy if effective_transform else "",
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "candidate_pool": candidate_pool,
        "selected_candidates": selected_candidates,
    }


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
        if score > 0:
            header += f" | score={score:.2f}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xây dựng grounded prompt theo 4 quy tắc từ slide:
    1. Evidence-only: Chỉ trả lời từ retrieved context
    2. Abstain: Thiếu context thì nói không đủ dữ liệu
    3. Citation: Gắn source/section khi có thể
    4. Short, clear, stable: Output ngắn, rõ, nhất quán
    """
    prompt = f"""Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời.

    Primary provider: Groq (OpenAI-compatible API) nếu được cấu hình.
    Fallback provider: OpenAI với model gpt-4o-mini.

    Hỗ trợ thêm Gemini để giữ tương thích với eval.py.

    Lưu ý: Dùng temperature=0 để output ổn định cho evaluation.
    """
    def _call_openai_compatible(api_key: str, model_name: str, base_url: Optional[str] = None) -> str:
        from openai import OpenAI

        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        return response.choices[0].message.content or ""

    def _call_gemini(model_name: str) -> str:
        import google.generativeai as genai  # type: ignore[reportMissingImports]

        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.0, max_output_tokens=512),
        )
        return getattr(response, "text", "") or ""

    def _call_provider(provider: str, model_name: str) -> str:
        if provider == "groq":
            groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
            if not groq_api_key:
                raise RuntimeError("Missing GROQ_API_KEY for Groq provider")
            return _call_openai_compatible(
                api_key=groq_api_key,
                model_name=model_name,
                base_url="https://api.groq.com/openai/v1",
            )

        if provider == "openai":
            openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not openai_api_key:
                raise RuntimeError("Missing OPENAI_API_KEY for OpenAI provider")
            return _call_openai_compatible(api_key=openai_api_key, model_name=model_name)

        if provider == "gemini":
            return _call_gemini(model_name)

        raise ValueError(f"Unsupported LLM provider: {provider}")

    try:
        return _call_provider(LLM_PROVIDER, LLM_MODEL)
    except Exception as primary_error:
        if FALLBACK_LLM_PROVIDER == LLM_PROVIDER and FALLBACK_LLM_MODEL == LLM_MODEL:
            raise

        logger.warning(
            "[call_llm] Primary provider '%s' failed: %s — falling back to '%s'",
            LLM_PROVIDER, primary_error, FALLBACK_LLM_PROVIDER,
        )
        return _call_provider(FALLBACK_LLM_PROVIDER, FALLBACK_LLM_MODEL)


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    use_query_transform: bool = False,
    query_transform_strategy: str = "expansion",
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid" | "rerank" | "query_transform"
        retrieval_mode: "dense" | "sparse" | "hybrid" | "rerank" | "query_transform"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        use_query_transform: Có rewrite query trước khi retrieve không
        query_transform_strategy: expansion | decomposition | hyde
        dense_weight: Trọng số dense trong hybrid retrieval
        sparse_weight: Trọng số sparse trong hybrid retrieval
        verbose: In thêm thông tin debug

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "use_query_transform": use_query_transform,
        "query_transform_strategy": query_transform_strategy,
        "dense_weight": dense_weight,
        "sparse_weight": sparse_weight,
    }

    retrieval_bundle = retrieve_candidates(
        query=query,
        retrieval_mode=retrieval_mode,
        top_k_search=top_k_search,
        top_k_select=top_k_select,
        use_rerank=use_rerank,
        use_query_transform=use_query_transform,
        query_transform_strategy=query_transform_strategy,
        dense_weight=dense_weight,
        sparse_weight=sparse_weight,
    )
    candidates = retrieval_bundle["selected_candidates"]
    retrieval_mode_effective = retrieval_bundle["base_mode"]
    query_variants = retrieval_bundle.get("query_variants", [query])

    if verbose:
        print(f"\n[RAG] Query: {query}")
        if len(query_variants) > 1:
            print(f"[RAG] Query variants: {query_variants}")
        print(
            f"[RAG] Retrieved {len(retrieval_bundle.get('candidate_pool', []))} candidates "
            f"(mode={retrieval_mode} -> base={retrieval_mode_effective})"
        )
        for i, c in enumerate(retrieval_bundle.get("candidate_pool", [])[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract sources ---
    sources = list({
        c["metadata"].get("source", "unknown")
        for c in candidates
    })

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "retrieval_bundle": retrieval_bundle,
        "config": config,
    }


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.

    Chạy hàm này để thấy sự khác biệt giữa dense, hybrid, rerank,
    và query transform.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule: Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = [
        (
            "baseline_dense",
            {
                "retrieval_mode": "dense",
                "use_rerank": False,
                "use_query_transform": False,
            },
        ),
        (
            "hybrid_rrf",
            {
                "retrieval_mode": "hybrid",
                "use_rerank": False,
                "use_query_transform": False,
                "dense_weight": 0.8,
                "sparse_weight": 0.2,
            },
        ),
        (
            "rerank_dense",
            {
                "retrieval_mode": "rerank",
                "use_rerank": True,
                "use_query_transform": False,
            },
        ),
        (
            "query_transform_dense",
            {
                "retrieval_mode": "query_transform",
                "use_rerank": False,
                "use_query_transform": True,
                "query_transform_strategy": "expansion",
            },
        ),
    ]

    for label, config in strategies:
        print(f"\n--- Strategy: {label} ---")
        try:
            bundle = retrieve_candidates(query, **config)
            selected = bundle["selected_candidates"]
            context_block = build_context_block(selected)
            est_tokens = max(1, len(context_block) // 4)
            print(f"Base mode: {bundle['base_mode']} | rerank={bundle['use_rerank']} | transform={bundle['use_query_transform']}")
            print(f"Query variants: {bundle['query_variants']}")
            print(f"Selected sources: {[c['metadata'].get('source', '?') for c in selected]}")
            print(f"Selected scores: {[round(float(c.get('score', 0)), 3) for c in selected]}")
            print(f"Estimated prompt tokens: {est_tokens}")
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

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",
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

    # Uncomment sau khi Sprint 3 hoàn thành:
    # print("\n--- Sprint 3: So sánh strategies ---")
    # compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    # compare_retrieval_strategies("ERR-403-AUTH")