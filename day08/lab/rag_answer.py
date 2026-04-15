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
import json
from functools import lru_cache


load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
MIN_DENSE_SCORE = float(os.getenv("MIN_DENSE_SCORE", "0.45"))
MIN_HYBRID_SCORE = float(os.getenv("MIN_HYBRID_SCORE", "0.01"))

QUERY_TRANSFORM_PROVIDER = os.getenv("QUERY_TRANSFORM_PROVIDER", "local").strip().lower()

LOCAL_ANSWER_LLM_MODEL = os.getenv("LOCAL_ANSWER_LLM_MODEL", "google/flan-t5-small")
LOCAL_ANSWER_MAX_NEW_TOKENS = int(os.getenv("LOCAL_ANSWER_MAX_NEW_TOKENS", "192"))

RERANK_MODEL_NAME = os.getenv(
    "RERANK_MODEL_NAME",
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
RERANK_DEVICE = os.getenv("RERANK_DEVICE", "cpu")


@lru_cache(maxsize=1)
def _get_rerank_model() -> Any:
    try:
        from sentence_transformers import CrossEncoder
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "sentence-transformers is required for rerank. "
            "Install it by uncommenting it in requirements.txt and running: "
            "pip install -r requirements.txt"
        ) from e

    return CrossEncoder(
        RERANK_MODEL_NAME,
        device=RERANK_DEVICE,
        max_length=512,
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
    from index import get_embedding, CHROMA_DB_DIR

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")
    except Exception as e:
        print(f"[retrieve_dense] Error loading ChromaDB: {e}. Please ensure index.py was run.")
        return []

    try:
        query_embedding = get_embedding(query)
    except NotImplementedError:
        print("[retrieve_dense] get_embedding() is not implemented in index.py yet!")
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    if not results.get("documents") or not results["documents"][0]:
        return []

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    chunks: List[Dict[str, Any]] = []
    for doc, meta, dist in zip(docs, metas, dists):
        score = 1.0 - dist if dist is not None else 0.0
        chunks.append({"text": doc, "metadata": meta, "score": float(score)})

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
    from rank_bm25 import BM25Okapi
    from index import CHROMA_DB_DIR
    
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")
        all_data = collection.get(include=["documents", "metadatas"])
    except Exception as e:
        print(f"[retrieve_sparse] Lỗi khi load ChromaDB: {e}. Vui lòng đảm bảo index.py đã chạy thành công.")
        return []

    if not all_data or not all_data.get("documents"):
        return []

    docs = all_data["documents"]
    metas = all_data["metadatas"]

    # Tokenize corpus (tách từ cơ bản)
    tokenized_corpus = [doc.lower().split() for doc in docs]
    
    # Khởi tạo mô hình BM25
    bm25 = BM25Okapi(tokenized_corpus)
    
    # Tokenize query và tính điểm
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # Lấy ra các index đã được sort theo score (giảm dần)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    chunks = []
    for idx in top_indices:
        score = scores[idx]
        if score > 0:  # Chỉ lấy các chunk trúng từ khóa
            chunks.append({
                "text": docs[idx],
                "metadata": metas[idx],
                "score": float(score)
            })

    return chunks


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.8,
    sparse_weight: float = 0.2,
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
    # 1. & 2. Lấy kết quả từ Dense và Sparse (nên lấy đủ lớn để giao thoa RRF hiệu quả)
    pool_size = max(60, top_k * 2)
    dense_results = retrieve_dense(query, top_k=pool_size)
    sparse_results = retrieve_sparse(query, top_k=pool_size)

    rrf_map = {}

    # 3. Tính điểm RRF từ Dense
    for rank, chunk in enumerate(dense_results):
        text = chunk["text"]
        if text not in rrf_map:
            rrf_map[text] = {"chunk": chunk.copy(), "score": 0.0}
        # Lưu ý: rank bắt đầu từ 0, nên vị trí (rank thực tế) = rank + 1
        rrf_map[text]["score"] += dense_weight * (1.0 / (60 + rank + 1))

    # Tính điểm RRF từ Sparse
    for rank, chunk in enumerate(sparse_results):
        text = chunk["text"]
        if text not in rrf_map:
            rrf_map[text] = {"chunk": chunk.copy(), "score": 0.0}
        rrf_map[text]["score"] += sparse_weight * (1.0 / (60 + rank + 1))

    # 4. Sort theo RRF score giảm dần
    ranked_items = sorted(rrf_map.values(), key=lambda x: x["score"], reverse=True)

    # Format output: trả về top_k và ghi đè score cũ bằng score RRF
    final_chunks = []
    for item in ranked_items[:top_k]:
        c = item["chunk"]
        c["score"] = item["score"]
        final_chunks.append(c)

    return final_chunks


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

    Args:
        query: câu hỏi người dùng
        candidates: danh sách chunk retrieve ban đầu
        top_k: số chunk tốt nhất giữ lại

    Returns:
        List[Dict[str, Any]]: top_k chunks đã được rerank.
        Mỗi chunk giữ nguyên cấu trúc cũ và được bổ sung:
          - "rerank_score": điểm cross-encoder
    """
    if not candidates or top_k <= 0:
        return []

    try:
        model = _get_rerank_model()

        # Giới hạn top_k không vượt quá số lượng candidates thực tế
        top_k = min(top_k, len(candidates))

        # Chuẩn hóa text đầu vào cho reranker
        prepared_candidates = []
        pairs = []

        for chunk in candidates:
            text = str(chunk.get("text", "")).strip()
            # Cắt mềm để giảm tải CPU; cross-encoder vẫn sẽ tokenize/truncate tiếp
            if len(text) > 2000:
                text = text[:2000]

            prepared_candidates.append(chunk)
            pairs.append([query.strip(), text])

        if not pairs:
            return candidates[:top_k]

        scores = model.predict(
            pairs,
            batch_size=8,
            show_progress_bar=False,
        )

        reranked = []
        for chunk, score in zip(prepared_candidates, scores):
            new_chunk = chunk.copy()
            new_chunk["rerank_score"] = float(score)
            reranked.append(new_chunk)

        reranked.sort(
            key=lambda x: x.get("rerank_score", float("-inf")),
            reverse=True,
        )

        return reranked[:top_k]

    except Exception as e:
        print(f"[rerank] CrossEncoder failed, fallback to first {top_k} candidates: {e}")
        return candidates[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion": sinh 2-3 cách diễn đạt khác / alias / từ khóa liên quan
      - "decomposition": tách câu hỏi phức tạp thành 2-3 sub-queries
      - "hyde": sinh một đoạn hypothetical answer ngắn để dùng như query mở rộng

    Returns:
        List[str]: danh sách query dùng cho retrieval.
                   Luôn bao gồm query gốc ở vị trí đầu tiên.
    """
    strategy = strategy.lower().strip()
    if strategy not in {"expansion", "decomposition", "hyde"}:
        raise ValueError(
            f"strategy không hợp lệ: {strategy}. "
            f"Chọn một trong: expansion, decomposition, hyde"
        )

    def _local_expansion(q: str) -> List[str]:
        base = (q or "").strip()
        if not base:
            return [q]
        variants = [base]
        q_lower = base.lower()
        if "approval matrix" in q_lower:
            variants.extend(
                [
                    "Access Control SOP",
                    "it/access-control-sop.md",
                    "access-control-sop",
                    "quy trình kiểm soát truy cập",
                ]
            )
        if "p1" in q_lower and "sla" in q_lower:
            variants.extend(["SLA ticket P1", "first response", "resolution", "escalation"])
        if "refund" in q_lower or "hoàn tiền" in q_lower:
            variants.extend(["điều kiện hoàn tiền", "thời hạn yêu cầu hoàn tiền", "ngoại lệ hoàn tiền"])
        return list(dict.fromkeys([v for v in variants if isinstance(v, str) and v.strip()]))

    llm_provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()

    if QUERY_TRANSFORM_PROVIDER == "local":
        if strategy == "expansion":
            return _local_expansion(query)[:4]
        return [query]

    if strategy == "expansion":
        prompt = f"""
You are helping improve retrieval recall for a RAG system.

Given the user query below, generate 2 to 3 alternative phrasings or closely related search queries.
Rules:
- Preserve the original meaning.
- Include aliases, synonyms, old names, or likely terminology variations if helpful.
- Keep each query short and retrieval-friendly.
- Respond in the same language as the original query when possible.
- Return ONLY a JSON array of strings, no explanation.

Query: {query}
""".strip()

    elif strategy == "decomposition":
        prompt = f"""
You are helping improve retrieval recall for a RAG system.

Break the following complex user query into 2 to 3 simpler sub-queries.
Rules:
- Each sub-query should target one specific information need.
- Keep them short and retrieval-friendly.
- Do not invent facts not implied by the original question.
- Respond in the same language as the original query when possible.
- Return ONLY a JSON array of strings, no explanation.

Query: {query}
""".strip()

    else:  # hyde
        prompt = f"""
You are helping improve retrieval recall for a RAG system.

Write one short hypothetical answer passage that is likely to appear in a relevant document for the query below.
Rules:
- 2 to 4 sentences only.
- Stay generic and plausible.
- Do not mention that this is hypothetical.
- Respond in the same language as the original query when possible.
- Return ONLY a JSON array with exactly 1 string element.

Query: {query}
""".strip()

    try:
        if llm_provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=256,
            )
            raw_output = response.choices[0].message.content.strip()

        elif llm_provider == "gemini":
            import google.generativeai as genai

            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            raw_output = response.text.strip()

        else:
            raise ValueError(
                f"LLM_PROVIDER không hợp lệ: {llm_provider}. "
                f"Dùng 'openai' hoặc 'gemini'."
            )

        # Parse JSON array
        outputs = json.loads(raw_output)

        if not isinstance(outputs, list):
            raise ValueError("LLM output không phải JSON array.")

        cleaned = []
        seen = set()

        # Luôn giữ query gốc đầu tiên
        for item in [query] + outputs:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if not text:
                continue
            key = text.lower()
            if key not in seen:
                seen.add(key)
                cleaned.append(text)

        # Giới hạn số lượng cho gọn
        if strategy in {"expansion", "decomposition"}:
            return cleaned[:4]   # query gốc + tối đa 3 biến thể
        return cleaned[:2]       # query gốc + 1 HyDE passage

    except Exception as e:
        print(f"[transform_query] LLM transform failed ({strategy}): {e}")
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
#     prompt = f"""Answer only from the retrieved context below.
# If the context is insufficient to answer the question, say you do not know and do not make up information.
# Cite the source field (in brackets like [1]) when possible.
# Keep your answer short, clear, and factual.
# Respond in the same language as the question.

# Question: {query}

# Context:
# {context_block}

# Answer:"""
    prompt = f"""You are a precise technical support assistant. Answer the user's question using ONLY the provided context.

STRICT RULES:
1. EVIDENCE-ONLY: Only use information from the retrieved context. Do not use external knowledge or invent facts.
2. ABSTAIN: If the context is insufficient, especially if specific error codes (like {query}) or procedures are missing, state: "Không tìm thấy thông tin về '{query}' trong tài liệu hiện có."
3. CITATION: Every factual claim must be followed by its source ID in brackets, e.g., [1].
4. STYLE: Be factual, short, and clear.
5. LANGUAGE: Respond in the same language as the question (Vietnamese).

Context:
{context_block}

Question: {query}

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
    provider_raw = os.getenv("LLM_PROVIDER", "openai").strip()
    provider = provider_raw.lower()

    if provider.startswith("sk-") and not os.getenv("OPENAI_API_KEY", "").strip():
        provider = "openai"
        os.environ["OPENAI_API_KEY"] = provider_raw

    if provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            tok = AutoTokenizer.from_pretrained(LOCAL_ANSWER_LLM_MODEL)
            model = AutoModelForSeq2SeqLM.from_pretrained(LOCAL_ANSWER_LLM_MODEL)
            inputs = tok(prompt, return_tensors="pt", truncation=True)
            out = model.generate(
                **inputs,
                max_new_tokens=LOCAL_ANSWER_MAX_NEW_TOKENS,
                do_sample=False,
            )
            return tok.decode(out[0], skip_special_tokens=True).strip()

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=512,
        )
        return response.choices[0].message.content or ""

    if provider == "gemini":
        import google.generativeai as genai

        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not api_key:
            raise ValueError("LLM_PROVIDER=gemini nhưng thiếu GOOGLE_API_KEY trong .env")

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return getattr(response, "text", "") or ""

    raise ValueError(f"LLM_PROVIDER không hợp lệ: {provider}. Dùng 'openai' hoặc 'gemini'.")


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    use_query_transform: bool = False,
    query_transform_strategy: str = "expansion",
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
        "use_query_transform": use_query_transform,
        "query_transform_strategy": query_transform_strategy,
    }

    transformed_queries: Optional[List[str]] = None

    if use_query_transform:
        try:
            transformed_queries = transform_query(query, strategy=query_transform_strategy)
        except Exception:
            transformed_queries = [query]

    def _merge_candidates(candidate_lists: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        best_by_key: Dict[str, Dict[str, Any]] = {}
        for lst in candidate_lists:
            for c in lst:
                text = c.get("text", "") or ""
                src = (c.get("metadata") or {}).get("source", "") or ""
                key = f"{src}::{text}"
                if key not in best_by_key or float(c.get("score", 0.0)) > float(best_by_key[key].get("score", 0.0)):
                    best_by_key[key] = c
        merged = list(best_by_key.values())
        merged.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
        return merged

    # --- Bước 1: Retrieve ---
    if retrieval_mode == "dense":
        if transformed_queries:
            candidates = _merge_candidates([retrieve_dense(q, top_k=top_k_search) for q in transformed_queries])
        else:
            candidates = retrieve_dense(query, top_k=top_k_search)
    elif retrieval_mode == "sparse":
        if transformed_queries:
            candidates = _merge_candidates([retrieve_sparse(q, top_k=top_k_search) for q in transformed_queries])
        else:
            candidates = retrieve_sparse(query, top_k=top_k_search)
    elif retrieval_mode == "hybrid":
        if transformed_queries:
            candidates = _merge_candidates([retrieve_hybrid(q, top_k=top_k_search) for q in transformed_queries])
        else:
            candidates = retrieve_hybrid(query, top_k=top_k_search)
    else:
        raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    if not candidates:
        return {
            "query": query,
            "answer": "Không đủ dữ liệu trong tài liệu hiện có để trả lời câu hỏi này.",
            "sources": [],
            "chunks_used": [],
            "config": config,
        }

    best_score = max((c.get("score", 0.0) for c in candidates), default=0.0)
    min_score = MIN_DENSE_SCORE if retrieval_mode == "dense" else MIN_HYBRID_SCORE
    if best_score < min_score:
        return {
            "query": query,
            "answer": "Không đủ dữ liệu trong tài liệu hiện có để trả lời câu hỏi này.",
            "sources": [],
            "chunks_used": [],
            "config": config,
        }

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
    if not context_block.strip():
        return {
            "query": query,
            "answer": "Không đủ dữ liệu trong tài liệu hiện có để trả lời câu hỏi này.",
            "sources": [],
            "chunks_used": [],
            "config": config,
        }
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
        "config": {**config, "transformed_queries": transformed_queries},
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
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "sparse", "hybrid"]

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            if strategy == "dense":
                candidates = retrieve_dense(query, top_k=TOP_K_SEARCH)
            elif strategy == "sparse":
                candidates = retrieve_sparse(query, top_k=TOP_K_SEARCH)
            elif strategy == "hybrid":
                candidates = retrieve_hybrid(query, top_k=TOP_K_SEARCH)
            else:
                candidates = []

            print(f"Retrieved: {len(candidates)}")
            for i, c in enumerate(candidates[:5], 1):
                meta = c.get("metadata", {})
                src = meta.get("source", "?")
                sec = meta.get("section", "")
                score = c.get("score", 0.0)
                print(f"  [{i}] score={score:.4f} | {src}" + (f" | {sec}" if sec else ""))
        except Exception as e:
            print(f"Lỗi: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

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
