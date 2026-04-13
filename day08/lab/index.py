"""
index.py — Sprint 1: Build RAG Index
====================================
Mục tiêu Sprint 1 (60 phút):
  - Đọc và preprocess tài liệu từ data/docs/
  - Chunk tài liệu theo cấu trúc tự nhiên (heading/section)
  - Gắn metadata: source, section, department, effective_date, access
  - Embed và lưu vào vector store (ChromaDB)

Definition of Done Sprint 1:
  ✓ Script chạy được và index đủ docs
  ✓ Có ít nhất 3 metadata fields hữu ích cho retrieval
  ✓ Có thể kiểm tra chunk bằng list_chunks()
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

# TODO Sprint 1: Điều chỉnh chunk size và overlap theo quyết định của nhóm
# Gợi ý từ slide: chunk 300-500 tokens, overlap 50-80 tokens
CHUNK_SIZE = 400       # tokens (ước lượng bằng số ký tự / 4)
CHUNK_OVERLAP = 80     # tokens overlap giữa các chunk

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
LOCAL_EMBEDDING_MODEL = os.getenv(
    "LOCAL_EMBEDDING_MODEL",
    "paraphrase-multilingual-MiniLM-L12-v2",
)


# =============================================================================
# STEP 1: PREPROCESS
# Làm sạch text trước khi chunk và embed
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    """
    Preprocess một tài liệu: extract metadata từ header và làm sạch nội dung.

    Args:
        raw_text: Toàn bộ nội dung file text
        filepath: Đường dẫn file để làm source mặc định

    Returns:
        Dict chứa:
          - "text": nội dung đã clean
          - "metadata": dict với source, department, effective_date, access

    TODO Sprint 1:
    - Extract metadata từ dòng đầu file (Source, Department, Effective Date, Access)
    - Bỏ các dòng header metadata khỏi nội dung chính
    - Normalize khoảng trắng, xóa ký tự rác

    Gợi ý: dùng regex để parse dòng "Key: Value" ở đầu file.
    """
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }
    content_lines = []
    header_done = False

    for line in lines:
        if not header_done:
            # TODO: Parse metadata từ các dòng "Key: Value"
            # Ví dụ: "Source: policy/refund-v4.pdf" → metadata["source"] = "policy/refund-v4.pdf"
            if line.startswith("Source:"):
                metadata["source"] = line.replace("Source:", "").strip()
            elif line.startswith("Department:"):
                metadata["department"] = line.replace("Department:", "").strip()
            elif line.startswith("Effective Date:"):
                metadata["effective_date"] = line.replace("Effective Date:", "").strip()
            elif line.startswith("Access:"):
                metadata["access"] = line.replace("Access:", "").strip()
            elif line.startswith("==="):
                # Gặp section heading đầu tiên → kết thúc header
                header_done = True
                content_lines.append(line)
            elif line.strip() == "" or line.isupper():
                # Dòng tên tài liệu (toàn chữ hoa) hoặc dòng trống
                continue
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)

    # TODO: Thêm bước normalize text nếu cần
    # Gợi ý: bỏ ký tự đặc biệt thừa, chuẩn hóa dấu câu
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)  # max 2 dòng trống liên tiếp

    return {
        "text": cleaned_text,
        "metadata": metadata,
    }


# =============================================================================
# STEP 2: CHUNK
# Chia tài liệu thành các đoạn nhỏ theo cấu trúc tự nhiên
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Chunk một tài liệu đã preprocess thành danh sách các chunk nhỏ.

    Args:
        doc: Dict với "text" và "metadata" (output của preprocess_document)

    Returns:
        List các Dict, mỗi dict là một chunk với:
          - "text": nội dung chunk
          - "metadata": metadata gốc + "section" của chunk đó

    TODO Sprint 1:
    1. Split theo heading "=== Section ... ===" hoặc "=== Phần ... ===" trước
    2. Nếu section quá dài (> CHUNK_SIZE * 4 ký tự), split tiếp theo paragraph
    3. Thêm overlap: lấy đoạn cuối của chunk trước vào đầu chunk tiếp theo
    4. Mỗi chunk PHẢI giữ metadata đầy đủ từ tài liệu gốc

    Gợi ý: Ưu tiên cắt tại ranh giới tự nhiên (section, paragraph)
    thay vì cắt theo token count cứng.
    """
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []

    # TODO: Implement chunking theo section heading
    # Bước 1: Split theo heading pattern "=== ... ==="
    sections = re.split(r"(===.*?===)", text)

    current_section = "General"
    current_section_text = ""

    for part in sections:
        if re.match(r"===.*?===", part):
            # Lưu section trước (nếu có nội dung)
            if current_section_text.strip():
                section_chunks = _split_by_size(
                    current_section_text.strip(),
                    base_metadata=base_metadata,
                    section=current_section,
                )
                chunks.extend(section_chunks)
            # Bắt đầu section mới
            current_section = part.strip("= ").strip()
            current_section_text = ""
        else:
            current_section_text += part

    # Lưu section cuối cùng
    if current_section_text.strip():
        section_chunks = _split_by_size(
            current_section_text.strip(),
            base_metadata=base_metadata,
            section=current_section,
        )
        chunks.extend(section_chunks)

    return chunks


def _soft_break_end(text: str, start: int, end: int) -> int:
    """Giảm `end` về ranh giới tự nhiên gần nhất (không nhỏ hơn start + 50% chunk)."""
    window = text[start:end]
    min_end = start + max(80, (end - start) // 2)
    for sep in ("\n\n", "\n", ". ", ": ", "; ", " "):
        pos = window.rfind(sep)
        if pos != -1:
            cand = start + pos + len(sep)
            if cand >= min_end:
                return cand
    return end


def _split_by_size(
    text: str,
    base_metadata: Dict,
    section: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    """
    Split theo paragraph trước, ghép đến gần chunk_chars; đoạn quá dài cắt mềm.
    Chunk kế tiếp lấy overlap từ đuôi chunk trước.
    """
    text = text.strip()
    if not text:
        return []

    meta = {**base_metadata, "section": section}

    if len(text) <= chunk_chars:
        return [{"text": text, "metadata": meta}]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    out: List[Dict[str, Any]] = []
    buf: List[str] = []

    def buf_len() -> int:
        if not buf:
            return 0
        return sum(len(x) + 2 for x in buf) - 2

    def flush_buf() -> None:
        if not buf:
            return
        out.append({"text": "\n\n".join(buf), "metadata": {**meta}})
        buf.clear()

    i = 0
    while i < len(paragraphs):
        p = paragraphs[i]

        if len(p) > chunk_chars:
            flush_buf()
            s = 0
            while s < len(p):
                e = min(s + chunk_chars, len(p))
                if e < len(p):
                    e = _soft_break_end(p, s, e)
                piece = p[s:e].strip()
                if piece:
                    out.append({"text": piece, "metadata": {**meta}})
                if e >= len(p):
                    break
                s = max(s + 1, e - overlap_chars)
            i += 1
            continue

        extra = len(p) + (2 if buf else 0)
        if buf and buf_len() + extra > chunk_chars:
            flush_buf()
            if out:
                tail = out[-1]["text"]
                ov = tail[-overlap_chars:] if len(tail) > overlap_chars else tail
                buf = [ov, p] if ov.strip() else [p]
            else:
                buf = [p]
        else:
            buf.append(p)
        i += 1

    flush_buf()
    return out


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

def _metadata_for_chroma(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Chroma chỉ chấp nhận scalar: str, int, float, bool."""
    out: Dict[str, Any] = {}
    for k, v in meta.items():
        if v is None:
            out[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text.

    Option A — OpenAI (EMBEDDING_PROVIDER=openai): text-embedding-3-small
    Option B — Local (EMBEDDING_PROVIDER=local): sentence-transformers
    """
    if not text or not text.strip():
        raise ValueError("get_embedding: empty text")

    if EMBEDDING_PROVIDER == "local":
        from sentence_transformers import SentenceTransformer

        if not hasattr(get_embedding, "_st_model"):
            setattr(
                get_embedding,
                "_st_model",
                SentenceTransformer(LOCAL_EMBEDDING_MODEL),
            )
        model = getattr(get_embedding, "_st_model")
        return model.encode(text, normalize_embeddings=True).tolist()

    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai. "
            "Set EMBEDDING_PROVIDER=local for offline embeddings."
        )

    if not hasattr(get_embedding, "_oa_client"):
        setattr(get_embedding, "_oa_client", OpenAI(api_key=api_key))
    client = getattr(get_embedding, "_oa_client")

    response = client.embeddings.create(
        input=text,
        model=OPENAI_EMBEDDING_MODEL,
    )
    from run_telemetry import get_telemetry

    tel = get_telemetry()
    if tel is not None:
        tel.add_embedding_usage(response.usage)
    return list(response.data[0].embedding)


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc docs → preprocess → chunk → embed → store.
    """
    import chromadb
    from tqdm import tqdm

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(db_dir))
    try:
        client.delete_collection("rag_lab")
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"},
    )

    doc_files = sorted(docs_dir.glob("*.txt"))
    if not doc_files:
        print(f"Không tìm thấy file .txt trong {docs_dir}")
        return

    from run_telemetry import RunTelemetry, telemetry_ctx

    _itel = RunTelemetry("index_build", label="rag_lab")
    _itok = telemetry_ctx.set(_itel)
    all_ids: List[str] = []
    try:
        all_embeddings: List[List[float]] = []
        all_documents: List[str] = []
        all_metadatas: List[Dict[str, Any]] = []

        all_ids.clear()
        global_idx = 0
        for filepath in doc_files:
            print(f"  Processing: {filepath.name}")
            raw_text = filepath.read_text(encoding="utf-8")
            doc = preprocess_document(raw_text, str(filepath))
            chunks = chunk_document(doc)
            print(f"    → {len(chunks)} chunks")

            for chunk in chunks:
                emb = get_embedding(chunk["text"])
                cid = f"{filepath.stem}_{global_idx}"
                global_idx += 1
                all_ids.append(cid)
                all_embeddings.append(emb)
                all_documents.append(chunk["text"])
                all_metadatas.append(_metadata_for_chroma(chunk["metadata"]))

        batch_size = 32
        for start in tqdm(
            range(0, len(all_ids), batch_size),
            desc="Upsert ChromaDB",
            unit="batch",
        ):
            batch = slice(start, start + batch_size)
            collection.upsert(
                ids=all_ids[batch],
                embeddings=all_embeddings[batch],
                documents=all_documents[batch],
                metadatas=all_metadatas[batch],
            )

        print(f"\nHoàn thành! Tổng số chunks đã index: {len(all_ids)}")

        try:
            from rag_answer import clear_bm25_cache

            clear_bm25_cache()
        except Exception:
            pass
    finally:
        telemetry_ctx.reset(_itok)
        _ient = _itel.finish(
            {
                "num_chunks": len(all_ids),
                "num_doc_files": len(doc_files),
                "slide_note": "ROI slide: embedding/API cost + latency — xem logs/runs.jsonl",
            }
        )
        print(
            f"[telemetry] index_build: {_ient['duration_ms']:.0f} ms, "
            f"cost ~ ${_ient['cost_usd']['total_usd']:.4f} (chủ yếu embedding) → logs/runs.jsonl"
        )


# =============================================================================
# STEP 4: INSPECT / KIỂM TRA
# Dùng để debug và kiểm tra chất lượng index
# =============================================================================

def list_chunks(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    """
    In ra n chunk đầu tiên trong ChromaDB để kiểm tra chất lượng index.

    TODO Sprint 1:
    Implement sau khi hoàn thành build_index().
    Kiểm tra:
    - Chunk có giữ đủ metadata không? (source, section, effective_date)
    - Chunk có bị cắt giữa điều khoản không?
    - Metadata effective_date có đúng không?
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(limit=n, include=["documents", "metadatas"])

        print(f"\n=== Top {n} chunks trong index ===\n")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"[Chunk {i+1}]")
            print(f"  Source: {meta.get('source', 'N/A')}")
            print(f"  Section: {meta.get('section', 'N/A')}")
            print(f"  Effective Date: {meta.get('effective_date', 'N/A')}")
            print(f"  Text preview: {doc[:120]}...")
            print()
    except Exception as e:
        print(f"Lỗi khi đọc index: {e}")
        print("Hãy chạy build_index() trước.")


def inspect_metadata_coverage(db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Kiểm tra phân phối metadata trong toàn bộ index.

    Checklist Sprint 1:
    - Mọi chunk đều có source?
    - Có bao nhiêu chunk từ mỗi department?
    - Chunk nào thiếu effective_date?

    TODO: Implement sau khi build_index() hoàn thành.
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["metadatas"])

        print(f"\nTổng chunks: {len(results['metadatas'])}")

        # TODO: Phân tích metadata
        # Đếm theo department, kiểm tra effective_date missing, v.v.
        departments = {}
        missing_date = 0
        for meta in results["metadatas"]:
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1

        print("Phân bố theo department:")
        for dept, count in departments.items():
            print(f"  {dept}: {count} chunks")
        print(f"Chunks thiếu effective_date: {missing_date}")

    except Exception as e:
        print(f"Lỗi: {e}. Hãy chạy build_index() trước.")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Sprint 1: Build RAG Index")
    print("=" * 60)

    doc_files = sorted(DOCS_DIR.glob("*.txt"))
    print(f"\nTìm thấy {len(doc_files)} tài liệu:")
    for f in doc_files:
        print(f"  - {f.name}")

    print("\n--- Test preprocess + chunking (1 file) ---")
    if doc_files:
        filepath = doc_files[0]
        raw = filepath.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(filepath))
        chunks = chunk_document(doc)
        print(f"\nFile: {filepath.name}")
        print(f"  Metadata: {doc['metadata']}")
        print(f"  Số chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n  [Chunk {i+1}] Section: {chunk['metadata']['section']}")
            print(f"  Text: {chunk['text'][:150]}...")

    if len(sys.argv) > 1 and sys.argv[1] == "build":
        print("\n--- Build Full Index (embed + ChromaDB) ---")
        build_index()
        list_chunks(n=5)
        inspect_metadata_coverage()
    else:
        print("\nChạy `python index.py build` để embed và lưu ChromaDB (cần API key hoặc EMBEDDING_PROVIDER=local).")
