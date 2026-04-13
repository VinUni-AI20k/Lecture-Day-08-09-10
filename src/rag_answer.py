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


def _chat_model() -> str:
    """
    Model chat completions (CHAT_MODEL). Mặc định gpt-4o-mini nếu không đặt.
    Không đọc EMBEDDING_MODEL.
    """
    return (os.getenv("CHAT_MODEL") or "").strip() or "gpt-4o-mini"


def _make_openai_client():
    """
    Client OpenAI SDK cho chat completions.

    CHAT_BASE_URL: để trống → https://api.openai.com/v1. Không dùng EMBEDDING_BASE_URL.
    """
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = (os.getenv("CHAT_BASE_URL") or "").strip()
    default_headers = None
    if base_url and "ngrok" in base_url.lower():
        default_headers = {"ngrok-skip-browser-warning": "true"}
    kwargs: Dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    if default_headers:
        kwargs["default_headers"] = default_headers
    return OpenAI(**kwargs)


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
        print(f"[retrieve_dense] ChromaDB error: {e}")
        return []

    try:
        query_embedding = get_embedding(query)
    except NotImplementedError:
        print("[retrieve_dense] get_embedding chưa được implement.")
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    out = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
            out.append({
                "text": doc,
                "metadata": meta,
                "score": 1.0 - dist
            })
    return out


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).
    """
    import chromadb
    from index import CHROMA_DB_DIR
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        print("[retrieve_sparse] Cần cài đặt rank_bm25: pip install rank-bm25")
        return []

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")
    except Exception as e:
        print(f"[retrieve_sparse] ChromaDB error: {e}")
        return []

    all_data = collection.get(include=["documents", "metadatas"])
    documents = all_data.get("documents", [])
    metadatas = all_data.get("metadatas", [])
    
    if not documents:
        return []

    tokenized_corpus = [doc.lower().split() for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    
    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            results.append({
                "text": documents[idx],
                "metadata": metadatas[idx],
                "score": float(scores[idx])
            })
            
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
    """
    # Lấy nhiều candidate hơn để merge
    dense_results = retrieve_dense(query, top_k=top_k * 2)
    sparse_results = retrieve_sparse(query, top_k=top_k * 2)

    docs_dict = {}
    rrf_scores = {}

    for rank, item in enumerate(dense_results):
        key = item["text"]
        if key not in docs_dict:
            docs_dict[key] = item
        if key not in rrf_scores:
            rrf_scores[key] = 0.0
        rrf_scores[key] += dense_weight * (1.0 / (60 + rank + 1))

    for rank, item in enumerate(sparse_results):
        key = item["text"]
        if key not in docs_dict:
            docs_dict[key] = item
        if key not in rrf_scores:
            rrf_scores[key] = 0.0
        rrf_scores[key] += sparse_weight * (1.0 / (60 + rank + 1))

    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    final_results = []
    for key, score in sorted_docs[:top_k]:
        doc_item = docs_dict[key].copy()
        doc_item["score"] = score
        final_results.append(doc_item)

    return final_results


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
    Rerank các candidate chunks bằng Jina AI Cross-Encoder.
    """
    import requests
    import os

    api_key = os.getenv("JINA_API") or os.getenv("AUTHORIZATION_JINA")
    model_name = os.getenv("RERANKING_MODEL", "jina-reranker-v2-base-multilingual")

    if not api_key:
        print("[rerank] Lỗi: Không tìm thấy JINA_API trong .env")
        return candidates[:top_k]

    url = "https://api.jina.ai/v1/rerank"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    documents = [c["text"] for c in candidates]

    data = {
        "model": model_name,
        "query": query,
        "top_n": top_k,
        "documents": documents,
        "return_documents": False
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        results = response.json()["results"]
        
        reranked = []
        for item in results:
            idx = item["index"]
            c = candidates[idx].copy()
            c["score"] = item["relevance_score"]
            reranked.append(c)
            
        return reranked
    except Exception as e:
        print(f"[rerank] Lỗi gọi Jina API: {e}")
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
    if not os.getenv("OPENAI_API_KEY"):
        return [query]

    client = _make_openai_client()

    if strategy == "expansion":
        prompt = (
            f"Given the query: '{query}'\n"
            "Generate 2-3 alternative phrasings or related terms in Vietnamese.\n"
            "Output as a JSON array of strings, no extra text."
        )
    elif strategy == "decomposition":
        prompt = (
            f"Break down this complex query into 2-3 simpler sub-queries: '{query}'\n"
            "Output as a JSON array of strings, no extra text."
        )
    elif strategy == "hyde":
        prompt = (
            f"Write a short hypothetical document passage that would answer this query: '{query}'\n"
            "Output as a JSON array containing only that one passage string, no extra text."
        )
    else:
        return [query]

    response = client.chat.completions.create(
        model=_chat_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=256,
    )
    import json
    try:
        queries = json.loads(response.choices[0].message.content)
        if isinstance(queries, list) and queries:
            return queries
    except (json.JSONDecodeError, TypeError):
        pass
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
    prompt = f"""Bạn là một trợ lý IT và HR nội bộ.
Dưới đây là các tài liệu tham khảo (Context).

YÊU CẦU BẮT BUỘC:
1. CHỈ sử dụng thông tin từ Context để trả lời. TUYỆT ĐỐI KHÔNG dùng kiến thức bên ngoài.
2. Nếu Context không có câu trả lời, hãy nói chính xác: "Tôi không có đủ dữ liệu để trả lời câu hỏi này."
3. Ở cuối mỗi thông tin cung cấp, BẮT BUỘC phải thêm số thứ tự nguồn trong ngoặc vuông (ví dụ: [1], [2]).
4. Trả lời ngắn gọn, rõ ràng, và chỉ tập trung vào câu hỏi. KHÔNG tự suy diễn hoặc thêm thông tin không có trong Context.
5. Nếu có thông tin người dùng (Tên, địa chỉ, số điện thoại, thông tin tài chính, ) nằm trong Context, Content, Câu hỏi thì KHÔNG được ghi nhớ và KHÔNG được đề cập đến trong câu trả lời.
6. Trả lời cùng ngôn ngữ với Câu hỏi.

Câu hỏi: {query}

[CONTEXT]
{context_block}
[END CONTEXT]

Trả lời:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM chat qua OpenAI SDK (_chat_model() = CHAT_MODEL).
    Lưu ý: Dùng temperature=0 hoặc thấp để output ổn định cho evaluation.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    llm_model = _chat_model()
    if not api_key:
        return "Lỗi: Không tìm thấy OPENAI_API_KEY trong .env. Vui lòng cấu hình."
        
    try:
        client = _make_openai_client()
        response = client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[call_llm] Lỗi gọi OpenAI API: {e}")
        return f"Lỗi không gọi được LLM: {e}"


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
        "Thời tiết hôm nay mưa to, nếu tôi muốn hoàn tiền vì đơn hàng bị ngập nước thì có được không?",
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
