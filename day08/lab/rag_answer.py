"""
rag_answer.py — Sprint 2 + Sprint 3 (ENHANCED)
===============================================
CẢI TIẾN ĐỘC ĐÁO SO VỚI BASELINE:

  ┌─────────────────────────────────────────────────────────────────┐
  │  PIPELINE MỚI: HyDE + Hybrid RRF + Smart Abstain Detection     │
  └─────────────────────────────────────────────────────────────────┘

  1. **HyDE — Hypothetical Document Embeddings** (Gao et al., 2022):
     Thay vì embed query trực tiếp, LLM sinh 1 đoạn văn "giả định"
     trả lời câu hỏi (hypothetical answer), rồi embed đoạn đó để search.
     Embedding của "đoạn văn trả lời" gần hơn với embedding chunk thật
     so với embedding của câu hỏi.
     → Đặc biệt hiệu quả với alias queries (q07) và multi-hop (gq06).

  2. **Multi-Query Fusion** (RAG-Fusion):
     Tự động sinh 2 cách diễn đạt khác nhau của query gốc bằng LLM,
     retrieve từng cách, fuse bằng RRF. Tăng recall cho paraphrase.

  3. **Smart Abstain Detection**:
     Trước khi generate, kiểm tra similarity score của top chunk.
     Nếu max_score < ABSTAIN_THRESHOLD → trả về abstain sớm,
     không gọi LLM, tiết kiệm cost và tránh hallucinate.
     → Áp dụng cho dense/sparse. Hybrid/HyDE/MultiQuery để LLM tự abstain.

  4. **Hybrid Retrieval (Dense + BM25 + RRF)** — giữ từ baseline.

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về answer có citation [1]
  ✓ rag_answer("Câu hỏi không có trong docs") → abstain

Definition of Done Sprint 3:
  ✓ HyDE retrieval chạy được end-to-end
  ✓ Scorecard baseline vs HyDE variant
"""

import os
import re
import json
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10
TOP_K_SELECT = 3

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

ABSTAIN_THRESHOLD = float(os.getenv("ABSTAIN_THRESHOLD", "0.20"))

_chroma_collection = None
_bm25_index = None
_bm25_chunks = None


# =============================================================================
# HELPERS
# =============================================================================

def _get_collection():
    global _chroma_collection
    if _chroma_collection is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        _chroma_collection = client.get_collection("rag_lab")
    return _chroma_collection


def call_llm(prompt: str) -> str:
    if LLM_PROVIDER == "gemini":
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY không được set")
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0, "max_output_tokens": 512}
        )
        return response.text
    else:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY không được set")
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        return response.choices[0].message.content


# =============================================================================
# RETRIEVAL — DENSE
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    from index import get_embedding
    collection = _get_collection()
    query_embedding = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "text": doc,
            "metadata": meta,
            "score": 1.0 - dist,
        })
    return chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25
# =============================================================================

def _build_bm25_index() -> Tuple[Any, List[Dict[str, Any]]]:
    global _bm25_index, _bm25_chunks
    if _bm25_index is not None:
        return _bm25_index, _bm25_chunks

    from rank_bm25 import BM25Okapi
    collection = _get_collection()
    results = collection.get(include=["documents", "metadatas"])
    all_chunks = [{"text": doc, "metadata": meta}
                  for doc, meta in zip(results["documents"], results["metadatas"])]
    tokenized = [c["text"].lower().split() for c in all_chunks]
    _bm25_index = BM25Okapi(tokenized)
    _bm25_chunks = all_chunks
    return _bm25_index, _bm25_chunks


def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    bm25, all_chunks = _build_bm25_index()
    scores = bm25.get_scores(query.lower().split())
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    max_score = max(scores) if max(scores) > 0 else 1.0
    return [
        {
            "text": all_chunks[i]["text"],
            "metadata": all_chunks[i]["metadata"],
            "score": float(scores[i] / max_score),
            "bm25_score": float(scores[i]),
        }
        for i in top_indices if scores[i] > 0
    ]


# =============================================================================
# RETRIEVAL — HYBRID (Dense + BM25 + RRF)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    dense_ranks = {r["text"]: rank for rank, r in enumerate(dense_results)}
    sparse_ranks = {r["text"]: rank for rank, r in enumerate(sparse_results)}

    all_texts = set(dense_ranks) | set(sparse_ranks)
    chunk_data: Dict[str, Dict] = {}
    for r in dense_results + sparse_results:
        chunk_data.setdefault(r["text"], r)

    RRF_K = 60
    rrf_scores = {
        text: (
            dense_weight / (RRF_K + dense_ranks.get(text, len(dense_results))) +
            sparse_weight / (RRF_K + sparse_ranks.get(text, len(sparse_results)))
        )
        for text in all_texts
    }

    sorted_texts = sorted(rrf_scores, key=lambda t: rrf_scores[t], reverse=True)[:top_k]
    results = []
    for text in sorted_texts:
        chunk = chunk_data[text].copy()
        chunk["score"] = rrf_scores[text]
        chunk["rrf_score"] = rrf_scores[text]
        results.append(chunk)
    return results


# =============================================================================
# CẢI TIẾN 1: HyDE — Hypothetical Document Embeddings
# =============================================================================

def retrieve_hyde(
    query: str,
    top_k: int = TOP_K_SEARCH,
    use_hybrid: bool = True,
) -> List[Dict[str, Any]]:
    hyde_prompt = (
        f"Hãy viết 2-3 câu trả lời ngắn gọn bằng tiếng Việt cho câu hỏi sau, "
        f"như thể bạn đang trích dẫn từ tài liệu nội bộ của công ty:\n\n"
        f"Câu hỏi: {query}\n\n"
        "Trả lời dưới dạng đoạn văn ngắn (không cần giải thích), "
        "dùng ngôn ngữ chính sách/quy trình. Nếu không biết, đoán hợp lý."
    )

    try:
        hypothetical_answer = call_llm(hyde_prompt).strip()
    except Exception as e:
        print(f"  [HyDE] Lỗi sinh hypothetical answer: {e} — fallback dense")
        return retrieve_dense(query, top_k=top_k)

    from index import get_embedding
    collection = _get_collection()
    hypo_embedding = get_embedding(hypothetical_answer)

    results = collection.query(
        query_embeddings=[hypo_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    hyde_results = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        hyde_results.append({
            "text": doc,
            "metadata": meta,
            "score": 1.0 - dist,
            "hyde_score": 1.0 - dist,
        })

    if not use_hybrid:
        return hyde_results

    sparse_results = retrieve_sparse(query, top_k=top_k)

    hyde_ranks = {r["text"]: rank for rank, r in enumerate(hyde_results)}
    sparse_ranks = {r["text"]: rank for rank, r in enumerate(sparse_results)}

    all_texts = set(hyde_ranks) | set(sparse_ranks)
    chunk_data: Dict[str, Dict] = {}
    for r in hyde_results + sparse_results:
        chunk_data.setdefault(r["text"], r)

    RRF_K = 60
    rrf_scores = {
        text: (
            0.65 / (RRF_K + hyde_ranks.get(text, len(hyde_results))) +
            0.35 / (RRF_K + sparse_ranks.get(text, len(sparse_results)))
        )
        for text in all_texts
    }

    sorted_texts = sorted(rrf_scores, key=lambda t: rrf_scores[t], reverse=True)[:top_k]
    final_results = []
    for text in sorted_texts:
        chunk = chunk_data[text].copy()
        chunk["score"] = rrf_scores[text]
        chunk["rrf_score"] = rrf_scores[text]
        chunk["retrieval_method"] = "hyde_hybrid"
        final_results.append(chunk)

    return final_results


# =============================================================================
# CẢI TIẾN 2: MULTI-QUERY FUSION (RAG-Fusion)
# =============================================================================

def retrieve_multi_query(
    query: str,
    top_k: int = TOP_K_SEARCH,
    n_variants: int = 2,
) -> List[Dict[str, Any]]:
    variant_prompt = (
        f"Cho câu hỏi sau bằng tiếng Việt: '{query}'\n"
        f"Hãy viết {n_variants} cách diễn đạt khác (paraphrase) của cùng câu hỏi này, "
        "dùng từ ngữ khác nhau nhưng cùng nghĩa. "
        "Trả về JSON array: [\"variant1\", \"variant2\"]\n"
        "Chỉ JSON, không giải thích."
    )

    queries = [query]
    try:
        response = call_llm(variant_prompt)
        json_match = re.search(r"\[.*?\]", response, re.DOTALL)
        if json_match:
            variants = json.loads(json_match.group())
            queries += [q for q in variants if isinstance(q, str)][:n_variants]
    except Exception as e:
        print(f"  [MultiQuery] Lỗi: {e} — dùng query gốc")

    all_results: List[List[Dict]] = []
    for q in queries:
        results = retrieve_hybrid(q, top_k=top_k)
        all_results.append(results)

    chunk_data: Dict[str, Dict] = {}
    text_ranks: Dict[str, List[int]] = {}

    for result_list in all_results:
        for rank, r in enumerate(result_list):
            text = r["text"]
            chunk_data.setdefault(text, r)
            if text not in text_ranks:
                text_ranks[text] = []
            text_ranks[text].append(rank)

    n_lists = len(all_results)
    max_rank = max(len(lst) for lst in all_results) if all_results else top_k

    RRF_K = 60
    rrf_scores = {}
    for text, ranks in text_ranks.items():
        while len(ranks) < n_lists:
            ranks.append(max_rank)
        score = sum(1.0 / (RRF_K + r) for r in ranks)
        rrf_scores[text] = score

    sorted_texts = sorted(rrf_scores, key=lambda t: rrf_scores[t], reverse=True)[:top_k]
    return [
        {**chunk_data[t], "score": rrf_scores[t], "retrieval_method": "multi_query"}
        for t in sorted_texts
    ]


# =============================================================================
# CẢI TIẾN 3: SMART ABSTAIN DETECTION
# =============================================================================

def should_abstain(candidates: List[Dict[str, Any]], threshold: float = ABSTAIN_THRESHOLD) -> bool:
    """
    Chỉ dùng cho dense/sparse (cosine score).
    RRF score (hybrid/hyde/multi_query) không dùng hàm này — xem rag_answer().
    """
    if not candidates:
        return True
    max_score = max(c.get("score", 0) for c in candidates)
    return max_score < threshold


# =============================================================================
# RERANK — Cross-Encoder
# =============================================================================

def rerank(query: str, candidates: List[Dict[str, Any]], top_k: int = TOP_K_SELECT) -> List[Dict[str, Any]]:
    try:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        pairs = [[query, chunk["text"]] for chunk in candidates]
        scores = model.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [{**chunk, "rerank_score": float(score)} for chunk, score in ranked[:top_k]]
    except ImportError:
        print("[rerank] CrossEncoder không khả dụng — fallback")
        return candidates[:top_k]
    except Exception as e:
        print(f"[rerank] Lỗi: {e} — fallback")
        return candidates[:top_k]


# =============================================================================
# AUGMENTATION — DOCUMENT REORDERING
# =============================================================================

def reorder_for_lost_in_middle(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(chunks) <= 2:
        return chunks
    top_half = [chunks[i] for i in range(0, len(chunks), 2)]
    bot_half = [chunks[i] for i in range(1, len(chunks), 2)]
    reordered = top_half + list(reversed(bot_half))
    return reordered


def build_context_block(
    chunks: List[Dict[str, Any]],
    use_reorder: bool = True,
) -> str:
    numbered = [(i + 1, chunk) for i, chunk in enumerate(chunks)]

    if use_reorder and len(chunks) > 2:
        reordered_chunks = reorder_for_lost_in_middle(chunks)
        text_to_num = {c["text"]: n for n, c in numbered}
        numbered = [(text_to_num.get(c["text"], i + 1), c)
                    for i, c in enumerate(reordered_chunks)]

    parts = []
    for cite_num, chunk in numbered:
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        score = chunk.get("score", 0)
        eff_date = meta.get("effective_date", "")

        header = f"[{cite_num}] Source: {source}"
        if section:
            header += f" | Section: {section}"
        if eff_date and eff_date != "unknown":
            header += f" | Effective: {eff_date}"
        if score > 0:
            header += f" | score={score:.3f}"

        parts.append(f"{header}\n{chunk.get('text', '')}")

    return "\n\n---\n\n".join(parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    return f"""Bạn là trợ lý nội bộ cho bộ phận CS + IT Helpdesk.

Context:
{context_block}

Câu hỏi: {query}

Quy tắc bắt buộc:
1. Chỉ trả lời dựa trên Context ở trên. KHÔNG dùng kiến thức ngoài.
2. Nếu Context không có thông tin → trả lời: "Không tìm thấy thông tin này trong tài liệu nội bộ."
3. Trích dẫn số nguồn [1], [2]... sau mỗi thông tin quan trọng.
4. Câu trả lời ngắn gọn, factual, bằng ngôn ngữ của câu hỏi.

Trả lời:"""


# =============================================================================
# PIPELINE CHÍNH: rag_answer()
# =============================================================================

def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    retrieval_mode:
      - "dense"       : Dense only (baseline)
      - "sparse"      : BM25 only
      - "hybrid"      : Dense + BM25 + RRF
      - "hyde"        : HyDE + BM25 hybrid
      - "multi_query" : RAG-Fusion với query variants
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
    elif retrieval_mode == "hyde":
        candidates = retrieve_hyde(query, top_k=top_k_search, use_hybrid=True)
    elif retrieval_mode == "multi_query":
        candidates = retrieve_multi_query(query, top_k=top_k_search)
    else:
        raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Mode: {retrieval_mode} | Candidates: {len(candidates)}")
        for i, c in enumerate(candidates[:5]):
            print(f"  [{i+1}] score={c.get('score', 0):.4f} | {c['metadata'].get('source', '?')} | {c['metadata'].get('section', '')[:40]}")

    # --- Bước 2: Smart Abstain Check ---
    # RRF scores (hybrid/hyde/multi_query) không thể dùng absolute threshold
    # vì score luôn nhỏ (~0.016) bất kể kết quả có liên quan hay không.
    # Với các mode này, để LLM tự abstain qua prompt (rule 2 trong grounded_prompt).
    # Với dense/sparse: dùng cosine threshold vì score mang ý nghĩa tuyệt đối.
    use_score_abstain = retrieval_mode in ("dense", "sparse")

    if use_score_abstain and should_abstain(candidates, threshold=ABSTAIN_THRESHOLD):
        abstain_answer = "Không tìm thấy thông tin này trong tài liệu nội bộ."
        if verbose:
            max_s = max((c.get("score", 0) for c in candidates), default=0)
            print(f"[RAG] ⚠ ABSTAIN (max_score={max_s:.4f} < threshold={ABSTAIN_THRESHOLD})")
        return {
            "query": query,
            "answer": abstain_answer,
            "sources": [],
            "chunks_used": candidates[:top_k_select] if candidates else [],
            "config": config,
            "abstained": True,
        }

    # Không có candidates nào (edge case)
    if not candidates:
        return {
            "query": query,
            "answer": "Không tìm thấy thông tin này trong tài liệu nội bộ.",
            "sources": [],
            "chunks_used": [],
            "config": config,
            "abstained": True,
        }

    # --- Bước 3: Rerank (optional) ---
    if use_rerank and len(candidates) > top_k_select:
        candidates = rerank(query, candidates, top_k=top_k_select)
        if verbose:
            print(f"[RAG] After rerank: {len(candidates)} chunks")
    else:
        candidates = candidates[:top_k_select]

    # --- Bước 4: Build context và generate ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Context ({len(context_block)} chars):")
        print(context_block[:400] + "...")

    answer = call_llm(prompt)

    sources = list({c["metadata"].get("source", "unknown") for c in candidates})

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
        "abstained": False,
    }


# =============================================================================
# RETRIEVAL — SPARSE / BM25
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    print(f"\n{'='*65}")
    print(f"A/B/C/D Comparison — Query: {query}")
    print("=" * 65)

    configs = [
        {"label": "Baseline (Dense)",        "retrieval_mode": "dense",       "use_rerank": False},
        {"label": "Variant A (Hybrid RRF)",  "retrieval_mode": "hybrid",      "use_rerank": False},
        {"label": "Variant B (HyDE★)",       "retrieval_mode": "hyde",        "use_rerank": False},
        {"label": "Variant C (MultiQuery★)", "retrieval_mode": "multi_query", "use_rerank": False},
    ]

    for cfg in configs:
        label = cfg.pop("label")
        print(f"\n--- {label} ---")
        try:
            result = rag_answer(query, verbose=False, **cfg)
            abstained = result.get("abstained", False)
            print(f"  Answer  : {'[ABSTAIN] ' if abstained else ''}{result['answer'][:200]}")
            print(f"  Sources : {result['sources']}")
            for i, c in enumerate(result["chunks_used"][:2]):
                print(f"  Chunk[{i+1}]: score={c.get('score', 0):.4f} | {c['metadata'].get('source', '?')} | {c['metadata'].get('section', '')[:35]}")
        except Exception as e:
            print(f"  Lỗi: {e}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 65)
    print("Sprint 2+3 (Enhanced): RAG Pipeline với HyDE + Smart Abstain")
    print("=" * 65)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì và cách xử lý?",
    ]

    print("\n--- Sprint 2: Test Baseline (Dense + Smart Abstain) ---")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = rag_answer(query, retrieval_mode="dense", verbose=True)
            print(f"Answer : {result['answer']}")
            print(f"Sources: {result['sources']}")
        except Exception as e:
            print(f"Lỗi: {e}")

    print("\n\n--- Sprint 3: So sánh Dense vs Hybrid vs HyDE ---")
    alias_queries = [
        "Approval Matrix để cấp quyền hệ thống là tài liệu nào?",
        "Mức phạt vi phạm SLA P1 là bao nhiêu?",
    ]
    for q in alias_queries:
        compare_retrieval_strategies(q)
