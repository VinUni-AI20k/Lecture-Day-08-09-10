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
from typing import List, Dict, Any, Optional, Tuple, Callable
from dotenv import load_dotenv
import chromadb
from openai import OpenAI
from rank_bm25 import BM25Okapi
from index import get_embedding, CHROMA_DB_DIR
import re
from query_trans import apply_query_transformations, deduplicate_chunks
bm25 = None
all_chunks = None

load_dotenv()

# =====================LLM_MODEL========================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


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
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    chunks: List[Dict[str, Any]] = []
    for idx, doc_text in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else None
        score = 1 - distance if isinstance(distance, (int, float)) else 0.0
        chunks.append({
            "text": doc_text,
            "metadata": metadata,
            "score": score,
        })

    return chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================
def load_all_chunks() -> List[Dict[str, Any]]:
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    results = collection.get(
        include=["documents", "metadatas"]
    )
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    all_chunks = []
    for doc_text, metadata in zip(documents, metadatas):
        all_chunks.append({
            "text": doc_text,
            "metadata": metadata,
        })
    return all_chunks

def init_sparse():
    global bm25, all_chunks
    all_chunks = load_all_chunks()
    corpus = [chunk["text"] for chunk in all_chunks]
    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

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
    global bm25, all_chunks
    
    # Initialize sparse retrieval nếu chưa được init
    if bm25 is None:
        init_sparse()
    
    if not all_chunks:
        return []
    
    # Tokenize query
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    
    # Lấy top_k indices
    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]
    
    # Tạo results kèm scores
    results = []
    for idx in top_indices:
        chunk = all_chunks[idx].copy()  # Copy để không thay đổi global
        chunk["score"] = float(scores[idx])
        results.append(chunk)
    
    return results


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def get_doc_id(doc: Dict[str, Any]) -> str:
    """Tạo unique doc_id từ metadata để match chunks giữa dense và sparse."""
    meta = doc["metadata"]
    # Dùng combination fields để đảm bảo unique
    source = meta.get("source", "unknown").replace("/", "_")
    section = meta.get("section_title", meta.get("section", "unknown"))
    chunk_idx = meta.get("chunk_index", 0)
    return f"{source}|{section}|{chunk_idx}"


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
    # TODO Sprint 3: Implement hybrid RRF
    dense_results = retrieve_dense(query, top_k=top_k * 2)
    sparse_results = retrieve_sparse(query, top_k=top_k * 2)
    
    #RRF fusion logic:
    #1. Tạo dict để map doc_id → (dense_rank, sparse_rank)
    doc_scores = {}
    for rank, doc in enumerate(dense_results, 1):
        doc_id = get_doc_id(doc)
        doc_scores[doc_id] = {"dense_rank": rank, "sparse_rank": None}
    for rank, doc in enumerate(sparse_results, 1):
        doc_id = get_doc_id(doc)
        if doc_id in doc_scores:
            doc_scores[doc_id]["sparse_rank"] = rank
        else:
            doc_scores[doc_id] = {"dense_rank": None, "sparse_rank": rank}

    #2. Tính RRF scores
    for doc_id, ranks in doc_scores.items():
        dense_rank = ranks["dense_rank"]
        sparse_rank = ranks["sparse_rank"]
        if dense_rank is not None and sparse_rank is not None:
            rrf_score = dense_weight * (1 / (60 + dense_rank)) + sparse_weight * (1 / (60 + sparse_rank))
        elif dense_rank is not None:
            rrf_score = dense_weight * (1 / (60 + dense_rank))
        elif sparse_rank is not None:
            rrf_score = sparse_weight * (1 / (60 + sparse_rank))
        else:
            rrf_score = 0
        doc_scores[doc_id]["rrf_score"] = rrf_score

    #3. Sắp xếp theo RRF score giảm dần
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1]["rrf_score"], reverse=True)
    top_docs = [doc_id for doc_id, _ in sorted_docs[:top_k]]
    #4. Trả về top_k docs — dùng get_doc_id() giống doc_scores để không bị key mismatch
    id_to_doc = {}
    for doc in dense_results:
        id_to_doc[get_doc_id(doc)] = doc
    for doc in sparse_results:
        key = get_doc_id(doc)
        if key not in id_to_doc:
            id_to_doc[key] = doc
    return [id_to_doc[doc_id] for doc_id in top_docs if doc_id in id_to_doc]


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
    return candidates[:top_k]


# =============================================================================
# RETRIEVE BY EMBEDDING — dùng cho HyDE
# =============================================================================

def retrieve_by_embedding(embedding: List[float], top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Retrieve chunks bằng embedding vector trực tiếp (không embed query).
    Dùng cho HyDE: embed hypothetical doc rồi retrieve bằng vector đó.
    """
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    chunks: List[Dict[str, Any]] = []
    for idx, doc_text in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else None
        score = 1 - distance if isinstance(distance, (int, float)) else 0.0
        chunks.append({"text": doc_text, "metadata": metadata, "score": score})
    return chunks


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(
    query: str,
    retrieve_fn: Callable,
    get_embedding: Optional[Callable] = None,
    retrieve_by_emb: Optional[Callable] = None,
    strategy: str = "auto",
    top_k: int = TOP_K_SEARCH,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Biến đổi query và retrieve kết quả.
    Internally gọi apply_query_transformations().

    Args:
        query:        Câu hỏi gốc
        retrieve_fn:  Hàm retrieve: (query_str, top_k) -> chunks
        get_embedding: Hàm embed (cần cho HyDE)
        strategy:     "auto" | "expansion" | "stepback" | "decomposition" | "hyde"
                      - "auto": tự động detect kỹ thuật phù hợp (recommended)
                      - specific: force một kỹ thuật cụ thể
        top_k:        Số chunks mỗi retrieve call
        verbose:      In debug log

    Returns:
        Dict {"chunks": [...], "techniques": [...], "queries": [...]}
    """
    from query_trans import (
        apply_query_transformations,
        expand_query,
        stepback_query,
        decompose_query,
        generate_hypothetical_doc,
        deduplicate_chunks,
    )

    if strategy == "auto":
        # Tự động detect: gọi apply_query_transformations
        return apply_query_transformations(
            query=query,
            retrieve_fn=retrieve_fn,
            call_llm=call_llm,
            get_embedding=get_embedding,
            retrieve_by_embedding=retrieve_by_emb,
            top_k=top_k,
            verbose=verbose,
        )

    # Force strategy cụ thể → sinh query variants → retrieve → dedup
    if strategy == "expansion":
        variants = expand_query(query, call_llm)
    elif strategy == "stepback":
        abstract = stepback_query(query, call_llm)
        variants = [query, abstract] if abstract != query else [query]
    elif strategy == "decomposition":
        sub_questions = decompose_query(query, call_llm)
        variants = [query] + [q for q in sub_questions if q != query]
    elif strategy == "hyde":
        hypo_doc = generate_hypothetical_doc(query, call_llm)
        variants = [hypo_doc]
    else:
        raise ValueError(f"strategy không hợp lệ: {strategy!r}. Chọn: auto | expansion | stepback | decomposition | hyde")

    if verbose:
        print(f"[transform_query] strategy={strategy!r} → {len(variants)} variants")
        for v in variants:
            print(f"  - {v}")

    chunk_lists = [retrieve_fn(q, top_k) for q in variants]
    chunks = deduplicate_chunks(chunk_lists, max_chunks=top_k)
    return {"chunks": chunks, "techniques": [strategy], "queries": variants}


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
If the context is insufficient to answer the question, say you do not know and do not make up information, suggest user to contact support.
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
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,     # temperature=0 để output ổn định, dễ đánh giá
        max_tokens=512,
    )
    return response.choices[0].message.content
    raise NotImplementedError(
        "TODO Sprint 2: Implement call_llm().\n"
        "Chọn Option A (OpenAI) hoặc Option B (Gemini) trong TODO comment."
    )


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    use_query_transform: bool = False,
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
        "use_query_transform": use_query_transform,
    }

    # --- Bước 1: Retrieve ---
    if use_query_transform:
        # Chọn retrieve_fn theo retrieval_mode
        if retrieval_mode == "dense":
            retrieve_fn = lambda q, k: retrieve_dense(q, top_k=k)
        elif retrieval_mode == "sparse":
            retrieve_fn = lambda q, k: retrieve_sparse(q, top_k=k)
        elif retrieval_mode == "hybrid":
            retrieve_fn = lambda q, k: retrieve_hybrid(q, top_k=k)
        else:
            raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

        # transform_query() gọi apply_query_transformations() bên trong (luôn dùng auto)
        trans_result = transform_query(
            query=query,
            retrieve_fn=retrieve_fn,
            get_embedding=get_embedding,
            retrieve_by_emb=retrieve_by_embedding,
            strategy="auto",
            top_k=top_k_search,
            verbose=verbose,
        )
        candidates = trans_result["chunks"]
        config["techniques"] = trans_result["techniques"]
        config["queries_used"] = trans_result["queries"]
    else:
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

    TODO Sprint 3:
    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "hybrid", "sparse"]  # Thêm "sparse" sau khi implement

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
    init_sparse()
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Test queries đọc từ data/grading_questions.json

    test_queries = [
        "SLA xử lý ticket P1 đã thay đổi như thế nào so với phiên bản trước?",
        "Khi làm việc remote, tôi phải dùng VPN và được kết nối trên tối đa bao nhiêu thiết bị?",
        "Đơn hàng mua trong chương trình Flash Sale và đã kích hoạt sản phẩm có được hoàn tiền không?",
        "Nếu chọn nhận store credit thay vì hoàn tiền, tôi được bao nhiêu phần trăm?",
    ]

    print("\n--- Sprint 2: Test Baseline---")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = rag_answer(query, retrieval_mode="hybrid", verbose=True)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError:
            print("Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước.")
        except Exception as e:
            print(f"Lỗi: {e}")

    print("\n--- Sprint 3: So sánh strategies ---")
    compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    compare_retrieval_strategies("ERR-403-AUTH")

    # =========================================================================
    # TEST QUERY TRANSFORMATION
    # use_query_transform=True để bật toàn bộ pipeline transform (auto-detect)
    # =========================================================================

    # --- EXPANSION triggers ---
    # Trigger khi: query <= 4 từ HOẶC chứa từ lóng/alias trong _INFORMAL_TERMS
    expansion_queries = [
        "nghỉ đẻ bao lâu?",           # "nghỉ đẻ" → alias cho "nghỉ thai sản"
        "bị lock tài khoản",           # "bị lock" → alias cho "tài khoản bị khóa"
        "approval matrix",             # tên cũ của Access Control SOP (≤ 2 từ)
        "wfh policy",                  # "wfh" → remote work
        "đổi trả hàng",               # "đổi trả" → hoàn tiền
    ]

    # --- STEP-BACK triggers ---
    # Trigger khi: query chứa mã lỗi, Jira ID, ticket#, IP, tool name, ext, URL
    stepback_queries = [
        "ERR-403-AUTH là lỗi gì?",             # ERR-\w+ pattern
        "Cisco AnyConnect cài đặt thế nào?",   # tool name pattern
        "ext. 9000 là số máy lẻ của ai?",      # ext.\d{3,4} pattern
        "Ticket IT-1234 bị delay xử lý sao?",  # Jira ID pattern [A-Z]{2,}-\d+
    ]

    # --- DECOMPOSITION triggers ---
    # Trigger khi: probe retrieve trả về chunks từ >= 2 nguồn khác nhau trong top-4
    # → query hỏi nhiều thứ liên quan đến nhiều tài liệu cùng lúc
    decomposition_queries = [
        # Cần SLA (sla_p1_2026) + Access Control (access_control_sop)
        "Khi xảy ra sự cố P1 ngoài giờ hành chính, quy trình on-call "
        "và cấp quyền truy cập khẩn cấp thế nào?",
        # Cần HR (hr_leave_policy) + Access Control (access_control_sop)
        "Nhân viên nghỉ việc thì hệ thống thu hồi quyền truy cập "
        "và chính sách hoàn tiền xử lý ra sao?",
    ]

    # --- HyDE triggers ---
    # Trigger khi: max score sau probe nằm trong [0.45, 0.58] — retriever không chắc
    # → query mơ hồ, vocabulary không khớp với văn phong doc
    hyde_queries = [
        "Hệ thống không phản hồi thì làm gì?",  # vague → SLA/incident
        "Tôi không vào được ứng dụng",            # vague → VPN/account lock
    ]

    print("\n" + "="*60)
    print("TEST QUERY TRANSFORMATION (use_query_transform=True)")
    print("="*60)

    all_transform_tests = [
        ("EXPANSION", expansion_queries),
        ("STEP-BACK", stepback_queries),
        ("DECOMPOSITION", decomposition_queries),
        ("HyDE", hyde_queries),
    ]

    for technique, queries in all_transform_tests:
        print(f"\n{'─'*60}")
        print(f"[{technique}] — expected trigger")
        print(f"{'─'*60}")
        for q in queries:
            print(f"\nQuery: {q}")
            try:
                result = rag_answer(
                    q,
                    retrieval_mode="hybrid",
                    use_query_transform=True,
                    verbose=True,
                )
                print(f"Techniques used: {result['config'].get('techniques', [])}")
                print(f"Answer: {result['answer']}")
                print(f"Sources: {result['sources']}")
            except Exception as e:
                print(f"Lỗi: {e}")

