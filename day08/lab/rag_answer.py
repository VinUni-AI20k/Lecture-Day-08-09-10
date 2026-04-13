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
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

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
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

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
    all_docs = all_results.get("documents", [])
    all_metas = all_results.get("metadatas", [])

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
            "metadata": all_metas[idx] or {},
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

    model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
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
    STRATEGY_PROMPTS = {
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

    if strategy not in STRATEGY_PROMPTS:
        logger.warning("[transform_query] Strategy '%s' không hỗ trợ, dùng query gốc", strategy)
        return [query]

    try:
        raw = call_llm(STRATEGY_PROMPTS[strategy])
        # Bóc markdown fence nếu có
        import re
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        alternatives = json.loads(cleaned)
        if not isinstance(alternatives, list):
            raise ValueError("LLM không trả về list")
        # Giữ query gốc ở đầu, dedup, loại chuỗi rỗng
        seen = {query}
        result = [query]
        for alt in alternatives:
            if isinstance(alt, str) and alt.strip() and alt not in seen:
                result.append(alt.strip())
                seen.add(alt)
        return result
    except Exception as exc:
        logger.warning("[transform_query] Thất bại (%s), dùng query gốc: %s", strategy, exc)
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
        import google.generativeai as genai

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
    verbose: bool = False,
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
    }

    # --- Bước 1: Retrieve ---
    if retrieval_mode == "dense":
        candidates = retrieve_dense(query, top_k=top_k_search)
    elif retrieval_mode == "sparse":
        candidates = retrieve_sparse(query, top_k=top_k_search)
    elif retrieval_mode == "hybrid":
        candidates = retrieve_hybrid(query, top_k=top_k_search)
    else:
        raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

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
        "config": config,
    }


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.

    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule: Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "hybrid"]

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