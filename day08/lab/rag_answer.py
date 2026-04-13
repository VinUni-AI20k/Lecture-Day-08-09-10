"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
Sprint 2 (60 phút): Baseline RAG
  - Dense retrieval từ ChromaDB
  - Grounded answer function với prompt ép citation
  - Trả lời được ít nhất 3 câu hỏi mẫu, output có source

Sprint 3 (60 phút): Tuning tối thiểu
  - Thêm hybrid retrieval (dense + sparse/BM25)
    - Hoặc thêm rerank (LLM-based)
  - Hoặc thử query transformation (expansion, decomposition, HyDE)
  - Tạo bảng so sánh baseline vs variant

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import json
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10  # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3  # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "openai-gpt-4o")
RERANK_MODEL = os.getenv("RERANK_MODEL", "openai-gpt-4o")


# --- OpenAI client singleton (dùng chung cho call_llm, transform_query, rerank) ---
@lru_cache(maxsize=1)
def _get_openai_client():
    from openai import OpenAI

    return OpenAI(
        api_key=os.getenv("SHOPAIKEY_API_KEY"),
        base_url="https://api.shopaikey.com/v1",
        default_headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        },
    )


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
    from index import CHROMA_DB_DIR, get_embedding

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append(
            {
                "text": doc,
                "metadata": meta,
                "score": 1 - dist,
            }
        )

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
    import chromadb
    from index import CHROMA_DB_DIR
    from rank_bm25 import BM25Okapi

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    all_data = collection.get(include=["documents", "metadatas"])

    all_docs = all_data["documents"]
    all_metas = all_data["metadatas"]

    if not all_docs:
        return []

    tokenized_corpus = [doc.lower().split() for doc in all_docs]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:top_k]

    chunks = []
    for idx in top_indices:
        chunks.append(
            {
                "text": all_docs[idx],
                "metadata": all_metas[idx],
                "score": float(scores[idx]),
            }
        )

    return chunks


# ===========================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# ===========================================================================


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
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    # Build rank maps (1-based)
    dense_rank = {chunk["text"]: rank for rank, chunk in enumerate(dense_results, 1)}
    sparse_rank = {chunk["text"]: rank for rank, chunk in enumerate(sparse_results, 1)}

    # Collect all unique chunks
    all_chunks = {}
    for chunk in dense_results + sparse_results:
        if chunk["text"] not in all_chunks:
            all_chunks[chunk["text"]] = chunk

    # Compute RRF scores
    k = 60  # hằng số RRF tiêu chuẩn
    rrf_scored = []
    for text, chunk in all_chunks.items():
        d_rank = dense_rank.get(text, top_k + 1)
        s_rank = sparse_rank.get(text, top_k + 1)
        rrf_score = dense_weight * (1.0 / (k + d_rank)) + sparse_weight * (
            1.0 / (k + s_rank)
        )
        rrf_scored.append((chunk, rrf_score))

    rrf_scored.sort(key=lambda x: x[1], reverse=True)

    return [
        {"text": chunk["text"], "metadata": chunk["metadata"], "score": score}
        for chunk, score in rrf_scored[:top_k]
    ]


# =============================================================================
# RERANK (Sprint 3 alternative)
# LLM-based rerank để chấm lại relevance sau search rộng
# =============================================================================


def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Rerank các candidate chunks bằng LLM.

    LLM rerank: chấm lại "chunk nào thực sự trả lời câu hỏi này?"
    Ưu điểm: không cần tải model local, dễ đồng bộ với cùng provider LLM

    Funnel logic (từ slide):
      Search rộng (top-20) → Rerank (top-6) → Select (top-3)

    TODO Sprint 3 (nếu chọn rerank):
    Option A — Rerank bằng LLM:
        Gửi list chunks cho LLM, yêu cầu trả về index theo relevance

    Option B — Cross-encoder:
        Có thể thêm lại nếu cần benchmark local model

    Khi nào dùng rerank:
    - Dense/hybrid trả về nhiều chunk nhưng có noise
    - Muốn chắc chắn chỉ 3-5 chunk tốt nhất vào prompt
    """
    if not candidates:
        return []

    client = _get_openai_client()
    max_candidates = min(len(candidates), TOP_K_SEARCH)

    candidate_lines = []
    for idx, chunk in enumerate(candidates[:max_candidates], 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        text = chunk.get("text", "")
        compact_text = re.sub(r"\s+", " ", text).strip()[:900]
        candidate_lines.append(
            f"{idx}. source={source}; section={section}; text={compact_text}"
        )

    prompt = f"""Bạn là bộ máy rerank cho RAG.
Nhiệm vụ: chọn các chunk liên quan nhất để trả lời câu hỏi.

Question: {query}
Top_k cần chọn: {top_k}

Candidates:
{chr(10).join(candidate_lines)}

Chỉ trả về JSON array chứa index theo thứ tự relevance giảm dần.
Ví dụ: [2, 1, 4]
Không trả lời thêm chữ nào."""

    response = client.chat.completions.create(
        model=RERANK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=128,
    )
    raw = (response.choices[0].message.content or "").strip()

    selected_indices: List[int] = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            selected_indices = [int(x) for x in parsed if str(x).isdigit()]
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    if not selected_indices:
        json_match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                if isinstance(parsed, list):
                    selected_indices = [int(x) for x in parsed if str(x).isdigit()]
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

    # Fallback an toàn: giữ thứ tự hiện tại nếu parse thất bại
    if not selected_indices:
        selected_indices = list(range(1, max_candidates + 1))

    dedup_valid_indices = []
    seen_idx = set()
    for idx in selected_indices:
        if 1 <= idx <= max_candidates and idx not in seen_idx:
            dedup_valid_indices.append(idx)
            seen_idx.add(idx)

    if len(dedup_valid_indices) < top_k:
        for idx in range(1, max_candidates + 1):
            if idx not in seen_idx:
                dedup_valid_indices.append(idx)
                seen_idx.add(idx)
            if len(dedup_valid_indices) >= top_k:
                break

    selected = []
    for rank, idx in enumerate(dedup_valid_indices[:top_k], 1):
        chunk = candidates[idx - 1]
        selected.append(
            {
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "score": float(top_k - rank + 1),
            }
        )

    return selected


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

    Ví dụ HyDE:
        "Viết một đoạn trả lời giả định ngắn, có vẻ đúng theo domain,
         để dùng làm truy vấn semantic search (không khẳng định là sự thật)."

    Khi nào dùng:
    - Expansion: query dùng alias/tên cũ (ví dụ: "Approval Matrix" → "Access Control SOP")
    - Decomposition: query hỏi nhiều thứ một lúc
    - HyDE: query mơ hồ, search theo nghĩa không hiệu quả
    """
    client = _get_openai_client()

    if strategy == "expansion":
        prompt = f"""Bạn là trợ lý mở rộng truy vấn cho hệ thống CS + IT Helpdesk nội bộ.
Knowledge base chứa tài liệu về: SLA xử lý ticket, chính sách hoàn tiền, SOP kiểm soát truy cập, FAQ IT helpdesk, quy trình nhân sự.
Tài liệu bằng tiếng Việt, có thuật ngữ kỹ thuật tiếng Anh.

Cho query: "{query}"

Sinh 2-3 cách diễn đạt thay thế giúp tìm kiếm tốt hơn. Bao gồm:
- Tương đương Việt/Anh (vd: "hoàn tiền" <-> "refund", "cấp quyền" <-> "access grant")
- Từ đồng nghĩa và alias (vd: "Approval Matrix" <-> "Access Control SOP")
- Thuật ngữ helpdesk liên quan, mã lỗi, mức ticket (P1/P2/P3) nếu phù hợp

Trả về CHỈ một JSON array of strings (bao gồm query gốc là phần tử đầu tiên).
Ví dụ: ["{query}", "cách diễn đạt 1", "cách diễn đạt 2"]"""

    elif strategy == "decomposition":
        prompt = f"""Bạn là trợ lý phân tách truy vấn cho hệ thống CS + IT Helpdesk nội bộ.

Cho query phức tạp: "{query}"

Tách thành 2-3 sub-query đơn giản, độc lập, cùng nhau bao phủ câu hỏi gốc.

Trả về CHỈ một JSON array of strings.
Ví dụ: ["sub-query 1", "sub-query 2", "sub-query 3"]"""

    elif strategy == "hyde":
        prompt = f"""Bạn là trợ lý tạo truy vấn HyDE cho hệ thống RAG nội bộ.

Mục tiêu: tạo một đoạn trả lời GIẢ ĐỊNH để tăng chất lượng semantic retrieval.
Lưu ý:
- Không cần đảm bảo đúng tuyệt đối, chỉ cần hợp lý theo domain CS + IT Helpdesk.
- Viết ngắn 3-5 câu, giàu từ khóa liên quan policy/SLA/quy trình.
- Trả về CHỈ một object JSON có key duy nhất "hyde".

Question: "{query}"

Output mẫu:
{{"hyde": "..."}}"""

    else:
        return [query]

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=256,
    )

    raw = response.choices[0].message.content.strip()

    # Parse JSON array
    if strategy in {"expansion", "decomposition"}:
        try:
            queries = json.loads(raw)
            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                return queries
        except json.JSONDecodeError:
            pass

    if strategy == "hyde":
        # Ưu tiên parse JSON object dạng {"hyde": "..."}
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                hyde_text = parsed.get("hyde")
                if isinstance(hyde_text, str) and hyde_text.strip():
                    return [query, hyde_text.strip()]
        except json.JSONDecodeError:
            pass

        # Fallback: lấy object JSON đầu tiên trong output markdown/text
        obj_match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if obj_match:
            try:
                parsed = json.loads(obj_match.group())
                if isinstance(parsed, dict):
                    hyde_text = parsed.get("hyde")
                    if isinstance(hyde_text, str) and hyde_text.strip():
                        return [query, hyde_text.strip()]
            except json.JSONDecodeError:
                pass

        # Fallback cuối: dùng toàn bộ text trả về làm HyDE query
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        if cleaned:
            return [query, cleaned]

    # Fallback: extract JSON from markdown code block
    json_match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if json_match:
        try:
            queries = json.loads(json_match.group())
            if isinstance(queries, list):
                return [str(q) for q in queries]
        except json.JSONDecodeError:
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

        department = meta.get("department", "")
        effective_date = meta.get("effective_date", "")

        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if department and department != "unknown":
            header += f" | dept={department}"
        if effective_date and effective_date != "unknown":
            header += f" | effective={effective_date}"
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
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

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
    client = _get_openai_client()
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
    use_rerank: bool = False,
    query_transform: Optional[str] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → (transform) → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng LLM rerank không
        query_transform: "expansion" | "decomposition" | "hyde" | None
        verbose: In thêm thông tin debug

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "query_transform": query_transform,
    }

    # --- Bước 0: Query Transformation (optional) ---
    queries = [query]
    if query_transform is not None:
        queries = transform_query(query, strategy=query_transform)
        if verbose:
            print(f"\n[RAG] Query transform ({query_transform}): {queries}")

    # --- Bước 1: Retrieve (cho mỗi query, merge kết quả) ---
    all_candidates = []
    for q in queries:
        if retrieval_mode == "dense":
            candidates = retrieve_dense(q, top_k=top_k_search)
        elif retrieval_mode == "sparse":
            candidates = retrieve_sparse(q, top_k=top_k_search)
        elif retrieval_mode == "hybrid":
            candidates = retrieve_hybrid(q, top_k=top_k_search)
        else:
            raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")
        all_candidates.extend(candidates)

    # Deduplicate by text, giữ score cao nhất
    seen = {}
    for chunk in all_candidates:
        text = chunk["text"]
        if text not in seen or chunk["score"] > seen[text]["score"]:
            seen[text] = chunk
    candidates = sorted(seen.values(), key=lambda c: c["score"], reverse=True)

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(
                f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}"
            )

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
    print("=" * 60)

    strategies = ["dense", "sparse"]  # Thêm "sparse" sau khi implement

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
    # print("=" * 60)
    # print("Sprint 2 + 3: RAG Answer Pipeline")
    # print("=" * 60)

    # # Test queries từ data/test_questions.json
    # test_queries = [
    #     "SLA xử lý ticket P1 là bao lâu?",
    #     "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
    #     "Ai phải phê duyệt để cấp quyền Level 3?",
    #     "ERR-403-AUTH là lỗi gì?",  # Query không có trong docs → kiểm tra abstain
    # ]

    # print("\n--- Sprint 2: Test Baseline (Dense) ---")
    # for query in test_queries:
    #     print(f"\nQuery: {query}")
    #     try:
    #         result = rag_answer(query, retrieval_mode="dense", verbose=True)
    #         print(f"Answer: {result['answer']}")
    #         print(f"Sources: {result['sources']}")
    #     except NotImplementedError:
    #         print(
    #             "Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước."
    #         )
    #     except Exception as e:
    #         print(f"Lỗi: {e}")

    # Uncomment sau khi Sprint 3 hoàn thành:
    print("\n--- Sprint 3: So sánh strategies ---")
    compare_retrieval_strategies(
        "Audit và review định kỳ cần thời gian bao lâu và cấp những quyền gì?"
    )
    compare_retrieval_strategies("ERR-403-AUTH liên quan đến chính sách nào?")

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
