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

    # Chuyển đổi format ChromaDB sang list of dicts
    chunks = []
    if results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            chunks.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": 1 - results["distances"][0][i]  # Cosine similarity
            })
    
    '''
    Trong ChromaDB, khi chúng ta cấu hình không gian vector là hnsw:space: cosine, kết quả trả về trong trường distances thực chất là Cosine Distance (Khoảng cách Cosine), chứ không phải là Cosine Similarity (Độ tương đồng Cosine).

    Mối quan hệ giữa hai đại lượng này được định nghĩa là: $$\text{Cosine Distance} = 1 - \text{Cosine Similarity}$$

    Vì vậy:

    Kết quả từ ChromaDB (distance): Càng nhỏ (gần về 0) thì càng giống nhau.
    Thứ chúng ta thường muốn hiển thị (score): Càng lớn (gần về 1) thì càng giống nhau.
    Đó là lý do tại sao dòng code đó thực hiện phép tính 1 - results["distances"][0][i]. Nó giúp chuyển đổi từ "khoảng cách" sang "độ tương đồng" để người dùng dễ quan sát hơn (ví dụ: score 0.95 nghe sẽ trực quan hơn là distance 0.05).
    '''

    return chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).
    """
    from rank_bm25 import BM25Okapi
    import chromadb
    from index import CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    
    # Lấy toàn bộ chunks từ database để xây dựng BM25 index
    all_docs = collection.get(include=["documents", "metadatas"])
    corpus = all_docs["documents"]
    metadatas = all_docs["metadatas"]

    if not corpus:
        return []

    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    
    # Lấy top_k kết quả
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    
    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            results.append({
                "text": corpus[idx],
                "metadata": metadatas[idx],
                "score": float(scores[idx]),
                "rank": top_indices.index(idx) + 1
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
    dense_results = retrieve_dense(query, top_k=top_k * 2)
    sparse_results = retrieve_sparse(query, top_k=top_k * 2)
    
    # Reciprocal Rank Fusion (RRF)
    # Score = sum(weight / (60 + rank))
    rrf_scores = {}  # {text_content: score}
    doc_map = {}     # {text_content: metadata}
    
    for i, res in enumerate(dense_results):
        txt = res["text"]
        doc_map[txt] = res["metadata"]
        rrf_scores[txt] = rrf_scores.get(txt, 0) + dense_weight * (1.0 / (60 + i + 1))
        
    for i, res in enumerate(sparse_results):
        txt = res["text"]
        doc_map[txt] = res["metadata"]
        rrf_scores[txt] = rrf_scores.get(txt, 0) + sparse_weight * (1.0 / (60 + i + 1))
        
    # Sort by RRF score
    sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    return [
        {"text": txt, "metadata": doc_map[txt], "score": score}
        for txt, score in sorted_rrf
    ]


# Reranking đã được loại bỏ theo yêu cầu để giảm dependency


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def mmr_select(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
    lambda_param: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Maximal Marginal Relevance: Đa dạng hóa các chunk được chọn.
    """
    if not candidates:
        return []

    import numpy as np
    from index import get_embedding
    from sklearn.metrics.pairwise import cosine_similarity

    query_emb = np.array(get_embedding(query)).reshape(1, -1)
    doc_embs = [np.array(get_embedding(c["text"])) for c in candidates]
    
    selected_indices = []
    unselected_indices = list(range(len(candidates)))

    # Chọn chunk đầu tiên có relevance cao nhất
    scores_with_query = cosine_similarity(query_emb, doc_embs)[0]
    best_first = np.argmax(scores_with_query)
    selected_indices.append(best_first)
    unselected_indices.remove(best_first)

    while len(selected_indices) < min(top_k, len(candidates)):
        best_mmr = -1e9
        best_idx = -1
        
        for idx in unselected_indices:
            # Relevance score
            rel = scores_with_query[idx]
            
            # Redundancy score (max similarity with already selected docs)
            current_doc_emb = doc_embs[idx].reshape(1, -1)
            selected_embs = [doc_embs[i] for i in selected_indices]
            redundancy = np.max(cosine_similarity(current_doc_emb, selected_embs)[0])
            
            mmr_score = lambda_param * rel - (1 - lambda_param) * redundancy
            if mmr_score > best_mmr:
                best_mmr = mmr_score
                best_idx = idx
        
        if best_idx != -1:
            selected_indices.append(best_idx)
            unselected_indices.remove(best_idx)
        else:
            break

    return [candidates[i] for i in selected_indices]


def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.
    """
    # Strategy expansion đơn giản (có thể nâng cấp lên LLM sau)
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
    Xây dựng grounded prompt với Grounding Constraints và Citation Formatting.
    """
    prompt = f"""Bạn là một trợ lý nội bộ chuyên nghiệp. Hãy trả lời câu hỏi dựa TRÊN DUY NHẤT các tài liệu được cung cấp dưới đây.

QUY TẮC NGHIÊM NGẶT (Grounding Constraints):
1. Chỉ sử dụng thông tin từ phần 'Context' để trả lời.
2. Nếu không tìm thấy câu trả lời trong Context, hãy trả lời chính xác là: "Tôi xin lỗi, thông tin này không có trong tài liệu nội bộ." và không được tự ý bịa thêm thông tin.
3. Không sử dụng kiến thức bên ngoài của bạn.

QUY TẮC TRÍCH DẪN (Citation Formatting):
1. Mỗi khi sử dụng thông tin từ một nguồn, hãy đặt mã số trích dẫn [n] ngay sau câu đó (ví dụ: [1]).
2. Cuối câu trả lời, hãy liệt kê danh sách các nguồn đã sử dụng.

Câu hỏi: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi OpenAI để sinh câu trả lời.
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512,
    )
    return response.choices[0].message.content


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_mmr: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (mmr) → generate.
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_mmr": use_mmr,
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

    # --- Bước 2: Post-process (MMR or simple truncate) ---
    if use_mmr:
        if verbose: print("[RAG] Running MMR...")
        candidates = mmr_select(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] Final selected: {len(candidates)} chunks")

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

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

    strategies = ["dense", "sparse", "hybrid"]  # Thêm "sparse" sau khi implement

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
    import argparse
    parser = argparse.ArgumentParser(description="RAG Answer Pipeline")
    parser.add_argument("--query", type=str, help="Câu hỏi cần trả lời")
    parser.add_argument("--mode", type=str, default="dense", choices=["dense", "sparse", "hybrid"], help="Chế độ retrieval")
    parser.add_argument("--mmr", action="store_true", help="Có dùng MMR đa dạng hóa không")
    parser.add_argument("--verbose", action="store_true", help="In thông tin debug")
    parser.add_argument("--compare", action="store_true", help="So sánh các chế độ retrieval với nhau")

    args = parser.parse_args()

    if args.compare and args.query:
        compare_retrieval_strategies(args.query) # <-- Gọi hàm này ở đây
    elif args.query:
        print(f"--- Running RAG for: {args.query} (mode={args.mode}, mmr={args.mmr}) ---")
        try:
            result = rag_answer(
                query=args.query,
                retrieval_mode=args.mode,
                use_mmr=args.mmr,
                verbose=args.verbose
            )
            print("\nANSWER:")
            print(result["answer"])
            print("\nSOURCES:")
            print(", ".join(result["sources"]))
        except Exception as e:
            print(f"Lỗi: {e}")
    else:
        # Chạy demo test queries
        test_queries = [
            "SLA xử lý ticket P1 là bao lâu?",
            "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
            "ERR-403-AUTH là lỗi gì?",
        ]
        
        for q in test_queries:
            print(f"\nQuery: {q}")
            try:
                result = rag_answer(q, retrieval_mode="dense", verbose=False)
                print(f"Answer: {result['answer']}")
            except Exception as e:
                print(f"Lỗi: {e}")
