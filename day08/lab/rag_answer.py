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
import importlib
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 6  # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3  # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

# HYBRID-specific: Giảm số chunk vì hybrid gọi cả dense + sparse (tốn token/quota)
TOP_K_HYBRID = 4  # Giảm xuống vì hybrid đã có kết hợp, đỡ cần tìm rộng

# LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3-flash-preview")

# Retry config
MAX_LLM_RETRIES = 3
INITIAL_RETRY_WAIT = 2.0  # seconds, exponential backoff
MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1024"))

_SPARSE_INDEX_CACHE: Dict[str, Any] = {}


def _get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""


def _extract_gemini_text(response: Any) -> str:
    """Lấy đầy đủ text từ Gemini response, kể cả khi có nhiều parts/candidates."""
    texts: List[str] = []

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text:
                texts.append(part_text)

    if texts:
        return "\n".join(t.strip() for t in texts if t and t.strip()).strip()

    # Fallback cho SDK versions trả text trực tiếp
    direct_text = getattr(response, "text", None)
    return (direct_text or "").strip()


def _tokenize_for_bm25(text: str) -> List[str]:
    """Tokenize text cho BM25 theo cách đơn giản, giữ được Unicode/tiếng Việt."""
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def _load_sparse_corpus() -> List[Dict[str, Any]]:
    """Load toàn bộ chunks từ ChromaDB để dùng cho BM25 sparse retrieval."""
    chromadb = importlib.import_module("chromadb")
    from index import CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    results = collection.get(include=["documents", "metadatas"])

    documents = results.get("documents", []) or []
    metadatas = results.get("metadatas", []) or []
    ids = results.get("ids", []) or []

    corpus = []
    for idx, (doc, meta) in enumerate(zip(documents, metadatas)):
        corpus.append(
            {
                "id": ids[idx] if idx < len(ids) else f"chunk_{idx}",
                "text": doc or "",
                "metadata": meta or {},
            }
        )

    return corpus


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

    TODO Sprint 2:
    1. Embed query bằng cùng model đã dùng khi index (xem index.py)
    2. Query ChromaDB với embedding đó
    3. Trả về kết quả kèm score

    Gợi ý:
        import chromadb
        from index import get_embedding, CHROMA_DB_DIR

        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")

        query_embedding = get_embedding(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        # Lưu ý: distances trong ChromaDB cosine = 1 - similarity
        # Score = 1 - distance
    """
    chromadb = importlib.import_module("chromadb")
    from index import get_embedding, CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    query_embedding = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    retrieved = []
    for doc, meta, distance in zip(docs, metas, distances):
        score = 1 - float(distance)  # Chroma cosine distance -> similarity
        retrieved.append(
            {
                "text": doc,
                "metadata": meta or {},
                "score": score,
            }
        )

    # sort giảm dần theo score để chắc chắn
    retrieved.sort(key=lambda x: x["score"], reverse=True)
    return retrieved
    # raise NotImplementedError(
    #     "TODO Sprint 2: Implement retrieve_dense().\n"
    #     "Tham khảo comment trong hàm để biết cách query ChromaDB."
    # )


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================


def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).

    Mạnh ở: exact term, mã lỗi, tên riêng (ví dụ: "ERR-403", "P1", "refund")
    Hay hụt: câu hỏi paraphrase, đồng nghĩa

    TODO Sprint 3 (nếu chọn hybrid):
    1. Cài rank_bm25: pip install rank-bm25
    2. Load tất cả chunks từ ChromaDB (hoặc rebuild từ docs)
    3. Tokenize và tạo BM25Index
    4. Query và trả về top_k kết quả

    Gợi ý:
        from rank_bm25 import BM25Okapi
        corpus = [chunk["text"] for chunk in all_chunks]
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    """
    cache_key = "default"

    BM25Okapi = importlib.import_module("rank_bm25").BM25Okapi

    if cache_key not in _SPARSE_INDEX_CACHE:
        corpus = _load_sparse_corpus()
        tokenized_corpus = [_tokenize_for_bm25(chunk["text"]) for chunk in corpus]
        _SPARSE_INDEX_CACHE[cache_key] = {
            "corpus": corpus,
            "bm25": BM25Okapi(tokenized_corpus),
        }

    cache = _SPARSE_INDEX_CACHE[cache_key]
    corpus = cache["corpus"]
    bm25 = cache["bm25"]

    if not corpus:
        return []

    tokenized_query = _tokenize_for_bm25(query)
    if not tokenized_query:
        return []

    scores = bm25.get_scores(tokenized_query)
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[
        :top_k
    ]

    results: List[Dict[str, Any]] = []
    for idx in ranked_indices:
        score = float(scores[idx])
        if score <= 0:
            continue
        chunk = corpus[idx]
        results.append(
            {
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "score": score,
            }
        )

    return results


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
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    if not dense_results and not sparse_results:
        return []

    def chunk_key(chunk: Dict[str, Any]) -> str:
        metadata = chunk.get("metadata", {}) or {}
        source = metadata.get("source", "")
        section = metadata.get("section", "")
        text = chunk.get("text", "")
        return f"{source}||{section}||{text}"

    dense_rank_map = {
        chunk_key(chunk): rank for rank, chunk in enumerate(dense_results, start=1)
    }
    sparse_rank_map = {
        chunk_key(chunk): rank for rank, chunk in enumerate(sparse_results, start=1)
    }

    merged: Dict[str, Dict[str, Any]] = {}
    all_chunks = dense_results + sparse_results

    for chunk in all_chunks:
        key = chunk_key(chunk)
        if key not in merged:
            merged[key] = {
                "text": chunk.get("text", ""),
                "metadata": chunk.get("metadata", {}) or {},
                "score": 0.0,
            }

        dense_rank = dense_rank_map.get(key)
        sparse_rank = sparse_rank_map.get(key)

        dense_score = (
            dense_weight * (1.0 / (60.0 + dense_rank))
            if dense_rank is not None
            else 0.0
        )
        sparse_score = (
            sparse_weight * (1.0 / (60.0 + sparse_rank))
            if sparse_rank is not None
            else 0.0
        )
        merged[key]["score"] += dense_score + sparse_score

        if dense_rank is not None and "dense_rank" not in merged[key]:
            merged[key]["dense_rank"] = dense_rank
        if sparse_rank is not None and "sparse_rank" not in merged[key]:
            merged[key]["sparse_rank"] = sparse_rank

    fused_results = sorted(
        merged.values(),
        key=lambda chunk: chunk["score"],
        reverse=True,
    )

    return fused_results[:top_k]


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
    # TODO Sprint 3: Implement rerank
    # Tạm thời trả về top_k đầu tiên (không rerank)
    from sentence_transformers import CrossEncoder

    model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    pairs = [[query, chunk["text"]] for chunk in candidates]
    scores = model.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in ranked[:top_k]]


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

        # TODO: Tùy chỉnh format nếu muốn (thêm effective_date, department, ...)
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

    TODO Sprint 2:
    Đây là prompt baseline. Trong Sprint 3, bạn có thể:
    - Thêm hướng dẫn về format output (JSON, bullet points)
    - Thêm ngôn ngữ phản hồi (tiếng Việt vs tiếng Anh)
    - Điều chỉnh tone phù hợp với use case (CS helpdesk, IT support)
    """
    prompt = f"""
You are an assistant that answers questions based ONLY on the retrieved context.
Strict rules:
1. Use only the information provided in the context.
2. If the context is insufficient to answer with certainty, respond exactly with: "Không đủ dữ liệu."
3. Do not make assumptions or fabricate any information.
4. When providing an answer, include citations using chunk indices such as [1], [2].
5. When possible, include the corresponding source/section from the cited chunks.
6. Keep the answer concise, clear, and in the same language as the question.

Question:
{query}

Context:
{context_block}

Answer:
"""
    return prompt


def call_llm(
    prompt: str,
    max_retries: int = MAX_LLM_RETRIES,
    initial_wait: float = INITIAL_RETRY_WAIT,
) -> str:
    """
    Gọi LLM để sinh câu trả lời với retry logic cho 503 errors.

    Args:
        prompt: Prompt để gửi tới LLM
        max_retries: Số lần retry tối đa (default=MAX_LLM_RETRIES env var)
        initial_wait: Thời gian chờ ban đầu (default=INITIAL_RETRY_WAIT), tăng exponentially

    Implements exponential backoff:
      - Retry 1: chờ 1s
      - Retry 2: chờ 2s
      - Retry 3: chờ 4s
      - Retry 4: chờ 8s
      - Retry 5: chờ 16s

    Option A — OpenAI (cần OPENAI_API_KEY):
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        return response.choices[0].message.content

    Option B — Google Gemini (cần GOOGLE_API_KEY):
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text

    Lưu ý: Dùng temperature=0 để output ổn định cho evaluation.
    """
    from google import genai
    from google.genai import types

    api_key = _get_gemini_api_key()
    if not api_key:
        raise ValueError("Thiếu GEMINI_API_KEY trong file .env")

    retry_count = 0
    wait_time = initial_wait
    last_error = None

    while retry_count <= max_retries:
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                ),
            )

            text = _extract_gemini_text(response)
            if text and text.strip():
                if retry_count > 0:
                    print(f"[LLM] ✓ Thành công sau {retry_count} retry(s)")
                return text.strip()

            return "Không đủ dữ liệu."

        except Exception as e:
            error_str = str(e)
            last_error = e

            # Check nếu là 503 UNAVAILABLE error
            if "503" in error_str or "UNAVAILABLE" in error_str:
                if retry_count < max_retries:
                    print(
                        f"[LLM] ⚠ 503 Error (attempt {retry_count + 1}/{max_retries}), chờ {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    retry_count += 1
                    wait_time *= 2  # Exponential backoff
                    continue
            raise e

    # Nếu hết retries
    if last_error:
        print(f"[LLM] ✗ Thất bại sau {max_retries} retry(s)")
        raise last_error

    return "Không đủ dữ liệu."
    # raise NotImplementedError(
    #     "TODO Sprint 2: Implement call_llm().\n"
    #     "Chọn Option A (OpenAI) hoặc Option B (Gemini) trong TODO comment."
    # )


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

    # --- Bước 1: Retrieve ---
    # Optimization: Giảm top_k cho hybrid vì nó gọi cả dense + sparse
    effective_top_k = top_k_search
    if retrieval_mode == "hybrid":
        effective_top_k = TOP_K_HYBRID
        if verbose:
            print(
                f"[RAG] Dùng TOP_K_HYBRID={TOP_K_HYBRID} (thay vì TOP_K_SEARCH={top_k_search}) để tối ưu hóa"
            )

    if retrieval_mode == "dense":
        candidates = retrieve_dense(query, top_k=effective_top_k)
    elif retrieval_mode == "sparse":
        candidates = retrieve_sparse(query, top_k=effective_top_k)
    elif retrieval_mode == "hybrid":
        candidates = retrieve_hybrid(query, top_k=effective_top_k)
    else:
        raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(
                f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}"
            )

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
    sources = list({c["metadata"].get("source", "unknown") for c in candidates})

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

    TODO Sprint 3:
    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print("=" * 60)

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
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",  # Query không có trong docs → kiểm tra abstain
    ]

    # print("\n--- Sprint 2: Test Baseline (Dense) ---")
    # for query in test_queries:
    #     print(f"\nQuery: {query}")
    #     try:
    #         result = rag_answer(query, retrieval_mode="dense", verbose=True)
    #         print(f"Answer: {result['answer']}")
    #         print(f"Sources: {result['sources']}")
    #     except NotImplementedError:
    #         print("Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước.")
    #     except Exception as e:
    #         print(f"Lỗi: {e}")

    # Uncomment sau khi Sprint 3 hoàn thành:
    print("\n--- Sprint 3: So sánh strategies (với optimization) ---")
    print(f"\n[INFO] OPTIMIZATION:")
    print(
        f"  • call_llm() có retry logic với exponential backoff (max_retries={MAX_LLM_RETRIES})"
    )
    print(
        f"  • Hybrid retrieval dùng TOP_K_HYBRID={TOP_K_HYBRID} (not {TOP_K_SEARCH}) để giảm token cost"
    )
    print(f"  • Dense/Sparse dùng TOP_K_SEARCH={TOP_K_SEARCH}")

    compare_retrieval_strategies("Ai phải phê duyệt để cấp quyền Level 3?")
    # print("\n\nViệc cần làm Sprint 2:")
    # print("  1. Implement retrieve_dense() — query ChromaDB")
    # print("  2. Implement call_llm() — gọi OpenAI hoặc Gemini")
    # print("  3. Chạy rag_answer() với 3+ test queries")
    # print("  4. Verify: output có citation không? Câu không có docs → abstain không?")

    # print("\nViệc cần làm Sprint 3:")
    # print("  1. Chọn 1 trong 3 variants: hybrid, rerank, hoặc query transformation")
    # print("  2. Implement variant đó")
    # print("  3. Chạy compare_retrieval_strategies() để thấy sự khác biệt")
    # print("  4. Ghi lý do chọn biến đó vào docs/tuning-log.md")
