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

load_dotenv()

# =============================================================================
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
    # [TL] Sprint 2: Dense retrieval — embed query → query ChromaDB → return ranked chunks
    import chromadb
    from index import get_embedding, CHROMA_DB_DIR

    # Connect to the persistent ChromaDB built in Sprint 1
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    # Embed the query using the SAME model used during indexing (text-embedding-3-small)
    # Using a different model here would produce incompatible vectors → wrong results
    query_embedding = get_embedding(query)

    # Query ChromaDB — returns distances (cosine distance = 1 - similarity)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),  # guard: don't request more than available
        include=["documents", "metadatas", "distances"],
    )

    # Convert to a flat list of chunk dicts with similarity scores
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "metadata": meta,
            "score": 1.0 - dist,  # cosine distance → similarity (higher = more relevant)
        })

    return chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    [RO] Sprint 3: BM25 keyword search.

    Mạnh ở: exact term, mã lỗi, tên riêng ("ERR-403", "P1", "Approval Matrix")
    Yếu ở : câu hỏi paraphrase, đồng nghĩa, câu dài tự nhiên

    Pipeline:
      ChromaDB.get() → toàn bộ chunks làm corpus
      BM25Okapi.get_scores() → score từng chunk
      Sort giảm dần → top_k kết quả

    Lưu ý: BM25 dùng tokenize đơn giản (split) — đủ cho unigram tiếng Việt
    với keyword kỹ thuật (mã lỗi, tên riêng viết liền).
    """
    from rank_bm25 import BM25Okapi
    import chromadb
    from index import CHROMA_DB_DIR

    # Load toàn bộ chunks từ ChromaDB để build BM25 corpus
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    all_data = collection.get(include=["documents", "metadatas"])
    all_docs = all_data["documents"]
    all_metas = all_data["metadatas"]

    if not all_docs:
        return []

    # Tokenize corpus: lowercase + split (đủ cho keyword matching)
    tokenized_corpus = [doc.lower().split() for doc in all_docs]
    bm25 = BM25Okapi(tokenized_corpus)

    # Score từng chunk với query
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # Lấy top_k indices theo BM25 score giảm dần
    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    return [
        {
            "text": all_docs[i],
            "metadata": all_metas[i],
            "score": float(scores[i]),
        }
        for i in top_indices
    ]


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
    [RO] Sprint 3: Hybrid = Dense + BM25, merge bằng Reciprocal Rank Fusion (RRF).

    Mạnh ở: giữ cả nghĩa (dense) lẫn keyword chính xác (BM25)
    Phù hợp: corpus có cả văn bản tự nhiên VÀ tên riêng/mã lỗi/điều khoản

    Công thức RRF (Cormack et al. 2009):
      RRF(doc) = dense_w × 1/(60 + rank_dense) + sparse_w × 1/(60 + rank_sparse)
      Hằng số 60 giảm ảnh hưởng của rank cao (rank 1 vs rank 2 không quá chênh lệch)

    A/B Rule: chỉ thay đổi retrieval_mode, giữ nguyên tất cả tham số khác.
    """
    dense_results  = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    # Accumulate RRF score cho từng chunk (key = 80 ký tự đầu của text)
    scores: Dict[str, Dict] = {}

    for rank, chunk in enumerate(dense_results):
        key = chunk["text"][:80]
        if key not in scores:
            scores[key] = {"chunk": chunk, "rrf": 0.0}
        scores[key]["rrf"] += dense_weight * (1.0 / (60 + rank))

    for rank, chunk in enumerate(sparse_results):
        key = chunk["text"][:80]
        if key not in scores:
            scores[key] = {"chunk": chunk, "rrf": 0.0}
        scores[key]["rrf"] += sparse_weight * (1.0 / (60 + rank))

    # Sort theo RRF score giảm dần → trả về top_k
    sorted_results = sorted(scores.values(), key=lambda x: x["rrf"], reverse=True)
    return [item["chunk"] for item in sorted_results[:top_k]]


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
    [TL] Sprint 2: Grounded prompt — siết chặt để force abstain khi context không đủ.

    4 quy tắc từ slide:
    1. Evidence-only: Chỉ trả lời từ retrieved context
    2. Hard abstain: Thiếu context → PHẢI nói không biết, KHÔNG được suy luận thêm
    3. Citation: Gắn [số] khi trích dẫn
    4. Short, clear, stable: Ngắn, rõ, nhất quán

    Lý do dùng "STRICT" và "DO NOT infer": tránh model dùng prior knowledge
    để tự suy luận thêm khi context score thấp (như ERR-403-AUTH).
    """
    prompt = f"""You are a strict internal helpdesk assistant. Answer ONLY using the context provided below.

RULES (follow strictly):
1. If the answer is clearly stated in the context, answer it and cite the source in [brackets] like [1].
2. If the context does NOT contain the answer, respond with exactly:
   "Không tìm thấy thông tin này trong tài liệu nội bộ. Vui lòng liên hệ bộ phận phụ trách."
3. DO NOT infer, guess, or use any knowledge outside the provided context.
4. Keep your answer concise and factual.
5. Respond in Vietnamese.

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
    # [TL] Sprint 2: Dùng OpenAI — khớp với LLM_PROVIDER=openai trong .env
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=LLM_MODEL,                          # gpt-4o-mini từ .env
        messages=[{"role": "user", "content": prompt}],
        temperature=0,     # [TL] temperature=0: output ổn định, tái hiện được → dễ A/B eval
        max_tokens=512,    # đủ cho câu trả lời ngắn gọn, grounded
    )
    return response.choices[0].message.content


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
    [RO] Sprint 3: So sánh dense vs hybrid trên cùng một query.
    Dùng để justify và ghi vào docs/tuning-log.md.
    A/B Rule: chỉ đổi retrieval_mode, giữ nguyên các tham số khác.
    """
    print(f"\n{'='*62}")
    print(f"Query: {query}")
    print('='*62)

    strategies = [
        ("dense",  {"retrieval_mode": "dense",  "use_rerank": False}),
        ("hybrid", {"retrieval_mode": "hybrid", "use_rerank": False}),
    ]

    for label, kwargs in strategies:
        print(f"\n--- [{label.upper()}] ---")
        try:
            result = rag_answer(query, verbose=False, **kwargs)
            print(f"  Answer  : {result['answer'][:120]}")
            print(f"  Sources : {result['sources']}")
            # In top-3 chunks để so sánh trực tiếp
            for i, c in enumerate(result["chunks_used"], 1):
                src = c["metadata"].get("source", "?")
                sec = c["metadata"].get("section", "?")
                scr = c.get("score", 0)
                print(f"  Chunk {i}: score={scr:.3f} | {src} | {sec}")
        except Exception as e:
            print(f"  ERROR: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 62)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 62)

    # -----------------------------------------------------------------------
    # SPRINT 2 — Baseline verification (dense)
    # -----------------------------------------------------------------------
    baseline_cases = [
        {"dod": "[DoD 1]", "query": "SLA xử lý ticket P1 là bao lâu?",
         "expect": "citation [1]"},
        {"dod": "[DoD 2]", "query": "ERR-403-AUTH là lỗi gì?",
         "expect": "abstain — không bịa"},
        {"dod": "[DoD 3]", "query": "Ai phải phê duyệt để cấp quyền Level 3?",
         "expect": "sources không rỗng"},
    ]

    print("\n--- Sprint 2: Baseline (Dense) ---")
    for case in baseline_cases:
        print(f"\n{'─'*55}")
        print(f"{case['dod']} {case['query']}")
        print(f"  Expect : {case['expect']}")
        try:
            r = rag_answer(case["query"], retrieval_mode="dense", verbose=False)
            print(f"  Answer : {r['answer'][:150]}")
            print(f"  Sources: {r['sources']}")
        except Exception as e:
            print(f"  ERROR  : {e}")

    # -----------------------------------------------------------------------
    # SPRINT 3 — [RO] A/B Compare: Dense vs Hybrid
    # -----------------------------------------------------------------------
    print("\n\n" + "=" * 62)
    print("Sprint 3: A/B Compare — Dense vs Hybrid")
    print("=" * 62)

    # Câu test quan trọng:
    # - alias query: dense có thể bỏ sót vì keyword không khớp
    # - keyword query: BM25 phải tìm P1 chính xác hơn
    # - abstain case:  cả hai phải abstain
    compare_queries = [
        "Approval Matrix để cấp quyền là tài liệu nào?",   # alias test
        "SLA xử lý ticket P1 là bao lâu?",                  # keyword test
        "ERR-403-AUTH là lỗi gì?",                          # abstain test
    ]

    for q in compare_queries:
        compare_retrieval_strategies(q)

    print("\n" + "=" * 62)
    print("Sprint 3 — Definition of Done Checklist")
    print("=" * 62)
    print("[DoD S3-1] retrieve_hybrid() chạy không crash")
    print("[DoD S3-2] Alias query → hybrid tìm được it/access-control-sop.md")
    print("[DoD S3-3] Kết quả khác nhau giữa DENSE và HYBRID ở alias query")
    print("[DoD S3-4] Abstain case → cả dense và hybrid đều không bịa")
    print()
    print("→ Ghi kết quả vào docs/tuning-log.md (Documentation Owner).")

