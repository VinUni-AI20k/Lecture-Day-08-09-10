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
import re
from collections import defaultdict
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Guard tối thiểu để abstain ổn định hơn ở Sprint 2
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.20"))
RRF_K = 60


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
    """
    import chromadb
    from index import get_embedding, CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    query_embedding = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    chunks: List[Dict[str, Any]] = []
    for doc, meta, distance in zip(documents, metadatas, distances):
        score = 1 - float(distance)  # cosine distance -> similarity
        chunks.append(
            {
                "text": doc or "",
                "metadata": meta or {},
                "score": score,
            }
        )

    # sort giảm dần theo score để chắc chắn ổn định
    chunks.sort(key=lambda x: x.get("score", 0.0), reverse=True)
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
    """
    import chromadb
    from rank_bm25 import BM25Okapi
    from index import CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    results = collection.get(include=["documents", "metadatas"])
    documents = results.get("documents", []) or []
    metadatas = results.get("metadatas", []) or []

    if not documents:
        return []

    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE)

    tokenized_corpus = [_tokenize(doc) for doc in documents]
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(query_tokens).tolist()

    # Chỉ giữ candidate có điểm > 0 để tránh đưa noise thuần túy vào context
    ranked_indices = sorted(
        range(len(bm25_scores)),
        key=lambda i: bm25_scores[i],
        reverse=True,
    )

    chunks: List[Dict[str, Any]] = []
    for idx in ranked_indices:
        raw_score = float(bm25_scores[idx])
        if raw_score <= 0:
            continue

        chunks.append(
            {
                "text": documents[idx] or "",
                "metadata": metadatas[idx] or {},
                "score": raw_score,
            }
        )
        if len(chunks) >= top_k:
            break

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
    """
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    if not dense_results and not sparse_results:
        return []
    if not sparse_results:
        return dense_results
    if not dense_results:
        return sparse_results

    def _chunk_key(chunk: Dict[str, Any]) -> str:
        meta = chunk.get("metadata", {})
        source = meta.get("source", "")
        section = meta.get("section", "")
        text = chunk.get("text", "")
        return f"{source}|{section}|{text[:180]}"

    fused = defaultdict(lambda: {"rrf": 0.0, "chunk": None, "dense_rank": None, "sparse_rank": None})

    for rank, chunk in enumerate(dense_results, start=1):
        key = _chunk_key(chunk)
        fused[key]["rrf"] += dense_weight * (1.0 / (RRF_K + rank))
        fused[key]["chunk"] = chunk
        fused[key]["dense_rank"] = rank

    for rank, chunk in enumerate(sparse_results, start=1):
        key = _chunk_key(chunk)
        fused[key]["rrf"] += sparse_weight * (1.0 / (RRF_K + rank))
        if fused[key]["chunk"] is None:
            fused[key]["chunk"] = chunk
        fused[key]["sparse_rank"] = rank

    merged: List[Dict[str, Any]] = []
    for item in fused.values():
        chunk = dict(item["chunk"] or {})
        # Scale nhẹ để tương thích guard relevance hiện tại trong rag_answer()
        fused_score = item["rrf"] * (RRF_K + 1)
        chunk["score"] = fused_score
        chunk["hybrid_debug"] = {
            "dense_rank": item["dense_rank"],
            "sparse_rank": item["sparse_rank"],
            "fused_score": fused_score,
        }
        merged.append(chunk)

    merged.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return merged[:top_k]



# =============================================================================
# RERANK (Sprint 3 alternative)
# =============================================================================

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Rerank các candidate chunks bằng cross-encoder.
    """
    # TODO Sprint 3: Implement rerank
    return candidates[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.
    """
    # TODO Sprint 3: Implement query transformation
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
        score = chunk.get("score", 0)
        text = chunk.get("text", "")

        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if score > 0:
            header += f" | score={score:.2f}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xây dựng grounded prompt theo 4 quy tắc:
    1. Evidence-only
    2. Abstain
    3. Citation
    4. Short, clear, stable
    """
    prompt = f"""Bạn là trợ lý RAG chỉ được phép trả lời từ context đã truy xuất.

Quy tắc:
1. Chỉ dùng thông tin có trong Context.
2. Nếu Context không đủ để trả lời, phải trả lời đúng cụm: "Không đủ dữ liệu".
3. Không suy đoán, không bịa thêm, không dùng kiến thức bên ngoài.
4. Khi trả lời được, phải trích dẫn ít nhất một citation dạng [1], [2], ...
5. Trả lời ngắn gọn, rõ ràng, cùng ngôn ngữ với câu hỏi.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời.
    """
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Thiếu OPENAI_API_KEY trong môi trường.")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=300,
    )

    content = response.choices[0].message.content
    return (content or "").strip()


def _normalize_abstain(answer: str) -> str:
    """
    Chuẩn hóa các biến thể abstain về đúng format Sprint 2.
    """
    if not answer:
        return "Không đủ dữ liệu"

    lowered = answer.strip().lower()
    abstain_markers = [
        "không đủ dữ liệu",
        "không có đủ dữ liệu",
        "không biết",
        "i do not know",
        "insufficient context",
        "insufficient information",
        "not enough information",
        "không đủ thông tin",
    ]
    if any(marker in lowered for marker in abstain_markers):
        return "Không đủ dữ liệu"
    return answer.strip()


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
            print(
                f"  [{i+1}] score={c.get('score', 0):.3f} | "
                f"{c.get('metadata', {}).get('source', '?')}"
            )

    # Guard cho trường hợp retrieval quá yếu / không có gì
    if not candidates:
        return {
            "query": query,
            "answer": "Không đủ dữ liệu",
            "sources": [],
            "chunks_used": [],
            "config": config,
        }

    best_score = candidates[0].get("score", 0.0)
    if best_score < MIN_RELEVANCE_SCORE:
        if verbose:
            print(f"[RAG] Best score too low ({best_score:.3f} < {MIN_RELEVANCE_SCORE}) -> abstain")
        return {
            "query": query,
            "answer": "Không đủ dữ liệu",
            "sources": [],
            "chunks_used": [],
            "config": config,
        }

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
        print(f"\n[RAG] Prompt:\n{prompt[:700]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)
    answer = _normalize_abstain(answer)

    # --- Bước 5: Extract sources ---
    sources = list({
        c.get("metadata", {}).get("source", "unknown")
        for c in candidates
        if c.get("metadata", {}).get("source")
    })

    # Nếu model trả lời có nội dung nhưng quên citation, gắn citation tối thiểu [1]
    # để bám DoD Sprint 2.
    if answer != "Không đủ dữ liệu" and "[" not in answer and candidates:
        answer = f"{answer} [1]"

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
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "hybrid", "sparse"]
    rows: List[Dict[str, Any]] = []

    for strategy in strategies:
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            rows.append(
                {
                    "strategy": strategy,
                    "answer": result["answer"],
                    "sources": ", ".join(result["sources"][:2]) or "-",
                    "top_score": (
                        f"{result['chunks_used'][0].get('score', 0.0):.3f}"
                        if result["chunks_used"] else "0.000"
                    ),
                }
            )
        except NotImplementedError as e:
            rows.append({"strategy": strategy, "answer": f"Chưa implement: {e}", "sources": "-", "top_score": "-"})
        except Exception as e:
            rows.append({"strategy": strategy, "answer": f"Lỗi: {e}", "sources": "-", "top_score": "-"})

    print("\n| Strategy | Top score | Sources (top-2) | Answer |")
    print("|---|---:|---|---|")
    for row in rows:
        safe_answer = str(row["answer"]).replace("\n", " ")
        print(f"| {row['strategy']} | {row['top_score']} | {row['sources']} | {safe_answer} |")



# =============================================================================
# MAIN — Demo và Test
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH",
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

    print("\n--- Sprint 3: Compare Baseline vs Variant ---")

    for query in test_queries:
        try:
            compare_retrieval_strategies(query)
        except Exception as e:
            print(f"Lỗi khi so sánh strategy cho query '{query}': {e}")

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
