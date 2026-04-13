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
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LAB_DIR            = Path(__file__).parent.resolve()

LLM_MODEL          = os.getenv("LLM_MODEL", "gpt-4o-mini")
CHROMA_PERSIST_DIR = str(LAB_DIR / os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db").lstrip("./"))
BM25_INDEX_DIR     = str(LAB_DIR / os.getenv("BM25_INDEX_DIR", "data/bm25_index").lstrip("./"))
EMBEDDING_MODEL    = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# =============================================================================
# SYSTEM PROMPT — Grounding Rules (Sprint 2)
# =============================================================================

SYSTEM_PROMPT = """
# ROLE
Bạn là AI chuyên gia hỗ trợ nội bộ cho khối CS và IT Helpdesk.

# CONTEXT GUIDELINES
Dưới đây là các đoạn thông tin được trích xuất từ tài liệu chính thức.
---
{context_block}
---

# CONSTRAINTS (BẮT BUỘC)
1. **Grounding**: Chỉ trả lời dựa trên thông tin có trong Context ở trên.
2. **Abstain**: Nếu Context không chứa đáp án, phải trả lời: "Tôi không tìm thấy thông tin này trong tài liệu".
3. **Citations**: Trích dẫn nguồn theo định dạng `[1]`, `[2]` ngay sau thông tin được lấy ra.
4. **No Hallucination**: Tuyệt đối không sử dụng kiến thức bên ngoài để bổ sung.

# OUTPUT FORMAT
- Ngôn ngữ: Tiếng Việt.
- Văn phong: Chuyên nghiệp, ngắn gọn.
"""


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Dense retrieval: tìm kiếm theo embedding similarity trong ChromaDB.
    Dùng LangChain Chroma — cùng cách index.py build index → tránh lỗi collection name mismatch.
    """
    from index import get_embeddings_fn, CHROMA_PERSIST_DIR
    from langchain_chroma import Chroma

    embedding_fn = get_embeddings_fn()
    vectorstore = Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=embedding_fn,
    )
    
    # Search
    results = vectorstore.similarity_search_with_score(query, k=top_k)
    
    # Convert to expected format
    formatted_results = []
    for doc, distance in results:
        # Distance to score (similarity)
        # Similarity approx = 1 - distance
        score = 1.0 - distance
        
        formatted_results.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": score
        })
        
    return formatted_results

    # similarity_search_with_score trả về List[(Document, score)]
    # score ở đây là cosine distance (nhỏ hơn = gần hơn) với Chroma mặc định
    results = vectorstore.similarity_search_with_score(query, k=top_k)

    chunks = []
    for doc, distance in results:
        # Chroma trả về L2 distance mặc định; chuyển thành similarity score 0-1
        score = max(0.0, 1.0 - distance)
        chunks.append({
            "text":     doc.page_content,
            "metadata": doc.metadata,
            "score":    score,
        })

    return chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25S).
    """
    # [Khai] retrieve_sparse — load BM25S index đã build từ index.py
    import pickle
    import bm25s

    # Retrieve global BM25_INDEX_DIR
    bm25_dir = BM25_INDEX_DIR
    with open(f"{bm25_dir}/bm25.pkl", "rb") as f:
        retriever = pickle.load(f)
    with open(f"{bm25_dir}/docs.pkl", "rb") as f:
        bm25_docs = pickle.load(f)

    tokens = bm25s.tokenize([query], stopwords=None)
    results, scores = retriever.retrieve(tokens, corpus=bm25_docs, k=min(top_k, len(bm25_docs)))

    chunks = []
    for doc, score in zip(results[0], scores[0]):
        chunks.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score),
        })
    return chunks


def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF).
    Hỗ trợ xử lý:
    - Tìm kiếm theo ý nghĩa (Dense)
    - Tìm kiếm theo từ khóa (Sparse): các tên riêng, mã lỗi, điều khoản
    - Query dùng alias/tên cũ (ví dụ: "Approval Matrix" → "Access Control SOP")
    """
    # [Khai] retrieve_hybrid — Dense + Sparse → RRF merge
    # Lý do chọn hybrid: corpus có cả ngôn ngữ tự nhiên (policy) lẫn
    # tên kỹ thuật/alias (ERR-403, Approval Matrix, ticket P1)
    # Dense bắt ngữ nghĩa, BM25 bắt keyword chính xác → RRF lấy điểm tốt nhất cả hai

    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    # RRF merge: score(doc) = Σ weight * 1/(k + rank), k=60 là hằng số RRF chuẩn
    RRF_K = 60
    score_map: Dict[str, Any] = {}

    for rank, chunk in enumerate(dense_results):
        cid = chunk["metadata"].get("chunk_id") or chunk["metadata"].get("source", "") + chunk["metadata"].get("section", "")
        if cid not in score_map:
            score_map[cid] = {"chunk": chunk, "rrf_score": 0.0}
        score_map[cid]["rrf_score"] += dense_weight * (1.0 / (RRF_K + rank))

    for rank, chunk in enumerate(sparse_results):
        cid = chunk["metadata"].get("chunk_id") or chunk["metadata"].get("source", "") + chunk["metadata"].get("section", "")
        if cid not in score_map:
            score_map[cid] = {"chunk": chunk, "rrf_score": 0.0}
        score_map[cid]["rrf_score"] += sparse_weight * (1.0 / (RRF_K + rank))

    merged = sorted(score_map.values(), key=lambda x: x["rrf_score"], reverse=True)

    results = []
    for item in merged[:top_k]:
        chunk = item["chunk"].copy()
        chunk["score"] = item["rrf_score"]
        results.append(chunk)
    return results


# =============================================================================
# CHÚ THÍCH SPRINT 3
# =============================================================================
# Thay vì dùng Cross-Encoder (Local Model) gây chậm và nặng máy,
# Nhóm quyết định sử dụng Hybrid Search (Dense + Sparse) làm Variant chính
# cho Sprint 3. Do đó, tính năng Rerank bằng model local đã được loại bỏ.


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
    # [Khai] transform_query — HyDE implementation
    if strategy != "hyde":
        return [query]

    # HyDE: dùng LLM generate đoạn văn giả định trả lời câu hỏi
    # Embed đoạn đó thay vì embed câu hỏi gốc → tăng recall với câu hỏi ngắn/mơ hồ
    # Fallback về query gốc nếu LLM fail (tránh crash pipeline)
    hyde_prompt = (
        f"Viết đoạn văn khoảng 80 từ trả lời câu hỏi sau, "
        f"dựa trên kiến thức về chính sách IT/HR nội bộ công ty.\n"
        f"Câu hỏi: {query}\nTrả lời:"
    )
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": hyde_prompt}],
            temperature=0.3,
            max_tokens=150,
        )
        hypothetical_doc = response.choices[0].message.content.strip()
        # Kết hợp query gốc + hypothetical doc để embed
        return [f"{query}\n\n{hypothetical_doc}"]
    except Exception:
        return [query]


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        text = chunk.get("text", "")

        header = f"[{i}] Nguồn: {source}"
        if section:
            header += f" | Section: {section}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)

def format_citations(sources: List[str]) -> str:
    """
    Tạo citation list ở cuối câu trả lời (Dành riêng cho Sprint 2 requirements).
    """
    if not sources:
        return ""
    lines = ["\n\n**Nguồn tham khảo:**"]
    for i, src in enumerate(sources, 1):
        lines.append(f"[{i}] {src}")
    return "\n".join(lines)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xây dựng grounded prompt.
    Sử dụng SYSTEM_PROMPT được định nghĩa ở trên làm template.
    """
    system_part = SYSTEM_PROMPT.format(context_block=context_block)
    
    prompt = f"{system_part}\n\nCâu hỏi: {query}\n\nTrả lời (trích dẫn [số] sau mỗi ý):"
    return prompt.strip()


def generate_answer(
    query: str,
    reranked_docs: List[Dict[str, Any]],
    has_context: bool,
    llm=None,
) -> Dict[str, Any]:
    """
    Core generation function cho Sprint 2.

    Args:
        query: Câu hỏi của người dùng
        reranked_docs: List các chunk đã qua rerank/select, mỗi phần tử là dict
                       với keys "text", "metadata", "score".
                       Hỗ trợ cả tuple (doc, score) để tương thích với ROLE_INDIVIDUALS spec.
        has_context: True nếu có chunk liên quan, False nếu retrieval không tìm thấy gì
        llm: Tuỳ chọn — LLM client bên ngoài (nếu None thì dùng call_llm() nội bộ)

    Returns:
        Dict với:
          - "answer": câu trả lời grounded có citation
          - "sources": list tên file nguồn
          - "citations": list số thứ tự trích dẫn

    Grounding rules (theo SYSTEM_PROMPT):
    - Nếu không có context → trả về câu "Không tìm thấy thông tin"
    - Nếu có context → build citation-marked context block rồi gọi LLM
    """
    # --- Trường hợp 1: Không có context ---
    if not has_context or not reranked_docs:
        return {
            "answer": "Không tìm thấy thông tin về câu hỏi này trong tài liệu hiện có.",
            "sources": [],
            "citations": [],
        }

    # --- Bước 1: Build context với citation markers [1], [2]... ---
    context_parts = []
    sources = []
    citation_indices = []

    for i, item in enumerate(reranked_docs, 1):
        # Hỗ trợ cả tuple (doc, score) lẫn dict thuần
        if isinstance(item, tuple):
            doc, score = item
            # doc có thể là LangChain Document (có .page_content / .metadata)
            # hoặc dict thông thường
            if hasattr(doc, "page_content"):
                text = doc.page_content
                meta = doc.metadata
            else:
                text = doc.get("text", "")
                meta = doc.get("metadata", {})
        else:
            # dict thuần (format nội bộ của rag_answer.py)
            text = item.get("text", "")
            meta = item.get("metadata", {})
            score = item.get("score", 0)

        src = meta.get("source", "unknown")
        section = meta.get("section", "")

        header = f"[{i}] Nguồn: {src}"
        if section:
            header += f" | {section}"

        context_parts.append(f"{header}\n{text}")
        sources.append(src)
        citation_indices.append(i)

    context_block = "\n\n---\n\n".join(context_parts)

    # --- Bước 2: Build prompt ---
    prompt = build_grounded_prompt(query, context_block)

    # --- Bước 3: Gọi LLM ---
    if llm is not None:
        # Nếu caller truyền LLM client (ví dụ LangChain ChatOpenAI)
        from langchain_core.messages import HumanMessage
        response = llm.invoke([
            HumanMessage(content=prompt),
        ])
        answer_text = response.content
    else:
        # Dùng OpenAI client nội bộ
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=512,
        )
        answer_text = response.choices[0].message.content

    return {
        "answer": answer_text,
        "sources": list(dict.fromkeys(sources)),   # deduplicated, order preserved
        "citations": citation_indices,
    }


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời sử dụng OpenAI.
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def rag_answer(
    query: str,
    retrieval_mode: str = "hybrid",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → generate.
    
    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào lời nhắc (lấy top đầu sau retrieve)
        verbose: In thêm thông tin debug
        
    Returns: Dict chứa kết quả (answer, sources, query, v.v)
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "model": "gpt-4o-mini",
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

    # --- Bước 2: Chọn top K chunk chất lượng nhất ---
    candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    if verbose:
        print(f"\n[RAG] Sending {len(candidates)} chunks to generate_answer()")

    # --- Bước 3: Generate (dùng generate_answer để có abstain + citation logic) ---
    has_context = len(candidates) > 0
    result = generate_answer(query, candidates, has_context=has_context)

    return {
        "query": query,
        "answer": result["answer"],
        "sources": result["sources"],
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

    print("\n--- Sprint 2: Test Baseline (Dense) ---")
    
    # Test câu hỏi cơ bản (Có trong Docs)
    query_s2 = "SLA xử lý ticket P1 là bao lâu?"
    print(f"\nQuery: {query_s2}")
    result_s2 = rag_answer(query_s2, retrieval_mode="dense", verbose=False)
    print(f"Answer: {result_s2['answer']}")
    
    print("\n--- Kiểm tra Abstain Loop ---")
    query_abstain = "ERR-403-AUTH là lỗi gì?"
    result_abstain = rag_answer(query_abstain, retrieval_mode="dense", verbose=False)
    print(f"\nQuery: {query_abstain}")
    print(f"Answer: {result_abstain['answer']}")
    
    print("\n" + "="*60)
    print("--- Sprint 3: Hybrid Search (Variant) ---")
    print("="*60)
    
    # Query khó: dùng tên cũ (alias) hoặc mã lỗi không có trong embedding tốt
    query_s3 = "Làm sao để có Approval Matrix và cấp quyền hệ thống?"
    print(f"\nQuery: {query_s3}")
    
    result_s3 = rag_answer(
        query_s3, 
        retrieval_mode="hybrid", 
        verbose=True
    )
    print(f"\nAnswer: {result_s3['answer']}\n")
