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
# ADDED: Prompt template tách biệt để dễ chỉnh sửa — xem prompt/rag_prompt.py
from prompt.rag_prompt import build_grounded_prompt

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


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
    # Added: Convert ChromaDB results to list of dict with text, metadata, and score
    retrieved_chunks = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        chunk = {
            "text": doc,
            "metadata": meta,
            "score": 1 - dist  # Convert distance to similarity score
        }
        retrieved_chunks.append(chunk)

    return retrieved_chunks


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
    # TODO Sprint 3: Implement BM25 search
    # Tạm thời return empty list
    # print("[retrieve_sparse] Chưa implement — Sprint 3")

    from rank_bm25 import BM25Okapi
    import chromadb
    from index import CHROMA_DB_DIR

    # Bước 1: Load tất cả chunks từ ChromaDB
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    all_results = collection.get(include=["documents", "metadatas"])

    all_docs = all_results["documents"]
    all_metas = all_results["metadatas"]

    if not all_docs:
        print("[retrieve_sparse] Không có chunk nào trong index")
        return []

    # Bước 2: Tokenize corpus và tạo BM25 index
    # ADDED: Strip punctuation trước khi split để tránh token như '"approval' ≠ 'approval'
    import re

    def tokenize(text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)  # thay dấu câu bằng khoảng trắng
        return text.split()

    tokenized_corpus = [tokenize(doc) for doc in all_docs]
    bm25 = BM25Okapi(tokenized_corpus)

    # Bước 3: Query BM25
    tokenized_query = tokenize(query)
    scores = bm25.get_scores(tokenized_query)

    # Bước 4: Lấy top_k kết quả theo score giảm dần
    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:top_k]

    retrieved_chunks = []
    for idx in top_indices:
        chunk = {
            "text": all_docs[idx],
            "metadata": all_metas[idx],
            "score": float(scores[idx]),
        }
        retrieved_chunks.append(chunk)

    return retrieved_chunks


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
    # TODO Sprint 3: Implement hybrid RRF
    # Tạm thời fallback về dense
    # print("[retrieve_hybrid] Chưa implement RRF — fallback về dense")
    # return retrieve_dense(query, top_k)

    RRF_K = 60  # Hằng số RRF tiêu chuẩn

    # Bước 1: Chạy cả 2 retrieval strategies
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    # Bước 2: Tính RRF score cho mỗi document
    # Dùng text làm key để merge (vì cùng chunk text = cùng document)
    doc_scores: Dict[str, Dict[str, Any]] = {}

    # Dense ranking
    for rank, chunk in enumerate(dense_results):
        text_key = chunk["text"]
        rrf_score = dense_weight * (1.0 / (RRF_K + rank + 1))
        if text_key not in doc_scores:
            doc_scores[text_key] = {
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "rrf_score": 0.0,
                "dense_rank": rank + 1,
                "sparse_rank": None,
            }
        doc_scores[text_key]["rrf_score"] += rrf_score

    # Sparse ranking
    for rank, chunk in enumerate(sparse_results):
        text_key = chunk["text"]
        rrf_score = sparse_weight * (1.0 / (RRF_K + rank + 1))
        if text_key not in doc_scores:
            doc_scores[text_key] = {
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "rrf_score": 0.0,
                "dense_rank": None,
                "sparse_rank": rank + 1,
            }
        else:
            doc_scores[text_key]["sparse_rank"] = rank + 1
        doc_scores[text_key]["rrf_score"] += rrf_score

    # Bước 3: Sort theo RRF score giảm dần và trả về top_k
    sorted_docs = sorted(
        doc_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )[:top_k]

    # Format lại kết quả
    results = []
    for doc in sorted_docs:
        results.append({
            "text": doc["text"],
            "metadata": doc["metadata"],
            "score": doc["rrf_score"],  # RRF score thay vì cosine similarity
        })

    return results


# =============================================================================
# RERANK (Sprint 3 alternative)
# Cross-encoder để chấm lại relevance sau search rộng
# =============================================================================

# Caching model cho rerank để không bị lag khi hệ thống tự động gọi nhiều lần
_cross_encoder_model = None

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
    global _cross_encoder_model
    
    if not candidates:
        return []

    print("\n[rerank] Đang chạy cross-encoder reranking để chấm điểm lại candidates...")
    
    # 1. Khởi tạo model (chỉ load 1 lần đầu tiên)
    if _cross_encoder_model is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    # 2. Tạo pairs: [[câu hỏi, văn bản 1], [câu hỏi, văn bản 2], ...]
    pairs = [[query, chunk["text"]] for chunk in candidates]
    
    # 3. Model đưa ra điểm số đánh giá mức độ liên quan thực sự (không chỉ dựa vào từ khóa/vector)
    scores = _cross_encoder_model.predict(pairs)
    
    # 4. Gom cặp candidate và điểm lại, sắp xếp giảm dần (từ cao xuống thấp)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    
    # 5. Extract chunk ra khỏi tuple và trả về top_k chunks có điểm cao nhất
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
    import json
    import re

    strategy = (strategy or "expansion").strip().lower()
    if strategy not in {"expansion", "decomposition", "hyde"}:
        return [query]

    if strategy == "expansion":
        transform_prompt = f"""Given the query: "{query}"
Generate 2-3 alternative phrasings or related terms in Vietnamese.
Keep each item concise and useful for retrieval.
Output strictly as a JSON array of strings."""
    elif strategy == "decomposition":
        transform_prompt = f"""Break down this complex query into 2-3 simpler sub-queries: "{query}"
Each sub-query should target one intent only.
Output strictly as a JSON array of strings."""
    else:  # hyde
        transform_prompt = f"""Question: "{query}"
Write 1 short hypothetical answer paragraph in Vietnamese that is likely to appear in relevant documents.
Do not include explanations.
Output strictly as a JSON array with exactly 1 string."""

    try:
        raw_output = call_llm(transform_prompt).strip()

        # Robustly extract JSON array in case model wraps it with extra text/markdown.
        json_match = re.search(r"\[[\s\S]*\]", raw_output)
        json_payload = json_match.group(0) if json_match else raw_output
        parsed = json.loads(json_payload)

        if not isinstance(parsed, list):
            return [query]

        cleaned: List[str] = []
        seen = {query.strip().lower()}
        for item in parsed:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)

        if strategy == "hyde":
            return cleaned[:1] if cleaned else [query]

        if cleaned:
            return [query] + cleaned[:3]
    except Exception:
        # Fall back to original query if transformation fails or output is malformed.
        pass

    # Fallback: đảm bảo luôn trả về List[str] (không bao giờ None)
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


# ADDED: build_grounded_prompt imported từ prompt/rag_prompt.py — xem file đó để chỉnh prompt
# (hàm đã được xóa khỏi đây để tránh shadow import gây đệ quy vô hạn)


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
    # from google import genai
    # # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    # client = genai.Client()
    # response = client.models.generate_content(
    #     model=GEMINI_MODEL, contents="Explain how AI works in a few words"
    # )
    # return response.text

    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,     # temperature=0 để output ổn định, dễ đánh giá
        max_tokens=512,
    )
    return response.choices[0].message.content


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    use_query_transform: bool = False,
    transform_strategy: str = "expansion",
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
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
        use_query_transform: Có dùng query transformation trước khi retrieve không
        transform_strategy: "expansion" | "decomposition" | "hyde"
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
    - Variant C: bật use_query_transform=True, transform_strategy="expansion"
    """
    def _print_candidates(title: str, items: List[Dict[str, Any]], preview_chars: int = 100) -> None:
        print(f"[RAG] {title}: {len(items)} chunks")
        for i, item in enumerate(items, 1):
            meta = item.get("metadata", {})
            score = item.get("score", 0.0)
            source = meta.get("source", "?")
            section = meta.get("section", "")
            text = str(item.get("text", "")).replace("\n", " ").strip()
            if len(text) > preview_chars:
                text = text[:preview_chars] + "..."

            section_part = f" | {section}" if section else ""
            print(f"  [{i}] score={score:.3f} | {source}{section_part}")
            print(f"      {text}")

    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "use_query_transform": use_query_transform,
        "transform_strategy": transform_strategy if use_query_transform else None,
        "dense_weight": dense_weight,
        "sparse_weight": sparse_weight,
    }

    # --- Bước 0: Query Transformation (optional) ---
    # ADDED: Expand/decompose/hyde query trước khi retrieve để tăng recall
    queries = [query]
    if use_query_transform:
        queries = transform_query(query, strategy=transform_strategy) or [query]
        if verbose:
            print(f"\n[RAG] Query transform ({transform_strategy}): {queries}")

    # --- Bước 1: Retrieve ---
    # ADDED: Retrieve cho từng query, merge và deduplicate theo text key
    def _retrieve(q: str) -> List[Dict[str, Any]]:
        if retrieval_mode == "dense":
            return retrieve_dense(q, top_k=top_k_search)
        elif retrieval_mode == "sparse":
            return retrieve_sparse(q, top_k=top_k_search)
        elif retrieval_mode == "hybrid":
            return retrieve_hybrid(q, top_k=top_k_search, dense_weight=dense_weight, sparse_weight=sparse_weight)
        else:
            raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    seen_texts: dict = {}
    for q in queries:
        for chunk in _retrieve(q):
            key = chunk["text"]
            if key not in seen_texts:
                seen_texts[key] = chunk
            else:
                # Giữ score cao nhất nếu chunk xuất hiện trong nhiều queries
                if chunk.get("score", 0) > seen_texts[key].get("score", 0):
                    seen_texts[key] = chunk
    candidates = list(seen_texts.values())

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieval mode: {retrieval_mode}")
        _print_candidates("Candidates BEFORE rerank/select", candidates)

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        stage_name = "Candidates AFTER rerank" if use_rerank else "Candidates AFTER top_k select"
        _print_candidates(stage_name, candidates)

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

    strategies = ["dense", "sparse", "hybrid"]

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
            
    # --- Chạy test variant Rerank ---
    # print("\n--- Strategy: dense + rerank ---")
    # try:
    #     # Gọi rag_answer với retrieval=dense nhưng BAT use_rerank=True
    #     # Tăng top_k_search từ 10 (mặc định) lên cao hơn để Reranker có nhiều ngữ cảnh để lựa chọn, ví dụ 15
    #     result = rag_answer(query, retrieval_mode="dense", top_k_search=15, top_k_select=3, use_rerank=True, verbose=False)
    #     print(f"Answer: {result['answer']}")
    #     print(f"Sources: {result['sources']}")
    # except Exception as e:
    #     print(f"Lỗi (Chưa install package?): {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Test queries từ data/test_questions.json
    # test_queries = [
    #     "SLA xử lý ticket P1 là bao lâu?",
    #     "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
    #     "Ai phải phê duyệt để cấp quyền Level 3?",
    #     "ERR-403-AUTH là lỗi gì?",  # Query không có trong docs → kiểm tra abstain
    # ]
    
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
    ]
    
    print("\n--- Sprint 2: Test Baseline (Dense) ---")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = rag_answer(query, retrieval_mode="dense", use_rerank=True, verbose=True)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError:
            print("Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước.")
        except Exception as e:
            print(f"Lỗi: {e}")

    # Uncomment sau khi Sprint 3 hoàn thành:
    print("\n--- Sprint 3: So sánh strategies ---")
    compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    compare_retrieval_strategies("ERR-403-AUTH")

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
