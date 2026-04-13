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
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation [1]
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# =============================================================================
# MODULE-LEVEL CACHE (tránh re-init mỗi lần gọi)
# =============================================================================

_chroma_collection = None   # ChromaDB collection singleton
_bm25_index = None          # BM25 index cache
_bm25_docs = None           # Docs tương ứng với BM25 index
_bm25_metas = None          # Metadata tương ứng
_cross_encoder = None       # CrossEncoder model cache


def _get_collection():
    """Trả về ChromaDB collection, khởi tạo một lần duy nhất."""
    global _chroma_collection
    if _chroma_collection is None:
        import chromadb
        from index import CHROMA_DB_DIR
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        _chroma_collection = client.get_collection("rag_lab")
    return _chroma_collection


def _get_bm25():
    """Trả về (bm25, docs, metas), build một lần duy nhất."""
    global _bm25_index, _bm25_docs, _bm25_metas
    if _bm25_index is None:
        from rank_bm25 import BM25Okapi
        collection = _get_collection()
        results = collection.get(include=["documents", "metadatas"])
        _bm25_docs = results["documents"]
        _bm25_metas = results["metadatas"]
        tokenized_corpus = [doc.lower().split() for doc in _bm25_docs]
        _bm25_index = BM25Okapi(tokenized_corpus)
    return _bm25_index, _bm25_docs, _bm25_metas


def _get_cross_encoder():
    """Trả về CrossEncoder model, load một lần duy nhất."""
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


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
    from index import get_embedding

    collection = _get_collection()
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    chunks = []
    if results["documents"] and len(results["documents"][0]) > 0:
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]
        
        for doc, meta, dist in zip(docs, metas, dists):
            chunks.append({
                "text": doc,
                "metadata": meta,
                "score": 1.0 - dist,  # cosine similarity
            })
            
    return chunks


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
    try:
        bm25, docs, metas = _get_bm25()
    except ImportError:
        print("[retrieve_sparse] Thiếu rank_bm25. Hãy cài: pip install rank-bm25")
        return []

    if not docs:
        return []

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    
    chunks = []
    for i in top_indices:
        chunks.append({
            "text": docs[i],
            "metadata": metas[i],
            "score": float(scores[i]), # BM25 score
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
    dense_results = retrieve_dense(query, top_k=top_k * 2)
    sparse_results = retrieve_sparse(query, top_k=top_k * 2)

    # RRF dictionary: key = chunk text, value = (metadata, rrf_score)
    # Using text as key assuming it's reasonably unique
    rrf_map = {}
    
    def rrf_score(rank, weight):
        return weight * (1.0 / (60 + rank))
        
    for i, chunk in enumerate(dense_results):
        txt = chunk["text"]
        if txt not in rrf_map:
            rrf_map[txt] = {"metadata": chunk["metadata"], "score": 0.0}
        rrf_map[txt]["score"] += rrf_score(i + 1, dense_weight)
        
    for i, chunk in enumerate(sparse_results):
        txt = chunk["text"]
        if txt not in rrf_map:
            rrf_map[txt] = {"metadata": chunk["metadata"], "score": 0.0}
        rrf_map[txt]["score"] += rrf_score(i + 1, sparse_weight)

    chunks = [
        {"text": txt, "metadata": data["metadata"], "score": data["score"]}
        for txt, data in rrf_map.items()
    ]
    
    return sorted(chunks, key=lambda x: x["score"], reverse=True)[:top_k]


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
        
    try:
        model = _get_cross_encoder()
    except ImportError:
        print("[rerank] Thiếu sentence_transformers. Bỏ qua rerank.")
        return candidates[:top_k]

    pairs = [[query, chunk["text"]] for chunk in candidates]
    scores = model.predict(pairs)
    
    for chunk, score in zip(candidates, scores):
        chunk["rerank_score"] = float(score)
        
    ranked = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
    return ranked[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion": Thêm từ đồng nghĩa, alias, tên cũ — tốt cho alias/tên cũ
      - "decomposition": Tách query phức tạp thành 2-3 sub-queries — tốt cho câu hỏi đa ý
      - "hyde": Sinh câu trả lời giả (Hypothetical Document Embedding) để embed thay query

    Returns:
        List[str] — luôn bao gồm query gốc + các query biến đổi.
        Ít nhất 1 phần tử (query gốc) ngay cả khi LLM thất bại.
    """
    import json
    import re

    if strategy == "expansion":
        prompt = f"""Bạn là trợ lý hỗ trợ tìm kiếm tài liệu nội bộ.
Cho query: "{query}"

Sinh ra 2-3 cách diễn đạt khác hoặc alias có thể xuất hiện trong tài liệu.
Ví dụ: "Approval Matrix" → ["Ma trận phê duyệt", "Access Control SOP", "quy trình cấp quyền"]

Chỉ trả về JSON array of strings, không giải thích thêm.
Output:"""

    elif strategy == "decomposition":
        prompt = f"""Bạn là trợ lý hỗ trợ tìm kiếm tài liệu nội bộ.
Cho query phức tạp: "{query}"

Tách thành 2-3 sub-query đơn giản hơn, mỗi câu hỏi một khía cạnh.
Ví dụ: "Ai duyệt và mất bao lâu để cấp quyền Level 3?" →
["Ai phê duyệt quyền Level 3?", "Thời gian xử lý cấp quyền Level 3 là bao lâu?"]

Chỉ trả về JSON array of strings, không giải thích thêm.
Output:"""

    elif strategy == "hyde":
        prompt = f"""Bạn là trợ lý hỗ trợ tìm kiếm tài liệu nội bộ.
Cho query: "{query}"

Hãy viết 1 đoạn văn ngắn (2-3 câu) mô phỏng nội dung của tài liệu có thể trả lời câu hỏi này.
Viết như thể đây là trích đoạn từ tài liệu chính sách/FAQ thực tế.

Chỉ trả về JSON array với 1 phần tử là đoạn văn đó, không giải thích thêm.
Output:"""

    else:
        raise ValueError(f"strategy không hợp lệ: {strategy}. Chọn: expansion | decomposition | hyde")

    try:
        raw = call_llm(prompt)
        # Lấy phần JSON từ response (bỏ markdown code block nếu có)
        json_match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if json_match:
            variants = json.loads(json_match.group())
        else:
            variants = json.loads(raw.strip())

        if not isinstance(variants, list):
            return [query]

        # Luôn giữ query gốc ở đầu, thêm variants (bỏ duplicate)
        all_queries = [query]
        for v in variants:
            if isinstance(v, str) and v.strip() and v.strip() != query:
                all_queries.append(v.strip())
        return all_queries

    except Exception as e:
        print(f"[transform_query] Lỗi parse LLM output ({strategy}): {e}")
        return [query]


def retrieve_with_transform(
    query: str,
    strategy: str = "expansion",
    retrieval_mode: str = "dense",
    top_k: int = TOP_K_SEARCH,
) -> List[Dict[str, Any]]:
    """
    Retrieve sau khi transform query: chạy retrieve cho từng sub-query,
    merge kết quả và dedup theo text, giữ score cao nhất cho mỗi chunk.

    Args:
        query: Query gốc
        strategy: Query transform strategy ("expansion" | "decomposition" | "hyde")
        retrieval_mode: Retrieval mode cho từng sub-query
        top_k: Số chunk trả về sau merge
    """
    transformed_queries = transform_query(query, strategy=strategy)

    seen: Dict[str, Dict[str, Any]] = {}
    for q in transformed_queries:
        if retrieval_mode == "dense":
            results = retrieve_dense(q, top_k=top_k)
        elif retrieval_mode == "sparse":
            results = retrieve_sparse(q, top_k=top_k)
        elif retrieval_mode == "hybrid":
            results = retrieve_hybrid(q, top_k=top_k)
        else:
            results = retrieve_dense(q, top_k=top_k)

        for chunk in results:
            key = chunk["text"]
            if key not in seen or chunk.get("score", 0) > seen[key].get("score", 0):
                seen[key] = chunk

    # Sort theo score giảm dần, trả về top_k
    merged = sorted(seen.values(), key=lambda c: c.get("score", 0), reverse=True)
    return merged[:top_k]


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

    TODO Sprint 2:
    Chọn một trong hai:

    Option A — OpenAI (cần OPENAI_API_KEY):
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,     # temperature=0 để output ổn định, dễ đánh giá
            max_tokens=512,
        )
        return response.choices[0].message.content

    Option B — Google Gemini (cần GOOGLE_API_KEY):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text

    Lưu ý: Dùng temperature=0 hoặc thấp để output ổn định cho evaluation.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        return response.choices[0].message.content
        
    else:  # gemini
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(gemini_model)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                max_output_tokens=512,
            )
        )
        return response.text


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    query_transform: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → (transform) → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        query_transform: None | "expansion" | "decomposition" | "hyde"
        verbose: In thêm thông tin debug

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "transformed_queries": list queries sau transform (nếu có)
          - "config": cấu hình pipeline đã dùng
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "query_transform": query_transform,
    }

    # --- Bước 0: Query Transform (optional) ---
    transformed_queries = None
    if query_transform is not None:
        transformed_queries = transform_query(query, strategy=query_transform)
        if verbose:
            print(f"\n[RAG] Query transform ({query_transform}): {transformed_queries}")

    # --- Bước 1: Retrieve ---
    if transformed_queries is not None:
        # Retrieve cho từng sub-query, merge + dedup
        candidates = retrieve_with_transform(
            query,
            strategy=query_transform,
            retrieval_mode=retrieval_mode,
            top_k=top_k_search,
        )
    elif retrieval_mode == "dense":
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

    result = {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }
    if transformed_queries is not None:
        result["transformed_queries"] = transformed_queries
    return result


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

# def compare_retrieval_strategies(query: str) -> None:
#     """
#     So sánh các retrieval strategies với cùng một query.

#     TODO Sprint 3:
#     Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
#     Dùng để justify tại sao chọn variant đó cho Sprint 3.

#     A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
#     """
#     print(f"\n{'='*60}")
#     print(f"Query: {query}")
#     print('='*60)

#     strategies = ["dense", "sparse", "hybrid"]

#     for strategy in strategies:
#         print(f"\n--- Strategy: {strategy} ---")
#         try:
#             result = rag_answer(query, retrieval_mode=strategy, verbose=False)
#             print(f"Answer: {result['answer']}")
#             print(f"Sources: {result['sources']}")
#         except NotImplementedError as e:
#             print(f"Chưa implement: {e}")
#         except Exception as e:
#             print(f"Lỗi: {e}")

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.
    In bảng so sánh baseline (dense) vs variants (sparse, hybrid).

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*70}")
    print(f"QUERY: {query}")
    print('='*70)

    strategies = [
        ("dense",  "Baseline — Dense (vector similarity)"),
        ("sparse", "Variant A — Sparse BM25 (keyword)"),
        ("hybrid", "Variant B — Hybrid RRF (dense + BM25)"),
    ]

    rows = []
    for mode, label in strategies:
        print(f"\n[{label}]")
        try:
            result = rag_answer(query, retrieval_mode=mode, verbose=False)
            top_chunks = result["chunks_used"]
            top_scores = [f"{c.get('score', 0):.3f}" for c in top_chunks]
            print(f"  Answer  : {result['answer'][:120]}...")
            print(f"  Sources : {result['sources']}")
            print(f"  Scores  : {top_scores}")
            rows.append({
                "mode": mode,
                "sources": result["sources"],
                "top_scores": top_scores,
                "answer_len": len(result["answer"]),
            })
        except Exception as e:
            print(f"  Lỗi: {e}")
            rows.append({"mode": mode, "error": str(e)})

    # Summary table
    print(f"\n{'─'*70}")
    print(f"{'Strategy':<12} {'Top-3 Scores':<35} {'#Sources':<10} {'Ans Len'}")
    print(f"{'─'*70}")
    for r in rows:
        if "error" in r:
            print(f"{r['mode']:<12} ERROR: {r['error'][:50]}")
        else:
            scores_str = ", ".join(r["top_scores"])
            print(f"{r['mode']:<12} {scores_str:<35} {len(r['sources']):<10} {r['answer_len']}")
    print(f"{'─'*70}")


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS QUERY TRANSFORM VARIANTS
# =============================================================================

def compare_query_transforms(query: str, retrieval_mode: str = "dense") -> None:
    """
    So sánh baseline (không transform) vs các query transform strategies.
    A/B Rule: chỉ đổi query_transform, giữ nguyên retrieval_mode.
    """
    print(f"\n{'='*70}")
    print(f"QUERY TRANSFORM COMPARISON")
    print(f"Query: {query}")
    print(f"Retrieval mode: {retrieval_mode}")
    print('='*70)

    variants = [
        (None,            "Baseline — No transform"),
        ("expansion",     "Variant: expansion (synonym/alias)"),
        ("decomposition", "Variant: decomposition (sub-queries)"),
        ("hyde",          "Variant: HyDE (hypothetical document)"),
    ]

    rows = []
    for transform, label in variants:
        print(f"\n[{label}]")
        if transform is not None:
            try:
                transformed = transform_query(query, strategy=transform)
                print(f"  Transformed queries: {transformed}")
            except Exception as e:
                print(f"  Transform lỗi: {e}")
        try:
            result = rag_answer(
                query,
                retrieval_mode=retrieval_mode,
                query_transform=transform,
                verbose=False,
            )
            top_chunks = result["chunks_used"]
            top_scores = [f"{c.get('score', 0):.3f}" for c in top_chunks]
            print(f"  Answer  : {result['answer'][:300]}...")
            print(f"  Sources : {result['sources']}")
            print(f"  Scores  : {top_scores}")
            rows.append({
                "transform": str(transform),
                "sources": result["sources"],
                "top_scores": top_scores,
                "answer_len": len(result["answer"]),
            })
        except Exception as e:
            print(f"  Lỗi: {e}")
            rows.append({"transform": str(transform), "error": str(e)})

    # Summary table
    print(f"\n{'─'*70}")
    print(f"{'Transform':<16} {'Top-3 Scores':<35} {'#Sources':<10} {'Ans Len'}")
    print(f"{'─'*70}")
    for r in rows:
        if "error" in r:
            print(f"{r['transform']:<16} ERROR: {r['error'][:46]}")
        else:
            scores_str = ", ".join(r["top_scores"])
            print(f"{r['transform']:<16} {scores_str:<35} {len(r['sources']):<10} {r['answer_len']}")
    print(f"{'─'*70}")

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

    print("\n--- Sprint 3: So sánh strategies ---")
    compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    compare_retrieval_strategies("ERR-403-AUTH")
    
    print("\n--- Sprint 3: So sánh query transform strategies ---")
    # expansion: tốt cho alias query ("Approval Matrix" → tên thật trong doc)
    compare_query_transforms(
        "Approval Matrix để cấp quyền là tài liệu nào?",
        retrieval_mode="dense",
    )
    # decomposition: tốt cho câu hỏi đa ý
    compare_query_transforms(
        "Ai duyệt và mất bao lâu để cấp quyền Level 3?",
        retrieval_mode="dense",
    )

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
