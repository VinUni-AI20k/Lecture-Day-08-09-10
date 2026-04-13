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
import json
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
_bm25_index = None
_bm25_chunks = None

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
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # ChromaDB cosine distance: score = 1 - distance
        score = 1.0 - dist
        chunks.append({
            "text": doc,
            "metadata": meta,
            "score": score,
        })

    return chunks

def _build_bm25_index() -> Tuple[Any, List[Dict]]:
    """
    Build BM25 index từ toàn bộ chunks trong ChromaDB.
    Cache để tránh rebuild nhiều lần.
    """
    global _bm25_index, _bm25_chunks

    if _bm25_index is not None:
        return _bm25_index, _bm25_chunks

    import chromadb
    from rank_bm25 import BM25Okapi
    from index import CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    # Lấy tất cả chunks
    results = collection.get(include=["documents", "metadatas"])
    all_docs = results["documents"]
    all_metas = results["metadatas"]

    _bm25_chunks = []
    tokenized_corpus = []

    for doc, meta in zip(all_docs, all_metas):
        _bm25_chunks.append({"text": doc, "metadata": meta})
        # Tokenize: lowercase + split (đơn giản, hiệu quả với tiếng Việt mixed)
        tokens = doc.lower().split()
        tokenized_corpus.append(tokens)

    _bm25_index = BM25Okapi(tokenized_corpus)
    return _bm25_index, _bm25_chunks


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
    bm25, all_chunks = _build_bm25_index()

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # Sort theo điểm giảm dần, lấy top_k
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for idx in top_indices:
        chunk = all_chunks[idx].copy()
        chunk["score"] = float(scores[idx])
        results.append(chunk)

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
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    # Tạo map text → rank cho cả hai danh sách
    dense_rank_map = {}
    for rank, chunk in enumerate(dense_results):
        key = chunk["text"][:200]  # dùng 200 char đầu làm key
        dense_rank_map[key] = rank

    sparse_rank_map = {}
    for rank, chunk in enumerate(sparse_results):
        key = chunk["text"][:200]
        sparse_rank_map[key] = rank

    # Gộp tất cả unique chunks
    all_chunks_map: Dict[str, Dict] = {}
    for chunk in dense_results + sparse_results:
        key = chunk["text"][:200]
        if key not in all_chunks_map:
            all_chunks_map[key] = chunk

    # Tính RRF score cho mỗi chunk
    RRF_K = 60
    scored_chunks = []
    for key, chunk in all_chunks_map.items():
        d_rank = dense_rank_map.get(key, len(dense_results))  # nếu không có → rank cuối
        s_rank = sparse_rank_map.get(key, len(sparse_results))
        rrf_score = (
            dense_weight * (1 / (RRF_K + d_rank)) +
            sparse_weight * (1 / (RRF_K + s_rank))
        )
        chunk_copy = chunk.copy()
        chunk_copy["score"] = rrf_score
        scored_chunks.append(chunk_copy)

    # Sort theo RRF score giảm dần
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]


# =============================================================================
# RERANK (Sprint 3 alternative)
# Cross-encoder để chấm lại relevance sau search rộng
# =============================================================================

# def rerank(
#     query: str,
#     candidates: List[Dict[str, Any]],
#     top_k: int = TOP_K_SELECT,
# ) -> List[Dict[str, Any]]:
#     """
#     Rerank các candidate chunks bằng cross-encoder.

#     Cross-encoder: chấm lại "chunk nào thực sự trả lời câu hỏi này?"
#     MMR (Maximal Marginal Relevance): giữ relevance nhưng giảm trùng lặp

#     Funnel logic (từ slide):
#       Search rộng (top-20) → Rerank (top-6) → Select (top-3)

#     TODO Sprint 3 (nếu chọn rerank):
#     Option A — Cross-encoder:
#         from sentence_transformers import CrossEncoder
#         model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
#         pairs = [[query, chunk["text"]] for chunk in candidates]
#         scores = model.predict(pairs)
#         ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
#         return [chunk for chunk, _ in ranked[:top_k]]

#     Option B — Rerank bằng LLM (đơn giản hơn nhưng tốn token):
#         Gửi list chunks cho LLM, yêu cầu chọn top_k relevant nhất

#     Khi nào dùng rerank:
#     - Dense/hybrid trả về nhiều chunk nhưng có noise
#     - Muốn chắc chắn chỉ 3-5 chunk tốt nhất vào prompt
#     """
#     # TODO Sprint 3: Implement rerank
#     # Tạm thời trả về top_k đầu tiên (không rerank)
#     global _rerank_model

#     if not candidates:
#         return candidates

#     try:
#         from sentence_transformers import CrossEncoder
#         if _rerank_model is None:
#             print("  [Rerank] Loading cross-encoder model...")
#             _rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

#         pairs = [[query, chunk["text"]] for chunk in candidates]
#         scores = _rerank_model.predict(pairs)

#         # Sort theo cross-encoder score
#         ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
#         result = []
#         for chunk, score in ranked[:top_k]:
#             chunk_copy = chunk.copy()
#             chunk_copy["rerank_score"] = float(score)
#             result.append(chunk_copy)
#         return result

#     except ImportError:
#         print("  [Rerank] CrossEncoder không available, fallback top_k")
#         return candidates[:top_k]
#     except Exception as e:
#         print(f"  [Rerank] Lỗi: {e}, fallback top_k")
#         return candidates[:top_k]

from openai import OpenAI
import numpy as np

client = OpenAI()

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:

    if not candidates:
        return candidates

    try:
        # Embed query
        query_emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        ).data[0].embedding

        texts = [c["text"] for c in candidates]

        # Embed candidates
        doc_embs = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        ).data

        scores = [
            cosine_similarity(query_emb, d.embedding)
            for d in doc_embs
        ]

        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)

        result = []
        for chunk, score in ranked[:top_k]:
            chunk_copy = chunk.copy()
            chunk_copy["rerank_score"] = float(score)
            result.append(chunk_copy)

        return result

    except Exception as e:
        print(f"[Rerank] Lỗi: {e}, fallback")
        return candidates[:top_k]
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
    if not candidates:
        return candidates

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    scored = []
    for chunk in candidates:
        prompt = f"""Rate how relevant this text passage is to answering the question.
Question: {query}
Passage: {chunk['text'][:500]}

Output ONLY a single integer from 0 to 10. Higher = more relevant."""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5,
            )
            score = int(response.choices[0].message.content.strip())
        except Exception:
            score = 5
        chunk_copy = chunk.copy()
        chunk_copy["rerank_score"] = score / 10.0
        scored.append((chunk_copy, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:top_k]]


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
    """
    Biến đổi query bằng LLM để tăng hiệu quả tìm kiếm.
    """
    if strategy == "expansion":
        prompt = f"""Bạn là một AI hỗ trợ tra cứu tài liệu nội bộ. 
        Hãy tạo ra 2 biến thể khác của câu hỏi sau để tăng khả năng tìm kiếm chính xác (giữ nguyên nghĩa, thay đổi từ ngữ/thuật ngữ tương đương):
        Câu hỏi: '{query}'
        Trả về kết quả dưới dạng JSON array của các chuỗi (strings), ví dụ: ["biến thể 1", "biến thể 2"]
        """
    elif strategy == "decomposition":
        prompt = f"""Hãy tách câu hỏi phức tạp sau đây thành 2-3 câu hỏi đơn giản hơn để thực hiện tra cứu riêng biệt:
        Câu hỏi: '{query}'
        Trả về kết quả dưới dạng JSON array của các chuỗi (strings), ví dụ: ["câu hỏi 1", "câu hỏi 2"]
        """
    elif strategy == "hyde":
        prompt = f"Hãy viết một câu trả lời ngắn gọn, mang tính tài liệu kỹ thuật cho câu hỏi: '{query}'"
    else:
        return [query]
    try:
        # Gọi LLM (đảm bảo call_llm đã được bạn implement)
        response_text = call_llm(prompt)
        
        if strategy in ["expansion", "decomposition"]:
            # Parse JSON từ response của LLM
            # Lưu ý: Có thể cần thêm bước xử lý chuỗi nếu LLM trả về markdown block
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            queries = json.loads(clean_json)
            return [query] + queries if strategy == "expansion" else queries
        elif strategy == "hyde":
            # HyDE thường dùng câu trả lời giả định để search thay cho câu hỏi
            return [response_text]
            
    except Exception as e:
        print(f"[transform_query] Lỗi: {e}. Fallback về query gốc.")
        return [query]
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
        date = meta.get("effective_date", "N/A")
        dept = meta.get("department", "N/A")

        # Xây dựng Header chi tiết: giúp LLM biết chunk này đến từ đâu và khi nào
        header = f"--- [TÀI LIỆU {i}] ---"
        meta_info = f"Nguồn: {source} | Mục: {section} | Phòng ban: {dept} | Ngày hiệu lực: {date}"
        
        # Kết hợp Header, Metadata và Nội dung
        chunk_entry = f"{header}\n{meta_info}\nNội dung: {text}"
        context_parts.append(chunk_entry)
    # Nối các chunk lại bằng 2 dấu xuống dòng để LLM dễ đọc
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
    prompt = f"""Bạn là một trợ lý AI hỗ trợ giải đáp thắc mắc về chính sách CS/IT cho nhân viên.
        Hãy trả lời câu hỏi dựa TRỰC TIẾP và DUY NHẤT vào các tài liệu được cung cấp dưới đây.
        CÁC QUY TẮC BẮT BUỘC:
        1. EVIDENCE-ONLY: Chỉ sử dụng thông tin có trong phần 'Context'. Không sử dụng kiến thức bên ngoài.
        2. ABSTAIN: Nếu thông tin trong Context không đủ để trả lời câu hỏi, hãy trả lời chính xác là: "Tôi xin lỗi, hiện tại tài liệu không có thông tin về vấn đề này."
        3. CITATION: Kết thúc mỗi ý trả lời, hãy trích dẫn nguồn bằng cách ghi số hiệu tài liệu trong ngoặc vuông, ví dụ [1], [2].
        4. FRESHNESS: Ưu tiên thông tin từ tài liệu có 'Ngày hiệu lực' (Effective Date) mới nhất nếu có sự mâu thuẫn.
        5. DEPT: Lưu ý thông tin 'Phòng ban' (Dept) để trả lời đúng đối tượng nếu câu hỏi có đề cập.
        CONTEXT (Dữ liệu tài liệu):
        {context_block}
        CÂU HỎI NGƯỜI DÙNG: {query}
        CÂU TRẢ LỜI CỦA BẠN (vui lòng trả lời bằng ngôn ngữ của câu hỏi):"""
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
    
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,     # temperature=0 để output ổn định cho evaluation
            max_tokens=600,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Lỗi gọi LLM: {e}"


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    query_strategy: str = None,   # Thêm tham số này để chọn expansion/decomposition/hyde
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

    # --- Bước 1: Chọn retrieval function dựa theo retrieval_mode ---
    # (Sprint 3: Hỗ trợ nhiều câu hỏi nếu có biến đổi query)
    all_queries = [query]
    if query_strategy:
        all_queries = transform_query(query, strategy=query_strategy)
        
    all_candidates = []
    for q in all_queries:
        if retrieval_mode == "dense":
            chunks = retrieve_dense(q, top_k=top_k_search)
        elif retrieval_mode == "sparse":
            chunks = retrieve_sparse(q, top_k=top_k_search)
        elif retrieval_mode == "hybrid":
            chunks = retrieve_hybrid(q, top_k=top_k_search)
        all_candidates.extend(chunks)
    # Lọc trùng (Deduplicate) do kết quả trả về từ nhiều query có thể giống nhau
    seen_text = set()
    unique_candidates = []
    for c in all_candidates:
        if c["text"] not in seen_text:
            unique_candidates.append(c)
            seen_text.add(c["text"])
    # --- Bước 2: Gọi rerank() nếu use_rerank=True ---
    if use_rerank:
        candidates = rerank(query, unique_candidates, top_k=top_k_select)
    else:
        # --- Bước 3: Truncate về top_k_select chunks ---
        # Sắp xếp theo score trước khi cắt để lấy được các chunk tốt nhất
        candidates = sorted(unique_candidates, key=lambda x: x.get("score", 0), reverse=True)[:top_k_select]

    # --- Bước 4: Build context block và grounded prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)
    if verbose:
        print(f"\n[RAG] Prompt preview:\n{prompt[:300]}...\n")
    # --- Bước 5: Gọi call_llm() để sinh câu trả lời ---
    answer = call_llm(prompt)
    # --- Bước 6: Trả về kết quả kèm metadata ---
    sources = list({c["metadata"].get("source", "unknown") for c in candidates})
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

    strategies = ["dense", "sparse","hybrid"]  # Thêm "sparse" sau khi implement

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
        "Sản phẩm kỹ thuật số có được hoàn tiền không?",
        "Escalation trong sự cố P1 diễn ra như thế nào?",
        "Approval Matrix để cấp quyền hệ thống là tài liệu nào?",
        "Nhân viên được làm remote tối đa mấy ngày mỗi tuần?",
        "ERR-403-AUTH là lỗi gì và cách xử lý?",
        "Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?",

          # Query không có trong docs → kiểm tra abstain
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
    print("\n--- Sprint 3: So sánh strategies ---")
    compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    compare_retrieval_strategies("ERR-403-AUTH")
    """
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
    """
