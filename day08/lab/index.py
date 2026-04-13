"""
index.py — Sprint 1 (ENHANCED): Contextual Chunking + Alias Injection
======================================================================
CẢI TIẾN SO VỚI BASELINE:
  1. **Contextual Chunking** (Anthropic, Oct 2024):
     Mỗi chunk được làm giàu bằng 1-2 câu ngữ cảnh sinh bởi LLM,
     đặt vào đầu chunk trước khi embed. Cải thiện recall ~35%.

  2. **Alias Injection**:
     Tài liệu có tên cũ (e.g. "Approval Matrix") được inject tên alias
     vào đầu content text — giúp BM25 match alias queries (q07).

  3. **Version-aware metadata**:
     Thêm trường `version` vào metadata để hỗ trợ temporal scoping.

Definition of Done Sprint 1:
  ✓ python index.py chạy không lỗi, tạo ra ChromaDB index
  ✓ Mỗi chunk có ít nhất 3 metadata fields (source, section, effective_date)
  ✓ list_chunks() hoạt động
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

CHUNK_SIZE = 400       # tokens (~1600 ký tự)
CHUNK_OVERLAP = 80

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")

# Bật/tắt Contextual Chunking (cần LLM → chậm hơn khi index)
ENABLE_CONTEXTUAL_CHUNKING = os.getenv("CONTEXTUAL_CHUNKING", "false").lower() == "true"

_embedding_model = None

# Alias map: filename → aliases & version info
# Dùng để inject alias text vào đầu chunk cho BM25 match
DOCUMENT_ALIASES: Dict[str, Dict] = {
    "access_control_sop.txt": {
        "aliases": ["Approval Matrix for System Access", "Approval Matrix", "Access Control"],
        "version": "",
    },
    "sla_p1_2026.txt": {
        "aliases": ["SLA ticket", "SLA P1", "quy định xử lý sự cố"],
        "version": "v2026.1",
    },
    "policy_refund_v4.txt": {
        "aliases": ["refund policy", "hoàn tiền", "chính sách hoàn trả v4"],
        "version": "v4",
    },
    "hr_leave_policy.txt": {
        "aliases": ["leave policy", "nghỉ phép 2026", "remote work policy"],
        "version": "2026",
    },
    "it_helpdesk_faq.txt": {
        "aliases": ["helpdesk FAQ", "câu hỏi IT thường gặp"],
        "version": "2026",
    },
}


# =============================================================================
# STEP 1: PREPROCESS
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    """
    Preprocess tài liệu: extract metadata + inject alias hint vào đầu content.
    """
    lines = raw_text.strip().split("\n")
    filename = Path(filepath).name
    alias_info = DOCUMENT_ALIASES.get(filename, {})

    metadata = {
        "source": Path(filepath).name,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
        "version": alias_info.get("version", ""),
        # aliases lưu dạng string (ChromaDB không hỗ trợ list)
        "aliases": " | ".join(alias_info.get("aliases", [])),
    }

    content_lines = []
    header_done = False

    for line in lines:
        stripped = line.strip()
        if not header_done:
            if stripped.startswith("Source:"):
                metadata["source"] = stripped.replace("Source:", "").strip()
            elif stripped.startswith("Department:"):
                metadata["department"] = stripped.replace("Department:", "").strip()
            elif stripped.startswith("Effective Date:"):
                metadata["effective_date"] = stripped.replace("Effective Date:", "").strip()
            elif stripped.startswith("Access:"):
                metadata["access"] = stripped.replace("Access:", "").strip()
            elif stripped.startswith("==="):
                header_done = True
                content_lines.append(line)
            elif stripped == "" or stripped.isupper():
                continue
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    cleaned_text = re.sub(r" +\n", "\n", cleaned_text)

    # Inject alias hint vào đầu content (giúp BM25 match tên cũ)
    if alias_info.get("aliases"):
        aliases_str = ", ".join(alias_info["aliases"])
        alias_hint = f"[Tên khác của tài liệu này: {aliases_str}]\n\n"
        cleaned_text = alias_hint + cleaned_text

    return {
        "text": cleaned_text,
        "metadata": metadata,
        "full_text": cleaned_text,
    }


# =============================================================================
# STEP 2: CHUNK (Section-based + Paragraph fallback)
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Chunk theo section heading, fallback theo paragraph."""
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []

    sections = re.split(r"(===.*?===)", text, flags=re.DOTALL)
    current_section = "General"
    current_section_text = ""

    for part in sections:
        if re.match(r"===.*?===", part.strip()):
            if current_section_text.strip():
                chunks.extend(_split_by_size(
                    current_section_text.strip(),
                    base_metadata=base_metadata,
                    section=current_section,
                ))
            current_section = part.strip().strip("=").strip()
            current_section_text = ""
        else:
            current_section_text += part

    if current_section_text.strip():
        chunks.extend(_split_by_size(
            current_section_text.strip(),
            base_metadata=base_metadata,
            section=current_section,
        ))

    return chunks


def _split_by_size(
    text: str,
    base_metadata: Dict,
    section: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    """Split text dài theo paragraph với overlap."""
    if len(text) <= chunk_chars:
        return [{"text": text, "metadata": {**base_metadata, "section": section}}]

    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    chunks = []
    current_chunk_paras: List[str] = []
    current_len = 0
    overlap_buffer = ""

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > chunk_chars and current_chunk_paras:
            chunk_text = overlap_buffer + "\n\n".join(current_chunk_paras)
            chunks.append({"text": chunk_text.strip(), "metadata": {**base_metadata, "section": section}})
            tail = "\n\n".join(current_chunk_paras)
            overlap_buffer = tail[-overlap_chars:] + "\n\n" if len(tail) > overlap_chars else ""
            current_chunk_paras = [para]
            current_len = para_len
        else:
            current_chunk_paras.append(para)
            current_len += para_len

    if current_chunk_paras:
        chunk_text = overlap_buffer + "\n\n".join(current_chunk_paras)
        chunks.append({"text": chunk_text.strip(), "metadata": {**base_metadata, "section": section}})

    return chunks


# =============================================================================
# STEP 2.5: CONTEXTUAL PREFIX (Tùy chọn — cần LLM)
# Tham khảo: Anthropic Contextual Retrieval (Oct 2024)
# =============================================================================

def add_contextual_prefix(chunk: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    """
    Sinh 1-2 câu ngữ cảnh bằng LLM, thêm vào đầu chunk trước khi embed.
    Kỹ thuật: Contextual Retrieval (Anthropic, 2024).
    """
    chunk_text = chunk["text"]
    section = chunk["metadata"].get("section", "")

    prompt = (
        f"Tài liệu: {source_name} | Section: {section}\n"
        f"Đoạn văn:\n{chunk_text[:500]}\n\n"
        "Viết 1-2 câu ngắn (tối đa 40 từ, tiếng Việt) mô tả ngữ cảnh đoạn này "
        "trong tài liệu. Chỉ nêu ngữ cảnh, không diễn giải nội dung."
    )

    try:
        from rag_answer import call_llm
        prefix = call_llm(prompt).strip()
        enriched = chunk.copy()
        enriched["text"] = f"[Ngữ cảnh: {prefix}]\n\n{chunk_text}"
        enriched["metadata"] = {**chunk["metadata"], "has_ctx_prefix": "true"}
        return enriched
    except Exception as e:
        print(f"  [Contextual] Lỗi: {e} — dùng chunk gốc")
        return chunk


# =============================================================================
# STEP 3: EMBED + STORE
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """Tạo embedding vector (local Sentence Transformers hoặc OpenAI)."""
    global _embedding_model

    if EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding
    else:
        from sentence_transformers import SentenceTransformer
        if _embedding_model is None:
            model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
            print(f"  [Embedding] Loading: {model_name}")
            _embedding_model = SentenceTransformer(model_name)
        return _embedding_model.encode(text, normalize_embeddings=True).tolist()


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """Pipeline: đọc → preprocess → chunk → (contextual) → embed → store."""
    import chromadb
    from tqdm import tqdm

    print(f"Build index từ: {docs_dir}")
    print(f"Embedding: {EMBEDDING_PROVIDER} | Contextual: {'BẬT' if ENABLE_CONTEXTUAL_CHUNKING else 'TẮT'}")

    db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_dir))

    try:
        client.delete_collection("rag_lab")
        print("  → Xóa collection cũ")
    except Exception:
        pass

    collection = client.create_collection("rag_lab", metadata={"hnsw:space": "cosine"})

    total_chunks = 0
    for filepath in docs_dir.glob("*.txt"):
        print(f"\n  {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw_text, str(filepath))
        chunks = chunk_document(doc)
        print(f"    → {len(chunks)} chunks")

        if ENABLE_CONTEXTUAL_CHUNKING:
            source_name = doc["metadata"].get("source", filepath.name)
            chunks = [add_contextual_prefix(c, source_name)
                      for c in tqdm(chunks, desc="    Contextual", leave=False)]

        ids, embeddings, documents, metadatas = [], [], [], []
        for i, chunk in enumerate(tqdm(chunks, desc="    Embed", leave=False)):
            # Sanitize metadata (ChromaDB chỉ nhận str/int/float)
            safe_meta = {k: (v if isinstance(v, (str, int, float)) else str(v))
                         for k, v in chunk["metadata"].items()}
            ids.append(f"{filepath.stem}_{i:04d}")
            embeddings.append(get_embedding(chunk["text"]))
            documents.append(chunk["text"])
            metadatas.append(safe_meta)

        collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        total_chunks += len(chunks)
        print(f"    ✓ {len(chunks)} chunks indexed")

    print(f"\n✓ Tổng: {total_chunks} chunks | DB: {db_dir}")


# =============================================================================
# STEP 4: INSPECT
# =============================================================================

def list_chunks(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(limit=n, include=["documents", "metadatas"])
        print(f"\n=== Top {n} chunks ===")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"\n[{i+1}] src={meta.get('source')} | sect={meta.get('section', '')[:40]}")
            print(f"     dept={meta.get('department')} | date={meta.get('effective_date')}")
            print(f"     aliases={meta.get('aliases', '')[:60]}")
            print(f"     text: {doc[:120].replace(chr(10), ' ')}...")
    except Exception as e:
        print(f"Lỗi: {e} — chạy build_index() trước")


def inspect_metadata_coverage(db_dir: Path = CHROMA_DB_DIR) -> None:
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["metadatas"])
        total = len(results["metadatas"])
        print(f"\n=== Metadata Coverage ({total} chunks) ===")
        departments: Dict[str, int] = {}
        sources: Dict[str, int] = {}
        missing_date = 0
        for meta in results["metadatas"]:
            d = meta.get("department", "unknown")
            departments[d] = departments.get(d, 0) + 1
            s = meta.get("source", "")
            if s:
                sources[s] = sources.get(s, 0) + 1
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1
        for dept, cnt in sorted(departments.items()):
            print(f"  {dept}: {cnt}")
        for src, cnt in sorted(sources.items()):
            print(f"  {src}: {cnt}")
        print(f"  Thiếu effective_date: {missing_date}/{total}")
    except Exception as e:
        print(f"Lỗi: {e}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 1 (Enhanced): Build Index")
    print("=" * 60)

    doc_files = list(DOCS_DIR.glob("*.txt"))
    print(f"Tìm thấy {len(doc_files)} tài liệu")

    build_index()
    list_chunks(n=5)
    inspect_metadata_coverage()
    print("\n✓ Hoàn thành!")
