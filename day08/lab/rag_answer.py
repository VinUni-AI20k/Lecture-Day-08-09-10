"""
rag_answer.py — RAG Pipeline: Retrieval + Grounded Answer
"""

import os
import re
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH        = int(os.getenv("TOP_K_RETRIEVAL", 10))
TOP_K_SELECT        = int(os.getenv("TOP_K_RERANK", 5))
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", 0.35))
LLM_MODEL           = os.getenv("OPENAI_CHAT_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))
CHROMA_PERSIST_DIR  = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
EMBEDDING_MODEL     = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# =============================================================================
# SYSTEM PROMPT
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
# RETRIEVAL — DENSE
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """Dense retrieval từ ChromaDB dùng embedding similarity."""
    from index import get_embeddings_fn, CHROMA_PERSIST_DIR
    from langchain_community.vectorstores import Chroma

    embedding_fn = get_embeddings_fn()
    vectorstore = Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=embedding_fn,
    )
    results = vectorstore.similarity_search_with_score(query, k=top_k)
    return [
        {"text": doc.page_content, "metadata": doc.metadata, "score": 1.0 - distance}
        for doc, distance in results
    ]


# =============================================================================
# RETRIEVAL — SPARSE (BM25S)
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """Sparse retrieval dùng BM25S — mạnh với keyword, alias, mã lỗi."""
    import pickle
    import bm25s

    bm25_dir = os.getenv("BM25_INDEX_DIR", "./data/bm25_index")
    with open(f"{bm25_dir}/bm25.pkl", "rb") as f:
        retriever = pickle.load(f)
    with open(f"{bm25_dir}/docs.pkl", "rb") as f:
        bm25_docs = pickle.load(f)

    tokens = bm25s.tokenize([query], stopwords=None)
    results, scores = retriever.retrieve(tokens, corpus=bm25_docs, k=min(top_k, len(bm25_docs)))
    return [
        {"text": doc.page_content, "metadata": doc.metadata, "score": float(score)}
        for doc, score in zip(results[0], scores[0])
    ]


# =============================================================================
# RETRIEVAL — HYBRID (Dense + BM25S + RRF)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: Dense + BM25S kết hợp bằng Reciprocal Rank Fusion (RRF k=60).
    Giữ được cả ngữ nghĩa (dense) lẫn keyword chính xác (sparse/alias).
    """
    dense_results  = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

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
# RERANK — LLM-as-Reranker (OpenAI)
# =============================================================================

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """Rerank chunks bằng gpt-4o-mini — không cần model local."""
    if not candidates:
        return []

    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    chunks_text = "\n\n".join(f"[{i+1}] {c['text'][:300]}" for i, c in enumerate(candidates))
    prompt = (
        f"Given the query: \"{query}\"\n\n"
        f"Rank the following chunks by relevance (most relevant first).\n"
        f"Return ONLY a JSON array of chunk numbers in order, e.g. [3,1,2].\n\n"
        f"{chunks_text}"
    )
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
        )
        match = re.search(r"\[[\d,\s]+\]", response.choices[0].message.content)
        order = json.loads(match.group()) if match else list(range(1, len(candidates) + 1))
        seen, ranked = set(), []
        for idx in order:
            i = idx - 1
            if 0 <= i < len(candidates) and i not in seen:
                ranked.append(candidates[i])
                seen.add(i)
        for i, c in enumerate(candidates):
            if i not in seen:
                ranked.append(c)
        return ranked[:top_k]
    except Exception:
        return candidates[:top_k]


# =============================================================================
# QUERY TRANSFORMATION — HyDE
# =============================================================================

def transform_query(query: str, strategy: str = "hyde") -> List[str]:
    """
    HyDE: LLM generate đoạn văn giả định trả lời câu hỏi,
    embed đoạn đó thay vì embed query gốc → tăng recall với câu hỏi ngắn/mơ hồ.
    """
    if strategy != "hyde":
        return [query]

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
        return [f"{query}\n\n{hypothetical_doc}"]
    except Exception:
        return [query]


# =============================================================================
# GENERATION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta    = chunk.get("metadata", {})
        source  = meta.get("source", "unknown")
        section = meta.get("section", "")
        text    = chunk.get("text", "")
        header  = f"[{i}] Nguồn: {source}" + (f" | Section: {section}" if section else "")
        context_parts.append(f"{header}\n{text}")
    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    system_part = SYSTEM_PROMPT.format(context_block=context_block)
    return f"{system_part}\n\nCâu hỏi: {query}\n\nTrả lời (trích dẫn [số] sau mỗi ý):".strip()


def generate_answer(
    query: str,
    reranked_docs: List[Dict[str, Any]],
    has_context: bool,
    llm=None,
) -> Dict[str, Any]:
    """
    Sinh câu trả lời grounded từ retrieved chunks.
    Nếu không có context → abstain (không gọi LLM).
    """
    if not has_context or not reranked_docs:
        return {
            "answer": (
                "Tôi không tìm thấy thông tin liên quan đến câu hỏi này trong tài liệu nội bộ hiện có. "
                "Tài liệu hiện tại bao gồm: SLA P1, chính sách hoàn tiền, Access Control SOP, HR Leave Policy, và IT Helpdesk FAQ. "
                "Nếu câu hỏi thuộc phạm vi trên, vui lòng liên hệ IT Helpdesk (ext. 9000) hoặc bộ phận có thẩm quyền để được hỗ trợ."
            ),
            "sources": [],
            "citations": [],
        }

    context_parts, sources, citation_indices = [], [], []
    for i, item in enumerate(reranked_docs, 1):
        if isinstance(item, tuple):
            doc, _ = item
            text = doc.page_content if hasattr(doc, "page_content") else doc.get("text", "")
            meta = doc.metadata if hasattr(doc, "metadata") else doc.get("metadata", {})
        else:
            text = item.get("text", "")
            meta = item.get("metadata", {})

        src     = meta.get("source", "unknown")
        section = meta.get("section", "")
        header  = f"[{i}] Nguồn: {src}" + (f" | {section}" if section else "")
        context_parts.append(f"{header}\n{text}")
        sources.append(src)
        citation_indices.append(i)

    prompt = build_grounded_prompt(query, "\n\n---\n\n".join(context_parts))

    if llm is not None:
        from langchain_core.messages import HumanMessage
        answer_text = llm.invoke([HumanMessage(content=prompt)]).content
    else:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        answer_text = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        ).choices[0].message.content

    return {
        "answer": answer_text,
        "sources": list(dict.fromkeys(sources)),
        "citations": citation_indices,
    }


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def rag_answer(
    query: str,
    retrieval_mode: str = "hybrid",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    retrieval_mode: "dense" | "sparse" | "hybrid"
    use_rerank: dùng LLM-as-reranker (gpt-4o-mini) để sắp xếp lại chunks
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
    }

    # Bước 1: Retrieve
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

    # Bước 2: Rerank hoặc truncate
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    # Bước 3: Lọc theo threshold, generate
    threshold = float(os.getenv("RELEVANCE_THRESHOLD", RELEVANCE_THRESHOLD))
    filtered  = [c for c in candidates if c.get("score", 1.0) >= threshold]
    has_context = len(filtered) > 0
    result = generate_answer(query, filtered if filtered else candidates, has_context=has_context)

    return {
        "query": query,
        "answer": result["answer"],
        "sources": result["sources"],
        "chunks_used": candidates,
        "config": config,
    }


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "SLA xử lý ticket P1 là bao lâu?"
    result = rag_answer(query, retrieval_mode="hybrid", use_rerank=True, verbose=True)
    print(f"\nAnswer: {result['answer']}")
    print(f"Sources: {result['sources']}")
