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
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


def _normalize_tokens(text: str) -> List[str]:
    return re.findall(r"[\w-]+", text.lower())


def _doc_key(item: Dict[str, Any]) -> str:
    meta = item.get("metadata", {})
    source = meta.get("source", "")
    section = meta.get("section", "")
    text = item.get("text", "")
    return f"{source}|{section}|{text[:160]}"


def _get_collection(auto_build: bool = True):
    import chromadb
    from index import CHROMA_DB_DIR, build_index

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    try:
        return client.get_collection("rag_lab")
    except Exception as exc:
        if not auto_build:
            raise exc

        print("[rag_answer] Chưa có collection rag_lab, đang tự build index...")
        build_index()
        return client.get_collection("rag_lab")


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
    from index import get_embedding

    try:
        collection = _get_collection(auto_build=True)
    except Exception as exc:
        print(f"[retrieve_dense] Không mở được collection rag_lab: {exc}")
        return []

    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        score = 1 - float(dist) if dist is not None else 0.0
        output.append({
            "text": doc,
            "metadata": meta or {},
            "score": score,
        })

    output.sort(key=lambda x: x.get("score", 0), reverse=True)
    return output


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
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        print("[retrieve_sparse] Chưa cài rank-bm25, bỏ qua sparse retrieval")
        return []

    try:
        collection = _get_collection(auto_build=True)
        data = collection.get(include=["documents", "metadatas"])
    except Exception as exc:
        print(f"[retrieve_sparse] Không đọc được collection rag_lab: {exc}")
        return []

    docs = data.get("documents", [])
    metas = data.get("metadatas", [])
    if not docs:
        return []

    tokenized_corpus = [_normalize_tokens(doc) for doc in docs]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = _normalize_tokens(query)
    scores = bm25.get_scores(tokenized_query)

    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:top_k]

    results = []
    for idx in top_indices:
        results.append({
            "text": docs[idx],
            "metadata": metas[idx] or {},
            "score": float(scores[idx]),
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
    dense_results = retrieve_dense(query, top_k=top_k * 2)
    sparse_results = retrieve_sparse(query, top_k=top_k * 2)

    if not sparse_results:
        return dense_results[:top_k]

    fused: Dict[str, Dict[str, Any]] = {}

    for rank, item in enumerate(dense_results, 1):
        key = _doc_key(item)
        score = dense_weight * (1 / (60 + rank))
        if key not in fused:
            fused[key] = {
                "text": item["text"],
                "metadata": item.get("metadata", {}),
                "score": 0.0,
            }
        fused[key]["score"] += score

    for rank, item in enumerate(sparse_results, 1):
        key = _doc_key(item)
        score = sparse_weight * (1 / (60 + rank))
        if key not in fused:
            fused[key] = {
                "text": item["text"],
                "metadata": item.get("metadata", {}),
                "score": 0.0,
            }
        fused[key]["score"] += score

    merged = list(fused.values())
    merged.sort(key=lambda x: x.get("score", 0), reverse=True)
    return merged[:top_k]


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
    if not candidates:
        return []

    query_tokens = set(_normalize_tokens(query))
    if not query_tokens:
        return candidates[:top_k]

    try:
        if os.getenv("RERANK_WITH_CROSS_ENCODER", "0") == "1":
            from sentence_transformers import CrossEncoder

            model_name = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
            model = CrossEncoder(model_name)
            pairs = [[query, chunk["text"]] for chunk in candidates]
            scores = model.predict(pairs)

            ranked = sorted(
                zip(candidates, scores),
                key=lambda x: float(x[1]),
                reverse=True,
            )

            out = []
            for chunk, score in ranked[:top_k]:
                c = dict(chunk)
                c["score"] = float(score)
                out.append(c)
            return out
    except Exception as exc:
        print(f"[rerank] Cross-encoder lỗi, fallback lexical rerank: {exc}")

    # Fallback lightweight rerank: kết hợp dense score và keyword overlap.
    reranked = []
    for c in candidates:
        base_score = float(c.get("score", 0.0))
        chunk_tokens = set(_normalize_tokens(c.get("text", "")))
        overlap = len(query_tokens & chunk_tokens) / max(len(query_tokens), 1)
        final_score = 0.7 * base_score + 0.3 * overlap
        new_item = dict(c)
        new_item["score"] = final_score
        reranked.append(new_item)

    reranked.sort(key=lambda x: x.get("score", 0), reverse=True)
    return reranked[:top_k]


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
    # Tạm thời trả về query gốc
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
    prompt = f"""Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.
When the context contains a list item as part of a larger rule or exception, always include that surrounding context (e.g. "This is listed as an exception to X" or "According to section Y...") so the answer is not misleading.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def build_grounded_prompt_v2(query: str, context_block: str) -> str:
    """
    Variant C prompt — cải thiện 3 điểm yếu từ grading_report:
    1. Completeness: liệt kê ĐẦY ĐỦ điều kiện/ngoại lệ, không dừng ở cái đầu tiên
    2. Abstain: nếu thông tin KHÔNG có trong context, nói rõ thay vì đoán
    3. Relevance cross-doc: khi câu hỏi liên quan đến emergency/khẩn cấp,
       ưu tiên section emergency/escalation trong context
    """
    return f"""Bạn là trợ lý tra cứu tài liệu nội bộ. Chỉ trả lời từ context được cung cấp.

QUY TẮC BẮT BUỘC:
1. EVIDENCE-ONLY: Chỉ dùng thông tin trong context. Tuyệt đối không dùng kiến thức chung.
2. ABSTAIN — quan trọng: Nếu thông tin cụ thể KHÔNG xuất hiện trong bất kỳ chunk nào,
   trả lời: "Thông tin này không có trong tài liệu hiện có." Không đoán, không ước tính.
3. COMPLETENESS: Khi câu hỏi hỏi về điều kiện, ngoại lệ, yêu cầu hoặc quy trình:
   - Liệt kê TẤT CẢ các mục liên quan tìm thấy trong context (không bỏ sót)
   - Nếu thông tin nằm ở nhiều chunk, tổng hợp cả hai
4. CITATION: Gắn số nguồn [1], [2]... cho mỗi thông tin quan trọng
5. EMERGENCY/KHẨN CẤP: Nếu câu hỏi đề cập "khẩn cấp", "emergency", "tạm thời" hoặc
   ngoài giờ hành chính, tìm và ưu tiên các section emergency/escalation trong context
6. NGÔN NGỮ: Trả lời bằng tiếng Việt

Câu hỏi: {query}

Context:
{context_block}

Câu trả lời:"""


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
    openai_key = os.getenv("OPENAI_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")

    if openai_key:
        from openai import OpenAI

        client = OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        return (response.choices[0].message.content or "").strip()

    if google_key:
        import google.generativeai as genai

        genai.configure(api_key=google_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return (response.text or "").strip()

    return "Không đủ dữ liệu để trả lời: chưa cấu hình API key cho LLM (OPENAI_API_KEY/GOOGLE_API_KEY)."


def suggest_followups(question: str, answer: str, n: int = 3) -> list[str]:
    """
    Dựa vào câu hỏi và câu trả lời vừa nhận, gợi ý n câu hỏi tiếp theo liên quan.
    Trả về list[str], tối đa n phần tử.
    """
    prompt = (
        f"Câu hỏi người dùng: {question}\n"
        f"Câu trả lời: {answer}\n\n"
        f"Hãy đề xuất đúng {n} câu hỏi tiếp theo ngắn gọn (<15 từ) mà người dùng có thể muốn hỏi tiếp, "
        f"liên quan trực tiếp đến nội dung câu trả lời trên. "
        f"Chỉ trả về danh sách, mỗi câu hỏi trên một dòng, không đánh số, không giải thích thêm."
    )
    try:
        raw = call_llm(prompt)
        lines = [l.strip().lstrip("-•·*0123456789. ") for l in raw.splitlines() if l.strip()]
        return lines[:n]
    except Exception:
        return []


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    prompt_version: str = "v1",
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
        "prompt_version": prompt_version,
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

    if not candidates:
        return {
            "query": query,
            "answer": "Không đủ dữ liệu trong tài liệu hiện có để trả lời câu hỏi này.",
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

    # --- Bước 2b: Low-score abstain guard (v2 only) ---
    # Nếu chunk tốt nhất có score < 0.35 → thông tin không liên quan, abstain luôn
    if prompt_version == "v2":
        top_score = max((c.get("score", 0) for c in candidates), default=0)
        if top_score < 0.35:
            return {
                "query": query,
                "answer": "Thông tin này không có trong tài liệu hiện có.",
                "sources": [],
                "chunks_used": candidates,
                "config": config,
            }

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    if prompt_version == "v2":
        prompt = build_grounded_prompt_v2(query, context_block)
    else:
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

    strategies = ["dense", "sparse", "hybrid"]

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
        except NotImplementedError:
            print("Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước.")
        except Exception as e:
            print(f"Lỗi: {e}")

    # Uncomment sau khi Sprint 3 hoàn thành:
    # print("\n--- Sprint 3: So sánh strategies ---")
    # compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    # compare_retrieval_strategies("ERR-403-AUTH")

    print("\n\nSprint 2 + 3 pipeline đã được implement.")
    print("Gợi ý chạy thật:")
    print("  1. Chạy build_index() trong index.py để tạo collection rag_lab")
    print("  2. Cấu hình OPENAI_API_KEY hoặc GOOGLE_API_KEY để bật generation")
    print("  3. So sánh dense / sparse / hybrid bằng compare_retrieval_strategies()")
    print("  4. Nếu muốn cross-encoder rerank: đặt RERANK_WITH_CROSS_ENCODER=1")
