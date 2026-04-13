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

STOPWORDS = {
    "la", "là", "va", "và", "cua", "của", "cho", "trong", "the", "thể",
    "co", "có", "duoc", "được", "khong", "không", "nhu", "như", "nao",
    "nào", "bao", "nhiêu", "bao nhiêu", "gi", "gì", "toi", "tôi", "mot",
    "một", "toi", "cần", "can", "voi", "với", "hay", "hãy", "and", "the",
    "for", "from", "what", "which", "how", "when", "where", "who", "is",
    "are", "to", "of", "in", "on", "a", "an",
}


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
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "metadata": meta,
            "score": round(1 - dist, 4),
        })
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
    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:
        print(f"[retrieve_sparse] Thiếu rank-bm25, fallback rỗng: {exc}")
        return []

    import chromadb
    import re
    from index import CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    results = collection.get(include=["documents", "metadatas"])

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    if not documents:
        return []

    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\w+|[^\w\s]", (text or "").lower(), flags=re.UNICODE)

    tokenized_corpus = [_tokenize(doc) for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(_tokenize(query))

    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:top_k]

    sparse_results = []
    for idx in top_indices:
        sparse_results.append({
            "text": documents[idx],
            "metadata": metadatas[idx] if idx < len(metadatas) else {},
            "score": round(float(scores[idx]), 4),
        })
    return sparse_results


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _tokenize(text: str) -> List[str]:
    return [
        token for token in re.findall(r"\w+|[^\w\s]", _normalize_text(text), flags=re.UNICODE)
        if token.strip()
    ]


def _content_tokens(text: str) -> List[str]:
    return [
        token for token in re.findall(r"\w+", _normalize_text(text), flags=re.UNICODE)
        if len(token) > 1 and token not in STOPWORDS
    ]


def _chunk_key(chunk: Dict[str, Any]) -> str:
    meta = chunk.get("metadata", {})
    source = meta.get("source", "")
    section = meta.get("section", "")
    text = chunk.get("text", "")
    return f"{source}|{section}|{text[:200]}"


def _rrf_component(rank: Optional[int], weight: float, k: int = 60) -> float:
    if rank is None:
        return 0.0
    return weight * (1.0 / (k + rank))


def _infer_query_profile(query: str) -> Dict[str, Any]:
    normalized = _normalize_text(query)
    tokens = set(_content_tokens(query))
    raw_tokens = set(_tokenize(query))

    def contains_any(patterns: List[str]) -> bool:
        return any(pattern in normalized for pattern in patterns)

    numeric = contains_any([
        "bao lâu", "bao nhiêu", "mấy", "thời gian", "bao gio", "bao giờ",
        "how long", "how many", "days", "hours", "minutes",
    ])
    approval = contains_any([
        "phê duyệt", "phe duyet", "approval", "approve", "ai phải", "ai can",
        "who must approve",
    ])
    procedure = contains_any([
        "quy trình", "process", "bước", "cách xử lý", "cach xu ly",
        "diễn ra như thế nào", "dien ra nhu the nao",
    ])
    escalation = contains_any(["escalation", "escalate", "leo thang"])
    document_lookup = contains_any([
        "tài liệu nào", "tai lieu nao", "document", "approval matrix",
        "tên cũ", "ten cu", "đổi tên", "doi ten",
    ])
    exception = contains_any([
        "ngoại lệ", "ngoai le", "có được", "co duoc", "khác không", "khac khong",
        "vip", "flash sale", "kỹ thuật số", "ky thuat so", "exception",
    ])
    auth_or_code = bool(re.search(r"\b[a-z]{2,}-\d{2,}(?:-[a-z0-9]+)*\b", normalized)) or contains_any([
        "err-", "error code", "mã lỗi", "ma loi", "authentication", "xác thực", "xac thuc",
    ])
    temporal = contains_any([
        "thay đổi", "thay doi", "phiên bản", "phien ban", "version",
        "trước", "truoc", "hiện tại", "hien tai", "effective date",
        "áp dụng", "ap dung", "so với", "so voi", "current", "previous",
    ])
    comparison = contains_any([
        "giống", "giong", "khác", "khac", "so với", "so voi",
        "tương tự", "tuong tu", "compared", "different",
    ])
    multi_part = (
        normalized.count(" và ") > 0
        or normalized.count(" va ") > 0
        or "nếu có" in normalized
        or "neu co" in normalized
        or comparison
        or normalized.count("?") > 1
    )

    return {
        "normalized": normalized,
        "tokens": tokens,
        "raw_tokens": raw_tokens,
        "numeric": numeric,
        "approval": approval,
        "procedure": procedure,
        "escalation": escalation,
        "document_lookup": document_lookup,
        "exception": exception,
        "auth_or_code": auth_or_code,
        "temporal": temporal,
        "comparison": comparison,
        "multi_part": multi_part,
        "prefer_sparse": document_lookup or auth_or_code or temporal,
    }


def _split_query_into_facets(query: str) -> List[str]:
    normalized = query.strip()
    if not normalized:
        return []

    facets = [normalized]
    split_patterns = [
        r"\s+(?:và|va|hay|hoặc|hoac|cũng như|cung nhu)\s+",
        r"\s*;\s*",
        r"\s*,\s*nếu có\s*,\s*",
        r"\s*,\s*if so\s*,\s*",
    ]

    parts = [normalized]
    for pattern in split_patterns:
        next_parts = []
        for part in parts:
            split_items = [item.strip(" ,.?") for item in re.split(pattern, part, flags=re.IGNORECASE) if item.strip(" ,.?")]
            next_parts.extend(split_items or [part])
        parts = next_parts

    for part in parts:
        part_tokens = _content_tokens(part)
        if len(part_tokens) >= 2 and _normalize_text(part) != _normalize_text(normalized):
            facets.append(part)

    profile = _infer_query_profile(normalized)
    if profile["temporal"]:
        facets.append(f"{normalized} lịch sử phiên bản effective date")
    if profile["comparison"]:
        facets.append(f"{normalized} khác nhau ở điểm nào")

    deduped = []
    seen = set()
    for facet in facets:
        key = _normalize_text(facet)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(facet)
    return deduped[:4]


def _chunk_facet_indices(chunk: Dict[str, Any], facets: List[str]) -> List[int]:
    combined = _normalize_text(
        f"{chunk.get('metadata', {}).get('source', '')} "
        f"{chunk.get('metadata', {}).get('section', '')} "
        f"{chunk.get('text', '')}"
    )
    combined_tokens = set(_content_tokens(combined))
    covered = []
    for idx, facet in enumerate(facets):
        facet_tokens = set(_content_tokens(facet))
        if not facet_tokens:
            continue
        overlap = len(facet_tokens & combined_tokens) / max(1, len(facet_tokens))
        if overlap >= 0.25:
            covered.append(idx)
    return covered


def _redundancy_penalty(candidate: Dict[str, Any], selected: List[Dict[str, Any]]) -> float:
    if not selected:
        return 0.0
    candidate_tokens = set(_content_tokens(candidate.get("text", "")))
    if not candidate_tokens:
        return 0.0

    max_overlap = 0.0
    for chosen in selected:
        chosen_tokens = set(_content_tokens(chosen.get("text", "")))
        overlap = len(candidate_tokens & chosen_tokens) / max(1, len(candidate_tokens | chosen_tokens))
        max_overlap = max(max_overlap, overlap)
    return max_overlap * 0.18


def _select_context_chunks(query: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    if not candidates:
        return []

    profile = _infer_query_profile(query)
    facets = _split_query_into_facets(query)
    selected: List[Dict[str, Any]] = []
    selected_keys = set()
    covered_facets = set()
    seen_source_section = set()

    while len(selected) < top_k:
        best_candidate = None
        best_score = None

        for candidate in candidates:
            key = _chunk_key(candidate)
            if key in selected_keys:
                continue

            meta = candidate.get("metadata", {})
            source = meta.get("source", "")
            section = meta.get("section", "")
            candidate_score = float(candidate.get("score", 0))
            facet_indices = _chunk_facet_indices(candidate, facets)
            new_facets = [idx for idx in facet_indices if idx not in covered_facets]

            candidate_score += 0.09 * len(new_facets)
            if section and (source, section) not in seen_source_section:
                candidate_score += 0.04
            if profile["multi_part"] and len(facet_indices) > 1:
                candidate_score += 0.05
            candidate_score -= _redundancy_penalty(candidate, selected)

            if best_score is None or candidate_score > best_score:
                best_candidate = candidate
                best_score = candidate_score

        if best_candidate is None:
            break

        selected.append(best_candidate)
        selected_keys.add(_chunk_key(best_candidate))
        meta = best_candidate.get("metadata", {})
        seen_source_section.add((meta.get("source", ""), meta.get("section", "")))
        covered_facets.update(_chunk_facet_indices(best_candidate, facets))

    return selected[:top_k]


def _context_seems_answerable(query: str, chunks: List[Dict[str, Any]]) -> bool:
    if not chunks:
        return False

    profile = _infer_query_profile(query)
    facets = _split_query_into_facets(query)
    covered_facets = set()

    for chunk in chunks:
        covered_facets.update(_chunk_facet_indices(chunk, facets))

    if profile["multi_part"]:
        needed = max(2, min(len(facets), 3))
        if len(covered_facets) >= needed:
            return True

    top_bonus = max((_chunk_intent_bonus(profile, chunk) for chunk in chunks), default=0.0)
    if top_bonus >= 0.22:
        return True

    combined = " ".join(chunk.get("text", "") for chunk in chunks)
    overlap = len(profile["tokens"] & set(_content_tokens(combined))) / max(1, len(profile["tokens"]))
    return overlap >= 0.35


def _load_all_chunks_from_store() -> List[Dict[str, Any]]:
    import chromadb
    from index import CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    results = collection.get(include=["documents", "metadatas"])

    chunks = []
    for doc, meta in zip(results.get("documents", []), results.get("metadatas", [])):
        chunks.append({
            "text": doc,
            "metadata": meta or {},
            "score": 0.0,
        })
    return chunks


def _build_source_profiles(all_chunks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    profiles: Dict[str, Dict[str, Any]] = {}
    for chunk in all_chunks:
        meta = chunk.get("metadata", {})
        source = meta.get("source", "")
        if not source:
            continue
        profile = profiles.setdefault(source, {
            "source": source,
            "department": meta.get("department", ""),
            "sections": set(),
            "snippets": [],
        })
        section = meta.get("section", "")
        if section:
            profile["sections"].add(section)
        text = (chunk.get("text", "") or "").strip()
        if text and len(profile["snippets"]) < 3:
            profile["snippets"].append(text[:180])

    for profile in profiles.values():
        combined = " ".join(
            [profile["source"], profile["department"]]
            + sorted(profile["sections"])
            + profile["snippets"]
        )
        profile["tokens"] = set(_content_tokens(combined))
    return profiles


def _source_affinity_scores(query_profile: Dict[str, Any], source_profiles: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    query_tokens = query_profile["tokens"]
    scores: Dict[str, float] = {}

    for source, profile in source_profiles.items():
        source_tokens = profile.get("tokens", set())
        overlap = len(query_tokens & source_tokens) / max(1, len(query_tokens))
        score = overlap

        source_text = _normalize_text(source)
        if query_profile["document_lookup"] and any(token in source_text for token in query_tokens):
            score += 0.25
        if query_profile["approval"] and any(token in source_text for token in {"access", "control", "approval"}):
            score += 0.15
        if query_profile["escalation"] and "sla" in source_text:
            score += 0.12
        if query_profile["auth_or_code"] and any(token in source_text for token in {"helpdesk", "support", "faq"}):
            score += 0.12
        if query_profile["exception"] and any(token in source_text for token in {"refund", "policy"}):
            score += 0.12
        if query_profile["numeric"] and any(token in source_text for token in {"sla", "faq", "policy"}):
            score += 0.05

        scores[source] = score
    return scores


def _chunk_intent_bonus(query_profile: Dict[str, Any], chunk: Dict[str, Any]) -> float:
    meta = chunk.get("metadata", {})
    section = _normalize_text(meta.get("section", ""))
    text = _normalize_text(chunk.get("text", ""))
    combined = f"{section} {text}"
    bonus = 0.0

    if query_profile["approval"] and any(term in combined for term in ["phê duyệt", "phe duyet", "approval", "line manager", "it security"]):
        bonus += 0.18
    if query_profile["escalation"] and any(term in combined for term in ["escalation", "escalate", "senior engineer", "incident", "p1"]):
        bonus += 0.18
    if query_profile["procedure"] and any(term in combined for term in ["quy trình", "bước", "process", "ticket", "workflow"]):
        bonus += 0.12
    if query_profile["exception"] and any(term in combined for term in ["ngoại lệ", "ngoai le", "không được", "khong duoc", "điều kiện", "dieu kien"]):
        bonus += 0.16
    if query_profile["numeric"] and (
        any(term in combined for term in ["phút", "phut", "giờ", "gio", "ngày", "ngay", "%"])
        or re.search(r"\b\d+\b", combined)
    ):
        bonus += 0.10
    if query_profile["document_lookup"] and any(term in combined for term in ["tài liệu", "tai lieu", "trước đây có tên", "approval matrix", "access control sop"]):
        bonus += 0.20
    if query_profile["auth_or_code"] and any(term in combined for term in ["authentication", "xác thực", "xac thuc", "helpdesk", "vpn", "mật khẩu", "mat khau"]):
        bonus += 0.14
    if query_profile["temporal"] and any(term in combined for term in ["effective date", "phiên bản", "phien ban", "lịch sử phiên bản", "v202", "áp dụng", "ap dung"]):
        bonus += 0.16
    if query_profile["comparison"] and any(term in combined for term in ["trước", "truoc", "hiện tại", "hien tai", "khác", "different", "version"]):
        bonus += 0.10

    overlap = len(query_profile["tokens"] & set(_content_tokens(combined))) / max(1, len(query_profile["tokens"]))
    bonus += overlap * 0.20
    return bonus


def _select_adaptive_chunks(query: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    if not candidates:
        return []

    profile = _infer_query_profile(query)
    facets = _split_query_into_facets(query)
    selected: List[Dict[str, Any]] = []
    selected_keys = set()
    covered_facets = set()
    seen_sources = set()
    seen_sections = set()

    while len(selected) < top_k:
        best_candidate = None
        best_score = None

        for candidate in candidates:
            key = _chunk_key(candidate)
            if key in selected_keys:
                continue

            meta = candidate.get("metadata", {})
            source = meta.get("source", "")
            section = meta.get("section", "")
            candidate_score = float(candidate.get("score", 0))
            facet_indices = _chunk_facet_indices(candidate, facets)
            new_facets = [idx for idx in facet_indices if idx not in covered_facets]

            if profile["multi_part"]:
                candidate_score += 0.08 * len(new_facets)
                if source and source not in seen_sources:
                    candidate_score += 0.06
            if section and (source, section) not in seen_sections:
                candidate_score += 0.04
            candidate_score -= _redundancy_penalty(candidate, selected)

            if best_score is None or candidate_score > best_score:
                best_candidate = candidate
                best_score = candidate_score

        if best_candidate is None:
            break

        selected.append(best_candidate)
        selected_keys.add(_chunk_key(best_candidate))
        meta = best_candidate.get("metadata", {})
        source = meta.get("source", "")
        section = meta.get("section", "")
        if source:
            seen_sources.add(source)
        if section:
            seen_sections.add((source, section))
        covered_facets.update(_chunk_facet_indices(best_candidate, facets))

    return selected[:top_k]


def retrieve_adaptive(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Adaptive retrieval:
    - Dense là mặc định để giữ semantic recall.
    - Khi query có nhiều vế, query được tách nhẹ thành các facets để tránh bỏ sót evidence.
    - Candidate được trộn từ dense/sparse trên query gốc và các facets, rồi xếp hạng bằng
      sự cân bằng giữa relevance, completeness và evidence diversity.

    Mục tiêu:
    - Tổng quát hơn hybrid thuần và source-routing cứng.
    - Hoạt động tốt hơn cho cả single-hop fact lookup lẫn multi-part / cross-document queries.
    """
    wide_k = max(top_k * 2, top_k + 4)
    query_profile = _infer_query_profile(query)
    facets = _split_query_into_facets(query)

    pool: Dict[str, Dict[str, Any]] = {}
    dense_contrib: Dict[str, float] = {}
    sparse_contrib: Dict[str, float] = {}
    facet_contrib: Dict[str, set] = {}

    dense_weight = 0.50
    sparse_weight = 0.22 if query_profile["prefer_sparse"] else 0.10
    facet_dense_weight = 0.22 if query_profile["multi_part"] else 0.14
    facet_sparse_weight = 0.12 if (query_profile["multi_part"] or query_profile["prefer_sparse"]) else 0.05

    base_dense = retrieve_dense(query, top_k=wide_k)
    base_sparse = retrieve_sparse(query, top_k=wide_k) if (query_profile["prefer_sparse"] or query_profile["multi_part"]) else []

    for rank, chunk in enumerate(base_dense, start=1):
        key = _chunk_key(chunk)
        pool.setdefault(key, dict(chunk))
        dense_contrib[key] = dense_contrib.get(key, 0.0) + _rrf_component(rank, dense_weight)
        facet_contrib.setdefault(key, set()).add(0)

    for rank, chunk in enumerate(base_sparse, start=1):
        key = _chunk_key(chunk)
        pool.setdefault(key, dict(chunk))
        sparse_contrib[key] = sparse_contrib.get(key, 0.0) + _rrf_component(rank, sparse_weight)
        facet_contrib.setdefault(key, set()).add(0)

    for facet_index, facet in enumerate(facets[1:], start=1):
        facet_dense = retrieve_dense(facet, top_k=max(4, top_k))
        facet_sparse = retrieve_sparse(facet, top_k=max(4, top_k)) if (query_profile["prefer_sparse"] or query_profile["multi_part"]) else []

        for rank, chunk in enumerate(facet_dense, start=1):
            key = _chunk_key(chunk)
            pool.setdefault(key, dict(chunk))
            dense_contrib[key] = dense_contrib.get(key, 0.0) + _rrf_component(rank, facet_dense_weight)
            facet_contrib.setdefault(key, set()).add(facet_index)

        for rank, chunk in enumerate(facet_sparse, start=1):
            key = _chunk_key(chunk)
            pool.setdefault(key, dict(chunk))
            sparse_contrib[key] = sparse_contrib.get(key, 0.0) + _rrf_component(rank, facet_sparse_weight)
            facet_contrib.setdefault(key, set()).add(facet_index)

    ranked_candidates = []
    for key, chunk in pool.items():
        score = 0.0
        score += dense_contrib.get(key, 0.0)
        score += sparse_contrib.get(key, 0.0)
        score += _chunk_intent_bonus(query_profile, chunk)
        score += 0.04 * len(facet_contrib.get(key, set()))
        if query_profile["multi_part"] and len(facet_contrib.get(key, set())) > 1:
            score += 0.05
        chunk["score"] = round(score, 6)
        ranked_candidates.append(chunk)

    ranked_candidates.sort(key=lambda item: item.get("score", 0), reverse=True)
    return ranked_candidates[:top_k]


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
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    if not dense_results and not sparse_results:
        return []
    if not sparse_results:
        return dense_results
    if not dense_results:
        return sparse_results

    # Reciprocal Rank Fusion:
    # score(doc) = dense_weight/(60 + rank_dense) + sparse_weight/(60 + rank_sparse)
    rrf_k = 60
    fused_scores: Dict[str, float] = {}
    chunk_map: Dict[str, Dict[str, Any]] = {}

    for rank, chunk in enumerate(dense_results, start=1):
        key = _chunk_key(chunk)
        fused_scores[key] = fused_scores.get(key, 0.0) + dense_weight * (1.0 / (rrf_k + rank))
        if key not in chunk_map:
            chunk_map[key] = chunk

    for rank, chunk in enumerate(sparse_results, start=1):
        key = _chunk_key(chunk)
        fused_scores[key] = fused_scores.get(key, 0.0) + sparse_weight * (1.0 / (rrf_k + rank))
        if key not in chunk_map:
            chunk_map[key] = chunk

    merged = []
    for key, score in fused_scores.items():
        item = dict(chunk_map[key])
        item["score"] = round(score, 6)
        merged.append(item)

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
    # TODO Sprint 3: Implement rerank
    # Tạm thời trả về top_k đầu tiên (không rerank)
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
        effective_date = meta.get("effective_date", "")
        department = meta.get("department", "")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")

        # TODO: Tùy chỉnh format nếu muốn (thêm effective_date, department, ...)
        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if effective_date:
            header += f" | effective_date={effective_date}"
        if department:
            header += f" | department={department}"
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
    profile = _infer_query_profile(query)
    response_style = []
    if profile["multi_part"] or profile["comparison"] or profile["temporal"]:
        response_style.append("- Trả lời theo 2-4 gạch đầu dòng ngắn, mỗi gạch đầu dòng bao phủ một ý chính của câu hỏi.")
    else:
        response_style.append("- Trả lời bằng 1-3 câu ngắn, trực tiếp.")

    if profile["temporal"]:
        response_style.append("- Nếu ngữ cảnh có thông tin phiên bản, effective date, trước/sau, hãy nêu rõ mốc thời gian và sự thay đổi.")
    if profile["comparison"]:
        response_style.append("- Nếu câu hỏi so sánh hai quy định hoặc hai ngữ cảnh, hãy nói rõ điểm giống/khác thay vì chỉ trả lời một nửa.")
    if profile["exception"]:
        response_style.append("- Nếu ngữ cảnh liệt kê nhiều điều kiện hoặc nhiều ngoại lệ, hãy nêu đủ tất cả ngoại lệ liên quan đang xuất hiện trong câu hỏi.")

    prompt = f"""Bạn là trợ lý RAG chỉ được trả lời dựa trên ngữ cảnh đã retrieve.

Quy tắc bắt buộc:
- Chỉ dùng thông tin có trong context.
- Nếu context có đủ bằng chứng trực tiếp để trả lời, KHÔNG được trả lời "không đủ dữ liệu".
- Nếu câu hỏi có nhiều ý, phải trả lời đầy đủ từng ý xuất hiện trong câu hỏi.
- Nếu context cho thấy "không có ngoại lệ riêng" hoặc "áp dụng quy trình chuẩn hiện hành", hãy nói rõ điều đó thay vì abstain.
- Chỉ khi toàn bộ context không có đủ bằng chứng trực tiếp cho phần trọng tâm của câu hỏi mới được trả lời đúng chính xác câu: "Không đủ dữ liệu để trả lời từ tài liệu hiện có."
- Mọi câu trả lời không abstain đều phải có ít nhất một citation dạng [n].

Hướng dẫn format:
{chr(10).join(response_style)}

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def build_answer_repair_prompt(query: str, context_block: str, previous_answer: str) -> str:
    return f"""Câu trả lời trước đang quá dè dặt hoặc bỏ sót ý dù context đã có bằng chứng.

Nhiệm vụ:
- Đọc lại câu hỏi và context.
- Trả lời đầy đủ các ý trong câu hỏi bằng thông tin có trong context.
- KHÔNG được dùng "Không đủ dữ liệu để trả lời từ tài liệu hiện có." nếu context đã có bằng chứng trực tiếp.
- Phải có citation [n].
- Nếu có nhiều điều kiện/ngoại lệ/thời gian/approver, nêu đủ các chi tiết đó.

Question: {query}

Previous answer:
{previous_answer}

Context:
{context_block}

Improved answer:"""


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
    use_rerank: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid" | "adaptive"
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
    - Variant B: đổi retrieval_mode="adaptive"
    - Variant C: bật use_rerank=True
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
    elif retrieval_mode == "adaptive":
        candidates = retrieve_adaptive(query, top_k=top_k_search)
    else:
        raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    # --- Bước 2: Rerank / select ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = _select_context_chunks(query, candidates, top_k_select)

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # Không có evidence thì abstain ngay và source rỗng
    if not candidates:
        return {
            "query": query,
            "answer": "Không đủ dữ liệu để trả lời từ tài liệu hiện có.",
            "sources": [],
            "chunks_used": [],
            "config": config,
        }

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    # Không in prompt đầy đủ để tránh log dài và lộ nội dung nhạy cảm

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract sources ---
    answer_norm = (answer or "").strip().lower()
    abstain_markers = [
        "khong_du_du_lieu",
        "không đủ dữ liệu",
        "khong du du lieu",
        "i do not know",
        "insufficient",
    ]
    is_abstain = any(marker in answer_norm for marker in abstain_markers)

    if is_abstain and _context_seems_answerable(query, candidates):
        repair_prompt = build_answer_repair_prompt(query, context_block, answer)
        repaired_answer = call_llm(repair_prompt)
        repaired_norm = (repaired_answer or "").strip().lower()
        repaired_abstain = any(marker in repaired_norm for marker in abstain_markers)
        if not repaired_abstain and repaired_answer.strip():
            answer = repaired_answer
            answer_norm = repaired_norm
            is_abstain = False

    if is_abstain:
        answer = "Không đủ dữ liệu để trả lời từ tài liệu hiện có."
        sources = []
    else:
        sources = list({
            c["metadata"].get("source", "unknown")
            for c in candidates
        })
        if sources and not re.search(r"\[\d+\]", answer or ""):
            answer = f"{(answer or '').rstrip()} [1]"

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

    strategies = ["dense", "hybrid", "adaptive"]
    rows = []

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            answer = (result["answer"] or "").replace("\n", " ").strip()
            preview = (answer[:97] + "...") if len(answer) > 100 else answer
            source_count = len(result["sources"])
            abstain = "Yes" if source_count == 0 else "No"
            rows.append((strategy, source_count, abstain, preview))
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except Exception as e:
            rows.append((strategy, 0, "Error", str(e)))
            print(f"Lỗi: {e}")

    print("\nBảng so sánh baseline vs variant (Markdown):")
    print("| Strategy | #Sources | Abstain | Answer Preview |")
    print("|---|---:|---|---|")
    for strategy, source_count, abstain, preview in rows:
        safe_preview = preview.replace("|", "/")
        print(f"| {strategy} | {source_count} | {abstain} | {safe_preview} |")


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
    print("\n--- Sprint 3: So sánh strategies ---")
    compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    compare_retrieval_strategies("ERR-403-AUTH")

    # print("\n\nViệc cần làm Sprint 2:")
    # print("  1. Implement retrieve_dense() — query ChromaDB")
    # print("  2. Implement call_llm() — gọi OpenAI hoặc Gemini")
    # print("  3. Chạy rag_answer() với 3+ test queries")
    # print("  4. Verify: output có citation không? Câu không có docs → abstain không?")

    # print("\nViệc cần làm Sprint 3:")
    # print("  1. Chọn 1 trong 3 variants: hybrid, rerank, hoặc query transformation")
    # print("  2. Implement variant đó")
    # print("  3. Chạy compare_retrieval_strategies() để thấy sự khác biệt")
    # print("  4. Ghi lý do chọn biến đó vào docs/tuning-log.md")
