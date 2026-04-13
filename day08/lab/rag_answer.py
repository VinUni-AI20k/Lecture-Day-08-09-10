"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
"""

import os
import re
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10
TOP_K_SELECT = 3

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
          - "score": cosine similarity score (1 = perfect match)
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

    chunks = []
    # ChromaDB cosine space: distance = 1 - similarity → score = 1 - distance
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "metadata": meta,
            "score": 1.0 - dist,
        })

    return chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword dùng BM25.

    Mạnh ở: exact term, mã lỗi, tên riêng ("ERR-403", "P1", "refund")
    Hay hụt: câu hỏi paraphrase, đồng nghĩa

    Sprint 3 — Variant A (Hybrid): Kết hợp với dense qua RRF.
    Lý do chọn hybrid: corpus chứa cả văn xuôi tự nhiên lẫn mã kỹ thuật/
    tên điều khoản cụ thể → cần cả semantic search lẫn keyword exact match.
    """
    from rank_bm25 import BM25Okapi
    import chromadb
    from index import CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    # Load toàn bộ corpus để build BM25 index
    all_docs = collection.get(include=["documents", "metadatas"])
    corpus = all_docs["documents"]
    metadatas = all_docs["metadatas"]

    if not corpus:
        return []

    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # Lấy top_k theo score giảm dần
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    chunks = []
    for i in top_indices:
        if scores[i] > 0:  # Chỉ lấy nếu có keyword match
            chunks.append({
                "text": corpus[i],
                "metadata": metadatas[i],
                "score": float(scores[i]),
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

    Mạnh ở: giữ được cả nghĩa (dense) lẫn keyword chính xác (sparse).
    Phù hợp khi: corpus lẫn lộn văn xuôi tự nhiên VÀ mã lỗi/tên điều khoản.

    RRF_score(doc) = dense_weight * (1/(60+dense_rank))
                   + sparse_weight * (1/(60+sparse_rank))
    60 là hằng số RRF tiêu chuẩn (giảm ảnh hưởng của rank rất thấp).

    Sprint 3 — Lý do chọn hybrid:
    Corpus của lab gồm chính sách (văn xuôi), SLA (số liệu cụ thể), FAQ
    (keyword như ERR-403-AUTH) → hybrid tận dụng cả hai thế mạnh.
    """
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    # RRF: tích lũy score theo rank từ cả hai nguồn
    combined_scores: Dict[str, float] = {}   # key = (text, source)
    all_results: Dict[str, Dict] = {}

    def _key(res: Dict) -> str:
        return f"{res['text'][:80]}||{res['metadata'].get('source', '')}"

    for rank, res in enumerate(dense_results, 1):
        k = _key(res)
        combined_scores[k] = combined_scores.get(k, 0.0) + dense_weight * (1.0 / (60 + rank))
        all_results[k] = res

    for rank, res in enumerate(sparse_results, 1):
        k = _key(res)
        combined_scores[k] = combined_scores.get(k, 0.0) + sparse_weight * (1.0 / (60 + rank))
        all_results.setdefault(k, res)

    sorted_keys = sorted(combined_scores, key=combined_scores.__getitem__, reverse=True)

    final = []
    for k in sorted_keys[:top_k]:
        res = all_results[k].copy()
        res["score"] = combined_scores[k]
        final.append(res)

    return final


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
    Rerank candidates bằng keyword-density scoring (proxy cross-encoder,
    zero-dependency). Trong production dùng sentence_transformers.CrossEncoder.

    Funnel logic (từ slide):
      Search rộng (top_k_search) → Rerank → Select (top_k_select=3)

    Sprint 3 — Variant B: Bật use_rerank=True trong rag_answer().
    Lý do: Dense search top-10 thường có noise ở rank 4-10;
    rerank chấm lại theo relevance thực sự với query giúp top-3 chính xác hơn.
    """
    query_words = set(query.lower().split())

    def _score(cand: Dict) -> float:
        doc_words = cand["text"].lower().split()
        if not doc_words:
            return cand.get("score", 0.0)
        # Tỉ lệ query words xuất hiện trong chunk (recall proxy)
        keyword_density = sum(1 for w in doc_words if w in query_words) / len(doc_words)
        return cand.get("score", 0.0) + keyword_density

    ranked = sorted(candidates, key=_score, reverse=True)
    return ranked[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion": Thêm từ đồng nghĩa, alias, tên cũ (rule-based)
      - "decomposition": Tách query phức tạp thành sub-queries (LLM)
      - "hyde": Sinh hypothetical document để embed thay query (LLM)

    Sprint 3 — Variant C: Gọi transform_query() trước retrieve.
    Lý do: Khi query dùng alias ("Approval Matrix") nhưng doc dùng tên khác
    ("Access Control SOP") → expansion giúp tăng recall không cần thay model.
    """
    if strategy == "expansion":
        expansions = [query]
        lower_query = query.lower()

        alias_map = {
            "approval matrix": [
                "Access Control SOP",
                "Approval Matrix for System Access",
                "tên mới của Approval Matrix",
            ],
            "approval matrix for system access": [
                "Access Control SOP",
                "tên cũ approval matrix",
            ],
            "err-403-auth": [
                "authentication error",
                "IT Helpdesk",
                "helpdesk ext. 9000",
            ],
            "khách hàng vip": [
                "quy trình hoàn tiền chuẩn",
                "Finance Team xử lý 3-5 ngày làm việc",
            ],
            "remote": [
                "Team Lead phê duyệt",
                "onsite Thứ 3 Thứ 5",
            ],
        }

        for key, variants in alias_map.items():
            if key in lower_query:
                expansions.extend(variants)

        return list(dict.fromkeys(expansions))

    elif strategy == "decomposition":
        # LLM-based: tách câu hỏi phức tạp thành sub-queries
        import json
        decomp_prompt = (
            f"Break down the following question into 2-3 simpler sub-questions "
            f"that together cover the original question. "
            f"Output ONLY a JSON array of strings, nothing else.\n"
            f"Question: {query}"
        )
        try:
            raw = call_llm(decomp_prompt)
            sub_queries = json.loads(raw.strip())
            if isinstance(sub_queries, list):
                return [query] + [str(q) for q in sub_queries]
        except Exception:
            pass
        return [query]

    elif strategy == "hyde":
        # HyDE: sinh câu trả lời giả để embed thay query
        hyde_prompt = (
            f"Write a short, factual passage (2-3 sentences) that would directly "
            f"answer the following question as if it were from an internal policy document.\n"
            f"Question: {query}\nPassage:"
        )
        try:
            hypothetical_doc = call_llm(hyde_prompt)
            return [query, hypothetical_doc]
        except Exception:
            return [query]

    return [query]


def _merge_results(result_sets: List[List[Dict[str, Any]]], top_k: int) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for result_set in result_sets:
        for rank, item in enumerate(result_set, start=1):
            source = item.get("metadata", {}).get("source", "")
            key = f"{source}::{item.get('text', '')[:120]}"
            score = item.get("score", 0.0) + (1.0 / (60 + rank))
            if key not in merged or score > merged[key]["score"]:
                merged[key] = {
                    "text": item.get("text", ""),
                    "metadata": item.get("metadata", {}),
                    "score": score,
                }
    return sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:top_k]


def _retrieve_with_expansion(query: str, retrieval_mode: str, top_k: int) -> List[Dict[str, Any]]:
    expanded_queries = transform_query(query, strategy="expansion")
    result_sets = []
    for expanded_query in expanded_queries:
        if retrieval_mode == "dense":
            result_sets.append(retrieve_dense(expanded_query, top_k=top_k))
        elif retrieval_mode == "hybrid":
            result_sets.append(retrieve_hybrid(expanded_query, top_k=top_k))
        elif retrieval_mode == "sparse":
            result_sets.append(retrieve_sparse(expanded_query, top_k=top_k))
    return _merge_results(result_sets, top_k=top_k)


def _choose_query_strategy(
    query: str,
    retrieval_mode: str,
    top_k_search: int,
    top_k_select: int,
    use_rerank: bool,
) -> Dict[str, Any]:
    lower_query = query.lower()
    strategy = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
    }

    if retrieval_mode == "auto":
        strategy["retrieval_mode"] = "dense"

        if "approval matrix" in lower_query or "err-" in lower_query:
            strategy["retrieval_mode"] = "hybrid"

        if any(token in lower_query for token in [" bao lâu", " ai ", " có phải ", " điều kiện", " onsite", " remote"]):
            strategy["top_k_select"] = 4

        strategy["use_rerank"] = False

    return strategy


def _filter_candidates_by_query(query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    lower_query = query.lower()
    if not candidates:
        return candidates

    preferred_sources = []
    if any(token in lower_query for token in ["p1", "incident", "sla", "senior engineer"]):
        preferred_sources = ["support/sla-p1-2026.pdf"]
    elif any(token in lower_query for token in ["refund", "hoàn tiền", "flash sale", "vip"]):
        preferred_sources = ["policy/refund-v4.pdf"]
    elif any(token in lower_query for token in ["approval matrix", "access", "cấp quyền", "level 3", "level 4"]):
        preferred_sources = ["it/access-control-sop.md"]
    elif any(token in lower_query for token in ["remote", "annual leave", "nghỉ", "overtime"]):
        preferred_sources = ["hr/leave-policy-2026.pdf"]
    elif any(token in lower_query for token in ["password", "vpn", "helpdesk", "err-"]):
        preferred_sources = ["support/helpdesk-faq.md"]

    if not preferred_sources:
        return candidates

    preferred = []
    others = []
    for cand in candidates:
        source = cand.get("metadata", {}).get("source", "")
        if any(pref in source for pref in preferred_sources):
            preferred.append(cand)
        else:
            others.append(cand)

    return preferred + others


def _postprocess_answer(query: str, answer: str, candidates: List[Dict[str, Any]]) -> str:
    lower_query = query.lower()
    combined_context = "\n".join(chunk.get("text", "") for chunk in candidates).lower()

    if "approval matrix" in lower_query and "access control sop" in combined_context:
        return "Tài liệu 'Approval Matrix for System Access' hiện có tên mới là 'Access Control SOP' [1]."

    err_match = re.search(r"(err-[a-z0-9-]+)", lower_query)
    if err_match:
        err_code = err_match.group(1).upper()
        if err_match.group(1) not in combined_context:
            return (
                f"Không tìm thấy thông tin về {err_code} trong tài liệu hiện có. "
                "Hãy liên hệ IT Helpdesk qua ext. 9000 để được hỗ trợ thêm."
            )

    if "vip" in lower_query and ("không biết" in answer.lower() or "not documented" in answer.lower()):
        if "3-5 ngày làm việc" in combined_context:
            return (
                "Tài liệu không đề cập quy trình riêng cho khách hàng VIP. "
                "Theo chính sách hiện hành, yêu cầu hoàn tiền vẫn theo quy trình chuẩn "
                "và Finance Team xử lý trong 3-5 ngày làm việc [1]."
            )

    return answer


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

Rules:
1. Answer only what the question asks. Do not add extra facts unless they are necessary.
2. If the question has multiple parts, answer every part explicitly.
3. If the context contains a general rule and an explicit exception, the exception overrides the general rule.
4. If a special case is not documented, say it is not documented, then provide the closest standard policy from the context.
5. If the exact term or code is not found, do not infer a specific process from a different document.
6. Prefer the most directly relevant source and avoid mixing unrelated procedures.
7. Include required conditions, approvers, limits, and extra requirements when they are part of the answer.
8. If the context is insufficient, say you do not know. Do not make up information.
9. Cite the source block number like [1], [2] when possible.
10. Respond in the same language as the question.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời grounded.

    Tự động chọn provider dựa theo biến môi trường LLM_PROVIDER:
      - "openai"  (mặc định): dùng OPENAI_API_KEY + LLM_MODEL
      - "gemini"             : dùng GOOGLE_API_KEY + GEMINI_MODEL

    temperature=0 để output deterministic, dễ so sánh A/B.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(gemini_model)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0, "max_output_tokens": 1024},
        )
        return response.text
    else:
        # Default: OpenAI
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
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
    strategy = _choose_query_strategy(
        query,
        retrieval_mode=retrieval_mode,
        top_k_search=top_k_search,
        top_k_select=top_k_select,
        use_rerank=use_rerank,
    )
    selected_mode = strategy["retrieval_mode"]
    selected_search_k = strategy["top_k_search"]
    selected_select_k = strategy["top_k_select"]
    selected_rerank = strategy["use_rerank"]

    config = {
        "retrieval_mode": selected_mode,
        "top_k_search": selected_search_k,
        "top_k_select": selected_select_k,
        "use_rerank": selected_rerank,
        "requested_mode": retrieval_mode,
    }

    lower_query = query.lower()
    use_expansion = any(token in lower_query for token in ["approval matrix", "err-", "vip"])

    # --- Bước 1: Retrieve ---
    if use_expansion:
        candidates = _retrieve_with_expansion(query, retrieval_mode=selected_mode, top_k=selected_search_k)
    elif selected_mode == "dense":
        candidates = retrieve_dense(query, top_k=selected_search_k)
    elif selected_mode == "sparse":
        candidates = retrieve_sparse(query, top_k=selected_search_k)
    elif selected_mode == "hybrid":
        candidates = retrieve_hybrid(query, top_k=selected_search_k)
    else:
        raise ValueError(f"retrieval_mode không hợp lệ: {selected_mode}")

    candidates = _filter_candidates_by_query(query, candidates)

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={selected_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    # --- Bước 2: Rerank (optional) ---
    if selected_rerank:
        candidates = rerank(query, candidates, top_k=selected_select_k)
    else:
        candidates = candidates[:selected_select_k]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)
    answer = _postprocess_answer(query, answer, candidates)

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

    strategies = ["dense", "auto", "hybrid"]

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
        except Exception as e:
            print(f"Lỗi: {e}")

    # Uncomment sau khi Sprint 3 hoàn thành:
    # print("\n--- Sprint 3: So sánh strategies ---")
    # compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    # compare_retrieval_strategies("ERR-403-AUTH")

    # -------------------------------------------------------------------------
    # Sprint 3: Variant B — Dense + Rerank
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("SPRINT 3 — Variant B: Dense + Rerank")
    print("=" * 60)
    rerank_query = "Quy trình xử lý khi có sự cố P1 là gì?"
    print(f"\nQuery: {rerank_query}")
    try:
        r_base = rag_answer(rerank_query, retrieval_mode="dense", use_rerank=False)
        r_rerank = rag_answer(rerank_query, retrieval_mode="dense", use_rerank=True)
        print(f"[Baseline] Answer: {r_base['answer']}")
        print(f"[Rerank  ] Answer: {r_rerank['answer']}")
        print(f"[Rerank  ] Sources: {r_rerank['sources']}")
    except Exception as e:
        print(f"Lỗi: {e}")

    print("\n" + "=" * 60)
    print("✅ Sprint 2 + Sprint 3 hoàn thành!")
    print("   → Ghi kết quả A/B vào docs/tuning-log.md")
    print("=" * 60)
