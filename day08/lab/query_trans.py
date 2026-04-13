"""
query_trans.py — Query Transformation Techniques
=================================================
Tập hợp các kỹ thuật biến đổi query trước khi retrieve,
nhằm cải thiện chất lượng retrieval cho các trường hợp:

  1. Query Expansion   — query ngắn / dùng alias / tiếng lóng
  2. Step-back         — query quá cụ thể (mã lỗi, ID, version)
  3. Query Decomp      — câu hỏi cần nhiều tài liệu (multi-hop)
  4. HyDE              — vocabulary mismatch, score thấp sau probe

Trigger flow:
    query
      │
      ├─ needs_expansion?  → expand_query()
      ├─ needs_stepback?   → stepback_query()
      ├─ probe retrieve → needs_decomposition()  → decompose_query()
      │                  → needs_hyde()          → hyde_embed()
      └─ all results merged → deduplicate_chunks()

Sử dụng trong rag_answer.py:
    from query_trans import apply_query_transformations
    all_chunks = apply_query_transformations(query, retrieve_fn, embed_fn)
"""

import os
import re
import json
from typing import List, Dict, Any, Callable, Optional

# ---------------------------------------------------------------------------
# Thresholds — chỉnh theo kết quả thực tế sau khi chạy scorecard
# ---------------------------------------------------------------------------
ABSTAIN_THRESHOLD = 0.45   # score < này → abstain (không đủ context)
HYDE_LOW = 0.45            # score trong vùng [HYDE_LOW, HYDE_HIGH] → trigger HyDE
HYDE_HIGH = 0.58
MULTIHOP_SOURCE_MIN = 2    # unique sources trong top-4 >= này → trigger decompose
EXPANSION_MAX_WORDS = 4    # query <= từ này → trigger expansion


# =============================================================================
# HELPER — JSON parse an toàn từ LLM output
# =============================================================================

def _parse_json_response(response: str) -> Any:
    """
    Parse JSON từ LLM output, chịu được text thừa xung quanh.
    Tìm block {...} hoặc [...] đầu tiên trong response.
    """
    match = re.search(r"(\{.*\}|\[.*\])", response, re.DOTALL)
    if not match:
        raise ValueError(f"Không tìm thấy JSON trong response: {response[:200]}")
    return json.loads(match.group())


# =============================================================================
# 1. QUERY EXPANSION
# Mục tiêu: mở rộng query ngắn / alias thành nhiều biến thể
# để tăng recall khi vocab của doc khác với query của user
# =============================================================================

# Từ người dùng hay dùng  →  từ tương đương trong docs thực tế
# Nguồn: khảo sát vocabulary 5 tài liệu trong data/docs/
_INFORMAL_TERMS = [
    # HR / Leave policy  (hr/leave-policy-2026.pdf)
    "nghỉ đẻ",        # → "nghỉ thai sản" (doc dùng: Mục 1.3)
    "đuổi việc",      # → "nhân viên nghỉ việc" (doc dùng: Section 5 access-control)
    "wfh",            # → "remote work" (doc dùng: Phần 4 leave-policy)
    "work from home", # → "remote work"

    # Refund / CS policy  (policy/refund-v4.pdf)
    "đổi trả",        # → "yêu cầu hoàn tiền" (doc dùng: Điều 2-4)
    "trả hàng",       # → "hoàn tiền"

    # IT Access control  (it/access-control-sop.md)
    "approval matrix", # → "Access Control SOP" (doc ghi chú tường minh: tên cũ)
    "xin quyền",       # → "Access Request ticket" (doc dùng: Section 3)
    "bị lock",         # → "tài khoản bị khóa" (doc dùng: Section 1 helpdesk-faq)
    "quên pass",       # → "quên mật khẩu" (doc dùng: Section 1 helpdesk-faq)

    # Incident / SLA  (support/sla-p1-2026.pdf)
    "sập",             # → "sự cố", "P1", "database sập" (doc dùng Phần 1)
    "mất mạng",        # → "mất kết nối VPN" / "sự cố" (doc dùng Section 2 helpdesk)
    "treo máy",        # → "sự cố P2/P3" (Phần 1 sla)
]


def needs_expansion(query: str) -> bool:
    """
    Trigger expansion khi:
      - Query <= EXPANSION_MAX_WORDS từ (quá ngắn, thiếu context embed)
      - Hoặc chứa từ thông thường / tiếng lóng không khớp văn phong doc
    """
    words = query.strip().split()
    if len(words) <= EXPANSION_MAX_WORDS:
        return True
    query_lower = query.lower()
    if any(term in query_lower for term in _INFORMAL_TERMS):
        return True
    return False


def expand_query(query: str, call_llm: Callable[[str], str]) -> List[str]:
    """
    Dùng LLM sinh 3-5 biến thể của query gốc:
    synonym, formal term, keyword viết tắt, tiếng Anh tương đương.

    Args:
        query:    Câu hỏi gốc
        call_llm: Hàm gọi LLM, signature (prompt: str) -> str

    Returns:
        List gồm query gốc + các biến thể (dedup)

    Example:
        "nghỉ đẻ" -> ["nghỉ đẻ", "nghỉ thai sản", "maternity leave",
                       "chế độ phụ sản", "trợ cấp sinh con"]
    """
    prompt = f"""Generate 3-5 alternative phrasings of the following query.
Include: synonyms, formal equivalents, English translation if relevant,
abbreviated forms, and related policy/technical terms.

Query: {query}

Output JSON only, no explanation:
{{"expansions": ["variant1", "variant2", "variant3"]}}"""

    try:
        raw = call_llm(prompt)
        data = _parse_json_response(raw)
        variants = data.get("expansions", [])
        # Luôn giữ query gốc ở đầu
        all_queries = [query] + [v for v in variants if v != query]
        return all_queries
    except Exception as e:
        print(f"[expand_query] LLM parse error: {e} — fallback về query gốc")
        return [query]


# =============================================================================
# 2. STEP-BACK PROMPTING
# Mục tiêu: từ câu hỏi quá cụ thể (mã lỗi, ID, version),
# sinh ra câu hỏi tổng quát hơn để retrieve policy/concept level
# =============================================================================

# Pattern quá cụ thể → không khớp trực tiếp với policy doc
# Nguồn: các anchor cụ thể trong 5 tài liệu data/docs/
_SPECIFIC_PATTERNS = [
    # ── Mã lỗi & ticket ──────────────────────────────────────────────────────
    r"ERR-\w+",                # ERR-403-AUTH (helpdesk-faq test q09)
    r"\b[A-Z]{2,}-\d+\b",    # Jira ticket ID: IT-1234, HR-89
    r"#\d{4,}",               # ticket number: #10234

    # ── Định danh người dùng / hệ thống ──────────────────────────────────────
    r"user\s*(id)?\s*[:#]?\s*\d+",              # user ID: 8910
    r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",# IP address

    # ── Phiên bản SLA nội bộ (corpus-specific) ───────────────────────────────
    # Dạng: v2026.1, v2025.3 — lịch sử phiên bản Phần 5 của sla-p1-2026.pdf
    # Khác với v4 trong policy_refund_v4 (v4 vẫn retrieve được bình thường)
    r"v\d{4}\.\d",            # v2026.1, v2025.3

    # ── Thông tin liên lạc nội bộ (xuất hiện trong docs nhưng dùng làm query
    #    → nên step-back lên quy trình/chính sách tổng quát) ─────────────────
    r"ext\.?\s*\d{3,4}",      # ext. 9000, ext. 1234, ext. 9999, ext. 2000
    r"https?://\S+",          # URLs: https://sso.company.internal/reset
    r"[\w.]+@company\.internal", # internal emails: helpdesk@company.internal

    # ── Tên công cụ cụ thể (đề cập trong docs như reference, không phải policy)
    r"Cisco AnyConnect|PagerDuty|Splunk|Okta", # tools nêu trong it docs
]


def needs_stepback(query: str) -> bool:
    """
    Trigger step-back khi query chứa pattern quá cụ thể:
    mã lỗi, ID, version, IP — những thứ thường không xuất hiện
    trong policy doc nhưng khái niệm parent của nó thì có.
    """
    return any(re.search(p, query, re.IGNORECASE) for p in _SPECIFIC_PATTERNS)


def stepback_query(query: str, call_llm: Callable[[str], str]) -> str:
    """
    Dùng LLM sinh ra câu hỏi tổng quát hơn (abstract/step-back question).
    Câu hỏi step-back nhắm vào khái niệm / quy trình tổng quát,
    không phải instance cụ thể.

    Args:
        query:    Câu hỏi gốc (cụ thể)
        call_llm: Hàm gọi LLM

    Returns:
        Câu hỏi tổng quát hơn (1 câu)

    Example:
        "Lỗi ERR-403-AUTH khi gọi API thanh toán lúc 2am"
        -> "Quy trình xử lý lỗi authentication trong tích hợp API là gì?"
    """
    prompt = f"""The following question is very specific (contains error codes, IDs, versions, etc.).
Generate ONE more general/abstract question that covers the underlying concept or policy.
The abstract question should be answerable from a policy or procedure document.

Specific question: {query}

Output JSON only:
{{"stepback_question": "..."}}"""

    try:
        raw = call_llm(prompt)
        data = _parse_json_response(raw)
        return data.get("stepback_question", query)
    except Exception as e:
        print(f"[stepback_query] LLM parse error: {e} — fallback về query gốc")
        return query


# =============================================================================
# 3. QUERY DECOMPOSITION (Multi-hop)
# Mục tiêu: tách câu hỏi cần nhiều tài liệu thành sub-questions độc lập
# Trigger: probe retrieve trả về chunks từ >= 2 nguồn khác nhau
# =============================================================================

def needs_decomposition(probe_chunks: List[Dict[str, Any]]) -> bool:
    """
    Trigger decomposition khi probe retrieve trả về chunks
    từ >= MULTIHOP_SOURCE_MIN tài liệu khác nhau trong top-4.

    Ý nghĩa: query đang liên quan đến nhiều doc cùng lúc
    → retrieve 1 lần không đủ, cần tách thành sub-questions
    và retrieve riêng từng cái.

    Args:
        probe_chunks: Kết quả probe retrieve (top-4 đến top-6 chunks)
    """
    if not probe_chunks:
        return False
    top4 = probe_chunks[:4]
    unique_sources = {c.get("metadata", {}).get("source", "") for c in top4}
    return len(unique_sources) >= MULTIHOP_SOURCE_MIN


def decompose_query(query: str, call_llm: Callable[[str], str]) -> List[str]:
    """
    Dùng LLM tách query phức thành 2-3 sub-questions,
    mỗi sub-question có thể được trả lời từ 1 tài liệu đơn lẻ.

    Args:
        query:    Câu hỏi gốc (multi-hop)
        call_llm: Hàm gọi LLM

    Returns:
        List các sub-questions (không gồm query gốc)

    Example:
        "P1 lúc 2am, quy trình on-call và cấp quyền tạm thời thế nào?"
        -> [
             "Quy trình xử lý sự cố P1 ngoài giờ hành chính là gì?",
             "Quy trình cấp quyền truy cập tạm thời khẩn cấp là gì?"
           ]
    """
    prompt = f"""Break the following question into 2-3 simpler sub-questions.
Each sub-question must be answerable from a SINGLE document section.
Do not repeat the original question.

Question: {query}

Output JSON only:
{{"sub_questions": ["sub-question 1", "sub-question 2"]}}"""

    try:
        raw = call_llm(prompt)
        data = _parse_json_response(raw)
        sub_qs = data.get("sub_questions", [])
        return [q for q in sub_qs if q.strip()]
    except Exception as e:
        print(f"[decompose_query] LLM parse error: {e} — fallback về query gốc")
        return [query]


# =============================================================================
# 4. HyDE — Hypothetical Document Embeddings
# Mục tiêu: bridge vocabulary gap giữa query (informal) và doc (formal)
# bằng cách embed đoạn văn giả thay vì embed query trực tiếp
# Trigger: score sau probe trong vùng [HYDE_LOW, HYDE_HIGH]
# =============================================================================

def needs_hyde(probe_chunks: List[Dict[str, Any]]) -> bool:
    """
    Trigger HyDE khi max similarity score sau probe nằm trong
    vùng mơ hồ [HYDE_LOW, HYDE_HIGH]:
      - Không đủ cao để tự tin (< HYDE_HIGH)
      - Không đủ thấp để abstain (>= ABSTAIN_THRESHOLD)

    Ý nghĩa: retriever đang tìm được gì đó nhưng không chắc chắn,
    có thể do query informal không khớp văn phong doc formal.

    Args:
        probe_chunks: Kết quả probe retrieve đã có score
    """
    if not probe_chunks:
        return False
    max_score = max(c.get("score", 0) for c in probe_chunks)
    return HYDE_LOW <= max_score < HYDE_HIGH


def generate_hypothetical_doc(query: str, call_llm: Callable[[str], str]) -> str:
    """
    Dùng LLM sinh đoạn văn giả — đoạn văn này viết theo văn phong
    của tài liệu chính sách nội bộ, như thể đây là câu trả lời
    trong một policy document thực sự.

    Mục đích: embedding của đoạn văn giả gần với doc thật hơn
    embedding của query ngắn / informal.

    Args:
        query:    Câu hỏi cần trả lời
        call_llm: Hàm gọi LLM

    Returns:
        Đoạn văn giả (hypothetical document passage), ~2-4 câu
    """
    prompt = f"""Write a short passage (2-4 sentences) as if it were an excerpt from
an internal company policy or procedure document that answers the question below.
Use formal, policy-style language. Do not say "hypothetically" or "imagine".

Question: {query}

Output the passage directly, no JSON, no explanation."""

    try:
        return call_llm(prompt).strip()
    except Exception as e:
        print(f"[generate_hypothetical_doc] LLM error: {e} — fallback về query gốc")
        return query


def hyde_retrieve(
    query: str,
    call_llm: Callable[[str], str],
    get_embedding: Callable[[str], List[float]],
    retrieve_by_embedding: Callable[[List[float], int], List[Dict[str, Any]]],
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Full HyDE pipeline:
      1. Generate hypothetical document passage
      2. Embed passage (không embed query gốc)
      3. Retrieve bằng hypothetical embedding

    Args:
        query:                 Câu hỏi gốc
        call_llm:              Hàm gọi LLM
        get_embedding:         Hàm embed text -> vector (từ index.py)
        retrieve_by_embedding: Hàm retrieve với embedding vector trực tiếp
                               signature: (embedding: List[float], top_k: int) -> chunks
        top_k:                 Số chunks muốn lấy

    Returns:
        List chunks retrieved bằng hypothetical embedding

    Gợi ý implement retrieve_by_embedding trong rag_answer.py:
        def retrieve_by_embedding(embedding, top_k=10):
            import chromadb
            from index import CHROMA_DB_DIR
            client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
            collection = client.get_collection("rag_lab")
            results = collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            # parse và return như retrieve_dense()
    """
    hypo_doc = generate_hypothetical_doc(query, call_llm)
    print(f"[HyDE] Hypothetical doc: {hypo_doc[:100]}...")

    hypo_embedding = get_embedding(hypo_doc)
    chunks = retrieve_by_embedding(hypo_embedding, top_k)
    return chunks


# =============================================================================
# DEDUPLICATION
# Merge chunks từ nhiều retrieval calls, loại bỏ trùng lặp theo text
# =============================================================================

def deduplicate_chunks(
    chunk_lists: List[List[Dict[str, Any]]],
    max_chunks: int = 10,
) -> List[Dict[str, Any]]:
    """
    Merge nhiều list chunks và dedup theo nội dung text.
    Giữ thứ tự: chunk xuất hiện trước (rank cao hơn) được ưu tiên.

    Args:
        chunk_lists: List của các list chunks (từ nhiều retrieve calls)
        max_chunks:  Số chunk tối đa trả về sau dedup

    Returns:
        Flat list chunks đã dedup, tối đa max_chunks phần tử
    """
    seen: set = set()
    merged: List[Dict[str, Any]] = []

    for chunk_list in chunk_lists:
        for chunk in chunk_list:
            # Dùng 80 ký tự đầu làm key dedup (đủ để phân biệt, chịu được whitespace nhỏ)
            key = chunk.get("text", "")[:80].strip()
            if key and key not in seen:
                seen.add(key)
                merged.append(chunk)
                if len(merged) >= max_chunks:
                    return merged

    return merged


# =============================================================================
# ORCHESTRATOR — apply_query_transformations()
# Entry point duy nhất cho rag_answer.py gọi vào
# =============================================================================

def apply_query_transformations(
    query: str,
    retrieve_fn: Callable[[str, int], List[Dict[str, Any]]],
    call_llm: Callable[[str], str],
    get_embedding: Optional[Callable[[str], List[float]]] = None,
    retrieve_by_embedding: Optional[Callable[[List[float], int], List[Dict[str, Any]]]] = None,
    top_k: int = 10,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Orchestrate toàn bộ query transformation pipeline.
    Tự động quyết định kỹ thuật nào áp dụng dựa trên trigger conditions.

    Args:
        query:                 Câu hỏi gốc
        retrieve_fn:           Hàm retrieve chuẩn: (query_str, top_k) -> chunks
        call_llm:              Hàm gọi LLM: (prompt) -> str
        get_embedding:         Hàm embed text (cần cho HyDE, optional)
        retrieve_by_embedding: Hàm retrieve bằng vector (cần cho HyDE, optional)
        top_k:                 Số chunks mỗi retrieve call
        verbose:               In debug log

    Returns:
        Dict với:
          - "chunks":      List chunks đã dedup, sẵn sàng đưa vào prompt
          - "techniques":  List tên kỹ thuật đã áp dụng (để log vào grading_run.json)
          - "queries":     Tất cả query variants đã dùng để retrieve

    Flow:
        query
          │
          ├─ needs_expansion?   → expand_query()   → retrieve mỗi variant
          ├─ needs_stepback?    → stepback_query()  → retrieve abstract
          ├─ Probe retrieve (top-6)
          │       ├─ needs_decomposition? → decompose_query() → retrieve mỗi sub-q
          │       └─ needs_hyde?          → hyde_retrieve()
          └─ deduplicate_chunks() → trả về top max_chunks
    """
    techniques_used: List[str] = []
    all_queries: List[str] = [query]
    chunk_lists: List[List[Dict[str, Any]]] = []

    # -------------------------------------------------------------------------
    # Bước 1: Query Expansion
    # -------------------------------------------------------------------------
    if needs_expansion(query):
        if verbose:
            print(f"[QueryTrans] Trigger: EXPANSION (query={repr(query)})")
        expanded = expand_query(query, call_llm)
        all_queries = expanded  # gồm cả query gốc
        techniques_used.append("expansion")
    else:
        expanded = [query]

    # -------------------------------------------------------------------------
    # Bước 2: Step-back
    # -------------------------------------------------------------------------
    if needs_stepback(query):
        if verbose:
            print(f"[QueryTrans] Trigger: STEP-BACK")
        abstract = stepback_query(query, call_llm)
        if abstract != query and abstract not in all_queries:
            all_queries.append(abstract)
        techniques_used.append("stepback")

    # -------------------------------------------------------------------------
    # Bước 3: Retrieve mỗi query variant từ bước 1 + 2
    # -------------------------------------------------------------------------
    for q in all_queries:
        chunks = retrieve_fn(q, top_k)
        chunk_lists.append(chunks)

    # -------------------------------------------------------------------------
    # Bước 4: Probe — dùng kết quả retrieve của query gốc để quyết định
    # -------------------------------------------------------------------------
    probe_chunks = chunk_lists[0] if chunk_lists else []

    # -------------------------------------------------------------------------
    # Bước 5: Query Decomposition (multi-hop)
    # -------------------------------------------------------------------------
    if needs_decomposition(probe_chunks):
        if verbose:
            unique_srcs = {c.get("metadata", {}).get("source", "") for c in probe_chunks[:4]}
            print(f"[QueryTrans] Trigger: DECOMPOSITION (sources={unique_srcs})")
        sub_questions = decompose_query(query, call_llm)
        for sub_q in sub_questions:
            if sub_q not in all_queries:
                all_queries.append(sub_q)
                chunk_lists.append(retrieve_fn(sub_q, top_k))
        techniques_used.append("decomposition")

    # -------------------------------------------------------------------------
    # Bước 6: HyDE (nếu có get_embedding và retrieve_by_embedding)
    # -------------------------------------------------------------------------
    if needs_hyde(probe_chunks):
        if get_embedding is not None and retrieve_by_embedding is not None:
            if verbose:
                max_score = max((c.get("score", 0) for c in probe_chunks), default=0)
                print(f"[QueryTrans] Trigger: HYDE (max_score={max_score:.3f})")
            hyde_chunks = hyde_retrieve(
                query, call_llm, get_embedding, retrieve_by_embedding, top_k
            )
            chunk_lists.append(hyde_chunks)
            techniques_used.append("hyde")
        else:
            if verbose:
                print("[QueryTrans] HYDE trigger nhưng get_embedding/retrieve_by_embedding chưa được truyền vào")

    # -------------------------------------------------------------------------
    # Bước 7: Dedup + merge
    # -------------------------------------------------------------------------
    final_chunks = deduplicate_chunks(chunk_lists, max_chunks=top_k)

    if verbose:
        print(f"[QueryTrans] Techniques applied: {techniques_used or ['none']}")
        print(f"[QueryTrans] Total queries used: {len(all_queries)}")
        print(f"[QueryTrans] Chunks after dedup: {len(final_chunks)}")

    return {
        "chunks": final_chunks,
        "techniques": techniques_used,
        "queries": all_queries,
    }


# =============================================================================
# QUICK TEST — python query_trans.py
# =============================================================================

if __name__ == "__main__":
    print("=== Query Transformation — Trigger Check ===\n")

    test_cases = [
        ("nghỉ đẻ",                        "expansion (short + informal)"),
        ("Lỗi ERR-403-AUTH khi gọi API",   "stepback (error code pattern)"),
        ("P1 escalation ngoai gio hanh chinh va cap quyen tam thoi", "decomposition (multi-topic, needs probe)"),
        ("Chinh sach hoan tien v4.2",       "stepback (version number)"),
        ("SLA P1?",                         "expansion (2 words only)"),
    ]

    print(f"{'Query':<50} {'Expected Trigger':<35} {'Expansion':^10} {'Stepback':^10}")
    print("-" * 110)
    for q, expected in test_cases:
        exp = needs_expansion(q)
        sb  = needs_stepback(q)
        print(f"{q:<50} {expected:<35} {str(exp):^10} {str(sb):^10}")

    print("\n[INFO] needs_decomposition() và needs_hyde() cần probe_chunks từ retrieve thực tế.")
    print("[INFO] Chạy apply_query_transformations() với retrieve_fn và call_llm thực để test đầy đủ.")
