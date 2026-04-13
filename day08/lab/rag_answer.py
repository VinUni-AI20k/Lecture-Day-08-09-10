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
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI  # Add OpenAI import to match index.py

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
# Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)
TOP_K_SELECT = 3

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Dense retrieval: tìm kiếm theo embedding similarity trong ChromaDB.
    """
    import chromadb
    from index import get_embedding, CHROMA_DB_DIR

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")
    except Exception as e:
        raise RuntimeError(
            f"ChromaDB not found. Run index.py first to build the index: {e}")

    # Embed query
    query_embedding = get_embedding(query)

    # Query ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    # Convert distances to similarity scores (1 - cosine_distance)
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        similarity_score = 1 - dist  # Convert distance to similarity
        chunks.append({
            "text": doc,
            "metadata": meta,
            "score": similarity_score,
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
    """
    from rank_bm25 import BM25Okapi
    import chromadb

    # Lấy tất cả chunks từ ChromaDB
    try:
        from index import CHROMA_DB_DIR
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")
        all_results = collection.get(
            include=["documents", "metadatas"]
        )
    except Exception as e:
        print(f"[retrieve_sparse] Lỗi truy cập ChromaDB: {e}")
        return []

    if not all_results["documents"]:
        return []

    # Tạo BM25 index
    corpus = all_results["documents"]
    metadatas = all_results["metadatas"]

    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

    # Query
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # Get top-k
    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    chunks = []
    for idx in top_indices:
        chunks.append({
            "text": corpus[idx],
            "metadata": metadatas[idx],
            "score": float(scores[idx]),
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
    """
    # Lấy results từ dense và sparse
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    # Tạo mapping: text -> (rank, score) cho từng strategy
    dense_dict = {}
    for rank, chunk in enumerate(dense_results):
        text_key = chunk["text"][:100]  # Use first 100 chars as key
        dense_dict[text_key] = (rank + 1, chunk["score"])

    sparse_dict = {}
    for rank, chunk in enumerate(sparse_results):
        text_key = chunk["text"][:100]
        sparse_dict[text_key] = (rank + 1, chunk["score"])

    # RRF score calculation: 1 / (k + rank)
    # k = 60 is standard RRF parameter
    K = 60
    rrf_scores = {}
    all_texts = set(dense_dict.keys()) | set(sparse_dict.keys())

    for text_key in all_texts:
        score = 0.0
        if text_key in dense_dict:
            rank, _ = dense_dict[text_key]
            score += dense_weight * (1.0 / (K + rank))
        if text_key in sparse_dict:
            rank, _ = sparse_dict[text_key]
            score += sparse_weight * (1.0 / (K + rank))
        rrf_scores[text_key] = score

    # Sort by RRF score and get top_k
    sorted_texts = sorted(
        rrf_scores.keys(),
        key=lambda x: rrf_scores[x],
        reverse=True
    )[:top_k]

    # Rebuild results
    results = []
    for text_key in sorted_texts:
        # Find the actual chunk from either dense or sparse results
        chunk = None
        if text_key in dense_dict:
            for c in dense_results:
                if c["text"][:100] == text_key:
                    chunk = c
                    break
        if chunk is None and text_key in sparse_dict:
            for c in sparse_results:
                if c["text"][:100] == text_key:
                    chunk = c
                    break

        if chunk:
            chunk["score"] = rrf_scores[text_key]
            results.append(chunk)

    return results


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
    Rerank các candidate chunks bằng cross-encoder để chấm lại relevance.

    Cross-encoder: chấm lại "chunk nào thực sự trả lời câu hỏi này?"
    """
    if not candidates:
        return []

    # Simple reranking: boost score if matches key terms in query
    from sentence_transformers import CrossEncoder

    try:
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        pairs = [[query, chunk["text"]] for chunk in candidates]
        scores = model.predict(pairs)

        # Add cross-encoder scores to chunks
        for chunk, score in zip(candidates, scores):
            chunk["rerank_score"] = float(score)

        # Sort by rerank score and return top-k
        ranked = sorted(
            candidates,
            key=lambda x: x.get("rerank_score", x.get("score", 0)),
            reverse=True
        )
        return ranked[:top_k]

    except Exception as e:
        print(f"[rerank] Lỗi tải cross-encoder: {e}")
        # Fallback: return top_k by original score
        return sorted(
            candidates,
            key=lambda x: x.get("score", 0),
            reverse=True
        )[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion": Thêm từ đồng nghĩa, alias, tên cũ
      - "decomposition": Tách query phức tạp thành 2-3 sub-queries
      - "hyde": Sinh câu trả lời giả để embed thay query
    """
    try:
        if strategy == "expansion":
            # Domain-specific expansion mappings
            expansions = {
                "quyền": ["permission", "access", "phê duyệt", "cấp"],
                "hoàn tiền": ["refund", "hoàn lại tiền", "trả tiền"],
                "ticket": ["sự cố", "issue", "yêu cầu"],
                "p1": ["p1", "critical", "khẩn cấp", "priority 1"],
            }

            queries = [query]  # Original
            query_lower = query.lower()

            for keyword, synonyms in expansions.items():
                if keyword in query_lower:
                    for synonym in synonyms:
                        if synonym.lower() not in query_lower:
                            expanded = query.replace(
                                keyword, f"{keyword} {synonym}")
                            queries.append(expanded)
                            break  # Add only one synonym per keyword

            return queries[:3]  # Limit to 3 variants

        elif strategy == "decomposition":
            # Simple decomposition heuristic
            if " và " in query or " or " in query.lower():
                parts = query.replace(" và ", " | ").split(" | ")
                return parts[:3]
            return [query]

        else:  # hyde or other
            return [query]

    except Exception as e:
        print(f"[transform_query] Error: {e}")
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
    Gọi LLM để sinh câu trả lời dùng OpenAI API (matching index.py approach).
    Falls back to Gemini if OpenAI fails.
    """
    from openai import OpenAI

    # Try OpenAI first
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.strip():
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # Deterministic output
                max_tokens=512,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️  OpenAI error: {e}")
            print("  Falling back to Gemini...")
    else:
        print("⚠️  OPENAI_API_KEY not set. Trying Gemini API...")

    # Fallback to Gemini
    try:
        import google.generativeai as genai

        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError(
                "Both OPENAI_API_KEY and GOOGLE_API_KEY not found in .env"
            )

        genai.configure(api_key=google_api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,  # Deterministic output
                max_output_tokens=512,
            )
        )
        return response.text
    except Exception as e:
        raise RuntimeError(f"❌ Both OpenAI and Gemini APIs failed: {e}")


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
        Dict với answer, sources, chunks_used, query, config
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
        print(
            f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(
                f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

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
    try:
        answer = call_llm(prompt)
    except Exception as e:
        answer = f"Lỗi khi gọi LLM: {str(e)}"

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
    print("\n" + "=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GOOGLE_API_KEY")

    print("\n🔑 API Configuration:")
    if openai_key and openai_key.strip():
        print("  ✅ OPENAI_API_KEY found (will use OpenAI)")
    else:
        print("  ⚠️  OPENAI_API_KEY not set (will try Gemini)")

    if gemini_key and gemini_key.strip():
        print("  ✅ GOOGLE_API_KEY found (fallback)")
    else:
        print("  ⚠️  GOOGLE_API_KEY not set (needed if OpenAI fails)")

    print()

    # Test queries từ data/test_questions.json
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "Sản phẩm kỹ thuật số có được hoàn tiền không?",
        "Tài khoản bị khóa sau bao nhiêu lần đăng nhập sai?",
    ]

    print("--- Sprint 2: Test Baseline (Dense Retrieval) ---\n")
    for i, query in enumerate(test_queries[:3], 1):
        print(f"[Query {i}] {query}")
        try:
            result = rag_answer(query, retrieval_mode="dense", verbose=True)
            print(f"\n✅ Answer: {result['answer']}\n")
            print(f"📚 Sources: {result['sources']}")
            print("-" * 60)
        except NotImplementedError as e:
            print(f"❌ Chưa implement: {e}")
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            import traceback
            traceback.print_exc()

    # Sprint 3: Compare strategies
    print("\n\n--- Sprint 3: So sánh strategies (Hybrid vs Dense) ---")
    test_query = test_queries[0]
    print(f"\nQuery: {test_query}\n")

    strategies = ["dense", "hybrid"]
    for strategy in strategies:
        print(f"  🔍 Strategy: {strategy}")
        try:
            result = rag_answer(
                test_query, retrieval_mode=strategy, verbose=False)
            print(f"     Answer: {result['answer'][:100]}...")
            print(f"     Sources: {result['sources']}\n")
        except Exception as e:
            print(f"     ❌ Error: {e}\n")

    print("\n" + "=" * 60)
    print("✅ RAG Pipeline Testing Complete!")
    print("=" * 60 + "\n")
